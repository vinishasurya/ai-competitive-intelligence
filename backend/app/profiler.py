"""Product profiler — design doc §10, step 1.

Takes a product URL, crawls the homepage plus discoverable pages (pricing,
features, about), and asks Claude to extract a structured ProductProfile.
The model only sees crawled page text and is instructed to leave fields null
rather than guess — profile content must be grounded in collected evidence.
"""

import ipaddress
from urllib.parse import urlparse

import anthropic
from pydantic import BaseModel, Field

from app import config
from app.tools.crawl import CrawlResult, crawl_page, crawl_page_rendered

CANDIDATE_PATHS = ["", "/pricing", "/features", "/about", "/product"]
MAX_CHARS_PER_PAGE = 12_000
# Below this much total text, the static crawl likely got a JS shell.
MIN_STATIC_CHARS = 400

SYSTEM_PROMPT = """You are a product analyst building a structured profile of a \
software product from its own website.

Rules:
- Use ONLY the page text provided. Do not use prior knowledge about the company, \
even if you recognize it.
- If a field cannot be determined from the provided text, set it to null (or an \
empty list) instead of guessing.
- category should be a concise market-category phrase a PM would use, e.g. \
"project management software for engineering teams".
- key_features should be the product's own claimed capabilities, normalized to \
short noun phrases, most important first, at most 10.
- pricing_summary should only reflect prices/tiers explicitly shown in the text."""


class ProductProfile(BaseModel):
    name: str
    domain: str
    category: str
    target_customer: str | None = None
    core_problem: str | None = None
    value_proposition: str | None = None
    key_features: list[str] = Field(default_factory=list)
    business_model: str | None = None
    pricing_summary: str | None = None


class ProfileResult(BaseModel):
    ok: bool
    url: str
    profile: ProductProfile | None = None
    pages: list[CrawlResult] = Field(default_factory=list)
    model: str = config.MODEL_PROFILER
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: float = 0.0
    error: str | None = None


def validate_url(raw: str) -> str:
    """Normalize and validate a user-submitted product URL. Raises ValueError."""
    raw = raw.strip()
    if not raw:
        raise ValueError("URL is empty")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"unsupported URL scheme: {parsed.scheme}")
    host = parsed.hostname or ""
    if "." not in host or host == "localhost" or host.endswith(".local"):
        raise ValueError(f"not a public hostname: {host or raw}")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass  # not an IP literal — a normal domain name, fine
    else:
        if not ip.is_global:
            raise ValueError(f"not a public address: {host}")
    return raw


def collect_pages(url: str) -> list[CrawlResult]:
    """Crawl the homepage and common discoverable pages; keep successes."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    pages = []
    seen_hashes = set()
    for path in CANDIDATE_PATHS:
        target = url if path == "" else base + path
        result = crawl_page(target)
        # Sites often redirect unknown paths to the homepage — dedupe by content.
        if result.ok and result.content_hash not in seen_hashes:
            seen_hashes.add(result.content_hash)
            pages.append(result)

    # JS-shell fallback: static fetches "succeeded" but got almost no text
    # (or nothing at all) — render the homepage in a real browser.
    total_chars = sum(len(p.raw_text or "") for p in pages)
    if total_chars < MIN_STATIC_CHARS:
        rendered = crawl_page_rendered(url)
        if rendered.ok and len(rendered.raw_text or "") > total_chars:
            pages.insert(0, rendered)
    return pages


def _build_evidence(pages: list[CrawlResult]) -> str:
    sections = []
    for page in pages:
        text = (page.raw_text or "")[:MAX_CHARS_PER_PAGE]
        sections.append(f"=== PAGE: {page.final_url or page.url} ===\n{text}")
    return "\n\n".join(sections)


def _call_model(evidence: str, domain: str) -> tuple[ProductProfile, anthropic.types.Usage]:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.parse(
        model=config.MODEL_PROFILER,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Build a product profile for the software product at {domain}. "
                f"Page text from its website follows.\n\n{evidence}"
            ),
        }],
        output_format=ProductProfile,
    )
    return response.parsed_output, response.usage


def build_profile(raw_url: str) -> ProfileResult:
    try:
        url = validate_url(raw_url)
    except ValueError as exc:
        return ProfileResult(ok=False, url=raw_url, error=f"invalid URL: {exc}")

    pages = collect_pages(url)
    if not pages:
        return ProfileResult(
            ok=False, url=url,
            error="could not read this site — it likely blocks automated access "
                  "from cloud servers; try a different product",
        )

    domain = urlparse(url).hostname
    try:
        profile, usage = _call_model(_build_evidence(pages), domain)
    except Exception as exc:
        return ProfileResult(
            ok=False, url=url, pages=pages, error=f"{type(exc).__name__}: {exc}"
        )

    return ProfileResult(
        ok=True,
        url=url,
        profile=profile,
        pages=pages,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_cents=config.estimate_cost_cents(
            config.MODEL_PROFILER, usage.input_tokens, usage.output_tokens
        ),
    )
