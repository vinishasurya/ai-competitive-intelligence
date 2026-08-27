# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP7 — Report UI (not started)
**Overall:** 7 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ✅ Done (2026-08-27, commit 6eb494e) |
| CP1 | Data model & schemas | ✅ Done (2026-08-27, commit 2247969) |
| CP2 | Research tools (search_web, crawl_page) | ✅ Done (2026-08-27, commit 33fb035) |
| CP3 | Product profiler | ✅ Done (2026-08-27, commit 303100f) |
| CP4 | Competitor discovery, verification, ranking | ✅ Done (2026-08-27, commit cea9c0b) |
| CP5 | Evidence collection & structured extraction | ✅ Done (2026-08-27, commit f4ec9c5) |
| CP6 | Report generation & validation | ✅ Done (2026-08-27, commit 59c9a13) |
| CP7 | Report UI | ⬜ Not started |
| CP8 | Evaluation suite (10-product benchmark) | ⬜ Not started |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
**The backend is end-to-end complete**: `run_pipeline(conn, url)` goes URL → profile → discovery → evidence → 4-section report of structured, cited claims + validation flags, all stored in SQLite. Live measured: ~2.5 min and 35–40¢ per report, 100% citation coverage on all 3 test products, validator catches real issues. 57 passing tests; `scripts/smoke_cp6.py <url>` runs the whole thing.

## Next step
CP7: report UI — FastAPI endpoints (start run, poll status, fetch report) + Next.js pages: URL input → progress → rendered report with trust labels (Verified/Reported/Interpretation), claim-level citation links with retrieval dates, shareable link. Screenshot required to close.

## Known failure modes (CP9 candidates)
- Pricing at non-standard paths missed (Jira's is at /software/jira/pricing, not /pricing) → shows "unavailable" despite public pricing. Fix idea: discover pricing URLs from homepage links or search.
- JS-rendered pricing (Notion) yields tier names without numbers — honest but incomplete.

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
