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
| CP9 | Iterate on worst failure mode | 🟡 Fix shipped + measured (+15pt pricing availability); manual re-review pending |
| CP10 | Deploy & portfolio polish | 🟡 Deployed, persistent, C2 UI live; demo video pending |

## Right now
**Baseline benchmark published** (`eval/results/baseline.md` — evaluation runs are named `baseline` / `post-fix`, both measuring the V1 product): 10/10 products, category accuracy 100%, competitor precision 84% strict / 100% lenient, pricing 16/16 labeled tiers, citation coverage 100%, 1 flag, mean 142s / 34¢ per report — all design-doc targets exceeded. 66 passing tests. Product runs in browser at localhost:3000.

## Manual review done (2026-08-27)
30 claims reviewed by hand: **citation validity 86.7%, hallucination rate 0%**. All 4 invalids are pricing claims; 3 are JS-rendered pricing pages (Slack, Notion, Lovable). Still open: benchmark label audit (`eval/benchmark.json`) — optional before post-fix re-score; and the reason for the Linear pricing invalid mark (ask Ravi's team).

## CP9 measured (2026-08-28)
Pricing retrieval fix (rendered fallback + URL discovery + misattribution guard): **pricing availability 70% → 85%**, everything else held, +2.2¢/+12s per report. Full table: `eval/results/comparison.md`.

## Live deployment (2026-08-28)
- **Repo:** https://github.com/vinishasurya/ai-competitive-intelligence (public)
- **Live demo:** https://ai-competitive-intelligence-eight.vercel.app (frontend, Vercel) → https://ai-competitive-intelligence-production.up.railway.app (backend, Railway/Docker/Playwright)
- Verified end-to-end on production via headless browser: Linear report in 156s / $0.35, 100% cited, citations resolve.
- Ops notes: FRONTEND_ORIGIN env wires CORS; git now pushes as vinishasurya via gh credential helper (old UmaRavisFamily keychain cred bypassed).

## Since deploy (2026-08-28)
- **C2 "Graphite & mint" UI live** (user-picked from mockups): stat-tile header, restyled trust badges, pricing comparison table (payload now includes structured `pricing`).
- **Reports persist across deploys**: Railway volume at `/data` + `DATABASE_PATH` env — verified (report/1 survived a redeploy).
- **JS-shell sites work** (Canva verified live); blocked sites get an honest error.
- Anthropic credits topped up after an out-of-credits failure; recommend auto-reload + spend limit both set.

## Remaining to finish the project
1. **Post-fix manual review** (`eval/results/post-fix_manual_review.md`) → fills citation-validity "improved 86.7% → X%" resume bullet (human task).
2. **Any further UI tweaks** — every push auto-deploys; reports now survive deploys.
3. **Demo video last** — re-record footage (`frontend/scripts/record-demo.mjs`) against the C2 UI, narrate per `docs/demo-script.md`, link in README.

## Failure gallery entries (for CP10)
1. Non-standard pricing paths (Jira) → URL discovery via links + search.
2. JS-rendered pricing (Slack/Notion/Lovable) → headless-browser fallback reading visible text.
3. Sibling-product price misattribution risk (Atlassian/Microsoft) → product-name guard; deliberate "unavailable > wrong".

## Blockers / open questions
- Housekeeping for the user: delete the stale `export ANTHROPIC_API_KEY=sk-ant-xxx...` placeholder from `~/.zshrc` (the code now overrides it, but it can confuse other tools).
