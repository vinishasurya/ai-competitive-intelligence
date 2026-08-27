# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP6 — Report generation & validation (not started)
**Overall:** 6 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ✅ Done (2026-08-27, commit 6eb494e) |
| CP1 | Data model & schemas | ✅ Done (2026-08-27, commit 2247969) |
| CP2 | Research tools (search_web, crawl_page) | ✅ Done (2026-08-27, commit 33fb035) |
| CP3 | Product profiler | ✅ Done (2026-08-27, commit 303100f) |
| CP4 | Competitor discovery, verification, ranking | ✅ Done (2026-08-27, commit cea9c0b) |
| CP5 | Evidence collection & structured extraction | ✅ Done (2026-08-27, commit f4ec9c5) |
| CP6 | Report generation & validation | ⬜ Not started |
| CP7 | Report UI | ⬜ Not started |
| CP8 | Evaluation suite (10-product benchmark) | ⬜ Not started |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
Pipeline works live through evidence: URL → profile → discovery → per-company sources stored in SQLite (incl. failed attempts) → positioning/features/pricing findings each citing source_ids. Integrity verified: 0 dangling refs across a 3-product run; pricing spot-checks match live pages; honest "unavailable" where pages are JS-hidden or at non-standard paths. ~13¢/product. 47 passing tests; live checks `scripts/smoke_cp2.py` … `smoke_cp5.py`.

## Next step
CP6: report generation — 4 sections generated from stored findings only, model returns structured claims (text, claim_type verified/reported/interpretation, source_ids, confidence) stored in the claims table; pre-display validation flags (claims without sources, dangling source_ids, pricing claims without primary source, unlabeled interpretation).

## Known failure modes (CP9 candidates)
- Pricing at non-standard paths missed (Jira's is at /software/jira/pricing, not /pricing) → shows "unavailable" despite public pricing. Fix idea: discover pricing URLs from homepage links or search.
- JS-rendered pricing (Notion) yields tier names without numbers — honest but incomplete.

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
