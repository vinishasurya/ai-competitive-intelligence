# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP5 — Evidence collection & structured extraction (not started)
**Overall:** 5 / 11 checkpoints complete

## Checkpoint board
| # | Checkpoint | Status |
|---|------------|--------|
| CP0 | Project scaffold | ✅ Done (2026-08-27, commit 6eb494e) |
| CP1 | Data model & schemas | ✅ Done (2026-08-27, commit 2247969) |
| CP2 | Research tools (search_web, crawl_page) | ✅ Done (2026-08-27, commit 33fb035) |
| CP3 | Product profiler | ✅ Done (2026-08-27, commit 303100f) |
| CP4 | Competitor discovery, verification, ranking | ✅ Done (2026-08-27, commit cea9c0b) |
| CP5 | Evidence collection & structured extraction | ⬜ Not started |
| CP6 | Report generation & validation | ⬜ Not started |
| CP7 | Report UI | ⬜ Not started |
| CP8 | Evaluation suite (10-product benchmark) | ⬜ Not started |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
Pipeline works live through discovery: URL → grounded profile (Opus) → 3-strategy competitor discovery → website verification (Haiku) → ranked top 5 with reasons, at ~10¢/product. 40 passing tests (`cd backend && uv run pytest`); live checks: `scripts/smoke_cp2.py` … `smoke_cp4.py`. Verified sets: Linear→[Jira, Shortcut, ClickUp, Monday, Plane], Tailscale→[Twingate, ZeroTier, NetBird, Zscaler, Netmaker].

## Next step
CP5: evidence collection & structured extraction — crawl homepage/features/pricing for the product + each verified competitor, store source records, extract normalized findings (features, pricing tiers) with source_ids attached; `extract_pricing` as its own tool. This is where the SQLite tables start being used by the pipeline.

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
