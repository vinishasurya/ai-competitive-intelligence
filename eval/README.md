# Evaluation suite

Home of the 10-product benchmark and metrics scripts (CP8–CP9).

Planned contents:
- `benchmark.json` — the fixed 10-product set with manual labels (category, relevant/irrelevant competitors, pricing ground truth)
- `run_eval.py` — runs the pipeline across the benchmark and computes: competitor precision, category accuracy, pricing accuracy, citation coverage, latency, cost per report
- `results/` — versioned results tables, including failures

Per the design doc: this suite is a core product feature. If time runs short, cut polish — never this.
