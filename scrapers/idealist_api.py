"""Idealist (formerly VolunteerMatch) — the primary source.

Idealist absorbed VolunteerMatch in Sept 2025 and now runs the combined
listings API. One search runs per entry in SEARCH_AREAS. Apply at idealist.org/en/open-network-api, then put the key in
an IDEALIST_API_KEY env var / GitHub secret.

Until the key arrives this scraper raises MissingKey and the runner skips it,
so the rest of the pipeline still works.

NOTE: the exact endpoint path and response field names come from the partner
docs you'll get with your key. Everything source-specific is isolated in
_to_opportunity() and SEARCH_URL below -- adjust those two, leave the rest.
"""

from __future__ import annotations

import os
from typing import Iterator

from pipeline.models import Opportunity
from pipeline.normalize import parse_min_age

from .base import Scraper, ScraperError

SEARCH_URL = "https://www.idealist.org/api/v1/listings/volunteer"

#: One search per area we claim to cover.
#:
#: The 15-mile Fremont circle already reaches every neighboring city on the
#: board -- Newark 4mi, Union City 5mi, Milpitas 9mi, Hayward 10mi, Pleasanton
#: 10mi, Dublin 11mi, Castro Valley 11mi. Adding a neighbor usually means
#: adding a city center to pipeline/geocode.py, not a search area here.
#:
#: San Jose at 17mi is the exception and gets its own circle. Don't widen
#: Fremont's radius to swallow it -- at 17+ miles you also pull in Oakland,
#: San Leandro and the Peninsula, which the board doesn't cover.
SEARCH_AREAS: list[tuple[str, float, float, int]] = [
    ("tri_city", 37.5485, -121.9886, 15),   # Fremont City Hall
    ("san_jose", 37.3382, -121.8863, 12),   # San Jose City Hall
]

#: Pages per area before we bail. 100 listings a page; Fremont's whole
#: supply is nowhere near this.
MAX_PAGES = 20


class MissingKey(ScraperError):
    pass


class IdealistScraper(Scraper):
    slug = "idealist"
    name = "Idealist"
    base_url = "https://www.idealist.org"
    check_robots = False  # documented API, not scraping

    def fetch(self) -> Iterator[Opportunity]:
        key = os.environ.get("IDEALIST_API_KEY")
        if not key:
            raise MissingKey("IDEALIST_API_KEY not set")

        self.session.headers["Authorization"] = f"Bearer {key}"
        seen: set[str] = set()

        for _area, lat, lon, radius in SEARCH_AREAS:
            for opp in self._search(lat, lon, radius):
                # Milpitas sits in both circles, so the same listing comes
                # back twice. Dropping it here keeps the run log honest --
                # the store would dedupe by id anyway, but the counts
                # printed by run.py would be inflated.
                if opp.id in seen:
                    continue
                seen.add(opp.id)
                yield opp

        # Deliberately checked across all areas, not per area: an area can
        # legitimately come back empty, but every area empty means the query
        # is wrong and we must not let the store expire real listings.
        if not seen:
            raise ScraperError("Idealist returned zero listings — check the query")

    def _search(self, lat: float, lon: float, radius: int) -> Iterator[Opportunity]:
        page = 0
        while True:
            resp = self.get(
                f"{SEARCH_URL}?lat={lat}&lon={lon}"
                f"&radius={radius}&page={page}&limit=100"
            )
            payload = resp.json()
            listings = payload.get("results") or payload.get("listings") or []
            if not listings:
                return

            for raw in listings:
                opp = self._to_opportunity(raw)
                if opp:
                    yield opp

            page += 1
            if page >= MAX_PAGES:
                return

    def _to_opportunity(self, raw: dict) -> Opportunity | None:
        title = (raw.get("title") or "").strip()
        url = raw.get("url") or raw.get("publicUrl") or ""
        if not title or not url:
            return None

        org = (raw.get("organization") or {}).get("name") or raw.get("orgName") or "Unknown"
        loc = raw.get("location") or {}
        desc = raw.get("description") or ""

        # Idealist exposes an explicit age requirement on many listings.
        stated_age = raw.get("ageRequirement") or raw.get("minimumAge")
        min_age = None
        if stated_age is not None:
            min_age = parse_min_age(str(stated_age)) or _as_int(stated_age)

        good_for = [g.lower() for g in raw.get("goodFor", [])]
        if min_age is None and "teens" in good_for:
            min_age = 13

        return Opportunity(
            source=self.slug,
            title=title,
            org=org,
            url=url,
            min_age=min_age,
            city=loc.get("city"),
            address=loc.get("address"),
            lat=_as_float(loc.get("latitude")),
            lon=_as_float(loc.get("longitude")),
            remote=(raw.get("locationType") or "").lower() == "remote",
            commitment="recurring" if raw.get("recurrence") == "Recurring" else None,
            signs_hours=True if "academic credit" in " ".join(
                b.lower() for b in raw.get("benefits", [])
            ) else None,
            causes=[],  # let normalize.enrich() map these into our buckets
            description=desc,
            starts_on=_iso(raw.get("startDate")),
            ends_on=_iso(raw.get("endDate")),
        )


def _as_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _as_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _iso(v) -> str | None:
    if not v:
        return None
    return str(v)[:10]
