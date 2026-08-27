"""CP3 live smoke test: profile 3 real products end-to-end.

Run from backend/:  uv run python scripts/smoke_cp3.py
"""

import json

from app.profiler import build_profile

PRODUCTS = ["linear.app", "slack.com", "notion.com"]


def main() -> None:
    total_cost = 0.0
    for raw_url in PRODUCTS:
        print(f"\n{'=' * 60}\nPROFILING: {raw_url}\n{'=' * 60}")
        result = build_profile(raw_url)
        if not result.ok:
            print(f"  FAILED: {result.error}")
            continue
        pages = [(p.final_url or p.url) for p in result.pages]
        print(f"  pages crawled: {len(pages)}")
        for p in pages:
            print(f"    - {p}")
        print(f"  tokens: {result.input_tokens} in / {result.output_tokens} out"
              f"  cost: {result.cost_cents:.2f}¢")
        total_cost += result.cost_cents
        print(json.dumps(result.profile.model_dump(), indent=2))
    print(f"\nTotal model cost this run: {total_cost:.2f}¢")


if __name__ == "__main__":
    main()
