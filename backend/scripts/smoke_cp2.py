"""CP2 live smoke test.

Runs search_web with the real Tavily key, crawls 3 real pricing pages plus
one guaranteed-failure URL, stores the results as source records in a
scratch SQLite db, and reads them back. Run from backend/:

    uv run python scripts/smoke_cp2.py
"""

import tempfile
from pathlib import Path

from app.db import connect, fetch_row, init_db, insert_row
from app.models import Product, Run, Source
from app.tools.crawl import crawl_page
from app.tools.search import search_web

CRAWL_TARGETS = [
    ("https://linear.app/pricing", "pricing"),
    ("https://slack.com/pricing", "pricing"),
    ("https://www.notion.com/pricing", "pricing"),
    ("https://this-domain-does-not-exist-xyz123.com", "other"),  # graceful failure case
]


def main() -> None:
    print("=== 1. search_web (live Tavily call) ===")
    response = search_web("alternatives to Linear project management", max_results=5)
    print(f"ok={response.ok}  query={response.query!r}")
    if not response.ok:
        print(f"  ERROR: {response.error}")
    for r in response.results:
        print(f"  {r.rank}. {r.title[:60]}  ->  {r.url}")

    print("\n=== 2. crawl_page -> source records in SQLite ===")
    db_path = Path(tempfile.mkdtemp()) / "smoke.db"
    conn = connect(db_path)
    init_db(conn)
    product_id = insert_row(
        conn, "products", Product(url="https://linear.app", domain="linear.app").to_row()
    )
    run_id = insert_row(conn, "runs", Run(product_id=product_id, status="running").to_row())

    for url, source_type in CRAWL_TARGETS:
        result = crawl_page(url)
        source = Source(
            run_id=run_id,
            url=result.url,
            source_type=source_type,
            fetched_at=result.fetched_at,
            raw_text=result.raw_text,
            http_status=result.http_status,
            content_hash=result.content_hash,
        )
        source_id = insert_row(conn, "sources", source.to_row())
        stored = Source.from_row(fetch_row(conn, "sources", source_id))
        text_len = len(stored.raw_text) if stored.raw_text else 0
        status = "OK  " if result.ok else "FAIL"
        cache = " (cache)" if result.from_cache else ""
        print(f"  [{status}] source_id={source_id} http={stored.http_status} "
              f"text={text_len:>6} chars hash={str(stored.content_hash)[:12]} "
              f"{url}{cache}")
        if not result.ok:
            print(f"         soft failure recorded: {result.error}")
        elif stored.raw_text:
            preview = " ".join(stored.raw_text.split())[:110]
            print(f"         preview: {preview}...")

    print("\n=== 3. cache check (recrawl first URL) ===")
    again = crawl_page(CRAWL_TARGETS[0][0])
    print(f"  from_cache={again.from_cache}  hash_matches={again.content_hash is not None}")

    conn.close()
    print(f"\nScratch db: {db_path}")


if __name__ == "__main__":
    main()
