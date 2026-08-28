# 3-minute demo script

Raw screen footage: `docs/demo-assets/demo-footage.webm` (~55s: submit flow +
progress, then a scroll-through of the Slack report). Record narration over
it, pausing/looping frames where noted, or re-record your own screen following
the same beats. Structure per the design doc: user problem → product
decisions → measured results.

**0:00–0:30 — The problem** *(over the home page frame)*
> "PMs redo the same competitive research constantly — who competes with us,
> what do they charge, what changed. Generic AI tools answer fast but can't
> be trusted: stale competitors, invented pricing, citations that don't hold
> up. I built a tool around one principle: an AI competitive report is only
> useful if a PM can verify it in seconds."

**0:30–1:00 — The run** *(typing + progress footage)*
> "You give it one thing: a product URL. It profiles the product from its own
> website, discovers competitors three independent ways, then — and this is
> the key decision — treats the AI's suggestions as leads, not facts. Every
> candidate's live website gets crawled and verified before it makes the
> report. About two and a half minutes and thirty-six cents later…"

**1:00–2:15 — The report** *(scroll-through footage; pause on details)*
> "…a four-section report where every claim is labeled. Green means verified
> on the company's own site — click the citation and the source page opens,
> with the retrieval date. Purple means AI analysis, clearly separated from
> fact, but still cited to the evidence it rests on."
>
> *(pause on the Slack pricing claim)* "My favorite detail: when it can't
> verify something, it says so. Slack's prices render in JavaScript, so the
> first version reported them unavailable rather than quoting numbers from
> the model's memory — and the sources list shows the failed fetch. Honesty
> is a feature."

**2:15–3:00 — Measured results** *(over the results table / README)*
> "The eval suite is part of the product: a 10-product labeled benchmark plus
> a human citation review. Measured: 84 to 100 percent competitor precision,
> 100 percent citation coverage, zero hallucinations in the human review.
> Then the loop closed: the benchmark showed pricing retrieval was the worst
> failure mode, I shipped headless-browser rendering and pricing-URL
> discovery, and re-measured — pricing availability went from 70 to 85
> percent, for twelve seconds and two cents per report. That's the project:
> not just an AI feature, but the evaluation loop that makes it trustworthy."
