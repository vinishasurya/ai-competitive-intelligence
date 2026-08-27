# Project Journal — AI Competitive Intelligence Platform

Append-only log. One entry per work session. Newest entry at the bottom.

Entry template:

```
## YYYY-MM-DD — short session title
**Done:** what was actually completed (with evidence — test output, screenshots)
**Decisions:** choices made and the why
**Problems:** what went sideways, how it was resolved (or not)
**Next:** the single next step
```

---

## 2026-08-27 — Project kickoff
**Done:** Created project workspace at `~/Projects/ai-competitive-intelligence`. Copied V1 and overall design docs into `docs/`. Wrote project `CLAUDE.md` breaking V1 into checkpoints CP0–CP10 with done-when criteria, plus this journal and `status.md`. No code yet.
**Decisions:** Scope locked to the V1 design doc (`docs/design-doc-v1.pdf`) — the overall design doc is reference-only. Checkpoints follow the design doc's 3-part build plan but split finer so each session can close a checkpoint. Evaluation suite (CP8–CP9) is treated as a core feature, never a cut candidate.
**Problems:** None.
**Next:** CP0 — scaffold the repo (backend/, frontend/, eval/), init git, get FastAPI + Next.js hello-world running locally.

## 2026-08-27 — CP0 complete: project scaffold
**Done:** Scaffolded the repo: `backend/` (FastAPI + uvicorn, managed with uv, Python 3.12), `frontend/` (Next.js 15 + TypeScript + Tailwind via create-next-app), `eval/` (README stub). Git initialized with .gitignore and .env.example (secrets never committed). Backend serves `/api/health`; frontend homepage fetches it client-side and renders the status. **Evidence:** `curl /api/health` returns `{"status":"ok","service":"ci-backend","version":"0.1.0"}`; headless-Chromium screenshot shows the page rendering the green "backend: ci-backend v0.1.0 — ok" line. Initial commit `6eb494e`.
**Decisions:** (1) uv over plain pip — faster installs, lockfile for reproducibility. (2) Frontend talks to backend via CORS + `NEXT_PUBLIC_API_URL` env var (defaults to localhost:8000) rather than a Next.js proxy rewrite — simpler and matches the eventual split deployment (hosted frontend + hosted backend). (3) Installed Playwright headless Chromium for screenshot verification — will reuse it for demo assets later.
**Problems:** None significant. `chromium-cli` wasn't available for screenshots; used `npx playwright screenshot` instead.
**Next:** CP1 — SQLite schema for all 7 tables (products, runs, competitors, sources, findings, claims, eval_results) + matching Pydantic models + insert/read round-trip test.

## 2026-08-27 — CP1 complete: data model & schemas
**Done:** `backend/app/schema.sql` with all 7 tables from design doc §12 (products, runs, competitors, sources, findings, claims, eval_results), FK constraints, CHECK constraints on status/section/claim_type/source_type enums, and per-run indexes. `backend/app/models.py` with Pydantic models mirroring each table via a `RowModel` base that handles JSON-column serialization. `backend/app/db.py` with connect/init/insert/fetch helpers (FK pragma on, table-name allowlist). **Evidence:** 3 pytest tests pass — full 7-table round-trip with realistic Linear/Jira sample data, FK rejection of an orphaned run, and DB-level rejection of an invalid status that bypasses Pydantic. Commit `2247969`.
**Decisions:** (1) Stdlib `sqlite3` + raw schema.sql over SQLAlchemy — fewer moving parts, transparent SQL; kept the DDL Postgres-portable (ISO-string timestamps set in Python, no SQLite-only features) to preserve the migration path. (2) Validation at two layers: Pydantic Literals at the app boundary AND SQL CHECK constraints — defense in depth for the data the whole eval story depends on. (3) `sources.competitor_id` / `findings.competitor_id` nullable = row is about the original product, not a competitor.
**Problems:** pytest couldn't import `app` from tests/ — fixed with `pythonpath = ["."]` in pyproject.
**Next:** CP2 — `search_web` + `crawl_page` tools; first decide the search API provider (Brave / Tavily / Serper) against the $1.20/report budget.

## 2026-08-27 — CP2 complete: research tools
**Done:** `app/tools/search.py` (`search_web` via Tavily REST) and `app/tools/crawl.py` (`crawl_page` with trafilatura text extraction, retrieval metadata, sha256 content hash, 24h on-disk page cache). Both follow a soft-failure contract: never raise, return `ok=False` + error + whatever metadata was collected. `app/config.py` loads `.env`. 6 offline unit tests (httpx monkeypatched) + `scripts/smoke_cp2.py` live smoke. **Evidence:** 9/9 tests pass; live smoke run: Tavily returned 5 real "Linear alternatives" results; linear.app/slack.com/notion.com pricing pages crawled to clean text (2k–11k chars) and round-tripped through the sources table; dead domain soft-failed with a recorded ConnectError; recrawl served from cache. Commit `33fb035`.
**Decisions:** (1) Tavily via direct REST + httpx instead of their SDK — one fewer dependency, transparent request shape. (2) trafilatura for HTML→text — purpose-built main-content extraction beats hand-rolled tag stripping, `favor_recall=True` since pricing tables matter more than noise reduction. (3) Soft-failure contract on both tools so one bad page/query can't kill a run (design doc §15). (4) Backend made an installable package (hatchling) so `import app` works in scripts, tests, and the server alike. (5) JS-heavy pages that yield no static text are reported as unavailable — accepted V1 limitation per design doc.
**Problems:** Scripts couldn't import `app` (pytest-only pythonpath fix) — solved properly by packaging the backend.
**Next:** CP3 — product profiler (URL validation → crawl homepage/pricing/features/about → structured profile via Claude structured output). Needs `ANTHROPIC_API_KEY` in `backend/.env`.

## 2026-08-27 — CP3 complete: product profiler
**Done:** `app/profiler.py`: URL validation (normalizes bare domains, rejects localhost/private IPs), page collection across homepage + /pricing /features /about /product with content-hash dedupe (sites redirect unknown paths to the homepage), and structured profile extraction via `client.messages.parse()` with a Pydantic `ProductProfile` schema — Opus 4.8, adaptive thinking, grounding prompt (page text only, null over guessing). Cost estimation per call wired into config. 16 offline tests (25 total passing). **Evidence:** live smoke on linear.app / slack.com / notion.com produced accurate profiles verified by eye; Linear's pricing tiers ($0/$10/$16) match its live page; Slack's summary correctly says "specific prices not listed" instead of inventing numbers — the grounding rule working. Cost: 11.49¢ total (~3.8¢/product). Commits `9d3d648`, `303100f`.
**Decisions:** (1) `messages.parse()` + Pydantic over ask-for-JSON — API-validated structure, no parsing failures. (2) Opus 4.8 for profiling per design doc's "larger model" tier; Haiku 4.5 preconfigured for CP5 extraction. (3) `load_dotenv(override=True)` so the project `.env` beats stale shell exports.
**Problems:** Two rounds of 401s. First: the key in `.env` was a placeholder. Second: after the real key was added, a stale `ANTHROPIC_API_KEY=sk-ant-xxx...` export in the user's shell profile shadowed it (dotenv doesn't override existing env vars by default) — fixed with `override=True`. User should also delete that export from `~/.zshrc`.
**Next:** CP4 — competitor discovery (3 strategies), dedupe, verification, ranking. The highest-risk checkpoint.

## 2026-08-27 — CP4 complete: competitor discovery, verification, ranking
**Done:** `app/discovery.py` implementing design doc §9: (1) model-generated leads (Opus 8-max), (2) search extraction from "alternatives to X" / "X vs" / "best {category}" Tavily queries (Haiku), (3) own-site comparison pages via domain-restricted search (added `include_domains` to search_web). Merge/dedupe by normalized name+domain with a 20-site aggregator blocklist (G2, Capterra, Reddit…), self-exclusion, per-candidate website verification (crawl homepage → Haiku judges direct/adjacent/different_market + confidence + one-line reason), ranking (confidence + 0.15 per extra strategy), top-5 cap, everything soft-fail. Usage/cost/tool-call accounting throughout. 15 new offline tests (40 total). **Evidence:** live smoke — Linear→[Jira, Shortcut, ClickUp, Monday, Plane]; Notion→[Confluence, Coda, Airtable, Asana, ClickUp]; Tailscale (niche B2B)→[Twingate, ZeroTier, NetBird, Zscaler, Netmaker], all with recorded methods+reasons. Verification caught real edge cases: Slite/Microsoft Loop rejected because crawled text didn't support the claim; Perimeter 81 rejected because its site is now Check Point SASE; Height's SSL failure recorded gracefully. ~10¢/product profile+discovery, 29¢ total run. Commit `cea9c0b`.
**Decisions:** (1) Model leads are leads, not evidence — nothing selected without website verification (design doc rule). (2) Verification cap of 12 candidates bounds cost/latency. (3) Verified-but-cut candidates kept in `rejected` with reasons — useful for the eval and the P1 "why selected" UI.
**Problems:** Test caught that merge trusted upstream domain normalization (www. duplicates) — fixed by normalizing at the merge boundary.
**Next:** CP5 — evidence collection + structured extraction (features/pricing findings with source_ids), `extract_pricing` tool.

## V2 ideas (parking lot — out of V1 scope)
- (log future feature ideas here instead of building them)
