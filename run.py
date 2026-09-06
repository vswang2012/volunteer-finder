#!/usr/bin/env python3
"""Weekly refresh. Run locally with `python run.py`, or let Actions do it.

    python run.py                 # full run
    python run.py --dry-run       # scrape and report, write nothing
    python run.py --only fremont_gov
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from pipeline.geocode import assign_coordinates
from pipeline.models import Opportunity
from pipeline.normalize import enrich
from pipeline.store import Store
from scrapers import ALL_SCRAPERS, MissingKey

DATA_PATH = Path(__file__).parent / "data" / "opportunities.json"


def collect(only: str | None) -> tuple[list[Opportunity], list[str], list[str]]:
    results: list[Opportunity] = []
    ok: list[str] = []
    failed: list[str] = []

    for cls in ALL_SCRAPERS:
        if only and cls.slug != only:
            continue

        scraper = cls()
        print(f"→ {cls.name} ({cls.slug})", flush=True)
        try:
            batch = list(scraper.fetch())
        except MissingKey as e:
            print(f"  skipped: {e}")
            continue
        except Exception as e:  # one bad source must not kill the run
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            failed.append(cls.slug)
            continue

        for opp in batch:
            enrich(opp)
            assign_coordinates(opp)
        results.extend(batch)
        ok.append(cls.slug)
        print(f"  {len(batch)} listings")

    return results, ok, failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="run a single scraper by slug")
    args = ap.parse_args()

    run_date = dt.date.today().isoformat()
    scraped, ok, failed = collect(args.only)

    if not ok:
        print("\nEvery source failed. Not touching the data file.", file=sys.stderr)
        return 1

    store = Store(DATA_PATH)
    report = store.merge(scraped, run_date, ok, failed)

    print()
    print(report.summary())

    if report.new:
        print("\nNew this week:")
        for opp in report.new[:20]:
            age = f"{opp.min_age}+" if opp.min_age else "age n/s"
            print(f"  · {opp.title} — {opp.org} ({age})")

    if args.dry_run:
        print("\n(dry run, nothing written)")
        return 0

    store.save()
    print(f"\nwrote {DATA_PATH}")
    # Non-zero on partial failure so the Actions run is visibly yellow/red.
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
