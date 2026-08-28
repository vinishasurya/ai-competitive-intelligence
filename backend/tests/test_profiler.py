"""Offline unit tests for the product profiler — no network, no API calls."""

import pytest

from app import profiler
from app.profiler import ProductProfile, build_profile, collect_pages, validate_url
from app.tools.crawl import CrawlResult


class TestValidateUrl:
    def test_normalizes_bare_domain(self):
        assert validate_url("linear.app") == "https://linear.app"

    def test_keeps_full_url(self):
        assert validate_url("https://linear.app/pricing") == "https://linear.app/pricing"

    def test_strips_whitespace(self):
        assert validate_url("  linear.app  ") == "https://linear.app"

    @pytest.mark.parametrize("bad", [
        "", "localhost", "http://localhost:8000", "ftp://example.com",
        "myserver.local", "http://127.0.0.1", "http://192.168.1.5", "notadomain",
    ])
    def test_rejects_invalid(self, bad):
        with pytest.raises(ValueError):
            validate_url(bad)


def _page(url, text, http_status=200, content_hash=None):
    return CrawlResult(
        ok=True, url=url, final_url=url, http_status=http_status,
        raw_text=text, content_hash=content_hash or f"hash-{hash(text)}",
        fetched_at="2026-08-27T00:00:00+00:00",
    )


def test_collect_pages_dedupes_redirects_to_homepage(monkeypatch):
    # /features and /about "redirect" to the homepage → identical content hash
    home = _page("https://acme.test", "homepage text", content_hash="same")

    def fake_crawl(url, **kwargs):
        if "/pricing" in url:
            return _page(url, "pricing text", content_hash="pricing")
        if "/product" in url:
            return CrawlResult(ok=False, url=url, fetched_at="t", error="HTTP 404")
        return home.model_copy(update={"url": url})

    monkeypatch.setattr(profiler, "crawl_page", fake_crawl)
    pages = collect_pages("https://acme.test")
    assert [p.content_hash for p in pages] == ["same", "pricing"]


def test_build_profile_rejects_bad_url():
    result = build_profile("localhost")
    assert not result.ok and "invalid URL" in result.error


def test_build_profile_soft_fails_when_nothing_crawls(monkeypatch):
    monkeypatch.setattr(
        profiler, "crawl_page",
        lambda url, **k: CrawlResult(ok=False, url=url, fetched_at="t", error="down"),
    )
    monkeypatch.setattr(
        profiler, "crawl_page_rendered",
        lambda url, **k: CrawlResult(ok=False, url=url, fetched_at="t", error="down"),
    )
    result = build_profile("https://acme.test")
    assert not result.ok and "blocks automated access" in result.error


def test_build_profile_happy_path(monkeypatch):
    monkeypatch.setattr(
        profiler, "crawl_page",
        lambda url, **k: _page(url, "Acme: issue tracking for teams. $10/user."),
    )

    captured = {}

    def fake_model(evidence, domain):
        captured["evidence"] = evidence
        captured["domain"] = domain

        class Usage:
            input_tokens, output_tokens = 5000, 400

        return ProductProfile(
            name="Acme", domain="acme.test", category="issue tracking software",
            key_features=["issue tracking"],
        ), Usage()

    monkeypatch.setattr(profiler, "_call_model", fake_model)
    result = build_profile("acme.test")

    assert result.ok
    assert result.profile.name == "Acme"
    assert "issue tracking for teams" in captured["evidence"]  # evidence reached the model
    assert captured["domain"] == "acme.test"
    assert result.cost_cents > 0  # usage was recorded and priced


def test_build_profile_soft_fails_on_model_error(monkeypatch):
    monkeypatch.setattr(
        profiler, "crawl_page", lambda url, **k: _page(url, "some text")
    )

    def boom(evidence, domain):
        raise RuntimeError("api down")

    monkeypatch.setattr(profiler, "_call_model", boom)
    result = build_profile("https://acme.test")
    assert not result.ok and "api down" in result.error
    assert result.pages  # crawled evidence is still preserved


class TestJsShellFallback:
    def test_rendered_homepage_used_when_static_text_is_a_shell(self, monkeypatch):
        shell = _page("https://canva.test", "Loading... app shell")  # tiny text
        monkeypatch.setattr(profiler, "crawl_page", lambda url, **k: shell)
        monkeypatch.setattr(
            profiler, "crawl_page_rendered",
            lambda url, **k: _page(url, "Canva: design anything. " * 50),
        )
        pages = collect_pages("https://canva.test")
        assert len(pages[0].raw_text) > 1000  # rendered page leads

    def test_no_rendered_call_when_static_is_rich(self, monkeypatch):
        rich = _page("https://acme.test", "Real homepage content. " * 50)
        monkeypatch.setattr(profiler, "crawl_page", lambda url, **k: rich)

        def boom(url, **k):
            raise AssertionError("rendered fetch should not be called")
        monkeypatch.setattr(profiler, "crawl_page_rendered", boom)
        pages = collect_pages("https://acme.test")
        assert pages

    def test_blocked_site_error_message(self, monkeypatch):
        monkeypatch.setattr(
            profiler, "crawl_page",
            lambda url, **k: CrawlResult(ok=False, url=url, fetched_at="t", error="HTTP 403"),
        )
        monkeypatch.setattr(
            profiler, "crawl_page_rendered",
            lambda url, **k: CrawlResult(ok=False, url=url, fetched_at="t", error="render: blocked"),
        )
        result = build_profile("https://blocked.test")
        assert not result.ok and "blocks automated access" in result.error
