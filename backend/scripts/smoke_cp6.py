"""CP6 live smoke test: full URL -> 4-section cited report, end to end.

    uv run python scripts/smoke_cp6.py <product-url>

Accumulates runs into data/smoke_cp6.db so products can be run one at a time.
"""

import sys
import textwrap

from app.db import DEFAULT_DB_PATH, connect, init_db
from app.pipeline import run_pipeline

DB_PATH = DEFAULT_DB_PATH.parent / "data" / "smoke_cp6.db"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: uv run python scripts/smoke_cp6.py <product-url>")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(DB_PATH)
    init_db(conn)

    result = run_pipeline(conn, sys.argv[1])
    print(f"run_id={result.run_id}  ok={result.ok}  "
          f"{result.duration_seconds:.0f}s  {result.cost_cents:.1f}¢  "
          f"{result.total_tokens} tokens  {result.tool_calls} tool calls")
    if not result.ok:
        sys.exit(f"FAILED: {result.error}")

    print(f"\nPRODUCT: {result.product_name} — {result.category}")
    print("COMPETITORS: " + ", ".join(c["name"] for c in result.competitors))

    report = result.report
    for section, claims in report.sections.items():
        print(f"\n### {section.upper()}")
        for c in claims:
            cites = ",".join(f"S{sid}" for sid in c.source_ids)
            label = {"verified": "V", "reported": "R", "interpretation": "I"}[c.claim_type]
            body = textwrap.fill(c.text, 96, subsequent_indent="      ")
            print(f"  [{label}|{cites}] {body}")

    print(f"\nCITATION COVERAGE (factual claims with sources): "
          f"{report.citation_coverage:.0%}" if report.citation_coverage is not None
          else "\nCITATION COVERAGE: n/a")
    if report.flags:
        print(f"VALIDATION FLAGS ({len(report.flags)}):")
        for f in report.flags:
            print(f"  - [{f.flag}] claim {f.claim_id} ({f.section}): {f.detail}")
    else:
        print("VALIDATION FLAGS: none")
    conn.close()


if __name__ == "__main__":
    main()
