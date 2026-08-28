# Baseline vs post-fix — CP9 improvement measurement

Both runs measure the same V1 product on the same 10-product benchmark with the
same labels. The CP9 change: pricing-page retrieval — headless-browser rendered
fallback for JS-rendered pricing pages (reading visible browser text), plus
pricing-URL discovery via homepage links and domain-restricted search, with a
product-name guard against attributing a sibling product's prices.

| Metric | Baseline | Post-fix | Δ |
|---|---|---|---|
| **Pricing available (companies)** | **42/60 (70%)** | **51/60 (85%)** | **+15 pts** |
| Pricing accuracy (labeled tiers) | 16/16 (100%) | 14/14 (100%) | — (evaluated set varies with discovery) |
| Competitor precision (strict / lenient) | 84% / 100% | 84% / 100% | — |
| Category accuracy | 100% | 100% | — |
| Citation coverage (automated) | 100% | 100% | — |
| Citation validity (manual, 30 claims) | 86.7% | pending re-review | see `post-fix_manual_review.md` |
| Hallucination rate (manual) | 0% | pending re-review | |
| Validation flags | 1 | 1 | — |
| Mean latency | 142s | 154s | +12s (rendering cost) |
| Mean cost / report | 34.0¢ | 36.2¢ | +2.2¢ |

## Pricing recovered by the fix
Slack ($0/$8.75/$18), Notion ($0/$10/$20 — in both its own run and airtable's),
Coda, Confluence, Lovable, Smartsheet, Sketch, Mockplus, Microsoft Power Apps,
Amazon Q Developer, Mattermost.

## Still unavailable, and why that's the right answer
- **Jira, Microsoft Teams** — multi-product companies (atlassian.com,
  microsoft.com) where discovered pricing pages belong to sibling products; the
  product-name guard refuses to misattribute prices. Unavailable > wrong.
- **Zscaler, OutSystems** — enterprise vendors with no public pricing.
- **Adobe XD, Rocket.Chat, Sourcegraph, Bubble, FullStory** — no extractable
  public pricing found by static or rendered fetch this run.

## Measurement notes
- The posthog post-fix run was re-measured after the first attempt's wall-clock
  was inflated by machine sleep (34 min wall vs 13 min compute); the timeout
  guard added in the fix brought it to 148s.
- Pricing-accuracy tier counts differ (16 vs 14) because discovery surfaces
  slightly different competitor sets run to run; accuracy on evaluated tiers
  was 100% in both.
