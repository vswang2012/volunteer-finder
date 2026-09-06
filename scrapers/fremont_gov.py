"""City of Fremont volunteer pages.

These listings almost never appear on Idealist, which is exactly why the app
is worth building. Parks & Rec, Environmental Services, Coastal Cleanup and
Adopt-A-Drain all run through the city site.

⚠ SELECTORS ARE UNVERIFIED. Municipal sites are CMS-driven and change layout
without notice. Open the page, confirm the markup, adjust the CSS selectors
in PAGES and _parse_page below. The scraper raises loudly rather than
returning an empty list, so a layout change shows up in your Actions log as a
red X instead of silently emptying the site.
"""

from __future__ import annotations

from typing import Iterator
from urllib.parse import urljoin

from pipeline.models import Opportunity

from .base import Scraper, ScraperError

PAGES = [
    "https://www.fremont.gov/residents/volunteer",
    "https://www.fremont.gov/government/departments/community-services/volunteer",
]

# Candidate containers, tried in order. Widen this list as you inspect pages.
ITEM_SELECTORS = [
    "div.listing-item",
    "article.node",
    "div.field--item",
    "main li",
]


class FremontGovScraper(Scraper):
    slug = "fremont_gov"
    name = "City of Fremont"
    base_url = "https://www.fremont.gov"

    def fetch(self) -> Iterator[Opportunity]:
        found = 0
        for page_url in PAGES:
            for opp in self._parse_page(page_url):
                yield opp
                found += 1

        if found == 0:
            raise ScraperError(
                "No listings parsed from fremont.gov — the page layout "
                "probably changed. Update ITEM_SELECTORS."
            )

    def _parse_page(self, page_url: str) -> Iterator[Opportunity]:
        soup = self.soup(page_url)

        items = []
        for selector in ITEM_SELECTORS:
            items = soup.select(selector)
            if len(items) >= 2:  # one match is usually a false positive
                break

        for item in items:
            link = item.find("a", href=True)
            if not link:
                continue

            title = link.get_text(strip=True)
            if len(title) < 6:
                continue

            # Skip nav chrome that matches a generic "main li" selector.
            if title.lower() in {"home", "contact us", "residents", "government"}:
                continue

            body = item.get_text(" ", strip=True)

            yield Opportunity(
                source=self.slug,
                title=title,
                org="City of Fremont",
                url=urljoin(page_url, link["href"]),
                city="Fremont",
                description=body,
                # min_age, causes and schedule are inferred by normalize.enrich()
            )
