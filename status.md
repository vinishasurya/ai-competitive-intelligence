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
**v1 benchmark published** (`eval/results/v1.md`): 10/10 products, category accuracy 100%, competitor precision 84% strict / 100% lenient, pricing 16/16 labeled tiers, citation coverage 100%, 1 flag, mean 142s / 34¢ per report — all design-doc targets exceeded. 66 passing tests. Product runs in browser at localhost:3000.

## Next step — TWO HUMAN TASKS, then CP9
1. **Manual review** (`eval/results/v1_manual_review.md`): open each sampled claim's citations, mark valid/invalid/hallucination → produces the citation-validity + hallucination-rate numbers.
2. **Label audit** (`eval/benchmark.json`): labels were Claude-drafted; the 8 strict-precision misses look like label gaps (Google Chat, Power Apps, Amazon Q, ClickUp-for-Airtable…) — approve or amend, then metrics can be re-scored from the stored v1.db without re-running pipelines.
Then CP9: fix highest-impact failure mode (leading candidate: pricing pages at non-standard paths, e.g. Jira) → re-run as v2 → before/after resume bullet.

## Known failure modes (CP9 candidates)
- Pricing at non-standard paths missed (Jira's is at /software/jira/pricing, not /pricing) → shows "unavailable" despite public pricing. Fix idea: discover pricing URLs from homepage links or search.
- JS-rendered pricing (Notion) yields tier names without numbers — honest but incomplete.

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
