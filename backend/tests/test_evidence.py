"""Offline unit tests for evidence collection & extraction — no network/API."""

import json

import pytest

from app import evidence
from app.db import connect, fetch_row, init_db, insert_row
from app.evidence import (
    CompanyFindings,
    PricingFindings,
    PricingTier,
    collect_and_extract,
    collect_sources,
)
from app.llm import Usage
from app.models import Product, Run
from app.tools.crawl import CrawlResult


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def run_id(conn):
    product_id = insert_row(
        conn, "products", Product(url="https://acme.test", domain="acme.test").to_row()
    )
    return insert_row(conn, "runs", Run(product_id=product_id).to_row())


def _page(url, text, content_hash):
    return CrawlResult(
        ok=True, url=url, final_url=url, http_status=200, raw_text=text,
        content_hash=content_hash, fetched_at="2026-08-27T00:00:00+00:00",
    )


def fake_crawl_ok(url, **kwargs):
    if "/pricing" in url:
        return _page(url, "Pro plan $12 per user/month. Free plan $0.", "hash-pricing")
    if "/features" in url:
        return _page(url, "Features: issue tracking, roadmaps.", "hash-features")
    return _page(url, "Acme homepage: issue tracking for teams.", "hash-home")


class TestCollectSources:
    def test_stores_all_page_types(self, conn, run_id, monkeypatch):
        monkeypatch.setattr(evidence, "crawl_page", fake_crawl_ok)
        stored = collect_sources(conn, run_id, None, "acme.test")
        assert [stype for _, stype, _ in stored] == ["homepage", "pricing", "features"]
        row = fetch_row(conn, "sources", stored[1][0])
        assert row["source_type"] == "pricing"
        assert "12 per user" in row["raw_text"]
        assert row["competitor_id"] is None  # source about the product itself

    def test_failures_are_stored_with_metadata(self, conn, run_id, monkeypatch):
        def crawl(url, **kwargs):
            if "/pricing" in url:
                return CrawlResult(ok=False, url=url, http_status=404,
                                   fetched_at="t", error="HTTP 404")
            return fake_crawl_ok(url)

        monkeypatch.setattr(evidence, "crawl_page", crawl)
        stored = collect_sources(conn, run_id, None, "acme.test")
        pricing_row = fetch_row(conn, "sources", stored[1][0])
        assert pricing_row["http_status"] == 404
        assert pricing_row["raw_text"] is None

    def test_duplicate_content_not_restored(self, conn, run_id, monkeypatch):
        # /features redirects to the homepage -> same content hash
        def crawl(url, **kwargs):
            if "/features" in url:
                return _page(url, "Acme homepage: issue tracking.", "hash-home")
            return fake_crawl_ok(url)

        monkeypatch.setattr(evidence, "crawl_page", crawl)
        stored = collect_sources(conn, run_id, None, "acme.test")
        assert [stype for _, stype, _ in stored] == ["homepage", "pricing"]


def fake_parse(model, system, user, output_format, usage, **kwargs):
    if output_format is PricingFindings:
        return PricingFindings(
            available=True,
            tiers=[PricingTier(name="Pro", price_text="$12 per user/month",
                               price_usd=12.0, billing_period="monthly")],
        )
    return CompanyFindings(
        positioning="Issue tracking for teams",
        target_customer="software teams",
        key_features=["issue tracking", "roadmaps"],
    )


class TestExtractAndStore:
    def test_findings_trace_to_stored_sources(self, conn, run_id, monkeypatch):
        monkeypatch.setattr(evidence, "crawl_page", fake_crawl_ok)
        monkeypatch.setattr(evidence, "parse", fake_parse)

        summary = collect_and_extract(conn, run_id, None, "Acme", "acme.test", Usage())
        assert summary.error is None
        assert summary.pages_ok == 3
        assert len(summary.finding_ids) == 3  # positioning, features, pricing

        for fid in summary.finding_ids:
            row = fetch_row(conn, "findings", fid)
            source_ids = json.loads(row["source_ids_json"])
            assert source_ids, f"finding {row['dimension']} has no sources"
            for sid in source_ids:
                assert sid in summary.source_ids
                assert fetch_row(conn, "sources", sid) is not None

        pricing = next(
            json.loads(fetch_row(conn, "findings", fid)["value_json"])
            for fid in summary.finding_ids
            if fetch_row(conn, "findings", fid)["dimension"] == "pricing"
        )
        assert pricing["tiers"][0]["price_usd"] == 12.0

    def test_pricing_unavailable_when_page_fails(self, conn, run_id, monkeypatch):
        def crawl(url, **kwargs):
            if "/pricing" in url:
                return CrawlResult(ok=False, url=url, http_status=404,
                                   fetched_at="t", error="HTTP 404")
            return fake_crawl_ok(url)

        monkeypatch.setattr(evidence, "crawl_page", crawl)
        monkeypatch.setattr(evidence, "parse", fake_parse)

        summary = collect_and_extract(conn, run_id, None, "Acme", "acme.test", Usage())
        pricing_rows = [
            fetch_row(conn, "findings", fid) for fid in summary.finding_ids
        ]
        pricing = next(
            json.loads(r["value_json"]) for r in pricing_rows if r["dimension"] == "pricing"
        )
        assert pricing["available"] is False
        assert pricing["tiers"] == []

    def test_company_level_soft_failure(self, conn, run_id, monkeypatch):
        def boom(url, **kwargs):
            raise RuntimeError("network stack on fire")

        monkeypatch.setattr(evidence, "crawl_page", boom)
        summary = collect_and_extract(conn, run_id, 1, "Ghost", "ghost.test", Usage())
        assert summary.error and "network stack on fire" in summary.error
        assert summary.finding_ids == []


def test_extract_pricing_empty_text_short_circuits():
    result = evidence.extract_pricing("   ", Usage())  # no API call needed
    assert result.available is False


# ---------- CP9: pricing retrieval fixes ----------

HOMEPAGE_HTML = """
<html><body>
<a href="/products">Products</a>
<a href="https://other-site.com/pricing">partner pricing</a>
<a href="/software/jira/pricing?tab=cloud">Jira Pricing</a>
<a href="/software/jira/plans">Plans</a>
</body></html>
"""


class TestFindPricingLink:
    def test_discovers_same_site_pricing_link(self, monkeypatch):
        class Resp:
            status_code = 200
            text = HOMEPAGE_HTML
            url = "https://acme.test/"

        monkeypatch.setattr(evidence.httpx, "get", lambda *a, **k: Resp())
        link = evidence.find_pricing_link("acme.test")
        # off-site link ignored; "pricing" preferred over "plans"; query stripped
        assert link == "https://acme.test/software/jira/pricing"

    def test_returns_none_when_homepage_unreachable(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("down")
        monkeypatch.setattr(evidence.httpx, "get", boom)
        assert evidence.find_pricing_link("acme.test") is None


class TestPricingFallbacks:
    def test_discovered_link_used_when_standard_path_fails(
        self, conn, run_id, monkeypatch
    ):
        def crawl(url, **kwargs):
            if url.endswith("/real-pricing"):
                return _page(url, "Pro $9 per user", "hash-realpricing")
            if "/pricing" in url:
                return CrawlResult(ok=False, url=url, http_status=404,
                                   fetched_at="t", error="HTTP 404")
            return fake_crawl_ok(url)

        monkeypatch.setattr(evidence, "crawl_page", crawl)
        monkeypatch.setattr(evidence, "find_pricing_link",
                            lambda d, n=None: "https://acme.test/real-pricing")
        stored = collect_sources(conn, run_id, None, "acme.test")
        pricing = [(sid, r) for sid, stype, r in stored if stype == "pricing"]
        assert len(pricing) == 2  # failed /pricing attempt + discovered page
        assert pricing[1][1].ok and "Pro $9" in pricing[1][1].raw_text

    def test_rendered_fallback_when_static_extraction_unavailable(
        self, conn, run_id, monkeypatch
    ):
        monkeypatch.setattr(evidence, "crawl_page", fake_crawl_ok)

        calls = {"n": 0}

        def fake_parse(model, system, user, output_format, usage, **kwargs):
            if output_format is PricingFindings:
                calls["n"] += 1
                if calls["n"] == 1:  # static text: nothing extractable
                    return PricingFindings(available=False)
                return PricingFindings(available=True, tiers=[PricingTier(
                    name="Pro", price_text="$25/mo", price_usd=25.0,
                    billing_period="monthly")])
            return CompanyFindings(positioning="x", key_features=["y"])

        monkeypatch.setattr(evidence, "parse", fake_parse)
        monkeypatch.setattr(
            evidence, "crawl_page_rendered",
            lambda url, **k: _page(url, "RENDERED: Pro $25/mo", "hash-rendered"),
        )

        summary = collect_and_extract(conn, run_id, None, "Acme", "acme.test", Usage())
        pricing_row = next(
            fetch_row(conn, "findings", fid) for fid in summary.finding_ids
            if fetch_row(conn, "findings", fid)["dimension"] == "pricing"
        )
        value = json.loads(pricing_row["value_json"])
        assert value["available"] and value["tiers"][0]["price_usd"] == 25.0
        # The finding cites the rendered source, which was stored with the text.
        cited = json.loads(pricing_row["source_ids_json"])
        src = fetch_row(conn, "sources", cited[0])
        assert "RENDERED" in src["raw_text"]

    def test_unavailable_when_render_also_fails(self, conn, run_id, monkeypatch):
        monkeypatch.setattr(evidence, "crawl_page", fake_crawl_ok)

        def fake_parse(model, system, user, output_format, usage, **kwargs):
            if output_format is PricingFindings:
                return PricingFindings(available=False)
            return CompanyFindings(positioning="x", key_features=["y"])

        monkeypatch.setattr(evidence, "parse", fake_parse)
        monkeypatch.setattr(
            evidence, "crawl_page_rendered",
            lambda url, **k: CrawlResult(ok=False, url=url, fetched_at="t",
                                         error="render timeout"),
        )
        summary = collect_and_extract(conn, run_id, None, "Acme", "acme.test", Usage())
        pricing_row = next(
            fetch_row(conn, "findings", fid) for fid in summary.finding_ids
            if fetch_row(conn, "findings", fid)["dimension"] == "pricing"
        )
        assert json.loads(pricing_row["value_json"])["available"] is False
