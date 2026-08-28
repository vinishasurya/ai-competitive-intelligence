"""Run the 10-product benchmark and publish results.

    cd backend && uv run python ../eval/run_eval.py --version v1 [--only a.com,b.com]

Writes eval/results/{version}.db (all run data), {version}.json,
{version}.md (results table), and {version}_manual_review.md (fixed
claim sample for citation-validity / hallucination review).
"""

import argparse
import json
import sys
from pathlib import Path

import json as _json
from datetime import datetime

from app.db import connect, init_db
from app.discovery import normalize_domain
from app.evaluation import (
    aggregate,
    evaluate_product,
    load_benchmark,
    record_eval_results,
)
from app.pipeline import PipelineResult, run_pipeline
from app.report import ReportResult, validate_run


def rebuild_result(conn, label) -> PipelineResult | None:
    """Reconstruct a PipelineResult from a previously completed run in the db,
    so --resume can score it without re-running the pipeline."""
    domain = normalize_domain(label.url)
    row = conn.execute(
        "SELECT r.*, p.category FROM runs r JOIN products p ON p.id = r.product_id "
        "WHERE p.domain LIKE ? AND r.status = 'completed' ORDER BY r.id DESC LIMIT 1",
        (f"%{domain}%",),
    ).fetchone()
    if row is None:
        return None
    run_id = row["id"]
    competitors = [
        {"name": c["name"], "domain": c["domain"]}
        for c in conn.execute(
            "SELECT name, domain FROM competitors WHERE run_id = ? AND verified = 1",
            (run_id,),
        ).fetchall()
    ]
    factual = sourced = 0
    for c in conn.execute(
        "SELECT claim_type, source_ids_json FROM claims WHERE run_id = ?", (run_id,)
    ).fetchall():
        if c["claim_type"] != "interpretation":
            factual += 1
            sourced += bool(_json.loads(c["source_ids_json"]))
    latency = (
        datetime.fromisoformat(row["finished_at"])
        - datetime.fromisoformat(row["started_at"])
    ).total_seconds()
    return PipelineResult(
        ok=True, url=label.url, run_id=run_id, category=row["category"],
        competitors=competitors,
        report=ReportResult(
            ok=True, run_id=run_id,
            citation_coverage=(sourced / factual) if factual else None,
            flags=validate_run(conn, run_id),
        ),
        cost_cents=row["cost_cents"], total_tokens=row["token_count"],
        tool_calls=row["tool_calls"], duration_seconds=latency,
    )

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"


def pct(x):
    return f"{x:.0%}" if x is not None else "n/a"


def write_markdown(version, evals, agg, path):
    lines = [
        f"# Benchmark results — {version}",
        "",
        f"{agg['completed']}/{agg['products']} products completed. "
        "Precision: strict = clearly-relevant only; lenient = not clearly irrelevant "
        "(defensible rubric). Pricing accuracy over "
        f"{agg['pricing_tiers_evaluated']} labeled tiers.",
        "",
        "| Product | Group | Category OK | Precision (strict/lenient) | "
        "Pricing | Citations | Flags | Latency | Cost |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for e in evals:
        if not e.ok:
            lines.append(f"| {e.url} | {e.group} | FAILED: {e.error} | | | | | | |")
            continue
        pricing = (f"{e.pricing_correct}/{e.pricing_evaluated}"
                   if e.pricing_evaluated else "—")
        lines.append(
            f"| {e.url} | {e.group} | {'✓' if e.category_ok else '✗'} "
            f"| {pct(e.strict_precision)} / {pct(e.lenient_precision)} "
            f"| {pricing} | {pct(e.citation_coverage)} | {e.flag_count} "
            f"| {e.latency_s:.0f}s | {e.cost_cents:.0f}¢ |"
        )
    lines += [
        "",
        "## Aggregate",
        "",
        "| Metric | Value |", "|---|---|",
        f"| Category accuracy | {pct(agg['category_accuracy'])} |",
        f"| Competitor precision (strict) | {pct(agg['competitor_precision_strict'])} |",
        f"| Competitor precision (lenient) | {pct(agg['competitor_precision_lenient'])} |",
        f"| Pricing accuracy | {pct(agg['pricing_accuracy'])} "
        f"({agg['pricing_tiers_evaluated']} tiers) |",
        f"| Citation coverage | {pct(agg['citation_coverage'])} |",
        f"| Validation flags (total) | {agg['total_validation_flags']} |",
        f"| Mean latency | {agg['mean_latency_s']}s |",
        f"| Mean cost / report | {agg['mean_cost_cents']}¢ |",
        "",
        "## Surfaced competitors and labels",
        "",
    ]
    for e in evals:
        if not e.ok:
            continue
        lines.append(f"**{e.url}** — category: {e.category}")
        for c in e.competitors:
            lines.append(f"- {c.name} ({c.domain}): {c.label}")
        for p in e.pricing:
            got = "" if p.got is None else f", got ${p.got}"
            lines.append(
                f"- pricing {p.domain} '{p.tier_contains}' expected "
                f"${p.expected}{got} -> {p.status}"
            )
        lines.append("")
    path.write_text("\n".join(lines))


def write_manual_review(version, conn, evals, path):
    lines = [
        f"# Manual review — {version}",
        "",
        "For each sampled claim, open the cited source(s) and mark:",
        "- **valid**: the cited source directly supports the claim",
        "- **invalid**: citation does not support the claim",
        "- **hallucination**: claim is contradicted by its cited source",
        "",
    ]
    for e in evals:
        if not e.ok:
            continue
        lines.append(f"## {e.url} (run {e.run_id})")
        sample = conn.execute(
            "SELECT c.section, c.text, c.source_ids_json FROM claims c "
            "WHERE c.run_id = ? AND c.claim_type != 'interpretation' "
            "AND c.section IN ('executive_summary','competitive_landscape',"
            "'pricing_comparison') GROUP BY c.section ORDER BY c.id",
            (e.run_id,),
        ).fetchall()
        for row in sample:
            urls = []
            for sid in json.loads(row["source_ids_json"]):
                src = conn.execute(
                    "SELECT url FROM sources WHERE id = ?", (sid,)
                ).fetchone()
                if src:
                    urls.append(src["url"])
            lines.append(f"- [ ] valid / [ ] invalid / [ ] hallucination — "
                         f"*{row['section']}*: {row['text']}")
            for u in urls:
                lines.append(f"  - {u}")
        lines.append("")
    path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--only", help="comma-separated product urls to run")
    parser.add_argument("--resume", action="store_true",
                        help="keep the existing db; skip products already completed")
    args = parser.parse_args()

    labels = load_benchmark(EVAL_DIR / "benchmark.json")
    if args.only:
        wanted = set(args.only.split(","))
        labels = [l for l in labels if l.url in wanted]

    RESULTS_DIR.mkdir(exist_ok=True)
    db_path = RESULTS_DIR / f"{args.version}.db"
    if not args.resume:
        db_path.unlink(missing_ok=True)
    conn = connect(db_path)
    init_db(conn)

    evals = []
    for i, label in enumerate(labels, 1):
        result = rebuild_result(conn, label) if args.resume else None
        if result is not None:
            print(f"[{i}/{len(labels)}] {label.url} ... (resumed from db)", flush=True)
        else:
            print(f"[{i}/{len(labels)}] {label.url} ...", flush=True)
            try:
                result = run_pipeline(conn, label.url)
            except Exception as exc:  # a crashed product must not kill the benchmark
                result = PipelineResult(ok=False, url=label.url,
                                        error=f"{type(exc).__name__}: {exc}")
        ev = evaluate_product(conn, label, result)
        if ev.run_id is not None:  # avoid duplicate metric rows on resume
            conn.execute("DELETE FROM eval_results WHERE run_id = ?", (ev.run_id,))
            conn.commit()
        record_eval_results(conn, ev)
        evals.append(ev)
        status = ("ok" if ev.ok else f"FAILED: {ev.error}")
        print(f"    {status}  precision={pct(ev.strict_precision)}/"
              f"{pct(ev.lenient_precision)}  citations={pct(ev.citation_coverage)}  "
              f"{ev.latency_s:.0f}s {ev.cost_cents:.0f}¢", flush=True)

    agg = aggregate(evals)
    (RESULTS_DIR / f"{args.version}.json").write_text(json.dumps({
        "version": args.version,
        "aggregate": agg,
        "products": [e.model_dump() for e in evals],
    }, indent=2))
    write_markdown(args.version, evals, agg, RESULTS_DIR / f"{args.version}.md")
    write_manual_review(args.version, conn, evals,
                        RESULTS_DIR / f"{args.version}_manual_review.md")
    conn.close()

    print("\nAGGREGATE:", json.dumps(agg, indent=2))
    print(f"\nResults: eval/results/{args.version}.md")


if __name__ == "__main__":
    main()
