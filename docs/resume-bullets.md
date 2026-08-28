# Resume bullets (measured numbers only)

Per the design doc: no targets or estimates on the resume — every number
below is from the published benchmark (`eval/results/`). One number is still
pending the post-fix human review; do not use it until filled.

- Built and launched an AI competitive-intelligence platform that turns a
  product URL into an evidence-backed landscape, feature, and pricing
  analysis across up to five verified competitors in ~2.5 minutes at ~$0.36
  per report.
- Designed a multi-step research workflow (automated competitor discovery
  with website verification, structured web extraction, claim-level
  citations) achieving 84% strict / 100% lenient competitor precision, 100%
  citation coverage, 100% pricing accuracy on labeled tiers, and a
  human-reviewed 0% hallucination rate across a 10-product benchmark.
- Created an evaluation system for groundedness, hallucination, latency, and
  cost, then used it to identify the top failure mode (pricing-page
  retrieval) and improved pricing availability from 70% to 85% [and citation
  validity from 86.7% to __% — **pending post-fix manual review**] by adding
  headless-browser rendering and pricing-URL discovery.

- Exposed the platform's research toolchain (web search, crawling,
  pricing extraction, competitor discovery) as a Model Context Protocol
  (MCP) server, making the same verified tools usable from any
  MCP-compatible AI client such as Claude Desktop.

- Built a bounded research agent ("Ask the analyst") that answers
  follow-up questions over a report's evidence base: an explicit
  tool-use loop where the model autonomously selects among five tools
  (stored claims, findings, sources, fresh search, crawling), capped at
  six turns, with every answer cited and the tool trace shown to users.

Interview talking points behind each number:
- **Why verification matters:** model-suggested competitors are leads, not
  facts — website verification caught an acquired company (Perimeter 81 →
  Check Point) that model memory still listed as independent.
- **Why "unavailable" beats a guess:** the misattribution guard (failure
  gallery #3) — we accepted lower coverage to keep prices truthful.
- **Why claims are database rows:** citation coverage is computed from the
  schema, not estimated from prose.
