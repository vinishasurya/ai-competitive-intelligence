# CLAUDE.md — AI Competitive Intelligence Platform (V1)

## What this project is
A portfolio MVP for APM / new-grad PM applications. A user enters a software product URL; the platform researches the product, discovers and verifies up to 5 competitors, and generates a 4-section competitive report (executive summary, competitive landscape, feature comparison, pricing comparison) where **every factual claim links to a retrievable public source with a retrieval date**.

The one principle everything serves: **an AI-generated report is only useful if a PM can quickly verify it.** Optimize for evidence quality, source traceability, and measured accuracy — never report length or technical flash.

## Source of truth
- `docs/design-doc-v1.pdf` — the V1 design doc. This is the spec. All scope questions resolve here.
- `docs/design-doc-overall.pdf` — the long-term vision. Context only; do NOT build from it.
- `status.md` — current progress. **Read this at the start of every session.**
- `journal.md` — append-only session log.

## About the user
- New grad actively applying to APM/PM roles. This project goes on the resume, so **measured results matter more than shipped features** — a working eval table beats an extra report section.
- Learning-oriented: explain the *why* behind technical decisions briefly as we build. Point out concepts worth knowing (structured outputs, eval design, agent workflows).
- Never put target or estimated numbers in resume material — only measured benchmark results.

## Stack (from design doc §11)
- **Frontend:** Next.js, React, TypeScript
- **Backend:** Python + FastAPI
- **Workflow:** explicit Python state machine (bounded steps — no uncontrolled agent loops)
- **DB:** SQLite (schema kept Postgres-migratable; no vector DB in V1)
- **Retrieval:** search API + public-page crawler
- **AI:** larger Claude model for profiling/synthesis, smaller model for extraction/classification
- **Tools:** `search_web`, `crawl_page`, `extract_pricing`, `find_alternatives` — independently testable; optionally exposed via MCP as a stretch

## Hard rules (from design doc)
1. **No hallucinated data, ever.** Reports generate from stored findings, not model general knowledge. Missing/ambiguous info renders as "unavailable" — never inferred.
2. **Pricing comes from official pricing pages only**, or it's marked unavailable.
3. **Claims are structured records** (text, type, source_ids, confidence) stored separately from prose so citation coverage is measurable.
4. **Three trust labels** in the UI: Verified (primary source) / Reported (secondary source) / Interpretation (labeled AI analysis).
5. **Bounded workflow:** hard limits on tool calls and cost per run; record latency, cost, tool calls, and failure states for every run.
6. **Scope discipline:** anything in design doc §6 (non-goals) is out. If a feature idea comes up, log it in the journal under "V2 ideas" and move on.
7. **If time runs short, cut visual polish before ever cutting the evaluation suite.**

## Checkpoints

Work proceeds checkpoint by checkpoint. A checkpoint is done only when its "Done when" criteria are demonstrated with real output (test run, screenshot, or command output) — "should work" doesn't count. Update `status.md` when a checkpoint's state changes; append to `journal.md` each session.

### CP0 — Project scaffold
Repo structure (backend/, frontend/, eval/), Python + Node environments, API keys wired via .env (never committed), git initialized with sensible .gitignore, hello-world FastAPI endpoint and Next.js page running locally.
**Done when:** both dev servers run locally and a smoke-test endpoint returns JSON to the frontend.

### CP1 — Data model & schemas
SQLite schema per design doc §12: products, runs, competitors, sources, findings, claims, eval_results. Pydantic models mirroring each table. Migration-friendly setup.
**Done when:** schema creates cleanly, and a scripted insert/read round-trip works for every table.

### CP2 — Research tools
`search_web` and `crawl_page` as independently testable modules: cleaned page text, URL, retrieval time, HTTP status, content hash. Soft failure on unreachable/dynamic pages. Basic page cache (P1, cheap to add here).
**Done when:** each tool runs standalone against 3 real sites and stores well-formed source records, including a graceful failure case.

### CP3 — Product profiler
URL validation → fetch homepage + discoverable pages (pricing, features, about) → structured profile (name, domain, category, target customer, core problem, value prop, key features, business model) via structured output.
**Done when:** profiler produces accurate structured profiles for 3 known products, verified by eye.

### CP4 — Competitor discovery, verification, ranking
Three strategies (model-generated leads, search queries like "alternatives to X", company comparison pages) → merge/dedupe by normalized name + domain → verify each candidate's live site addresses the same category/customer problem → rank by overlap + frequency + evidence strength → cap at 5, with a stored "why selected" explanation.
**Done when:** pipeline runs on 3 test products and returns ≤5 verified, defensible competitors each, with discovery method(s) recorded per competitor. This is the highest-risk checkpoint — test it hardest.

### CP5 — Evidence collection & structured extraction
For the product + each verified competitor: crawl homepage/features/pricing pages, store source records, then extract normalized findings (features, pricing tiers with billing period and limits) with source_ids attached. `extract_pricing` as its own testable tool.
**Done when:** 3-product test run produces findings rows where every finding traces to real stored sources, and pricing matches the live pages on manual spot-check.

### CP6 — Report generation & validation
Generate 4 sections from stored findings only. Model returns structured claims (text, type, source_ids, confidence). Pre-display validation flags: claims without sources, dangling source_ids, pricing claims lacking a primary pricing source, unlabeled interpretation.
**Done when:** a full end-to-end run (URL → report JSON) completes on 3 products with zero validation flags, or flags correctly surfaced.

### CP7 — Report UI
Next.js interface: URL input → inferred profile preview → progress states during research (P1) → rendered report with claim-level citation links, retrieval dates, and the three trust labels. Shareable stable link or PDF export. Retry for failed runs (P1).
**Done when:** the full flow works in the browser end-to-end and citations open to the correct sources. Screenshot recorded.

### CP8 — Evaluation suite
10-product benchmark (4 established, 3 niche B2B, 2 recently launched, 1 ambiguous category) with manual labels: accepted category, relevant/irrelevant competitors, public pricing for top 3 competitors. Automated metrics: competitor precision, category accuracy, pricing accuracy, citation coverage, latency, cost per report. Manual-review protocol for citation validity + hallucination rate on a fixed claim sample.
**Done when:** the suite runs across all 10 products and produces a complete results table, including failures.

### CP9 — Iterate on the worst failure mode
Analyze eval results, identify the highest-impact failure mode, ship one targeted fix, re-run the benchmark, and record before/after numbers. This is the resume's "improved X from A to B" bullet — do not skip it.
**Done when:** results table shows two versions with a measured improvement (or an honest documented regression).

### CP10 — Deploy & portfolio polish
Deploy frontend + backend (managed hosting; add Postgres only if the host requires it). Public GitHub repo with architecture + evaluation README, published results table, failure gallery (3 meaningful failures → product changes), 3-minute demo video, updated design doc, resume bullets filled with **measured** numbers.
**Done when:** all §17 launch criteria pass and a recruiter could try the live demo with zero local setup.

## Session workflow
1. **Session start:** read `status.md` (and skim the last journal entry) before doing anything.
2. **During:** plan mode for any 3+ step task or architectural decision; show real output before calling anything done.
3. **Session end (or after significant progress):** append a dated entry to `journal.md` — what was done, decisions made + why, problems hit, next step. Then rewrite `status.md` to reflect current reality.
4. `journal.md` is append-only history; `status.md` is a snapshot that gets fully rewritten and stays short.
