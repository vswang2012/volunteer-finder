# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A weekly-refreshed static board of volunteer opportunities in Fremont, Newark,
Union City and San Jose, CA, aimed at high-school-age students. A Python pipeline scrapes sources, merges
results into a committed JSON file, and a single dependency-free HTML page
reads that JSON in the browser. There is no server and no database.

## Repository layout is currently flattened

Every file sits in the repo root, but the code imports and the CI workflow
assume a package layout. **Restore this structure before running anything** —
the imports below are what the code actually expects:

| Current file | Expected path |
|---|---|
| `models.py`, `normalize.py`, `store.py` | `pipeline/` (they use relative imports like `from .models import`) |
| `base.py`, `fremont_gov.py`, `idealist_api.py` | `scrapers/` (they use `from .base import` and `from pipeline.models import`) |
| `index.html` | `site/` (it fetches `../data/opportunities.json`) |
| `opportunities.json` | `data/` |
| `test_store.py` | `tests/` (it does `sys.path.insert(0, parents[1])`) |
| `refresh.yml` | `.github/workflows/` |

Also missing and needed:

- `pipeline/__init__.py`
- `scrapers/__init__.py` — must export `ALL_SCRAPERS` (list of scraper classes)
  **and** re-export `MissingKey`; `run.py` imports both from the package, but
  `MissingKey` is defined in `scrapers/idealist_api.py`.
- `requirements.txt` — `requests`, `beautifulsoup4`, `pytest`.

## Commands

```bash
pip install -r requirements.txt

python seed.py              # write ~10 hand-entered starter listings into data/
python run.py               # full scrape + merge + write
python run.py --dry-run     # scrape and print the report, write nothing
python run.py --only fremont_gov

python -m pytest tests/ -q
python -m pytest tests/test_store.py::test_first_seen_is_never_overwritten -q

python -m http.server        # then open http://localhost:8000/site/
```

The page must be served, not opened from disk — the browser blocks the
`fetch` of a `file://` JSON.

`run.py` exit codes are meaningful: `0` clean, `1` every source failed (data
file untouched), `2` partial failure. CI relies on this to turn the run yellow.

## Architecture

```
run.py  (or seed.py)
  └─ scrapers/*.py     one Scraper subclass per source → Opportunity objects
  └─ pipeline/normalize.enrich(opp)   infer min_age / causes / schedule from text
  └─ pipeline/store.Store.merge(...)  merge into data/opportunities.json + diff
       └─ committed by GitHub Actions → site/index.html renders it client-side
```

`pipeline/models.py` holds the one schema every scraper must emit. `store.py`
is where the product actually lives — scrapers can break and be fixed, but if
merge logic is wrong, "new this week" lies and the board loses trust.

## Invariants — do not break these

These are load-bearing design decisions, each guarded by a test in
`tests/test_store.py`:

1. **`first_seen` is written once, never overwritten.** It is the sole basis of
   "new this week". `merge()` copies it off the existing record before
   replacing the object.
2. **`Opportunity.stable_id()` hashes source + org + title + canonical URL —
   deliberately not description or dates.** Orgs reword blurbs constantly; a
   reworded blurb must not resurface as new. `_canonical_url()` strips
   `utm_*`/`fbclid`/etc. so tracking params don't spawn duplicates.
3. **A failed scraper is not an empty scraper.** `_expire()` only considers
   sources in `sources_ok`. If a source errors, its listings are left alone —
   otherwise one bad Sunday wipes the board.
4. **A listing survives one missed run** before being hidden (`GRACE_RUNS = 2`).
5. **`min_age = None` means the source never said** — not "no minimum". Those
   listings render in a separate "age isn't posted" group rather than being
   filtered out. Never guess an age to fill the field.
6. **Scraper-supplied values always win over inference.** `enrich()` only fills
   fields the scraper left `None`/empty.
7. **A scraper raises on zero results** rather than returning `[]`. An empty
   list is indistinguishable from "everything closed" and will expire real
   listings. Both existing scrapers do this explicitly.
8. **`data/opportunities.json` is committed on purpose.** `git log -p` on it is
   the audit trail for what appeared and vanished each week. `save()` uses
   `indent=2, sort_keys=True` to keep those diffs readable — keep it that way.

## Adding a scraper

Subclass `Scraper` in `scrapers/`, set `slug`/`name`, implement `fetch()` as a
generator of `Opportunity`, register it in `scrapers/__init__.py`. Fill only
what the page actually states; leave everything else `None`.

Use `self.get()` / `self.soup()` rather than `requests` directly — they do the
`robots.txt` check and throttle to one request every 2 seconds. These are small
nonprofit servers. Set `check_robots = False` only for a documented API with a
key. Check each site's terms before adding it.

## Source status

- **Idealist** (`idealist_api.py`) — primary source, needs `IDEALIST_API_KEY`
  (env var locally, GitHub secret in CI). Raises `MissingKey` and is skipped
  without one. `SEARCH_URL` and the field names in `_to_opportunity()` are
  placeholders until the partner docs arrive with the key; keep all
  source-specific mapping confined to those two places.
- **City of Fremont** (`fremont_gov.py`) — **blocked before selectors even
  matter.** fremont.gov sits behind Akamai and returns **403 for
  `/robots.txt`** to a non-browser User-Agent. `RobotFileParser` reads a 403
  as "disallow everything", so `Scraper._allowed()` returns False and the
  fallback in `base.py` never fires — the run reports "robots.txt disallows"
  when the real problem is UA blocking. Fixing `ITEM_SELECTORS` alone will not
  help. `sanjoseca.gov` and `newarkca.gov` block the same way, so any city
  scraper will hit this. City listings rarely appear on Idealist, which is the
  whole reason this project exists.
- **Not built:** Fremont Library (Communico platform, clean HTML — easiest
  next), JustServe, Tri-City Volunteers.

Idealist absorbed VolunteerMatch in September 2025. There is one API now — do
not build against `volunteermatch.org`.

## Search geography

`SEARCH_AREAS` in `scrapers/idealist_api.py` holds one
`(name, lat, lon, radius)` per area: Fremont City Hall at 15 miles (covers
Newark and Union City, ~5 miles out) and San Jose City Hall at 12 miles. Add a
city by adding an area, not by widening Fremont's radius — 17+ miles from
Fremont reaches San Jose but also Oakland and the Peninsula. The circles
overlap around Milpitas, so `fetch()` dedupes by `Opportunity.id`.

The circles are not clipped to city limits; a San Jose search also returns
Santa Clara and Sunnyvale. Pre-existing behavior, left alone.

## Hand-entered listings

`seed.py` is the bootstrap dataset (`source="seed"`), and because `run.py`
never lists `seed` in `sources_ok`, `_expire()` skips it — seed rows never
expire. Two rules when adding one:

- `min_age` is what the source actually publishes. Eight of the twenty rows
  have no posted age floor; those stay `None`, land in the site's "age isn't
  posted" group, and carry a phone number in the description so a student can
  ask. Do not fill the gap with a guess.
- **Set `min_age` explicitly whenever the description mentions any other
  number of years.** `parse_min_age()` reads "camps for ages 5 to 12" as a
  minimum age of 5. An explicit value blocks the inference (invariant #6) —
  this is what the League of Volunteers row relies on.

`signs_hours=False` is meaningful and distinct from `None`: Second Harvest
states it won't sign third-party forms, which is not the same as a source
staying silent.

## Map tiles

`site/index.html` renders a Leaflet map from **`tile.openstreetmap.org`** —
keyless, `detectRetina: false` to stay inside OSM's tile usage policy.

**Do not switch to `basemaps.cartocdn.com`.** CARTO requires an API key now,
and without one it still returns `HTTP 200` with a well-formed PNG — but every
tile has "API KEY REQUIRED" watermarked across it. A status-code or
content-type check passes while the map is visibly ruined. Verify tiles by
screenshotting the page, not by fetching them.

Coordinates come from `pipeline/geocode.py`, which is a curated lookup
(address → org+city → city center), so nothing geocodes in the browser and no
key is needed there either. Listings that fall through to a city center share
a point with every other listing in that city, so those markers stack.

## Privacy constraint

Do not add anything that collects classmates' email addresses or other personal
data. The users are minors; storing that turns a student project into a
liability. For the weekly digest, push the diff to a Discord webhook or publish
RSS instead.
