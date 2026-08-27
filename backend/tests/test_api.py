"""API endpoint tests — pipeline faked, db in tmp_path, no network/API calls."""

import time

import pytest
from fastapi.testclient import TestClient

from app import main
from app.db import connect, init_db, insert_row
from app.models import Claim, Competitor, Product, Run, Source
from app.pipeline import PipelineResult


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "api.db"
    monkeypatch.setattr(main, "connect", lambda *a, **k: connect(db_path))
    conn = connect(db_path)
    init_db(conn)
    conn.close()
    with TestClient(main.app) as test_client:
        yield test_client
    main.JOBS.clear()


def _wait_for(client, job_id, status, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/runs/{job_id}").json()
        if job["status"] == status:
            return job
        time.sleep(0.02)
    raise AssertionError(f"job never reached {status}: {job}")


def test_run_job_lifecycle_success(client, monkeypatch):
    def fake_pipeline(conn, url, on_progress=None):
        on_progress("profiling", "reading site")
        on_progress("report", "writing executive summary")
        return PipelineResult(ok=True, url=url, run_id=42, duration_seconds=1.0)

    monkeypatch.setattr(main, "run_pipeline", fake_pipeline)
    job_id = client.post("/api/runs", json={"url": "acme.test"}).json()["job_id"]
    job = _wait_for(client, job_id, "completed")
    assert job["run_id"] == 42
    assert job["stage"] == "done"


def test_run_job_lifecycle_failure(client, monkeypatch):
    monkeypatch.setattr(
        main, "run_pipeline",
        lambda conn, url, on_progress=None: PipelineResult(
            ok=False, url=url, error="profiling: invalid URL"),
    )
    job_id = client.post("/api/runs", json={"url": "localhost"}).json()["job_id"]
    job = _wait_for(client, job_id, "failed")
    assert "invalid URL" in job["error"]


def test_unknown_job_and_run_404(client):
    assert client.get("/api/runs/nope").status_code == 404
    assert client.get("/api/reports/9999").status_code == 404


def test_report_endpoint_serves_stored_run(client, tmp_path):
    conn = connect(tmp_path / "api.db")
    product_id = insert_row(conn, "products", Product(
        url="https://acme.test", domain="acme.test", name="Acme",
        category="issue tracking",
    ).to_row())
    run_id = insert_row(conn, "runs", Run(
        product_id=product_id, status="completed", cost_cents=35,
    ).to_row())
    insert_row(conn, "competitors", Competitor(
        run_id=run_id, name="Jira", domain="atlassian.com",
        relationship="direct", confidence=0.9, verified=True,
        discovery_methods=["search"],
    ).to_row())
    source_id = insert_row(conn, "sources", Source(
        run_id=run_id, url="https://acme.test/pricing", source_type="pricing",
        http_status=200,
    ).to_row())
    insert_row(conn, "claims", Claim(
        run_id=run_id, section="pricing_comparison",
        text="Acme Pro costs $12.", claim_type="verified",
        source_ids=[source_id], confidence=0.95,
    ).to_row())
    conn.close()

    payload = client.get(f"/api/reports/{run_id}").json()
    assert payload["product"]["name"] == "Acme"
    assert payload["competitors"][0]["name"] == "Jira"
    claim = payload["sections"]["pricing_comparison"][0]
    assert claim["claim_type"] == "verified"
    assert claim["source_ids"] == [source_id]
    assert payload["sources"][str(source_id)]["source_type"] == "pricing"
    assert payload["citation_coverage"] == 1.0
    assert payload["flags"] == []
