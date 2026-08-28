"""MCP server tests: tools are registered and callable through the MCP layer."""

import asyncio
import json

import mcp_server
from app.tools.crawl import CrawlResult
from app.tools.search import SearchResponse, SearchResult

EXPECTED_TOOLS = {
    "search_web", "crawl_page_text", "extract_pricing",
    "profile_product", "discover_competitors",
}


def test_all_tools_registered_with_descriptions():
    tools = asyncio.run(mcp_server.server.list_tools())
    by_name = {t.name: t for t in tools}
    assert set(by_name) == EXPECTED_TOOLS
    for tool in by_name.values():
        assert tool.description, f"{tool.name} is missing a description"


def test_search_tool_callable_through_mcp(monkeypatch):
    monkeypatch.setattr(
        mcp_server, "_search_web",
        lambda query, max_results=8: SearchResponse(
            ok=True, query=query,
            results=[SearchResult(rank=1, title="Jira", url="https://atlassian.com",
                                  snippet="Jira software")],
        ),
    )
    result = asyncio.run(
        mcp_server.server.call_tool("search_web", {"query": "alternatives to Linear"})
    )
    text = result[0][0].text if isinstance(result, tuple) else result.content[0].text
    payload = json.loads(text)
    assert payload["ok"] and payload["results"][0]["url"] == "https://atlassian.com"


def test_crawl_tool_truncates_text(monkeypatch):
    monkeypatch.setattr(
        mcp_server, "crawl_page",
        lambda url, **k: CrawlResult(
            ok=True, url=url, final_url=url, http_status=200,
            raw_text="x" * 50_000, content_hash="h",
            fetched_at="2026-08-28T00:00:00+00:00",
        ),
    )
    result = asyncio.run(
        mcp_server.server.call_tool("crawl_page_text", {"url": "https://acme.test"})
    )
    text = result[0][0].text if isinstance(result, tuple) else result.content[0].text
    payload = json.loads(text)
    assert len(payload["raw_text"]) == mcp_server.MAX_TEXT
