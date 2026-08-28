"""Report generation & validation — design doc §10 steps 6–7.

Each of the four report sections is generated from the run's stored findings
(never from model general knowledge) as structured claims: text, claim_type
(verified / reported / interpretation), source_ids, confidence. Claims are
stored in the claims table so citation coverage is computable, then a
deterministic validator flags problems before anything is displayed.
"""

import json
import sqlite3
from typing import Literal

from pydantic import BaseModel, Field

from app import config
from app.db import fetch_row, insert_row
from app.llm import Usage, parse
from app.models import Claim

SECTIONS = [
    "executive_summary",
    "competitive_landscape",
    "feature_comparison",
    "pricing_comparison",
]

SECTION_INSTRUCTIONS = {
    "executive_summary": (
        "Write a concise executive overview: what the subject product is and who it "
        "serves, the overall shape of its competitive landscape, and 1-2 key "
        "takeaways. Takeaways and landscape characterizations are interpretation."
    ),
    "competitive_landscape": (
        "One claim per competitor describing what it is and how it positions itself "
        "(verified, from that company's findings). You may add interpretation claims "
        "about how the field segments (e.g. incumbents vs open-source challengers)."
    ),
    "feature_comparison": (
        "Compare important capabilities across the subject and competitors using the "
        "features findings. State factual overlaps as verified claims citing both "
        "sides' sources; judgments about differentiation are interpretation."
    ),
    "pricing_comparison": (
        "Compare public pricing tiers, prices, and billing periods across companies "
        "using the pricing findings only. Where pricing is unavailable, state that "
        "explicitly. Value-for-money judgments are interpretation."
    ),
}

GENERATION_SYSTEM = """You write one section of a competitive intelligence report \
as structured, citable claims.

You receive a JSON evidence bundle: companies (the subject product and its \
competitors) with findings extracted from their own websites, and a sources \
index mapping source_ids to page URLs, types, and retrieval times.

Rules:
- Base every claim ONLY on the bundle. No outside knowledge, even about \
companies you recognize.
- claim_type:
  * verified: a fact directly stated in a finding extracted from the company's \
own website. Must cite that finding's source_ids.
  * reported: a fact supported only by a non-primary source. Rare here.
  * interpretation: analysis, synthesis, comparison judgments, or takeaways. \
ALL recommendations and judgments must be labeled interpretation, and must \
cite the source_ids of the evidence they rest on.
- Cite only source_ids that exist in the sources index. Never cite nothing on a \
verified or reported claim.
- Pricing facts must cite sources whose type is "pricing". If a company's \
pricing finding says unavailable, say so as a verified claim citing that \
finding's sources.
- Write 3-8 claims, each 1-2 specific, readable sentences. confidence is 0..1.
- Style: never use em dashes or en dashes in claim text. Use commas, colons, \
parentheses, or separate sentences instead."""


def _clean_text(text: str) -> str:
    """House style: no em/en dashes in user-facing generated text."""
    return (
        text.replace(" — ", ", ").replace("—", "-")
            .replace(" – ", ", ").replace("–", "-")
    )


# ---------- structured-output schemas ----------

class ClaimOut(BaseModel):
    text: str
    claim_type: Literal["verified", "reported", "interpretation"]
    source_ids: list[int] = Field(default_factory=list)
    confidence: float


class SectionClaims(BaseModel):
    claims: list[ClaimOut] = Field(default_factory=list)


class StoredClaim(BaseModel):
    id: int
    section: str
    text: str
    claim_type: str
    source_ids: list[int]
    confidence: float | None


class ValidationFlag(BaseModel):
    claim_id: int
    section: str
    flag: Literal[
        "factual_claim_without_sources",
        "dangling_source_id",
        "pricing_claim_without_pricing_source",
        "possible_unlabeled_interpretation",
    ]
    detail: str


class ReportResult(BaseModel):
    ok: bool
    run_id: int
    sections: dict[str, list[StoredClaim]] = Field(default_factory=dict)
    flags: list[ValidationFlag] = Field(default_factory=list)
    citation_coverage: float | None = None  # sourced factual claims / factual claims
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: float = 0.0
    error: str | None = None


# ---------- evidence bundle ----------

def load_bundle(conn: sqlite3.Connection, run_id: int) -> dict:
    run = fetch_row(conn, "runs", run_id)
    product = fetch_row(conn, "products", run["product_id"])

    def findings_for(competitor_id):
        cond = "competitor_id IS NULL" if competitor_id is None else "competitor_id = ?"
        args = (run_id,) if competitor_id is None else (run_id, competitor_id)
        rows = conn.execute(
            f"SELECT dimension, value_json, source_ids_json FROM findings "
            f"WHERE run_id = ? AND {cond}", args,
        ).fetchall()
        return [
            {
                "dimension": r["dimension"],
                "value": json.loads(r["value_json"]),
                "source_ids": json.loads(r["source_ids_json"]),
            }
            for r in rows
        ]

    companies = [{
        "name": product["name"],
        "domain": product["domain"],
        "role": "subject",
        "findings": findings_for(None),
    }]
    for comp in conn.execute(
        "SELECT * FROM competitors WHERE run_id = ? AND verified = 1", (run_id,)
    ).fetchall():
        companies.append({
            "name": comp["name"],
            "domain": comp["domain"],
            "role": "competitor",
            "relationship": comp["relationship"],
            "findings": findings_for(comp["id"]),
        })

    sources = {
        str(r["id"]): {
            "url": r["url"],
            "type": r["source_type"],
            "fetched_at": r["fetched_at"],
            "ok": r["http_status"] == 200,
        }
        for r in conn.execute(
            "SELECT id, url, source_type, fetched_at, http_status FROM sources "
            "WHERE run_id = ?", (run_id,),
        ).fetchall()
    }
    return {"subject": product["name"], "companies": companies, "sources": sources}


# ---------- generation ----------

def generate_section(section: str, bundle: dict, usage: Usage) -> SectionClaims:
    return parse(
        config.MODEL_PROFILER,
        GENERATION_SYSTEM,
        f"Section to write: {section}\n{SECTION_INSTRUCTIONS[section]}\n\n"
        f"Evidence bundle:\n{json.dumps(bundle)}",
        SectionClaims,
        usage,
        max_tokens=16000,
    )


def generate_report(
    conn: sqlite3.Connection, run_id: int, on_progress=None
) -> ReportResult:
    usage = Usage()
    progress = on_progress or (lambda stage, detail: None)
    bundle = load_bundle(conn, run_id)
    sections: dict[str, list[StoredClaim]] = {}
    try:
        for section in SECTIONS:
            progress("report", f"writing {section.replace('_', ' ')}")
            result = generate_section(section, bundle, usage)
            stored = []
            for claim in result.claims:
                claim = claim.model_copy(update={"text": _clean_text(claim.text)})
                claim_id = insert_row(conn, "claims", Claim(
                    run_id=run_id, section=section, text=claim.text,
                    claim_type=claim.claim_type, source_ids=claim.source_ids,
                    confidence=claim.confidence,
                ).to_row())
                stored.append(StoredClaim(
                    id=claim_id, section=section, text=claim.text,
                    claim_type=claim.claim_type, source_ids=claim.source_ids,
                    confidence=claim.confidence,
                ))
            sections[section] = stored
    except Exception as exc:
        return ReportResult(
            ok=False, run_id=run_id, sections=sections,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
            cost_cents=usage.cost_cents,
            error=f"generation failed in {section}: {type(exc).__name__}: {exc}",
        )

    flags = validate_run(conn, run_id)
    factual = [c for cs in sections.values() for c in cs if c.claim_type != "interpretation"]
    coverage = (
        sum(1 for c in factual if c.source_ids) / len(factual) if factual else None
    )
    return ReportResult(
        ok=True, run_id=run_id, sections=sections, flags=flags,
        citation_coverage=coverage,
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        cost_cents=usage.cost_cents,
    )


# ---------- report payload for the UI / shareable link ----------

def report_payload(conn: sqlite3.Connection, run_id: int) -> dict | None:
    """Everything the report page needs, assembled from stored rows."""
    run = fetch_row(conn, "runs", run_id)
    if run is None:
        return None
    product = fetch_row(conn, "products", run["product_id"])

    sections: dict[str, list[dict]] = {s: [] for s in SECTIONS}
    factual = sourced = 0
    for row in conn.execute(
        "SELECT * FROM claims WHERE run_id = ? ORDER BY id", (run_id,)
    ).fetchall():
        source_ids = json.loads(row["source_ids_json"])
        if row["claim_type"] != "interpretation":
            factual += 1
            sourced += bool(source_ids)
        sections.setdefault(row["section"], []).append({
            "id": row["id"], "text": _clean_text(row["text"]),
            "claim_type": row["claim_type"],
            "source_ids": source_ids, "confidence": row["confidence"],
        })

    competitors = [
        {
            "id": r["id"], "name": r["name"], "domain": r["domain"],
            "relationship": r["relationship"], "confidence": r["confidence"],
            "discovery_methods": json.loads(r["discovery_methods_json"]),
        }
        for r in conn.execute(
            "SELECT * FROM competitors WHERE run_id = ? AND verified = 1", (run_id,)
        ).fetchall()
    ]
    sources = {
        str(r["id"]): {
            "url": r["url"], "source_type": r["source_type"],
            "fetched_at": r["fetched_at"], "ok": r["http_status"] == 200,
        }
        for r in conn.execute(
            "SELECT id, url, source_type, fetched_at, http_status FROM sources "
            "WHERE run_id = ?", (run_id,),
        ).fetchall()
    }

    # Structured pricing findings per company, for the comparison table.
    comp_by_id = {c["id"]: c for c in conn.execute(
        "SELECT id, name, domain FROM competitors WHERE run_id = ?", (run_id,)
    ).fetchall()}
    pricing_rows = []
    for row in conn.execute(
        "SELECT competitor_id, value_json, source_ids_json FROM findings "
        "WHERE run_id = ? AND dimension = 'pricing' ORDER BY competitor_id IS NOT NULL, id",
        (run_id,),
    ).fetchall():
        value = json.loads(row["value_json"])
        comp = comp_by_id.get(row["competitor_id"])
        pricing_rows.append({
            "company": comp["name"] if comp else product["name"],
            "domain": comp["domain"] if comp else product["domain"],
            "is_subject": comp is None,
            "available": bool(value.get("available")),
            "tiers": value.get("tiers", []),
            "notes": _clean_text(value["notes"]) if value.get("notes") else None,
            "source_ids": json.loads(row["source_ids_json"]),
        })

    return {
        "pricing": pricing_rows,
        "run": {
            "id": run["id"], "status": run["status"], "error": run["error"],
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "cost_cents": run["cost_cents"], "token_count": run["token_count"],
            "tool_calls": run["tool_calls"],
        },
        "product": {
            "name": product["name"], "domain": product["domain"],
            "url": product["url"], "category": product["category"],
        },
        "competitors": competitors,
        "sections": sections,
        "sources": sources,
        "flags": [f.model_dump() for f in validate_run(conn, run_id)],
        "citation_coverage": (sourced / factual) if factual else None,
    }


# ---------- deterministic validation (design doc §10 step 7) ----------

INTERPRETATION_MARKERS = [
    "should", "recommend", "suggests", "likely", "appears to", "seems",
    "well-positioned", "advantage", "best choice", "stands out", "winner",
]


def validate_run(conn: sqlite3.Connection, run_id: int) -> list[ValidationFlag]:
    flags: list[ValidationFlag] = []
    valid_source_ids = {
        r["id"] for r in conn.execute(
            "SELECT id FROM sources WHERE run_id = ?", (run_id,)
        ).fetchall()
    }
    pricing_source_ids = {
        r["id"] for r in conn.execute(
            "SELECT id FROM sources WHERE run_id = ? AND source_type = 'pricing'",
            (run_id,),
        ).fetchall()
    }

    for row in conn.execute(
        "SELECT id, section, text, claim_type, source_ids_json FROM claims "
        "WHERE run_id = ?", (run_id,),
    ).fetchall():
        source_ids = json.loads(row["source_ids_json"])
        factual = row["claim_type"] in ("verified", "reported")

        if factual and not source_ids:
            flags.append(ValidationFlag(
                claim_id=row["id"], section=row["section"],
                flag="factual_claim_without_sources",
                detail=f"'{row['text'][:80]}' has no citations",
            ))
        for sid in source_ids:
            if sid not in valid_source_ids:
                flags.append(ValidationFlag(
                    claim_id=row["id"], section=row["section"],
                    flag="dangling_source_id",
                    detail=f"cites source {sid}, which does not exist in this run",
                ))
        if (
            factual and row["section"] == "pricing_comparison"
            and source_ids and not any(sid in pricing_source_ids for sid in source_ids)
        ):
            flags.append(ValidationFlag(
                claim_id=row["id"], section=row["section"],
                flag="pricing_claim_without_pricing_source",
                detail=f"'{row['text'][:80]}' cites no pricing-page source",
            ))
        if factual:
            text = row["text"].lower()
            hit = next((m for m in INTERPRETATION_MARKERS if m in text), None)
            if hit:
                flags.append(ValidationFlag(
                    claim_id=row["id"], section=row["section"],
                    flag="possible_unlabeled_interpretation",
                    detail=f"factual claim contains judgment language ('{hit}')",
                ))
    return flags
