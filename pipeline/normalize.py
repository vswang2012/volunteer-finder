"""Turning messy source text into the fields the filters depend on.

Age is the highest-value field in the whole app and the least consistently
published, so it gets the most attention here.
"""

from __future__ import annotations

import re
from typing import Optional

from .models import CAUSES

# Order matters -- more specific patterns first.
_AGE_PATTERNS: list[tuple[str, int]] = [
    (r"\bages?\s*(\d{1,2})\s*(?:\+|and\s+(?:up|older|above))", 0),
    # No trailing \b here: "14+" ends on a non-word char, so a boundary
    # assertion would never match.
    (r"\b(\d{1,2})\s*(?:\+|and\s+(?:up|older|above))", 0),
    (r"\bmust\s+be\s+(?:at\s+least\s+)?(\d{1,2})\b", 0),
    (r"\bminimum\s+age[:\s]+(\d{1,2})\b", 0),
    (r"\bages?\s*(\d{1,2})\s*(?:-|to|–)\s*\d{1,2}\b", 0),
    (r"\b(\d{1,2})\s*years?\s+(?:of\s+age\s+)?(?:or\s+older|and\s+over)\b", 0),
]

# Phrases that imply an age floor without stating a number.
_AGE_HINTS: list[tuple[str, int]] = [
    (r"\bhigh[- ]school\s+(?:students?|volunteers?|age)", 14),
    (r"\bteen\s+volunteers?\b", 13),
    (r"\bgood\s+for:?\s*teens\b", 13),
    (r"\bmiddle\s+school\b", 11),
    (r"\badults?\s+only\b", 18),
    (r"\bmust\s+be\s+18\b", 18),
]

_CAUSE_KEYWORDS: dict[str, list[str]] = {
    "animals": ["animal", "shelter", "dog", "cat", "wildlife", "humane"],
    "arts": ["art", "museum", "music", "theater", "theatre", "gallery"],
    "community": ["community", "neighborhood", "civic", "cleanup", "clean-up"],
    "education": ["tutor", "education", "literacy", "mentor", "homework", "school"],
    "environment": [
        "environment", "park", "garden", "tree", "creek", "trail",
        "recycl", "sustainab", "coastal", "watershed", "habitat",
    ],
    "food": ["food bank", "pantry", "meal", "hunger", "food distribution", "kitchen"],
    "health": ["hospital", "health", "clinic", "patient", "medical", "blood"],
    "seniors": ["senior", "elder", "assisted living", "retirement"],
    "tech": ["coding", "software", "web", "data", "computer", "stem", "robotics"],
    "youth": ["youth", "kids", "children", "camp", "after-school", "afterschool"],
}

_WEEKEND = re.compile(r"\b(weekend|saturday|sunday|sat\b|sun\b)", re.I)
_WEEKDAY = re.compile(r"\b(weekday|monday|tuesday|wednesday|thursday|friday|after school)", re.I)
_HOURS = re.compile(
    r"\b(community\s+service\s+hours?|service\s+hours?|academic\s+credit|"
    r"sign\s+off|verify\s+hours?|volunteer\s+hours?)\b",
    re.I,
)
_RECURRING = re.compile(r"\b(recurring|weekly|monthly|every\s+\w+day|ongoing)\b", re.I)
_ONE_TIME = re.compile(r"\b(one[- ]time|done\s+in\s+a\s+day|single\s+(?:day|event))\b", re.I)


def parse_min_age(*texts: Optional[str]) -> Optional[int]:
    """Return a stated minimum age, or None if the source never said.

    Returning None rather than a guess is intentional: the UI shows those
    listings under "age not stated" so students know to ask, instead of
    being quietly filtered out of something they could have done.
    """
    blob = " ".join(t for t in texts if t).lower()
    if not blob:
        return None

    for pattern, _ in _AGE_PATTERNS:
        m = re.search(pattern, blob)
        if m:
            age = int(m.group(1))
            if 5 <= age <= 25:  # sanity bound; filters out "must be 100% reliable"
                return age

    for pattern, implied in _AGE_HINTS:
        if re.search(pattern, blob):
            return implied

    return None


def detect_causes(*texts: Optional[str]) -> list[str]:
    blob = " ".join(t for t in texts if t).lower()
    found = [
        cause
        for cause, words in _CAUSE_KEYWORDS.items()
        if any(w in blob for w in words)
    ]
    return sorted(found) or []


def detect_schedule(*texts: Optional[str]) -> tuple[Optional[bool], Optional[bool]]:
    blob = " ".join(t for t in texts if t)
    if not blob:
        return None, None
    weekend = bool(_WEEKEND.search(blob)) or None
    weekday = bool(_WEEKDAY.search(blob)) or None
    return weekend, weekday


def detect_commitment(*texts: Optional[str]) -> Optional[str]:
    blob = " ".join(t for t in texts if t)
    if _ONE_TIME.search(blob):
        return "one_time"
    if _RECURRING.search(blob):
        return "recurring"
    return None


def detect_signs_hours(*texts: Optional[str]) -> Optional[bool]:
    blob = " ".join(t for t in texts if t)
    return True if _HOURS.search(blob) else None


def clean_text(s: Optional[str], limit: int = 600) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s


def enrich(opp) -> None:
    """Fill in any inferable field the scraper left blank. Mutates in place.

    Scraper-supplied values always win -- an explicit "Age Requirement: 14+"
    on the page beats anything we pattern-match out of prose.
    """
    text = (opp.title, opp.description)
    if opp.min_age is None:
        opp.min_age = parse_min_age(*text)
    if not opp.causes:
        opp.causes = detect_causes(*text)
    if opp.weekend is None or opp.weekday is None:
        we, wd = detect_schedule(*text)
        opp.weekend = opp.weekend if opp.weekend is not None else we
        opp.weekday = opp.weekday if opp.weekday is not None else wd
    if opp.commitment is None:
        opp.commitment = detect_commitment(*text)
    if opp.signs_hours is None:
        opp.signs_hours = detect_signs_hours(*text)
    opp.description = clean_text(opp.description)
