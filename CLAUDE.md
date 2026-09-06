# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A weekly-refreshed static board of volunteer opportunities across nine cities
around Fremont, CA — Fremont, Newark, Union City, Milpitas, Hayward, Castro
Valley, Dublin, Pleasanton and San Jose — aimed at high-school-age students. A Python pipeline scrapes sources, merges
results into a committed JSON file, and a single dependency-free HTML page
reads that JSON in the browser. There is no server and no database.

## Layout

```
run.py                  weekly refresh entry point
seed.py                 hand-entered bootstrap listings (28 rows, 9 cities)
pipeline/
  models.py             the one schema every scraper emits
  normalize.py          infer min_age / causes / schedule from free text
  geocode.py            curated address → lat/lon tables, no external API
  store.py              merge + expire + weekly diff
scrapers/
  __init__.py           ALL_SCRAPERS registry; also re-exports MissingKey
  base.py               robots check + throttling
  idealist_api.py       primary source, needs a key
  fremont_gov.py        city scrape, currently blocked (see Source status)
site/index.html         the whole front end: filters, list, Leaflet map
data/opportunities.json committed dataset
tests/test_store.py     store, age parsing and geocode tests
```

Paths are load-bearing: `site/index.html` fetches `../data/opportunities.json`,
and `tests/test_store.py` does `sys.path.insert(0, parents[1])`. Moving files
breaks both silently.

`scrapers/__init__.py` re-exports `MissingKey` even though it's defined in
`idealist_api.py`, because `run.py` imports it from the package and treats it
differently from a real failure — a source without credentials is skipped, not
counted as broken.

## Commands

A `.venv` on python3.12 is checked into the working tree (not the repo) to
match CI, which pins 3.12. The system python here is 3.9 and does import the
package fine, but don't rely on that.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python seed.py            # write the 28 bootstrap listings into data/
.venv/bin/python run.py             # full scrape + merge + write
.venv/bin/python run.py --dry-run   # scrape and print the report, write nothing
.venv/bin/python run.py --only idealist

.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m pytest tests/test_store.py::test_first_seen_is_never_overwritten -q

.venv/bin/python -m http.server 8000 --bind 127.0.0.1
# then open http://127.0.0.1:8000/site/
```

The page must be served, not opened from disk — the browser blocks the `fetch`
of a `file://` JSON.

`run.py` exit codes are meaningful: `0` clean, `1` every source failed (data
file untouched), `2` partial failure. CI relies on this to turn the run yellow.

### Verifying front-end changes

`python -m http.server` answers with `304 Not Modified`, so a soft browser
reload keeps serving stale HTML. Hard-reload (Cmd+Shift+R) after editing
`site/index.html`, or you will debug a page that isn't the one on disk.

The map cannot be checked by fetching URLs — see **Map tiles** for why. Render
it and look at the pixels:

```bash
CHROME=$(find ~/.cache/puppeteer/chrome-headless-shell -name chrome-headless-shell | head -1)
"$CHROME" --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=1280,1050 --virtual-time-budget=20000 \
  --screenshot=/tmp/site.png "http://127.0.0.1:8000/site/index.html"
```

Full `Google Chrome.app --headless=new` hangs in this environment; the
puppeteer headless shell works.

## Architecture

```
run.py  (or seed.py)
  └─ scrapers/*.py     one Scraper subclass per source → Opportunity objects
  └─ pipeline/normalize.enrich(opp)          infer min_age / causes / schedule
  └─ pipeline/geocode.assign_coordinates(opp)  fill lat/lon from lookup tables
  └─ pipeline/store.Store.merge(...)         merge into data/ + weekly diff
       └─ committed by GitHub Actions → site/index.html renders it client-side
```

Order matters: `enrich()` then `assign_coordinates()`, both before `merge()`.
Skipping the geocode step leaves `lat`/`lon` as `None` and the listing renders
in the list but never on the map.

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
`(name, lat, lon, radius)` per area: Fremont City Hall at 15 miles and San
Jose City Hall at 12 miles.

**Adding a neighboring city usually needs no change here.** The Fremont circle
already reaches all of them — Newark 4mi, Union City 5mi, Milpitas 9mi,
Hayward 10mi, Pleasanton 10mi, Dublin 11mi, Castro Valley 11mi. What a new
city does need is an entry in `CITY_CENTERS` in `pipeline/geocode.py`, or its
listings get no coordinates and never appear on the map.

San Jose at 17mi is the one that needed its own circle. Don't widen Fremont's
radius instead — 17+ miles also pulls in Oakland, San Leandro and the
Peninsula. The circles overlap around Milpitas, so `fetch()` dedupes by
`Opportunity.id`.

The circles are not clipped to city limits; a San Jose search also returns
Santa Clara and Sunnyvale. Pre-existing behavior, left alone.

## Hand-entered listings

`seed.py` is the bootstrap dataset (`source="seed"`), and because `run.py`
never lists `seed` in `sources_ok`, `_expire()` skips it — seed rows never
expire. Two rules when adding one:

- `min_age` is what the source actually publishes. Ten of the 28 rows have no
  posted age floor; those stay `None`, land in the site's "age isn't posted"
  group, and carry a phone number or email in the description so a student can
  ask. Do not fill the gap with a guess.
- **Set `min_age` explicitly whenever the description mentions any other
  number of years.** `parse_min_age()` reads "camps for ages 5 to 12" as a
  minimum age of 5. An explicit value blocks the inference (invariant #6) —
  this is what the League of Volunteers row relies on.
- The inverse trap: when a listing is open to students but *mentions* an adult
  restriction, the parser turns that into a floor and hides the row from the
  people it's for. Both "18 and older" and "adults only" parse as 18. The
  Humane Society Silicon Valley row keeps `min_age=None` and is deliberately
  worded "for adult volunteers" to match neither pattern — don't reword it.

`signs_hours=False` is meaningful and distinct from `None`: Second Harvest
states it won't sign third-party forms, which is not the same as a source
staying silent.

## The front end

`site/index.html` is the entire UI — no build step, no framework, no npm. Its
only runtime dependencies are three CDNs: Leaflet (unpkg), Google Fonts, and
OSM tiles. It reads `data/opportunities.json`
with `{cache:'no-store'}`, so listing data is never stale even on a soft
reload; only the HTML itself caches.

Filtering lives in `eligible()`. It checks `status`, `min_age`, `max_age`, the
city dropdown, and the four chips (`new`, `weekend`, `hours`, `one_time`). Two
things to know:

- **`max_age` is enforced.** Four rows cap age (teen-only cohorts like the
  13–17 League of Volunteers program), and they correctly disappear once you
  age past the cap.
- **The city dropdown is derived from the data**, not hardcoded —
  `populateCityFilter()` collects distinct `city` values. A new city appears in
  the filter automatically, but only if `city` is spelled consistently, since
  matching goes through `normalizeCity()` (trim + lowercase). Use `"San Jose"`,
  not `"San José"`, in the `city` field; the accent belongs in `org` only.

Results render in two groups: listings with a stated minimum age, then "Age
isn't posted — worth asking". That second group is the point of invariant #5,
not an afterthought.

## Map tiles

`site/index.html` renders a Leaflet map from **`tile.openstreetmap.org`** —
keyless, `detectRetina: false` to stay inside OSM's tile usage policy.

**Do not switch to `basemaps.cartocdn.com`.** CARTO requires an API key now,
and without one it still returns `HTTP 200` with a well-formed PNG — but every
tile has "API KEY REQUIRED" watermarked across it. A status-code or
content-type check passes while the map is visibly ruined. Verify tiles by
screenshotting the page, not by fetching them.

Coordinates come from `pipeline/geocode.py`, a three-tier curated lookup:
exact address → org+city → city center. Nothing geocodes in the browser, so no
key is needed there either. Adding a city means adding a `CITY_CENTERS` entry
at minimum, or its listings get no coordinates and never plot.

## Deployment (Vercel)

The host serves two files. `scripts/vercel-build.sh` copies `site/index.html`
to `public/index.html` and `data/opportunities.json` to
`public/data/`; `vercel.json` points `outputDirectory` at `public`.

**`vercel.json` is not optional.** Without it, Vercel sees `requirements.txt`
at the repo root, auto-detects a Python app, and fails with *"No python
entrypoint found"* — it looks for `app.py`/`wsgi.py`/`api/index.py` and there
is none, because the Python here is CI tooling that never runs on the host.
`framework: null` plus an explicit `buildCommand` and `outputDirectory` is what
suppresses that detection.

The deployed layout puts `index.html` at `/` while local dev serves it from
`/site/`. The page's `fetch('../data/opportunities.json')` works in both:
browsers clamp a leading `..` at the web root (RFC 3986 remove_dot_segments),
so it resolves to `/data/opportunities.json` either way. Don't "fix" that path
to `./data/` — it would break local dev.

`public/` is gitignored. The weekly Action commits `data/opportunities.json`,
which pushes to `main` and triggers a redeploy, so the board refreshes without
anyone touching Vercel.

## Known rough edges

- **Stacked markers.** 6 listings sit on 3 shared points, because orgs sharing
  an address (or falling back to a city center) get identical coordinates.
  Leaflet draws them on top of each other and only the top pin is clickable.
  Needs jitter or clustering.
- **The `<h1>` still reads "Volunteer openings around Fremont"** while the
  board covers nine cities. Accurate as a region descriptor, stale as a title.
- **No scraper currently returns anything.** Both sources are unavailable
  (missing key, edge-blocked), so `run.py` exits 1 and the 28 seed rows are the
  entire dataset. Until one source works, the weekly diff has nothing to show.

## Privacy constraint

Do not add anything that collects classmates' email addresses or other personal
data. The users are minors; storing that turns a student project into a
liability. For the weekly digest, push the diff to a Discord webhook or publish
RSS instead.
