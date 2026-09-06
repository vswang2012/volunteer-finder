"""Base class every scraper inherits.

Design rule: a scraper either returns a full list of what it found, or it
raises. It never returns a partial list on error -- a half-scrape looks
identical to "half the listings closed" and would wrongly expire them.
"""

from __future__ import annotations

import time
import urllib.robotparser
from typing import Iterator
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from pipeline.models import Opportunity

USER_AGENT = (
    "FremontVolunteerFinder/1.0 (student project; "
    "contact: your-email@example.com)"
)

# Be a good citizen. These are small nonprofit servers, not a CDN.
REQUEST_DELAY_SECONDS = 2.0
TIMEOUT = 20


class ScraperError(RuntimeError):
    pass


class Scraper:
    slug: str = ""
    name: str = ""
    base_url: str = ""
    #: Set False only for sources with a documented API and a key.
    check_robots: bool = True

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last_request = 0.0
        self._robots: urllib.robotparser.RobotFileParser | None = None

    # -- subclasses implement this -------------------------------------
    def fetch(self) -> Iterator[Opportunity]:
        raise NotImplementedError

    # -- plumbing ------------------------------------------------------
    def get(self, url: str) -> requests.Response:
        if self.check_robots and not self._allowed(url):
            raise ScraperError(f"robots.txt disallows {url}")
        self._throttle()
        resp = self.session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp

    def soup(self, url: str) -> BeautifulSoup:
        return BeautifulSoup(self.get(url).text, "html.parser")

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request = time.monotonic()

    def _allowed(self, url: str) -> bool:
        if self._robots is None:
            parts = urlparse(url)
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
            try:
                rp.read()
            except Exception:
                # No reachable robots.txt: proceed, but stay slow and polite.
                rp.parse([])
            self._robots = rp
        return self._robots.can_fetch(USER_AGENT, url)
