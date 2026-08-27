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

## V2 ideas (parking lot — out of V1 scope)
- (log future feature ideas here instead of building them)
