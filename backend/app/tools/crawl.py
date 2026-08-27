"""crawl_page: fetch a public URL and return cleaned text plus retrieval
metadata (design doc §11 tool interface, §10 step 4 source records).

Soft-failure contract: never raises. Unreachable hosts, HTTP errors, and
pages with no extractable text all return ok=False with the metadata we
did manage to collect, so the pipeline can record the attempt and move on.

A small on-disk cache (24h TTL) avoids refetching the same page across
runs during development — cuts latency and is polite to the sites.
"""

import hashlib
import json
import time
from datetime import datetime, timezone

import httpx
import trafilatura
from pydantic import BaseModel

from app import config

USER_AGENT = "ci-research-bot/0.1 (portfolio research project)"
CACHE_TTL_SECONDS = 24 * 60 * 60


class CrawlResult(BaseModel):
    ok: bool
    url: str
    final_url: str | None = None
    http_status: int | None = None
    raw_text: str | None = None
    content_hash: str | None = None
    fetched_at: str
    from_cache: bool = False
    error: str | None = None


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cache_path(url: str):
    return config.CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".json")


def _cache_get(url: str) -> CrawlResult | None:
    path = _cache_path(url)
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL_SECONDS:
        try:
            cached = CrawlResult(**json.loads(path.read_text()))
            return cached.model_copy(update={"from_cache": True})
        except (json.JSONDecodeError, ValueError):
            return None  # corrupt cache entry — refetch
    return None


def _cache_put(url: str, result: CrawlResult) -> None:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(url).write_text(result.model_dump_json())


def crawl_page(url: str, timeout: float = 20.0, use_cache: bool = True) -> CrawlResult:
    if use_cache and (cached := _cache_get(url)):
        return cached

    fetched_at = _utcnow()
    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as exc:
        return CrawlResult(
            ok=False, url=url, fetched_at=fetched_at, error=f"{type(exc).__name__}: {exc}"
        )

    if resp.status_code >= 400:
        return CrawlResult(
            ok=False,
            url=url,
            final_url=str(resp.url),
            http_status=resp.status_code,
            fetched_at=fetched_at,
            error=f"HTTP {resp.status_code}",
        )

    text = trafilatura.extract(resp.text, include_tables=True, favor_recall=True)
    if not text:
        return CrawlResult(
            ok=False,
            url=url,
            final_url=str(resp.url),
            http_status=resp.status_code,
            fetched_at=fetched_at,
            error="no extractable text (page may require JavaScript)",
        )

    result = CrawlResult(
        ok=True,
        url=url,
        final_url=str(resp.url),
        http_status=resp.status_code,
        raw_text=text,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        fetched_at=fetched_at,
    )
    if use_cache:
        _cache_put(url, result)
    return result
