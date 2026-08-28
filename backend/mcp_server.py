"""MCP server exposing the platform's research tools (design doc §11).

Any MCP-compatible client (Claude Desktop, Claude Code, ...) can use these
tools directly. Run over stdio:

    uv run python mcp_server.py

Requires SEARCH_API_KEY in backend/.env for search_web and
discover_competitors; ANTHROPIC_API_KEY additionally for extract_pricing,
profile_product, and discover_competitors (they call Claude internally).
"""

from mcp.server.mcpserver import MCPServer

from app.evidence import extract_pricing as _extract_pricing
from app.llm import Usage
from app.tools.crawl import crawl_page, crawl_page_rendered
from app.tools.search import search_web as _search_web

server = MCPServer(
    name="competitive-intelligence",
    description="Research tools: web search, page crawling, pricing extraction, "
                "and competitor discovery with website verification.",
)

MAX_TEXT = 20_000


@server.tool()
def search_web(query: str, max_results: int = 8) -> dict:
    """Search the public web and return ranked results with URLs and snippets.

    Args:
        query: The search query, e.g. "alternatives to Linear".
        max_results: Maximum results to return (1-10).
    """
    response = _search_web(query, max_results=min(max_results, 10))
    return response.model_dump()


@server.tool()
def crawl_page_text(url: str, render_js: bool = False) -> dict:
    """Fetch a public web page and return its cleaned text plus retrieval
    metadata (final URL, HTTP status, retrieval time, content hash).

    Args:
        url: The page URL to fetch.
        render_js: Set true for JavaScript-heavy pages; fetches with a real
            headless browser (slower, ~5s) instead of a static request.
    """
    result = crawl_page_rendered(url) if render_js else crawl_page(url)
    payload = result.model_dump()
    if payload.get("raw_text"):
        payload["raw_text"] = payload["raw_text"][:MAX_TEXT]
    return payload


@server.tool()
def extract_pricing(url: str) -> dict:
    """Extract structured pricing (tiers, prices, billing periods, limits)
    from an official pricing page. Only reports prices explicitly stated on
    the page; returns available=false rather than guessing. Falls back to a
    rendered browser fetch when the static page hides prices behind
    JavaScript.

    Args:
        url: The pricing page URL, e.g. "https://linear.app/pricing".
    """
    usage = Usage()
    page = crawl_page(url)
    pricing = _extract_pricing(page.raw_text or "", usage) if page.ok else None
    if pricing is None or not pricing.available:
        rendered = crawl_page_rendered(url)
        if rendered.ok:
            candidate = _extract_pricing(rendered.raw_text or "", usage)
            if candidate.available:
                page, pricing = rendered, candidate
    if pricing is None:
        return {"available": False, "error": page.error,
                "cost_cents": round(usage.cost_cents, 2)}
    payload = pricing.model_dump()
    payload["source_url"] = page.final_url or url
    payload["retrieved_at"] = page.fetched_at
    payload["cost_cents"] = round(usage.cost_cents, 2)
    return payload


@server.tool()
def profile_product(url: str) -> dict:
    """Build a structured profile of a software product from its own website:
    category, target customer, core problem, value proposition, key features,
    and pricing summary. Grounded in crawled page text only. Takes ~20-40s
    and costs a few cents of model usage.

    Args:
        url: The product's website, e.g. "linear.app".
    """
    from app.profiler import build_profile

    result = build_profile(url)
    if not result.ok:
        return {"ok": False, "error": result.error}
    return {
        "ok": True,
        "profile": result.profile.model_dump(),
        "pages_used": [p.final_url or p.url for p in result.pages],
        "cost_cents": round(result.cost_cents, 2),
    }


@server.tool()
def discover_competitors(url: str) -> dict:
    """Discover and verify up to five competitors for a software product.
    Combines three strategies (model-generated leads, web search, the
    product's own comparison pages), then verifies each candidate against
    its live website before selecting. Takes ~1-2 minutes and costs ~10
    cents of model usage.

    Args:
        url: The product's website, e.g. "linear.app".
    """
    from app.discovery import discover_competitors as _discover
    from app.profiler import build_profile

    prof = build_profile(url)
    if not prof.ok:
        return {"ok": False, "error": f"profiling: {prof.error}"}
    disc = _discover(prof.profile)
    if not disc.ok:
        return {"ok": False, "error": f"discovery: {disc.error}"}
    return {
        "ok": True,
        "product": {"name": prof.profile.name, "category": prof.profile.category},
        "competitors": [
            {
                "name": c.name, "domain": c.domain,
                "relationship": c.relationship, "confidence": c.confidence,
                "discovery_methods": c.discovery_methods,
                "why_selected": c.why_selected,
            }
            for c in disc.competitors
        ],
        "candidates_considered": disc.candidates_considered,
        "cost_cents": round(prof.cost_cents + disc.cost_cents, 2),
    }


if __name__ == "__main__":
    server.run(transport="stdio")
