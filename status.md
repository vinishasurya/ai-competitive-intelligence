# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP1 — Data model & schemas (not started)
**Overall:** 1 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ✅ Done (2026-08-27, commit 6eb494e) |
| CP1 | Data model & schemas | ⬜ Not started |
| CP2 | Research tools (search_web, crawl_page) | ⬜ Not started |
| CP3 | Product profiler | ⬜ Not started |
| CP4 | Competitor discovery, verification, ranking | ⬜ Not started |
| CP5 | Evidence collection & structured extraction | ⬜ Not started |
| CP6 | Report generation & validation | ⬜ Not started |
| CP7 | Report UI | ⬜ Not started |
| CP8 | Evaluation suite (10-product benchmark) | ⬜ Not started |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
Repo scaffolded and verified end-to-end: FastAPI backend (`uv run uvicorn app.main:app --port 8000` from `backend/`) and Next.js frontend (`npm run dev` from `frontend/`) run locally; homepage fetches `/api/health` and shows a green status line.

## Next step
CP1: write the SQLite schema (products, runs, competitors, sources, findings, claims, eval_results per design doc §12), Pydantic models, and a round-trip smoke test.

## Blockers / open questions
- Pick a search API at CP2 (Brave / Tavily / Serper — weigh per-query cost against the $1.20/report budget).
- Need `ANTHROPIC_API_KEY` in `backend/.env` (copy from `.env.example`) before CP3.
