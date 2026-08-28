# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP9 — Iterate on worst failure mode (not started; manual review first)
**Overall:** 9 / 11 checkpoints complete

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
| CP7 | Report UI | ✅ Done (2026-08-27, commit c5c90e0) |
| CP8 | Evaluation suite (10-product benchmark) | ✅ Done (2026-08-27, commit 0a32a3a) |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
**Baseline benchmark published** (`eval/results/baseline.md` — evaluation runs are named `baseline` / `post-fix`, both measuring the V1 product): 10/10 products, category accuracy 100%, competitor precision 84% strict / 100% lenient, pricing 16/16 labeled tiers, citation coverage 100%, 1 flag, mean 142s / 34¢ per report — all design-doc targets exceeded. 66 passing tests. Product runs in browser at localhost:3000.

## Manual review done (2026-08-27)
30 claims reviewed by hand: **citation validity 86.7%, hallucination rate 0%**. All 4 invalids are pricing claims; 3 are JS-rendered pricing pages (Slack, Notion, Lovable). Still open: benchmark label audit (`eval/benchmark.json`) — optional before post-fix re-score; and the reason for the Linear pricing invalid mark (ask Ravi's team).

## Next step
CP9: fix the confirmed highest-impact failure mode — **pricing-page retrieval** (JS-rendered pages + non-standard paths like Jira's). Candidate fixes: headless-browser rendering fallback for pricing pages, and/or pricing-URL discovery from homepage links/search. Then re-run benchmark as post-fix for the before/after bullet.

## Known failure modes (CP9 candidates)
- Pricing at non-standard paths missed (Jira's is at /software/jira/pricing, not /pricing) → shows "unavailable" despite public pricing. Fix idea: discover pricing URLs from homepage links or search.
- JS-rendered pricing (Notion) yields tier names without numbers — honest but incomplete.

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
