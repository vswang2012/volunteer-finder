"""One module per source. Register new scrapers in ALL_SCRAPERS below.

MissingKey is re-exported here because run.py treats it differently from a
real failure: a source without credentials is skipped, not counted as broken.
"""

from .base import Scraper, ScraperError
from .fremont_gov import FremontGovScraper
from .idealist_api import IdealistScraper, MissingKey

#: Order is cosmetic -- it only sets the order of the run log.
ALL_SCRAPERS: list[type[Scraper]] = [
    IdealistScraper,
    FremontGovScraper,
]

__all__ = ["ALL_SCRAPERS", "Scraper", "ScraperError", "MissingKey"]
