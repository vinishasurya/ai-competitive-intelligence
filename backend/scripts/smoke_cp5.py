"""CP5 live smoke test: URL -> profile -> discovery -> stored sources+findings.

Runs the pipeline for each product into a real SQLite db, then verifies that
every finding row traces to stored source rows. Usage:

    uv run python scripts/smoke_cp5.py [product ...]
Defaults to linear.app notion.com tailscale.com; pass domains to run fewer.
"""

import json
import sys
from datetime import datetime, timezone

from app.db import DEFAULT_DB_PATH, connect, fetch_row, init_db, insert_row
from app.discovery import discover_competitors
from app.evidence import collect_and_extract
from app.llm import Usage
from app.models import Competitor, Product, Run
from app.profiler import build_profile

DB_PATH = DEFAULT_DB_PATH.parent / "data" / "smoke_cp5.db"


def run_product(conn, raw_url: str) -> float:
    print(f"\n{'=' * 64}\nPRODUCT: {raw_url}\n{'=' * 64}")
    prof = build_profile(raw_url)
    if not prof.ok:
        print(f"  profiling FAILED: {prof.error}")
        return 0.0
    profile = prof.profile
    print(f"  profile: {profile.name} — {profile.category}")

    product_id = insert_row(conn, "products", Product(
        url=prof.url, domain=profile.domain, name=profile.name,
        category=profile.category, profile=profile.model_dump(),
    ).to_row())
    run_id = insert_row(conn, "runs", Run(product_id=product_id, status="running").to_row())

    disc = discover_competitors(profile)
    if not disc.ok:
        print(f"  discovery FAILED: {disc.error}")
        return prof.cost_cents + disc.cost_cents

    usage = Usage()
    companies = [(None, profile.name, profile.domain)]
    for comp in disc.competitors:
        comp_id = insert_row(conn, "competitors", Competitor(
            run_id=run_id, name=comp.name, domain=comp.domain,
            relationship=comp.relationship, confidence=comp.confidence,
            discovery_methods=comp.discovery_methods, verified=True,
        ).to_row())
        companies.append((comp_id, comp.name, comp.domain))

    print(f"  collecting evidence for {len(companies)} companies...")
    for comp_id, name, domain in companies:
        s = collect_and_extract(conn, run_id, comp_id, name, domain, usage)
        status = f"pages {s.pages_ok} ok/{s.pages_failed} failed, {len(s.finding_ids)} findings"
        print(f"    {name:<14} {status}" + (f"  ERROR: {s.error}" if s.error else ""))

    total_cost = prof.cost_cents + disc.cost_cents + usage.cost_cents
    conn.execute(
        "UPDATE runs SET status='completed', finished_at=?, cost_cents=?, "
        "token_count=?, tool_calls=? WHERE id=?",
        (datetime.now(timezone.utc).isoformat(), round(total_cost),
         prof.input_tokens + prof.output_tokens + disc.input_tokens
         + disc.output_tokens + usage.input_tokens + usage.output_tokens,
         disc.tool_calls, run_id),
    )
    conn.commit()

    # Pricing spot-check output
    print(f"\n  PRICING extracted (run {run_id}):")
    rows = conn.execute(
        "SELECT f.competitor_id, f.value_json, f.source_ids_json FROM findings f "
        "WHERE f.run_id=? AND f.dimension='pricing'", (run_id,)
    ).fetchall()
    for row in rows:
        comp = fetch_row(conn, "competitors", row["competitor_id"]) if row["competitor_id"] else None
        who = comp["name"] if comp else profile.name
        value = json.loads(row["value_json"])
        srcs = json.loads(row["source_ids_json"])
        if value.get("available"):
            tiers = ", ".join(
                f"{t['name']}={t['price_text']}" for t in value["tiers"][:4]
            )
            print(f"    {who:<14} [src {srcs}] {tiers}")
        else:
            print(f"    {who:<14} [src {srcs}] UNAVAILABLE ({value.get('notes')})")

    print(f"  cost: profile {prof.cost_cents:.1f}¢ + discovery {disc.cost_cents:.1f}¢ "
          f"+ evidence {usage.cost_cents:.1f}¢ = {total_cost:.1f}¢")
    return total_cost


def integrity_check(conn) -> None:
    print(f"\n{'=' * 64}\nINTEGRITY CHECK: every finding traces to stored sources")
    findings = conn.execute("SELECT id, dimension, source_ids_json FROM findings").fetchall()
    dangling = 0
    for f in findings:
        for sid in json.loads(f["source_ids_json"]):
            if fetch_row(conn, "sources", sid) is None:
                dangling += 1
                print(f"  DANGLING: finding {f['id']} ({f['dimension']}) -> source {sid}")
    sources = conn.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"]
    print(f"  findings: {len(findings)}, sources: {sources}, dangling refs: {dangling}")
    print("  PASS" if dangling == 0 else "  FAIL")


def main() -> None:
    products = sys.argv[1:] or ["linear.app", "notion.com", "tailscale.com"]
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    conn = connect(DB_PATH)
    init_db(conn)
    total = sum(run_product(conn, p) for p in products)
    integrity_check(conn)
    print(f"\nTotal model cost this run: {total:.1f}¢\nDatabase: {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
