"""CP4 live smoke test: full profile -> discovery pipeline on 3 real products.

Run from backend/:  uv run python scripts/smoke_cp4.py
"""

from app.discovery import discover_competitors
from app.profiler import build_profile

PRODUCTS = ["linear.app", "notion.com", "tailscale.com"]


def main() -> None:
    total_cost = 0.0
    for raw_url in PRODUCTS:
        print(f"\n{'=' * 64}\nPRODUCT: {raw_url}\n{'=' * 64}")
        prof = build_profile(raw_url)
        if not prof.ok:
            print(f"  profiling FAILED: {prof.error}")
            continue
        print(f"  profile: {prof.profile.name} — {prof.profile.category}"
              f"  ({prof.cost_cents:.1f}¢)")

        disc = discover_competitors(prof.profile)
        if not disc.ok:
            print(f"  discovery FAILED: {disc.error}")
            continue

        print(f"  candidates: {disc.candidates_considered} considered, "
              f"{disc.candidates_verified} verified, "
              f"{len(disc.competitors)} selected")
        print(f"  discovery cost: {disc.cost_cents:.1f}¢  "
              f"tool calls: {disc.tool_calls}  "
              f"tokens: {disc.input_tokens} in / {disc.output_tokens} out")

        print(f"\n  SELECTED COMPETITORS for {prof.profile.name}:")
        for i, c in enumerate(disc.competitors, 1):
            methods = "+".join(c.discovery_methods)
            print(f"   {i}. {c.name} ({c.domain})  [{c.relationship}, "
                  f"conf {c.confidence:.2f}, via {methods}]")
            print(f"      why: {c.why_selected}")

        if disc.rejected:
            print("\n  rejected/cut:")
            for c in disc.rejected:
                print(f"   - {c.name} ({c.domain}): {(c.why_selected or 'n/a')[:90]}")

        total_cost += prof.cost_cents + disc.cost_cents

    print(f"\n{'=' * 64}\nTotal model cost this run: {total_cost:.1f}¢")


if __name__ == "__main__":
    main()
