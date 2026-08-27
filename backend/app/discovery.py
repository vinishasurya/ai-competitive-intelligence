"""Competitor discovery, verification, and ranking — design doc §9, §10 steps 2–3.

Three discovery strategies produce candidate leads; candidates are merged by
normalized name/domain, verified against their own live websites, ranked, and
capped at five. Model-generated candidates are treated as leads, not evidence —
nothing is selected without website verification.
"""

import json
import re
from typing import Literal
from urllib.parse import urlparse

import anthropic
from pydantic import BaseModel, Field

from app import config
from app.profiler import ProductProfile
from app.tools.crawl import crawl_page
from app.tools.search import search_web

MAX_CANDIDATES_TO_VERIFY = 12
MAX_COMPETITORS = 5
MAX_VERIFY_CHARS = 8_000

# Review sites, listicle publishers, and platforms that show up constantly in
# "alternatives to X" searches but are never themselves the competitor.
AGGREGATOR_DOMAINS = {
    "g2.com", "capterra.com", "getapp.com", "softwareadvice.com",
    "trustradius.com", "gartner.com", "alternativeto.net", "producthunt.com",
    "reddit.com", "quora.com", "medium.com", "wikipedia.org", "youtube.com",
    "linkedin.com", "x.com", "twitter.com", "facebook.com", "forbes.com",
    "techcrunch.com", "zapier.com", "news.ycombinator.com",
}


# ---------- structured-output schemas ----------

class CandidateLead(BaseModel):
    name: str
    domain: str
    reason: str


class LeadList(BaseModel):
    candidates: list[CandidateLead] = Field(default_factory=list)


class Verification(BaseModel):
    is_competitor: bool
    relationship: Literal["direct", "adjacent", "different_market"]
    confidence: float  # 0.0 - 1.0
    reason: str


class Candidate(BaseModel):
    name: str
    domain: str
    discovery_methods: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    verified: bool = False
    relationship: str | None = None
    confidence: float = 0.0
    why_selected: str | None = None


class DiscoveryResult(BaseModel):
    ok: bool
    product_domain: str
    candidates_considered: int = 0
    candidates_verified: int = 0
    competitors: list[Candidate] = Field(default_factory=list)  # final top 5
    rejected: list[Candidate] = Field(default_factory=list)     # verified-but-cut or failed
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: float = 0.0
    tool_calls: int = 0
    error: str | None = None


# ---------- helpers ----------

def normalize_domain(raw: str) -> str:
    raw = raw.strip().lower()
    if "://" in raw:
        raw = urlparse(raw).netloc
    raw = raw.split("/")[0]
    return raw.removeprefix("www.")


def normalize_name(raw: str) -> str:
    name = raw.strip().lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\b(inc|llc|ltd|corp|app|software|hq)\b", "", name).strip()
    return re.sub(r"\s+", " ", name)


class _Usage:
    """Accumulates token usage and cost across all model calls in one run."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_cents = 0.0

    def add(self, model: str, usage) -> None:
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cost_cents += config.estimate_cost_cents(
            model, usage.input_tokens, usage.output_tokens
        )


def _parse(model: str, system: str, user: str, output_format, usage: _Usage):
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    kwargs = {}
    if model == config.MODEL_PROFILER:
        kwargs["thinking"] = {"type": "adaptive"}
    response = client.messages.parse(
        model=model,
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=output_format,
        **kwargs,
    )
    usage.add(model, response.usage)
    return response.parsed_output


# ---------- strategy 1: model-generated leads ----------

MODEL_LEADS_SYSTEM = """You are a competitive analyst. Given a structured profile \
of a software product, list its most likely direct competitors.

Rules:
- Up to 8 competitors, most relevant first.
- domain must be the company's official website domain (e.g. "asana.com").
- These are leads that will be independently verified — prefer well-known, \
currently active products you are confident exist.
- Do not include the product itself, review sites, or generic marketplaces."""


def model_candidates(profile: ProductProfile, usage: _Usage) -> list[Candidate]:
    leads = _parse(
        config.MODEL_PROFILER,
        MODEL_LEADS_SYSTEM,
        f"Product profile:\n{json.dumps(profile.model_dump(), indent=2)}",
        LeadList,
        usage,
    )
    return [
        Candidate(
            name=lead.name,
            domain=normalize_domain(lead.domain),
            discovery_methods=["model_generated"],
            evidence=[lead.reason],
        )
        for lead in leads.candidates
    ]


# ---------- strategies 2 & 3: search-based ----------

EXTRACT_SYSTEM = """You extract competitor products mentioned in web search results.

Rules:
- Only include actual software products/companies that compete with the subject \
product — never review sites, blogs, listicle publishers, or marketplaces.
- domain must be the competitor's own official website domain. If the results \
don't show it and you don't confidently know it, skip that competitor.
- reason should quote or closely paraphrase the search-result evidence.
- Do not include the subject product itself. Return an empty list if nothing qualifies."""


def _format_results(responses) -> str:
    lines = []
    for resp in responses:
        for r in resp.results:
            lines.append(f"- [{r.title}]({r.url}): {r.snippet[:300]}")
    return "\n".join(lines)


def search_candidates(profile: ProductProfile, usage: _Usage) -> tuple[list[Candidate], int]:
    queries = [
        f"alternatives to {profile.name}",
        f"{profile.name} vs",
        f"best {profile.category}",
    ]
    responses = [search_web(q, max_results=8) for q in queries]
    responses = [r for r in responses if r.ok and r.results]
    if not responses:
        return [], len(queries)

    mentions = _parse(
        config.MODEL_EXTRACTOR,
        EXTRACT_SYSTEM,
        f"Subject product: {profile.name} ({profile.domain}) — {profile.category}\n\n"
        f"Search results:\n{_format_results(responses)}",
        LeadList,
        usage,
    )
    return [
        Candidate(
            name=m.name,
            domain=normalize_domain(m.domain),
            discovery_methods=["search"],
            evidence=[m.reason],
        )
        for m in mentions.candidates
    ], len(queries)


def comparison_page_candidates(
    profile: ProductProfile, usage: _Usage
) -> tuple[list[Candidate], int]:
    """Strategy 3: pages on the product's own site comparing it to others."""
    resp = search_web(
        f"{profile.name} vs comparison", max_results=8, include_domains=[profile.domain]
    )
    if not resp.ok or not resp.results:
        return [], 1

    mentions = _parse(
        config.MODEL_EXTRACTOR,
        EXTRACT_SYSTEM,
        f"Subject product: {profile.name} ({profile.domain}) — {profile.category}\n\n"
        f"These are comparison pages from the subject's OWN website. Extract the "
        f"companies it compares itself against:\n{_format_results([resp])}",
        LeadList,
        usage,
    )
    return [
        Candidate(
            name=m.name,
            domain=normalize_domain(m.domain),
            discovery_methods=["comparison_page"],
            evidence=[m.reason],
        )
        for m in mentions.candidates
    ], 1


# ---------- merge, verify, rank ----------

def merge_candidates(
    groups: list[list[Candidate]], product_domain: str, product_name: str
) -> list[Candidate]:
    product_domain = normalize_domain(product_domain)
    product_name_norm = normalize_name(product_name)
    merged: dict[str, Candidate] = {}
    for group in groups:
        for cand in group:
            cand = cand.model_copy(update={"domain": normalize_domain(cand.domain)})
            if not cand.domain or "." not in cand.domain:
                continue
            if cand.domain == product_domain or normalize_name(cand.name) == product_name_norm:
                continue
            if cand.domain in AGGREGATOR_DOMAINS:
                continue
            key = cand.domain
            if key in merged:
                existing = merged[key]
                for m in cand.discovery_methods:
                    if m not in existing.discovery_methods:
                        existing.discovery_methods.append(m)
                existing.evidence.extend(cand.evidence)
            else:
                merged[key] = cand.model_copy(deep=True)
    # Most methods first, preserving discovery order within ties.
    return sorted(merged.values(), key=lambda c: -len(c.discovery_methods))


VERIFY_SYSTEM = """You verify whether a company is a real competitor to a subject \
product, using text from the company's own website.

- direct: solves the same core customer problem for a similar audience
- adjacent: overlapping category or audience, but a different core job
- different_market: not meaningfully competing

Rules:
- Judge ONLY from the provided website text and profile.
- is_competitor is true only for direct or adjacent relationships supported by \
the website text.
- confidence is 0.0-1.0 for your overall judgment.
- reason: one sentence a PM could read to understand why this was selected."""


def verify_candidate(
    candidate: Candidate, profile: ProductProfile, usage: _Usage
) -> Candidate:
    page = crawl_page(f"https://{candidate.domain}")
    if not page.ok:
        return candidate.model_copy(update={
            "verified": False, "confidence": 0.0,
            "why_selected": f"unverifiable: {page.error}",
        })
    verdict = _parse(
        config.MODEL_EXTRACTOR,
        VERIFY_SYSTEM,
        f"Subject product profile:\n{json.dumps(profile.model_dump(), indent=2)}\n\n"
        f"Candidate competitor: {candidate.name} ({candidate.domain})\n"
        f"Text from {page.final_url}:\n{(page.raw_text or '')[:MAX_VERIFY_CHARS]}",
        Verification,
        usage,
    )
    return candidate.model_copy(update={
        "verified": verdict.is_competitor,
        "relationship": verdict.relationship,
        "confidence": verdict.confidence,
        "why_selected": verdict.reason,
    })


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Score = verification confidence + bonus per extra discovery strategy."""
    def score(c: Candidate) -> float:
        return c.confidence + 0.15 * (len(c.discovery_methods) - 1)
    return sorted(candidates, key=score, reverse=True)


# ---------- top-level pipeline ----------

def discover_competitors(profile: ProductProfile) -> DiscoveryResult:
    usage = _Usage()
    tool_calls = 0
    try:
        generated = model_candidates(profile, usage)
        tool_calls += 1
        searched, calls = search_candidates(profile, usage)
        tool_calls += calls
        compared, calls = comparison_page_candidates(profile, usage)
        tool_calls += calls
    except Exception as exc:
        return DiscoveryResult(
            ok=False, product_domain=profile.domain,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
            cost_cents=usage.cost_cents, tool_calls=tool_calls,
            error=f"discovery failed: {type(exc).__name__}: {exc}",
        )

    merged = merge_candidates(
        [generated, searched, compared], profile.domain, profile.name
    )
    to_verify = merged[:MAX_CANDIDATES_TO_VERIFY]

    verified: list[Candidate] = []
    rejected: list[Candidate] = []
    for cand in to_verify:
        tool_calls += 1
        try:
            result = verify_candidate(cand, profile, usage)
        except Exception as exc:  # one bad candidate never kills the run
            result = cand.model_copy(update={
                "verified": False,
                "why_selected": f"verification error: {type(exc).__name__}: {exc}",
            })
        (verified if result.verified else rejected).append(result)

    ranked = rank(verified)
    selected = ranked[:MAX_COMPETITORS]
    rejected.extend(ranked[MAX_COMPETITORS:])

    return DiscoveryResult(
        ok=True,
        product_domain=profile.domain,
        candidates_considered=len(merged),
        candidates_verified=len(to_verify),
        competitors=selected,
        rejected=rejected,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_cents=usage.cost_cents,
        tool_calls=tool_calls,
    )
