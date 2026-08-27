"""Evidence collection & structured extraction — design doc §10 steps 4–5.

For the original product and each verified competitor:
1. Crawl a fixed set of official pages (homepage, pricing, features) and store
   every attempt as a `sources` row — successes with raw text and content hash,
   failures with their retrieval metadata, so the report can show what was tried.
2. Extract normalized findings (positioning, features, pricing) from that stored
   evidence. Every finding row carries the source_ids it was extracted from —
   this is the link that makes claim-level citations measurable later.

Pricing is extracted only from pricing pages; when none is available the
pricing finding says so explicitly instead of guessing (design doc §14).
"""

import sqlite3
from typing import Literal

from pydantic import BaseModel, Field

from app import config
from app.db import insert_row
from app.llm import Usage, parse
from app.models import Finding, Source
from app.tools.crawl import CrawlResult, crawl_page

PAGE_PLAN: list[tuple[str, str]] = [  # (source_type, path)
    ("homepage", ""),
    ("pricing", "/pricing"),
    ("features", "/features"),
]
MAX_EXTRACT_CHARS = 15_000


# ---------- structured-output schemas ----------

class PricingTier(BaseModel):
    name: str
    price_text: str  # verbatim from the page, e.g. "$10 per user/month"
    price_usd: float | None = None  # numeric price if unambiguous, else null
    billing_period: Literal["monthly", "annual", "one_time", "custom", "unknown"] = "unknown"
    key_limits: list[str] = Field(default_factory=list)


class PricingFindings(BaseModel):
    available: bool
    tiers: list[PricingTier] = Field(default_factory=list)
    notes: str | None = None


class CompanyFindings(BaseModel):
    positioning: str | None = None
    target_customer: str | None = None
    key_features: list[str] = Field(default_factory=list)


class EvidenceSummary(BaseModel):
    company: str
    domain: str
    source_ids: list[int] = Field(default_factory=list)
    finding_ids: list[int] = Field(default_factory=list)
    pages_ok: int = 0
    pages_failed: int = 0
    error: str | None = None


# ---------- step 4: collect and store sources ----------

def collect_sources(
    conn: sqlite3.Connection, run_id: int, competitor_id: int | None, domain: str
) -> list[tuple[int, str, CrawlResult]]:
    """Crawl the page plan for one company; store every attempt as a source row.

    Returns (source_id, source_type, crawl_result) for each stored attempt.
    Duplicate content (paths redirecting to the homepage) is not re-stored.
    """
    stored: list[tuple[int, str, CrawlResult]] = []
    seen_hashes: set[str] = set()
    for source_type, path in PAGE_PLAN:
        url = f"https://{domain}{path}"
        result = crawl_page(url)
        if result.ok and result.content_hash in seen_hashes:
            continue
        if result.ok:
            seen_hashes.add(result.content_hash)
        source = Source(
            run_id=run_id,
            competitor_id=competitor_id,
            url=result.final_url or result.url,
            source_type=source_type,
            fetched_at=result.fetched_at,
            raw_text=result.raw_text,
            http_status=result.http_status,
            content_hash=result.content_hash,
        )
        source_id = insert_row(conn, "sources", source.to_row())
        stored.append((source_id, source_type, result))
    return stored


# ---------- extract_pricing: independently testable tool (design doc §11) ----------

PRICING_SYSTEM = """You extract pricing information from the text of an official \
pricing page.

Rules:
- Extract ONLY prices, tiers, billing periods, and limits explicitly stated in \
the text. Never estimate or fill in from prior knowledge.
- price_text is the verbatim price wording; price_usd is the number only when a \
single unambiguous USD amount is stated (use the monthly per-user amount when \
both monthly and annual are shown, and note the annual price in key_limits).
- "Contact us" / custom tiers: price_usd null, billing_period "custom".
- If the text contains no usable pricing, return available=false with empty tiers."""


def extract_pricing(pricing_text: str, usage: Usage) -> PricingFindings:
    if not pricing_text.strip():
        return PricingFindings(available=False, notes="empty pricing text")
    return parse(
        config.MODEL_EXTRACTOR,
        PRICING_SYSTEM,
        f"Pricing page text:\n{pricing_text[:MAX_EXTRACT_CHARS]}",
        PricingFindings,
        usage,
    )


# ---------- step 5: structured findings ----------

COMPANY_SYSTEM = """You extract a company's positioning and features from text on \
its own website.

Rules:
- Use ONLY the provided text; no prior knowledge, no guessing. Missing -> null/empty.
- positioning: one sentence describing what the product is and its main promise.
- target_customer: who the site says it serves.
- key_features: up to 10 claimed capabilities as short noun phrases, most \
important first."""


def extract_findings(
    conn: sqlite3.Connection,
    run_id: int,
    competitor_id: int | None,
    company_name: str,
    sources: list[tuple[int, str, CrawlResult]],
    usage: Usage,
) -> list[int]:
    """Extract positioning/features/pricing findings; each cites its source ids."""
    finding_ids: list[int] = []

    def store(dimension: str, value, source_ids: list[int]) -> None:
        finding = Finding(
            run_id=run_id, competitor_id=competitor_id,
            dimension=dimension, value=value, source_ids=source_ids,
        )
        finding_ids.append(insert_row(conn, "findings", finding.to_row()))

    # Positioning + features from homepage/features pages.
    general = [(sid, r) for sid, stype, r in sources if stype != "pricing" and r.ok]
    if general:
        text = "\n\n".join(
            f"=== PAGE: {r.final_url or r.url} ===\n{(r.raw_text or '')[:MAX_EXTRACT_CHARS]}"
            for _, r in general
        )
        company = parse(
            config.MODEL_EXTRACTOR, COMPANY_SYSTEM,
            f"Company: {company_name}\n\n{text}", CompanyFindings, usage,
        )
        general_ids = [sid for sid, _ in general]
        store("positioning", {
            "positioning": company.positioning,
            "target_customer": company.target_customer,
        }, general_ids)
        store("features", company.key_features, general_ids)

    # Pricing strictly from pricing pages (primary source rule).
    pricing_sources = [(sid, r) for sid, stype, r in sources if stype == "pricing"]
    pricing_ok = [(sid, r) for sid, r in pricing_sources if r.ok]
    if pricing_ok:
        sid, result = pricing_ok[0]
        pricing = extract_pricing(result.raw_text or "", usage)
        store("pricing", pricing.model_dump(), [sid])
    else:
        attempted = [sid for sid, _ in pricing_sources]
        store("pricing", {
            "available": False,
            "tiers": [],
            "notes": "no accessible pricing page found",
        }, attempted)

    return finding_ids


def collect_and_extract(
    conn: sqlite3.Connection,
    run_id: int,
    competitor_id: int | None,
    company_name: str,
    domain: str,
    usage: Usage,
) -> EvidenceSummary:
    """Full evidence pass for one company. Soft-fails per company."""
    summary = EvidenceSummary(company=company_name, domain=domain)
    try:
        sources = collect_sources(conn, run_id, competitor_id, domain)
        summary.source_ids = [sid for sid, _, _ in sources]
        summary.pages_ok = sum(1 for _, _, r in sources if r.ok)
        summary.pages_failed = sum(1 for _, _, r in sources if not r.ok)
        summary.finding_ids = extract_findings(
            conn, run_id, competitor_id, company_name, sources, usage
        )
    except Exception as exc:
        summary.error = f"{type(exc).__name__}: {exc}"
    return summary
