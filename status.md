# Status — AI Competitive Intelligence Platform (V1)

**Last updated:** 2026-08-27
**Current checkpoint:** CP8 — Evaluation suite (not started)
**Overall:** 8 / 11 checkpoints complete

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
| CP8 | Evaluation suite (10-product benchmark) | ⬜ Not started |
| CP9 | Iterate on worst failure mode | ⬜ Not started |
| CP10 | Deploy & portfolio polish | ⬜ Not started |

## Right now
**The product works end-to-end in the browser**: enter a URL at localhost:3000 → staged progress → report page with trust labels, claim-level citations (open real source URLs, show retrieval dates), competitor chips, validation flags, and a stable shareable link (`/report/{run_id}`). Verified via Playwright on slack.com: 133s, $0.30, 100% citation coverage. 61 passing tests. Servers: `uv run uvicorn app.main:app --port 8000` (backend/), `npm run dev` (frontend/); browser drive: `node scripts/drive-cp7.mjs <url>` (frontend/).

## Next step
CP8: evaluation suite — build the 10-product benchmark (4 established, 3 niche B2B, 2 recent, 1 ambiguous) with manual labels (category, relevant/irrelevant competitors, pricing ground truth), automated metrics runner (competitor precision, category accuracy, pricing accuracy, citation coverage, latency, cost), manual-review protocol for citation validity + hallucination rate. This produces the resume numbers.

## Known failure modes (CP9 candidates)
- Pricing at non-standard paths missed (Jira's is at /software/jira/pricing, not /pricing) → shows "unavailable" despite public pricing. Fix idea: discover pricing URLs from homepage links or search.
- JS-rendered pricing (Notion) yields tier names without numbers — honest but incomplete.

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
