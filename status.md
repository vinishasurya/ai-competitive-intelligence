# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP0 — Project scaffold (not started)
**Overall:** 0 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ⬜ Not started |
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
Workspace initialized: design docs in `docs/`, CLAUDE.md / journal.md / status.md created. No code exists yet.

## Next step
Start CP0: scaffold `backend/` (FastAPI) + `frontend/` (Next.js) + `eval/`, init git, confirm both dev servers run and talk to each other.

## Blockers / open questions
- Need to pick a search API for CP2 (options: Brave Search API, Tavily, Serper — decide at CP2, weigh cost per query against the $1.20/report budget).
- Need an Anthropic API key in `.env` by CP3.
