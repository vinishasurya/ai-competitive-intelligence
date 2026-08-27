"""Full research pipeline: URL -> profile -> discovery -> evidence -> report.

One call orchestrates the bounded workflow from design doc §10 and records the
run's status, cost, tokens, and tool calls on the runs row. Each stage soft-
fails; a failed stage marks the run failed with the error preserved.
"""

import sqlite3
import time
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.db import insert_row
from app.discovery import discover_competitors
from app.evidence import EvidenceSummary, collect_and_extract
from app.llm import Usage
from app.models import Competitor, Product, Run
from app.profiler import build_profile
from app.report import ReportResult, generate_report


class PipelineResult(BaseModel):
    ok: bool
    url: str
    run_id: int | None = None
    product_name: str | None = None
    category: str | None = None
    competitors: list[dict] = Field(default_factory=list)
    evidence: list[EvidenceSummary] = Field(default_factory=list)
    report: ReportResult | None = None
    cost_cents: float = 0.0
    total_tokens: int = 0
    tool_calls: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


def _finish_run(conn, run_id, status, cost_cents, tokens, tool_calls, error=None):
    conn.execute(
        "UPDATE runs SET status=?, finished_at=?, cost_cents=?, token_count=?, "
        "tool_calls=?, error=? WHERE id=?",
        (status, datetime.now(timezone.utc).isoformat(), round(cost_cents),
         tokens, tool_calls, error, run_id),
    )
    conn.commit()


def run_pipeline(
    conn: sqlite3.Connection, raw_url: str, on_progress=None
) -> PipelineResult:
    started = time.monotonic()
    result = PipelineResult(ok=False, url=raw_url)
    progress = on_progress or (lambda stage, detail: None)

    # Stage 1: profile
    progress("profiling", f"reading {raw_url} and building a product profile")
    prof = build_profile(raw_url)
    result.cost_cents += prof.cost_cents
    result.total_tokens += prof.input_tokens + prof.output_tokens
    if not prof.ok:
        result.error = f"profiling: {prof.error}"
        result.duration_seconds = time.monotonic() - started
        return result
    profile = prof.profile
    result.product_name, result.category = profile.name, profile.category

    product_id = insert_row(conn, "products", Product(
        url=prof.url, domain=profile.domain, name=profile.name,
        category=profile.category, profile=profile.model_dump(),
    ).to_row())
    run_id = insert_row(conn, "runs", Run(product_id=product_id, status="running").to_row())
    result.run_id = run_id

    # Stage 2: discovery
    progress("discovery", f"finding and verifying competitors of {profile.name}")
    disc = discover_competitors(profile)
    result.cost_cents += disc.cost_cents
    result.total_tokens += disc.input_tokens + disc.output_tokens
    result.tool_calls += disc.tool_calls
    if not disc.ok:
        result.error = f"discovery: {disc.error}"
        result.duration_seconds = time.monotonic() - started
        _finish_run(conn, run_id, "failed", result.cost_cents,
                    result.total_tokens, result.tool_calls, result.error)
        return result

    companies = [(None, profile.name, profile.domain)]
    for comp in disc.competitors:
        comp_id = insert_row(conn, "competitors", Competitor(
            run_id=run_id, name=comp.name, domain=comp.domain,
            relationship=comp.relationship, confidence=comp.confidence,
            discovery_methods=comp.discovery_methods, verified=True,
        ).to_row())
        companies.append((comp_id, comp.name, comp.domain))
        result.competitors.append({
            "name": comp.name, "domain": comp.domain,
            "relationship": comp.relationship, "confidence": comp.confidence,
            "why": comp.why_selected,
        })

    # Stage 3: evidence
    usage = Usage()
    for i, (comp_id, name, domain) in enumerate(companies, 1):
        progress("evidence", f"researching {name} ({i}/{len(companies)})")
        summary = collect_and_extract(conn, run_id, comp_id, name, domain, usage)
        result.evidence.append(summary)
        result.tool_calls += summary.pages_ok + summary.pages_failed
    result.cost_cents += usage.cost_cents
    result.total_tokens += usage.input_tokens + usage.output_tokens

    # Stage 4: report + validation
    report = generate_report(conn, run_id, on_progress=progress)
    result.report = report
    result.cost_cents += report.cost_cents
    result.total_tokens += report.input_tokens + report.output_tokens
    result.duration_seconds = time.monotonic() - started

    if not report.ok:
        result.error = f"report: {report.error}"
        _finish_run(conn, run_id, "failed", result.cost_cents,
                    result.total_tokens, result.tool_calls, result.error)
        return result

    result.ok = True
    _finish_run(conn, run_id, "completed", result.cost_cents,
                result.total_tokens, result.tool_calls)
    return result
