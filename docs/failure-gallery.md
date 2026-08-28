# Failure gallery

Three meaningful failures found by measurement, and the product changes they
drove. Per the design doc, publishing failures is part of the product: a
narrow tool with demonstrated (and honestly bounded) quality beats a broad one
with unverified output.

## 1. Pricing at non-standard paths

**Failure:** The evidence collector assumed pricing lives at `/pricing`.
Atlassian's Jira pricing lives at `/software/jira/pricing`, so Jira — a
top-ranked competitor in the Linear run — showed "pricing unavailable"
despite having public pricing. Found in the first 3-product evidence test
(CP5) and confirmed across the baseline benchmark.

**Change:** `find_pricing_link` — discover the pricing URL from the
homepage's actual links, falling back to a domain-restricted web search.

**Result:** Contributed to pricing availability rising 70% → 85%. Jira itself
remains unavailable — see failure 3 for why that's deliberate.

## 2. JavaScript-rendered pricing pages

**Failure:** The static crawler cannot execute JavaScript, so pricing pages
that render prices client-side (Slack, Notion, Lovable) produced tier names
without numbers, or nothing. The system honestly reported "unavailable" — but
the human citation review marked those claims invalid: a citation can't
demonstrate prices are unpublished when a browser plainly shows them. This
failure mode caused 3 of the 4 invalid marks in the baseline review (citation
validity 86.7%).

**Change:** A headless-Chromium fallback (`crawl_page_rendered`) that
re-fetches the pricing page and reads the **visible browser text** — a second
bug found during the fix: the HTML-extraction library silently drops rendered
price elements, so extracting from rendered HTML still returned nothing.
Every rendered fetch is stored as its own source row, so citations point at
what was actually read.

**Result:** Slack ($0/$8.75/$18), Notion ($0/$10/$20), Lovable, Coda,
Confluence, Smartsheet and 5 more recovered. Measured cost of the fix: +12s
latency and +2.2¢ per report.

## 3. Sibling-product price misattribution (the fix we refused to ship)

**Failure risk:** For multi-product companies, pricing-URL discovery can find
the *wrong product's* pricing page. Searching "Jira pricing" on atlassian.com
surfaces Jira Service Management's pricing — extracting it would confidently
attribute a sibling product's prices to Jira. That is exactly the
plausible-but-wrong output this product exists to prevent, and it is worse
than "unavailable."

**Change:** The discovery ranks URLs containing the product's own name first,
and when no safe match exists, pricing stays **unavailable by design**.
Jira and Microsoft Teams remain unavailable in the post-fix results for this
reason.

**Lesson:** Coverage metrics reward guessing; trust requires an explicit
decision about when *not* to answer. The design doc's rule — "missing or
ambiguous information is displayed as unavailable instead of inferred" —
had to be enforced against the improvement pressure of our own benchmark.
