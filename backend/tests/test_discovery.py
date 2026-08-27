"""Offline unit tests for competitor discovery — no network, no API calls."""

import pytest

from app import discovery
from app.discovery import (
    Candidate,
    discover_competitors,
    merge_candidates,
    normalize_domain,
    normalize_name,
    rank,
)
from app.profiler import ProductProfile

PROFILE = ProductProfile(
    name="Acme", domain="acme.test", category="issue tracking software",
    key_features=["issues"],
)


class TestNormalization:
    @pytest.mark.parametrize("raw,expected", [
        ("https://www.asana.com/pricing", "asana.com"),
        ("WWW.Asana.com", "asana.com"),
        ("asana.com/", "asana.com"),
        ("asana.com", "asana.com"),
    ])
    def test_domain(self, raw, expected):
        assert normalize_domain(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("Asana, Inc.", "asana"),
        ("Linear App", "linear"),
        ("ClickUp", "clickup"),
    ])
    def test_name(self, raw, expected):
        assert normalize_name(raw) == expected


def _cand(name, domain, methods, evidence=None):
    return Candidate(
        name=name, domain=domain, discovery_methods=list(methods),
        evidence=evidence or [f"found {name}"],
    )


class TestMerge:
    def test_merges_same_domain_across_strategies(self):
        merged = merge_candidates(
            [
                [_cand("Jira", "atlassian.com", ["model_generated"])],
                [_cand("Jira Software", "www.atlassian.com", ["search"])],
            ],
            "acme.test", "Acme",
        )
        assert len(merged) == 1
        assert set(merged[0].discovery_methods) == {"model_generated", "search"}
        assert len(merged[0].evidence) == 2

    def test_drops_product_itself_by_domain_and_name(self):
        merged = merge_candidates(
            [[
                _cand("Acme", "acme.test", ["search"]),
                _cand("Acme Inc", "acme-mirror.test", ["search"]),
                _cand("Jira", "atlassian.com", ["search"]),
            ]],
            "acme.test", "Acme",
        )
        assert [c.domain for c in merged] == ["atlassian.com"]

    def test_drops_aggregators_and_invalid_domains(self):
        merged = merge_candidates(
            [[
                _cand("G2", "g2.com", ["search"]),
                _cand("Mystery", "notadomain", ["search"]),
                _cand("Jira", "atlassian.com", ["search"]),
            ]],
            "acme.test", "Acme",
        )
        assert [c.domain for c in merged] == ["atlassian.com"]

    def test_sorts_by_strategy_count(self):
        merged = merge_candidates(
            [
                [_cand("A", "a.test", ["model_generated"]), _cand("B", "b.test", ["model_generated"])],
                [_cand("B", "b.test", ["search"])],
            ],
            "acme.test", "Acme",
        )
        assert [c.domain for c in merged] == ["b.test", "a.test"]


class TestRank:
    def test_multi_strategy_beats_slightly_higher_confidence(self):
        one_method = _cand("A", "a.test", ["model_generated"]).model_copy(
            update={"verified": True, "confidence": 0.9}
        )
        three_methods = _cand(
            "B", "b.test", ["model_generated", "search", "comparison_page"]
        ).model_copy(update={"verified": True, "confidence": 0.8})
        assert rank([one_method, three_methods])[0].domain == "b.test"


class TestPipeline:
    def test_full_pipeline_with_fakes(self, monkeypatch):
        monkeypatch.setattr(
            discovery, "model_candidates",
            lambda p, u: [_cand("Jira", "atlassian.com", ["model_generated"]),
                          _cand("Ghost", "ghost.test", ["model_generated"])],
        )
        monkeypatch.setattr(
            discovery, "search_candidates",
            lambda p, u: ([_cand("Jira", "atlassian.com", ["search"]),
                           _cand("Basecamp", "basecamp.com", ["search"])], 3),
        )
        monkeypatch.setattr(
            discovery, "comparison_page_candidates", lambda p, u: ([], 1)
        )

        def fake_verify(cand, profile, usage):
            if cand.domain == "ghost.test":
                raise RuntimeError("site exploded")
            return cand.model_copy(update={
                "verified": True, "relationship": "direct",
                "confidence": 0.9, "why_selected": "same category",
            })

        monkeypatch.setattr(discovery, "verify_candidate", fake_verify)

        result = discover_competitors(PROFILE)
        assert result.ok
        assert result.candidates_considered == 3
        # Jira merged across two strategies ranks first; the exploding
        # candidate was rejected without killing the run.
        assert result.competitors[0].domain == "atlassian.com"
        assert set(result.competitors[0].discovery_methods) == {"model_generated", "search"}
        assert {c.domain for c in result.competitors} == {"atlassian.com", "basecamp.com"}
        assert any("verification error" in (c.why_selected or "") for c in result.rejected)
        assert result.tool_calls == 8  # 1 gen + 3 search + 1 comparison + 3 verify

    def test_caps_at_five_competitors(self, monkeypatch):
        many = [_cand(f"C{i}", f"c{i}.test", ["search"]) for i in range(9)]
        monkeypatch.setattr(discovery, "model_candidates", lambda p, u: [])
        monkeypatch.setattr(discovery, "search_candidates", lambda p, u: (many, 3))
        monkeypatch.setattr(discovery, "comparison_page_candidates", lambda p, u: ([], 1))
        monkeypatch.setattr(
            discovery, "verify_candidate",
            lambda c, p, u: c.model_copy(update={
                "verified": True, "relationship": "direct", "confidence": 0.8,
                "why_selected": "ok",
            }),
        )
        result = discover_competitors(PROFILE)
        assert len(result.competitors) == 5
        assert len(result.rejected) == 4  # verified but cut by the cap

    def test_soft_fails_when_generation_dies(self, monkeypatch):
        def boom(p, u):
            raise RuntimeError("model down")
        monkeypatch.setattr(discovery, "model_candidates", boom)
        result = discover_competitors(PROFILE)
        assert not result.ok and "model down" in result.error
