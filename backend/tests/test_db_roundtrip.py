"""Insert one realistic record into every table, read it back, and verify
the model <-> row conversion (including JSON columns) is lossless."""

import sqlite3

import pytest

from app.db import connect, fetch_row, init_db, insert_row
from app.models import Claim, Competitor, EvalResult, Finding, Product, Run, Source


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    init_db(conn)
    yield conn
    conn.close()


def roundtrip(conn, table, model):
    row_id = insert_row(conn, table, model.to_row())
    loaded = type(model).from_row(fetch_row(conn, table, row_id))
    assert loaded == model.model_copy(update={"id": row_id})
    return row_id


def test_all_tables_roundtrip(conn):
    product_id = roundtrip(
        conn,
        "products",
        Product(
            url="https://linear.app",
            domain="linear.app",
            name="Linear",
            category="project management software",
            profile={"target_customer": "software teams", "key_features": ["issues", "roadmaps"]},
        ),
    )

    run_id = roundtrip(conn, "runs", Run(product_id=product_id, status="running"))

    competitor_id = roundtrip(
        conn,
        "competitors",
        Competitor(
            run_id=run_id,
            name="Jira",
            domain="atlassian.com",
            relationship="direct",
            confidence=0.92,
            discovery_methods=["model_generated", "search_alternatives"],
            verified=True,
        ),
    )

    source_id = roundtrip(
        conn,
        "sources",
        Source(
            run_id=run_id,
            competitor_id=competitor_id,
            url="https://www.atlassian.com/software/jira/pricing",
            source_type="pricing",
            raw_text="Standard $7.53 per user/month...",
            http_status=200,
            content_hash="abc123",
        ),
    )

    roundtrip(
        conn,
        "findings",
        Finding(
            run_id=run_id,
            competitor_id=competitor_id,
            dimension="pricing",
            value={"tier": "Standard", "price_usd": 7.53, "billing": "monthly"},
            source_ids=[source_id],
        ),
    )

    roundtrip(
        conn,
        "claims",
        Claim(
            run_id=run_id,
            section="pricing_comparison",
            text="Jira's Standard tier costs $7.53 per user per month.",
            claim_type="verified",
            source_ids=[source_id],
            confidence=0.95,
        ),
    )

    roundtrip(
        conn,
        "eval_results",
        EvalResult(
            run_id=run_id,
            metric="competitor_precision",
            score=0.8,
            details={"relevant": 4, "total": 5},
        ),
    )


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        insert_row(conn, "runs", Run(product_id=999).to_row())


def test_invalid_status_rejected_by_db(conn):
    product_id = insert_row(
        conn, "products", Product(url="https://x.com", domain="x.com").to_row()
    )
    row = Run(product_id=product_id).to_row()
    row["status"] = "bogus"  # bypass Pydantic to prove the DB CHECK also guards
    with pytest.raises(sqlite3.IntegrityError):
        insert_row(conn, "runs", row)
