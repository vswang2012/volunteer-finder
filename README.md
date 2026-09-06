# East Bay volunteer board

Aggregates volunteer opportunities for high-school-age students across nine
cities around Fremont, CA — Fremont, Newark, Union City, Milpitas, Hayward,
Castro Valley, Dublin, Pleasanton and San Jose — and highlights what's **new
this week**.

## Run it

```bash
pip install -r requirements.txt
python seed.py                 # starter listings so the site isn't empty
python -m http.server           # then open localhost:8000/site/
```

Opening `site/index.html` straight from disk won't work — the browser blocks
the `fetch` of the JSON file. You need a server, even a local one.

```bash
python run.py --dry-run         # scrape and report, write nothing
python run.py --only fremont_gov
python -m pytest tests/ -q
```

## How it works

```
GitHub Actions (Sundays, 07:00 UTC)
  └─ run.py
       ├─ scrapers/*      one class per source, all emit Opportunity objects
       ├─ normalize.py    infer min_age, causes, schedule from free text
       └─ store.py        merge into data/opportunities.json, compute the diff
                          └─ committed to the repo → static site rebuilds
```

`data/opportunities.json` is committed on purpose. Git history gives you a
free audit trail — `git log -p data/opportunities.json` shows exactly what
appeared and vanished each week, which is invaluable when a scraper starts
lying.

### The rules that matter

- **`first_seen` is written once, never overwritten.** It's the entire basis
  of "new this week."
- **The listing ID hashes source + org + title + URL** — not the description.
  Orgs reword blurbs constantly; a reworded blurb must not resurface as new.
- **A failed scraper is not an empty scraper.** If a source errors, its
  existing listings are left alone. Otherwise one bad Sunday wipes the board.
- **A listing survives one missed run** (`GRACE_RUNS = 2`) before being hidden.
- **`min_age = None` means the source never said.** Those listings go in a
  separate "age isn't posted" group rather than being hidden — being quietly
  filtered out of something you could have done is the worse failure.

## Status of each source

| Source | Type | State |
|---|---|---|
| Idealist (ex-VolunteerMatch) | API | Needs a key — apply at [idealist.org/en/open-network-api](https://idealist.org/en/open-network-api). Endpoint paths in `scrapers/idealist_api.py` are placeholders until the partner docs arrive with your key. |
| City of Fremont | Scrape | **Selectors unverified.** Open the pages, confirm the markup, fix `ITEM_SELECTORS`. |
| Fremont Library | Scrape | Not built. Communico platform, clean HTML — easiest next one. |
| JustServe | Scrape | Not built. Heavily used in the Tri-City area. |
| Tri-City Volunteers | Scrape | Not built. |

Idealist absorbed VolunteerMatch in September 2025, so there's one API now,
not two. Don't build against `volunteermatch.org`.

### Search geography

`scrapers/idealist_api.py` runs one search per entry in `SEARCH_AREAS`:

| Area | Centroid | Radius |
|---|---|---|
| `tri_city` | Fremont City Hall | 15 mi |
| `san_jose` | San Jose City Hall | 12 mi |

Every neighboring city on the board already falls inside the Tri-City circle:

| City | Miles from Fremont City Hall |
|---|---|
| Newark | 4 |
| Union City | 5 |
| Milpitas | 9 |
| Hayward | 10 |
| Pleasanton | 10 |
| Dublin | 11 |
| Castro Valley | 11 |
| San Jose | 17 |

So adding a neighbor is usually a matter of adding a city center to
`pipeline/geocode.py`, not a new search area here. San Jose is the exception
at 17 miles — and widening Fremont's radius to reach it would drag in Oakland,
San Leandro and the Peninsula. The two circles overlap around Milpitas;
`fetch()` dedupes by listing id so the run log stays honest.

Neither circle is clipped to city limits, so the searches also return Santa
Clara, Sunnyvale and Livermore listings. That was already true of the Fremont
search and is left as-is.

## Adding a source

1. Subclass `Scraper` in `scrapers/`, set `slug` / `name`, implement `fetch()`
   as a generator of `Opportunity`.
2. Fill only what the page actually states. Leave the rest `None` —
   `normalize.enrich()` infers what it safely can, and your explicit values
   always win over its guesses.
3. **Raise on zero results.** Returning `[]` looks identical to "everything
   closed" and will expire real listings.
4. Register it in `scrapers/__init__.py`.

Check `robots.txt` and the terms of each site first. `Scraper.get()` does the
robots check and throttles to one request every 2 seconds by default. These
are small nonprofit servers; don't hammer them.

## Before you share this with people

Don't collect classmates' email addresses for a digest. Storing personal data
on a group of minors turns a fun project into a liability and is the kind of
thing a school will shut down. Push the weekly diff to a Discord webhook or
publish an RSS feed instead — same result, no database of kids.
