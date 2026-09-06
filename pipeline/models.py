"""The single schema every scraper must produce.

If a scraper can't fill a field, it leaves it as None. Never guess. A missing
min_age is very different from min_age=0, and students filtering for "I'm 15"
need to know which one they're looking at.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# Cause buckets we normalize into. Sources use wildly different vocabularies.
CAUSES = [
    "animals",
    "arts",
    "community",
    "education",
    "environment",
    "food",
    "health",
    "seniors",
    "tech",
    "youth",
]

COMMITMENTS = ["one_time", "recurring", "ongoing"]


@dataclass
class Opportunity:
    # --- identity -----------------------------------------------------
    source: str                      # scraper slug, e.g. "fremont_gov"
    title: str
    org: str
    url: str

    # --- the fields students actually filter on -----------------------
    min_age: Optional[int] = None    # None = source didn't say. Show as "not stated".
    max_age: Optional[int] = None
    city: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    remote: bool = False

    commitment: Optional[str] = None      # one of COMMITMENTS
    weekend: Optional[bool] = None        # available on weekends
    weekday: Optional[bool] = None
    signs_hours: Optional[bool] = None    # will verify community service hours
    causes: list[str] = field(default_factory=list)

    description: str = ""
    starts_on: Optional[str] = None       # ISO date
    ends_on: Optional[str] = None

    # --- lifecycle, managed by the store, never by a scraper ----------
    id: str = ""
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    status: str = "open"                  # open | expired

    def __post_init__(self) -> None:
        if not self.id:
            self.id = self.stable_id()

    def stable_id(self) -> str:
        """Survives cosmetic changes to a listing, breaks on real ones.

        Deliberately excludes description and dates -- orgs edit those
        constantly, and a reworded blurb should not read as a brand new
        opportunity in the weekly digest.
        """
        key = "|".join(
            [
                self.source,
                _slug(self.org),
                _slug(self.title),
                _canonical_url(self.url),
            ]
        )
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Opportunity":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def _slug(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _canonical_url(url: str) -> str:
    """Strip tracking junk so ?utm_source=... doesn't spawn a duplicate."""
    url = (url or "").strip().lower()
    url = re.sub(r"[?&](utm_[a-z]+|fbclid|gclid|ref|source)=[^&]*", "", url)
    url = re.sub(r"[?&]$", "", url)
    return url.rstrip("/")
