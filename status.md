# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP4 — Competitor discovery, verification, ranking (not started)
**Overall:** 4 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ✅ Done (2026-08-27, commit 6eb494e) |
| CP1 | Data model & schemas | ✅ Done (2026-08-27, commit 2247969) |
| CP2 | Research tools (search_web, crawl_page) | ✅ Done (2026-08-27, commit 33fb035) |
| CP3 | Product profiler | ✅ Done (2026-08-27, commit 303100f) |
| CP4 | Competitor discovery, verification, ranking | ⬜ Not started |
| CP5 | Evidence collection & structured extraction | ⬜ Not started |
| CP6 | Report generation & validation | ⬜ Not started |
| CP7 | Report UI | ⬜ Not started |
| CP8 | Evaluation suite (10-product benchmark) | ⬜ Not started |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
Pipeline through profiling works live: schema + research tools + product profiler (`build_profile(url)` → grounded structured profile via Opus 4.8, ~3.8¢/product). 25 passing tests (`cd backend && uv run pytest`); live checks: `scripts/smoke_cp2.py`, `scripts/smoke_cp3.py`. Both API keys working in `backend/.env`.

## Next step
CP4: competitor discovery — model-generated leads + search queries ("alternatives to X") + comparison pages → dedupe by name/domain → verify each candidate's site addresses the same category → rank → top 5 with "why selected". Highest-risk checkpoint; test on 3 products.

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
