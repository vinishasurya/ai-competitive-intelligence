"""Offline tests for report generation & validation — no network/API."""

import pytest

from app import pipeline, report
from app.db import connect, fetch_row, init_db, insert_row
from app.models import Claim, Competitor, Finding, Product, Run, Source
from app.report import (
    ClaimOut,
    SectionClaims,
    generate_report,
    load_bundle,
    validate_run,
)


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def seeded(conn):
    """Product + run + competitor + sources + findings, ready for reporting."""
    product_id = insert_row(conn, "products", Product(
        url="https://acme.test", domain="acme.test", name="Acme",
        category="issue tracking",
    ).to_row())
    run_id = insert_row(conn, "runs", Run(product_id=product_id, status="running").to_row())
    comp_id = insert_row(conn, "competitors", Competitor(
        run_id=run_id, name="Jira", domain="atlassian.com",
        relationship="direct", confidence=0.9, verified=True,
    ).to_row())
    home_id = insert_row(conn, "sources", Source(
        run_id=run_id, url="https://acme.test", source_type="homepage",
        raw_text="Acme homepage", http_status=200,
    ).to_row())
    pricing_id = insert_row(conn, "sources", Source(
        run_id=run_id, url="https://acme.test/pricing", source_type="pricing",
        raw_text="Pro $12", http_status=200,
    ).to_row())
    insert_row(conn, "findings", Finding(
        run_id=run_id, dimension="features", value=["issues"], source_ids=[home_id],
    ).to_row())
    insert_row(conn, "findings", Finding(
        run_id=run_id, competitor_id=comp_id, dimension="pricing",
        value={"available": True}, source_ids=[pricing_id],
    ).to_row())
    return {"run_id": run_id, "comp_id": comp_id,
            "home_id": home_id, "pricing_id": pricing_id}


class TestValidate:
    def _claim(self, conn, run_id, section, text, claim_type, source_ids):
        return insert_row(conn, "claims", Claim(
            run_id=run_id, section=section, text=text,
            claim_type=claim_type, source_ids=source_ids, confidence=0.9,
        ).to_row())

    def test_clean_claims_produce_no_flags(self, conn, seeded):
        s = seeded
        self._claim(conn, s["run_id"], "executive_summary",
                    "Acme is an issue tracker.", "verified", [s["home_id"]])
        self._claim(conn, s["run_id"], "pricing_comparison",
                    "Acme's Pro tier costs $12.", "verified", [s["pricing_id"]])
        self._claim(conn, s["run_id"], "executive_summary",
                    "Acme should focus on enterprise.", "interpretation", [s["home_id"]])
        assert validate_run(conn, s["run_id"]) == []

    def test_factual_claim_without_sources(self, conn, seeded):
        s = seeded
        self._claim(conn, s["run_id"], "executive_summary",
                    "Acme has many users.", "verified", [])
        flags = validate_run(conn, s["run_id"])
        assert [f.flag for f in flags] == ["factual_claim_without_sources"]

    def test_dangling_source_id(self, conn, seeded):
        s = seeded
        self._claim(conn, s["run_id"], "feature_comparison",
                    "Acme tracks issues.", "verified", [9999])
        flags = validate_run(conn, s["run_id"])
        assert [f.flag for f in flags] == ["dangling_source_id"]

    def test_source_from_other_run_is_dangling(self, conn, seeded):
        s = seeded
        other_product = insert_row(conn, "products", Product(
            url="https://other.test", domain="other.test").to_row())
        other_run = insert_row(conn, "runs", Run(product_id=other_product).to_row())
        foreign_source = insert_row(conn, "sources", Source(
            run_id=other_run, url="https://other.test", source_type="homepage",
        ).to_row())
        self._claim(conn, s["run_id"], "executive_summary",
                    "Acme is a tracker.", "verified", [foreign_source])
        assert [f.flag for f in validate_run(conn, s["run_id"])] == ["dangling_source_id"]

    def test_pricing_claim_without_pricing_source(self, conn, seeded):
        s = seeded
        self._claim(conn, s["run_id"], "pricing_comparison",
                    "Acme costs $12 per user.", "verified", [s["home_id"]])
        assert [f.flag for f in validate_run(conn, s["run_id"])] == [
            "pricing_claim_without_pricing_source"
        ]

    def test_judgment_language_in_verified_claim(self, conn, seeded):
        s = seeded
        self._claim(conn, s["run_id"], "feature_comparison",
                    "Acme is the best choice for teams.", "verified", [s["home_id"]])
        assert [f.flag for f in validate_run(conn, s["run_id"])] == [
            "possible_unlabeled_interpretation"
        ]


class TestBundleAndGeneration:
    def test_bundle_shape(self, conn, seeded):
        bundle = load_bundle(conn, seeded["run_id"])
        assert bundle["subject"] == "Acme"
        assert [c["role"] for c in bundle["companies"]] == ["subject", "competitor"]
        assert bundle["companies"][0]["findings"][0]["dimension"] == "features"
        assert str(seeded["pricing_id"]) in bundle["sources"]

    def test_generate_report_stores_claims_and_computes_coverage(
        self, conn, seeded, monkeypatch
    ):
        s = seeded

        def fake_generate_section(section, bundle, usage):
            if section == "pricing_comparison":
                return SectionClaims(claims=[ClaimOut(
                    text="Acme Pro costs $12.", claim_type="verified",
                    source_ids=[s["pricing_id"]], confidence=0.95,
                )])
            return SectionClaims(claims=[
                ClaimOut(text=f"Fact for {section}.", claim_type="verified",
                         source_ids=[s["home_id"]], confidence=0.9),
                ClaimOut(text=f"Analysis for {section}.", claim_type="interpretation",
                         source_ids=[s["home_id"]], confidence=0.7),
            ])

        monkeypatch.setattr(report, "generate_section", fake_generate_section)
        result = generate_report(conn, s["run_id"])

        assert result.ok
        assert set(result.sections) == set(report.SECTIONS)
        assert result.flags == []
        assert result.citation_coverage == 1.0
        stored = conn.execute(
            "SELECT COUNT(*) c FROM claims WHERE run_id=?", (s["run_id"],)
        ).fetchone()["c"]
        assert stored == 7  # 3 sections x 2 + pricing x 1

    def test_generation_failure_soft_fails(self, conn, seeded, monkeypatch):
        def boom(section, bundle, usage):
            raise RuntimeError("model down")
        monkeypatch.setattr(report, "generate_section", boom)
        result = generate_report(conn, seeded["run_id"])
        assert not result.ok and "model down" in result.error


class TestPipeline:
    def test_discovery_failure_marks_run_failed(self, conn, monkeypatch):
        from app.discovery import DiscoveryResult
        from app.profiler import ProductProfile, ProfileResult

        profile = ProductProfile(name="Acme", domain="acme.test", category="tracking")
        monkeypatch.setattr(
            pipeline, "build_profile",
            lambda url: ProfileResult(ok=True, url="https://acme.test",
                                      profile=profile, cost_cents=1.0),
        )
        monkeypatch.setattr(
            pipeline, "discover_competitors",
            lambda p: DiscoveryResult(ok=False, product_domain="acme.test",
                                      error="search api down"),
        )
        result = pipeline.run_pipeline(conn, "acme.test")
        assert not result.ok and "search api down" in result.error
        run = fetch_row(conn, "runs", result.run_id)
        assert run["status"] == "failed"
        assert "search api down" in run["error"]


def test_clean_text_removes_dashes():
    from app.report import _clean_text
    assert _clean_text("fast — and cheap") == "fast, and cheap"
    assert _clean_text("2024—2026 range") == "2024-2026 range"
    assert _clean_text("mid – tier") == "mid, tier"
    assert "—" not in _clean_text("a — b—c — d")
