"""Offline tests for benchmark evaluation metrics."""

import pytest

from app.db import connect, init_db, insert_row
from app.evaluation import (
    PricingTruth,
    ProductEval,
    aggregate,
    score_category,
    score_competitors,
    score_pricing,
)
from app.models import Competitor, Finding, Product, Run


class TestCategory:
    def test_keyword_match_case_insensitive(self):
        assert score_category("Project Management software for teams",
                              ["project management"])

    def test_no_match(self):
        assert not score_category("payroll software", ["project management"])
        assert not score_category(None, ["x"])


class TestCompetitors:
    def test_three_way_labeling_with_normalization(self):
        scores = score_competitors(
            [("Jira", "www.atlassian.com"), ("Mystery", "unknown.io"),
             ("Figma", "figma.com")],
            relevant=["atlassian.com"], irrelevant=["figma.com"],
        )
        assert [s.label for s in scores] == [
            "relevant", "defensible_unknown", "clearly_irrelevant"
        ]


@pytest.fixture
def seeded(tmp_path):
    conn = connect(tmp_path / "eval.db")
    init_db(conn)
    product_id = insert_row(conn, "products", Product(
        url="https://acme.test", domain="acme.test", name="Acme").to_row())
    run_id = insert_row(conn, "runs", Run(product_id=product_id).to_row())
    comp_id = insert_row(conn, "competitors", Competitor(
        run_id=run_id, name="Rival", domain="rival.test", verified=True).to_row())
    insert_row(conn, "findings", Finding(
        run_id=run_id, dimension="pricing",
        value={"available": True, "tiers": [
            {"name": "Pro Plan", "price_usd": 12.0},
            {"name": "Enterprise", "price_usd": None},
        ]},
    ).to_row())
    insert_row(conn, "findings", Finding(
        run_id=run_id, competitor_id=comp_id, dimension="pricing",
        value={"available": False, "tiers": []},
    ).to_row())
    yield conn, run_id
    conn.close()


class TestPricing:
    def test_all_statuses(self, seeded):
        conn, run_id = seeded
        scores = score_pricing(conn, run_id, "acme.test", [
            PricingTruth(domain="acme.test", tier_contains="Pro", price_usd=12.0),
            PricingTruth(domain="acme.test", tier_contains="Pro", price_usd=99.0),
            PricingTruth(domain="acme.test", tier_contains="Ghost Tier", price_usd=5.0),
            PricingTruth(domain="rival.test", tier_contains="Basic", price_usd=8.0),
            PricingTruth(domain="absent.test", tier_contains="Any", price_usd=1.0),
        ])
        assert [s.status for s in scores] == [
            "correct",                  # price matches
            "incorrect",                # wrong expected price
            "incorrect",                # tier not found
            "extraction_unavailable",   # rival's pricing finding unavailable
            "not_evaluated",            # company never surfaced in the run
        ]


class TestAggregate:
    def test_means_and_pricing_totals(self):
        evals = [
            ProductEval(url="a", group="g", ok=True, category_ok=True,
                        strict_precision=0.8, lenient_precision=1.0,
                        citation_coverage=1.0, latency_s=100, cost_cents=30,
                        pricing=[]),
            ProductEval(url="b", group="g", ok=True, category_ok=False,
                        strict_precision=0.6, lenient_precision=0.8,
                        citation_coverage=0.9, latency_s=200, cost_cents=50,
                        pricing=[]),
            ProductEval(url="c", group="g", ok=False, error="boom"),
        ]
        agg = aggregate(evals)
        assert agg["completed"] == 2
        assert agg["category_accuracy"] == 0.5
        assert agg["competitor_precision_strict"] == 0.7
        assert agg["mean_latency_s"] == 150
        assert agg["pricing_accuracy"] is None  # nothing evaluated
