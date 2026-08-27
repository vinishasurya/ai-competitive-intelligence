"""API server: start research runs, report progress, serve stored reports.

Runs execute on a background thread (V1 is single-user; no job queue by
design). Job state lives in memory; completed reports live in SQLite, so
report links stay stable across restarts.
"""

import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.db import connect, init_db
from app.pipeline import run_pipeline
from app.report import report_payload

JOBS: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    init_db(conn)
    conn.close()
    yield


app = FastAPI(title="AI Competitive Intelligence API", version="0.2.0",
              lifespan=lifespan)

# The Next.js dev server runs on a different port, so the browser blocks
# cross-origin requests unless the API explicitly allows them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    url: str


def _execute(job_id: str, url: str) -> None:
    job = JOBS[job_id]
    job["status"] = "running"
    conn = connect()  # SQLite connections are per-thread
    try:
        result = run_pipeline(
            conn, url,
            on_progress=lambda stage, detail: job.update(stage=stage, detail=detail),
        )
        job["run_id"] = result.run_id
        if result.ok:
            job.update(status="completed", stage="done",
                       detail=f"report ready ({result.duration_seconds:.0f}s)")
        else:
            job.update(status="failed", error=result.error)
    except Exception as exc:
        job.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    finally:
        conn.close()


@app.post("/api/runs")
def start_run(body: RunRequest) -> dict:
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "status": "queued", "stage": "queued", "detail": "starting...",
        "run_id": None, "error": None,
    }
    threading.Thread(target=_execute, args=(job_id, body.url), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/runs/{job_id}")
def get_job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return job


@app.get("/api/reports/{run_id}")
def get_report(run_id: int) -> dict:
    conn = connect()
    try:
        payload = report_payload(conn, run_id)
    finally:
        conn.close()
    if payload is None:
        raise HTTPException(status_code=404, detail="unknown run")
    return payload


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "ci-backend", "version": "0.2.0"}
