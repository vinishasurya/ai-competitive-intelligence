# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP3 — Product profiler (not started)
**Overall:** 3 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ✅ Done (2026-08-27, commit 6eb494e) |
| CP1 | Data model & schemas | ✅ Done (2026-08-27, commit 2247969) |
| CP2 | Research tools (search_web, crawl_page) | ✅ Done (2026-08-27, commit 33fb035) |
| CP3 | Product profiler | ⬜ Not started |
| CP4 | Competitor discovery, verification, ranking | ⬜ Not started |
| CP5 | Evidence collection & structured extraction | ⬜ Not started |
| CP6 | Report generation & validation | ⬜ Not started |
| CP7 | Report UI | ⬜ Not started |
| CP8 | Evaluation suite (10-product benchmark) | ⬜ Not started |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
Data layer + research tools working: 7-table SQLite schema with tested round-trips, `search_web` (Tavily, key in `backend/.env`) and `crawl_page` (trafilatura extraction, content hashes, 24h disk cache, soft failures) verified live against real pricing pages. 9 passing tests (`cd backend && uv run pytest`); live check: `uv run python scripts/smoke_cp2.py`.

## Next step
CP3: product profiler — URL validation, crawl homepage + discoverable pages (pricing/features/about), extract a structured product profile with Claude structured output.

## Blockers / open questions
- **Need `ANTHROPIC_API_KEY` in `backend/.env` before CP3 can run live.**
