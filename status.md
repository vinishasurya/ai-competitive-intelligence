# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP2 — Research tools (not started)
**Overall:** 2 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ✅ Done (2026-08-27, commit 6eb494e) |
| CP1 | Data model & schemas | ✅ Done (2026-08-27, commit 2247969) |
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
Data layer is in place: 7-table SQLite schema (`backend/app/schema.sql`), Pydantic models with lossless row conversion (`backend/app/models.py`), db helpers (`backend/app/db.py`), 3 passing tests (`cd backend && uv run pytest`). Dev servers: `uv run uvicorn app.main:app --port 8000` (backend/), `npm run dev` (frontend/).

## Next step
CP2: build `search_web` and `crawl_page` as independently testable tools. First decision: pick the search API (Brave / Tavily / Serper) and get a key into `backend/.env`.

## Blockers / open questions
- Pick a search API at CP2 (Brave / Tavily / Serper — weigh per-query cost against the $1.20/report budget).
- Need `ANTHROPIC_API_KEY` in `backend/.env` (copy from `.env.example`) before CP3.
