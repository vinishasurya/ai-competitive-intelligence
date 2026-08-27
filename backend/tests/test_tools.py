"""Offline unit tests for the research tools — no network, httpx is faked."""

import httpx
import pytest

from app.tools import crawl, search

SAMPLE_HTML = """
<html><head><title>Acme</title></head><body>
<main><h1>Acme Pricing</h1><p>Starter plan costs $10 per user per month
and includes unlimited projects for growing software teams.</p>
<p>The Business plan costs $25 per user per month and adds SSO,
audit logs, and priority support for larger organizations.</p></main>
</body></html>
"""


class FakeResponse:
    def __init__(self, status_code=200, text="", url="https://acme.test/pricing"):
        self.status_code = status_code
        self.text = text
        self.url = url


def test_crawl_extracts_text_and_hash(monkeypatch, tmp_path):
    monkeypatch.setattr(crawl.config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(text=SAMPLE_HTML))

    result = crawl.crawl_page("https://acme.test/pricing")
    assert result.ok
    assert "$10 per user" in result.raw_text
    assert result.http_status == 200
    assert len(result.content_hash) == 64  # sha256 hex
    assert result.fetched_at and not result.from_cache


def test_crawl_second_hit_comes_from_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(crawl.config, "CACHE_DIR", tmp_path)
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return FakeResponse(text=SAMPLE_HTML)

    monkeypatch.setattr(httpx, "get", fake_get)
    first = crawl.crawl_page("https://acme.test/pricing")
    second = crawl.crawl_page("https://acme.test/pricing")

    assert len(calls) == 1  # network hit only once
    assert second.from_cache and not first.from_cache
    assert second.content_hash == first.content_hash


def test_crawl_soft_fails_on_network_error(monkeypatch, tmp_path):
    monkeypatch.setattr(crawl.config, "CACHE_DIR", tmp_path)

    def fake_get(*a, **k):
        raise httpx.ConnectError("dns failure")

    monkeypatch.setattr(httpx, "get", fake_get)
    result = crawl.crawl_page("https://doesnotexist.test")
    assert not result.ok
    assert "ConnectError" in result.error
    assert result.raw_text is None


def test_crawl_soft_fails_on_http_error(monkeypatch, tmp_path):
    monkeypatch.setattr(crawl.config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(status_code=404))

    result = crawl.crawl_page("https://acme.test/missing")
    assert not result.ok
    assert result.http_status == 404


def test_search_soft_fails_without_api_key(monkeypatch):
    monkeypatch.setattr(search.config, "SEARCH_API_KEY", "")
    response = search.search_web("alternatives to acme")
    assert not response.ok
    assert "SEARCH_API_KEY" in response.error


def test_search_parses_tavily_payload(monkeypatch):
    monkeypatch.setattr(search.config, "SEARCH_API_KEY", "test-key")

    class FakePost:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {"title": "Best Acme alternatives", "url": "https://example.com/alts",
                     "content": "Top 10 Acme competitors...", "score": 0.97}
                ]
            }

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakePost())
    response = search.search_web("alternatives to acme")
    assert response.ok
    assert response.results[0].rank == 1
    assert response.results[0].url == "https://example.com/alts"
