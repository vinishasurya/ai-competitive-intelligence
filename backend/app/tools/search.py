"""search_web: ranked public search results via the Tavily API.

Soft-failure contract (design doc §15): never raises. Returns a
SearchResponse with ok=False and an error message instead, so a single
failed query can't kill a whole research run.
"""

import httpx
from pydantic import BaseModel

from app import config

TAVILY_ENDPOINT = "https://api.tavily.com/search"


class SearchResult(BaseModel):
    rank: int
    title: str
    url: str
    snippet: str
    score: float | None = None


class SearchResponse(BaseModel):
    ok: bool
    query: str
    results: list[SearchResult] = []
    error: str | None = None


def search_web(query: str, max_results: int = 8) -> SearchResponse:
    if not config.SEARCH_API_KEY:
        return SearchResponse(ok=False, query=query, error="SEARCH_API_KEY is not set")
    try:
        resp = httpx.post(
            TAVILY_ENDPOINT,
            headers={"Authorization": f"Bearer {config.SEARCH_API_KEY}"},
            json={"query": query, "max_results": max_results, "search_depth": "basic"},
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        return SearchResponse(ok=False, query=query, error=f"{type(exc).__name__}: {exc}")

    results = [
        SearchResult(
            rank=i + 1,
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
            score=item.get("score"),
        )
        for i, item in enumerate(payload.get("results", []))
    ]
    return SearchResponse(ok=True, query=query, results=results)
