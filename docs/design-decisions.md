# Design decisions & deviations from the original design doc

The original V1 design doc is at [`docs/design-doc-v1.pdf`](design-doc-v1.pdf).
This file records what changed — and what deliberately didn't — during the
build, per the doc's own requirement to publish it "updated with decisions
that changed during development."

## Held as designed

- **Scope discipline** — every §6 non-goal stayed out: no monitoring, no
  sentiment, no vector DB, no job queue, no auth. SQLite (in WAL mode) proved
  sufficient through the full benchmark.
- **Trust model** — verified/reported/interpretation labels, claim-level
  `source_ids`, pricing from primary sources only, unavailable-over-inferred.
  Enforced three ways: prompts, a deterministic pre-display validator, and
  schema (claims are rows, so coverage is computed not estimated).
- **Bounded workflow** — an explicit Python pipeline (profile → discovery →
  evidence → report), no agent loops; per-run cost/token/tool-call accounting.
- **Eval as a product feature** — the benchmark, metrics, and human-review
  protocol shipped as designed and drove the one iteration cycle (see
  [failure gallery](failure-gallery.md)).

## Decisions made during the build

1. **Structured outputs everywhere.** All model calls use `messages.parse()`
   with Pydantic schemas — API-validated structure instead of prompt-and-parse.
2. **Model tiering by call frequency.** Opus 4.8 for the two synthesis-heavy
   steps (profiling, report sections); Haiku 4.5 for extraction and
   per-candidate verification, which run ~20× per report. Result: ~$0.36 per
   report against the $1.20 budget.
3. **Discovery verification is non-negotiable.** Model-generated candidates
   are leads only; selection requires the candidate's live website to support
   the relationship. This caught real-world drift the model's memory missed
   (Perimeter 81's site now belongs to Check Point SASE post-acquisition).
4. **Failed fetches are stored as sources.** "Pricing page attempted, HTTP
   404, on [date]" is evidence too — it lets the report cite the absence.
5. **Rendered fallback reads visible text, not HTML.** Added in the CP9
   iteration (see failure gallery #2); scoped to pricing pages only to bound
   latency and cost.
6. **Strict/lenient precision split.** The benchmark rubric labels
   competitors clearly-relevant / defensible / clearly-irrelevant. Reporting
   both numbers (84% / 100%) is more honest than picking one: several
   "misses" were defensible competitors the label lists hadn't anticipated
   (Google Chat for Slack, Power Apps for Retool).
7. **Evaluation runs are named `baseline` / `post-fix`** to avoid colliding
   with "V1" meaning the product's scope.

## Known limitations (honest edges of V1)

- Multi-product companies (Atlassian, Microsoft) often resolve to
  "pricing unavailable" by deliberate misattribution guard.
- Benchmark labels were AI-drafted and human-spot-checked; the pricing ground
  truth covers 14–16 tiers, all verified against live pages during
  development. A larger, independently labeled truth set would strengthen the
  numbers.
- Discovery varies slightly run to run (model sampling + live search), so
  per-run competitor sets — and therefore evaluated pricing tiers — differ at
  the margin.
- English-language products with public websites only, per design doc scope.
