"""Benchmark evaluation — design doc §13. The eval system is a product feature.

Scores a completed pipeline run against manually labeled ground truth:
- category accuracy (profile category matches accepted keywords)
- competitor precision (strict: clearly-relevant only; lenient: not clearly
  irrelevant — the 'defensible' rubric from §15)
- pricing accuracy (extracted tiers vs prices verified on live pages)
- citation coverage / flags / latency / cost come from the run itself
Results are also written to the eval_results table.
"""

import json
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.db import insert_row
from app.discovery import normalize_domain
from app.models import EvalResult


# ---------- benchmark labels ----------

class PricingTruth(BaseModel):
    domain: str
    tier_contains: str
    price_usd: float


class ProductLabel(BaseModel):
    url: str
    group: str
    category_keywords: list[str]
    relevant: list[str]
    irrelevant: list[str]
    pricing_truth: list[PricingTruth] = Field(default_factory=list)


def load_benchmark(path: str | Path) -> list[ProductLabel]:
    data = json.loads(Path(path).read_text())
    return [ProductLabel(**p) for p in data["products"]]


# ---------- per-metric scoring ----------

def score_category(category: str | None, keywords: list[str]) -> bool:
    if not category:
        return False
    lowered = category.lower()
    return any(k.lower() in lowered for k in keywords)


class CompetitorScore(BaseModel):
    name: str
    domain: str
    label: Literal["relevant", "defensible_unknown", "clearly_irrelevant"]


def score_competitors(
    surfaced: list[tuple[str, str]], relevant: list[str], irrelevant: list[str]
) -> list[CompetitorScore]:
    rel = {normalize_domain(d) for d in relevant}
    irr = {normalize_domain(d) for d in irrelevant}
    scores = []
    for name, domain in surfaced:
        d = normalize_domain(domain)
        label = ("relevant" if d in rel
                 else "clearly_irrelevant" if d in irr
                 else "defensible_unknown")
        scores.append(CompetitorScore(name=name, domain=d, label=label))
    return scores


class PricingScore(BaseModel):
    domain: str
    tier_contains: str
    expected: float
    got: float | None = None
    status: Literal["correct", "incorrect", "extraction_unavailable", "not_evaluated"]


def score_pricing(
    conn: sqlite3.Connection, run_id: int, product_domain: str,
    truths: list[PricingTruth],
) -> list[PricingScore]:
    """Compare labeled tier prices against this run's stored pricing findings."""
    product_domain = normalize_domain(product_domain)
    competitors = {
        normalize_domain(r["domain"]): r["id"]
        for r in conn.execute(
            "SELECT id, domain FROM competitors WHERE run_id = ?", (run_id,)
        ).fetchall()
    }

    def pricing_finding(domain: str) -> dict | None:
        if domain == product_domain:
            cond, args = "competitor_id IS NULL", (run_id,)
        elif domain in competitors:
            cond, args = "competitor_id = ?", (run_id, competitors[domain])
        else:
            return None
        row = conn.execute(
            f"SELECT value_json FROM findings WHERE run_id = ? AND {cond} "
            f"AND dimension = 'pricing'",
            args if domain != product_domain else (run_id,),
        ).fetchone()
        return json.loads(row["value_json"]) if row else None

    scores = []
    for truth in truths:
        domain = normalize_domain(truth.domain)
        if domain != product_domain and domain not in competitors:
            scores.append(PricingScore(
                domain=domain, tier_contains=truth.tier_contains,
                expected=truth.price_usd, status="not_evaluated",
            ))
            continue
        value = pricing_finding(domain)
        if not value or not value.get("available"):
            scores.append(PricingScore(
                domain=domain, tier_contains=truth.tier_contains,
                expected=truth.price_usd, status="extraction_unavailable",
            ))
            continue
        tier = next(
            (t for t in value.get("tiers", [])
             if truth.tier_contains.lower() in (t.get("name") or "").lower()),
            None,
        )
        got = tier.get("price_usd") if tier else None
        correct = got is not None and abs(got - truth.price_usd) < 0.01
        scores.append(PricingScore(
            domain=domain, tier_contains=truth.tier_contains,
            expected=truth.price_usd, got=got,
            status="correct" if correct else "incorrect",
        ))
    return scores


# ---------- assembling one product's evaluation ----------

class ProductEval(BaseModel):
    url: str
    group: str
    ok: bool
    error: str | None = None
    run_id: int | None = None
    category: str | None = None
    category_ok: bool | None = None
    competitors: list[CompetitorScore] = Field(default_factory=list)
    strict_precision: float | None = None
    lenient_precision: float | None = None
    pricing: list[PricingScore] = Field(default_factory=list)
    citation_coverage: float | None = None
    flag_count: int = 0
    latency_s: float = 0.0
    cost_cents: float = 0.0
    tokens: int = 0

    @property
    def pricing_evaluated(self) -> int:
        return sum(1 for p in self.pricing if p.status != "not_evaluated")

    @property
    def pricing_correct(self) -> int:
        return sum(1 for p in self.pricing if p.status == "correct")


def evaluate_product(conn, label: ProductLabel, result) -> ProductEval:
    """Score one PipelineResult against its benchmark label."""
    ev = ProductEval(
        url=label.url, group=label.group, ok=result.ok, error=result.error,
        run_id=result.run_id, category=result.category,
        latency_s=round(result.duration_seconds, 1),
        cost_cents=round(result.cost_cents, 1), tokens=result.total_tokens,
    )
    if not result.ok:
        return ev
    ev.category_ok = score_category(result.category, label.category_keywords)
    ev.competitors = score_competitors(
        [(c["name"], c["domain"]) for c in result.competitors],
        label.relevant, label.irrelevant,
    )
    n = len(ev.competitors)
    if n:
        ev.strict_precision = sum(c.label == "relevant" for c in ev.competitors) / n
        ev.lenient_precision = sum(
            c.label != "clearly_irrelevant" for c in ev.competitors
        ) / n
    product_domain = normalize_domain(label.url)
    ev.pricing = score_pricing(conn, result.run_id, product_domain, label.pricing_truth)
    if result.report:
        ev.citation_coverage = result.report.citation_coverage
        ev.flag_count = len(result.report.flags)
    return ev


def record_eval_results(conn, ev: ProductEval) -> None:
    """Persist metric rows into the eval_results table for this run."""
    if ev.run_id is None:
        return
    metrics = {
        "category_accuracy": 1.0 if ev.category_ok else 0.0,
        "competitor_precision_strict": ev.strict_precision,
        "competitor_precision_lenient": ev.lenient_precision,
        "citation_coverage": ev.citation_coverage,
        "validation_flags": float(ev.flag_count),
        "latency_seconds": ev.latency_s,
        "cost_cents": ev.cost_cents,
    }
    if ev.pricing_evaluated:
        metrics["pricing_accuracy"] = ev.pricing_correct / ev.pricing_evaluated
    for metric, score in metrics.items():
        if score is None:
            continue
        insert_row(conn, "eval_results", EvalResult(
            run_id=ev.run_id, metric=metric, score=score,
            details={"url": ev.url},
        ).to_row())


# ---------- aggregate ----------

def aggregate(evals: list[ProductEval]) -> dict:
    done = [e for e in evals if e.ok]

    def mean(values):
        values = [v for v in values if v is not None]
        return round(sum(values) / len(values), 3) if values else None

    pricing_eval = sum(e.pricing_evaluated for e in done)
    pricing_correct = sum(e.pricing_correct for e in done)
    return {
        "products": len(evals),
        "completed": len(done),
        "category_accuracy": mean([e.category_ok for e in done]),
        "competitor_precision_strict": mean([e.strict_precision for e in done]),
        "competitor_precision_lenient": mean([e.lenient_precision for e in done]),
        "pricing_tiers_evaluated": pricing_eval,
        "pricing_accuracy": round(pricing_correct / pricing_eval, 3) if pricing_eval else None,
        "citation_coverage": mean([e.citation_coverage for e in done]),
        "total_validation_flags": sum(e.flag_count for e in done),
        "mean_latency_s": mean([e.latency_s for e in done]),
        "mean_cost_cents": mean([e.cost_cents for e in done]),
    }
