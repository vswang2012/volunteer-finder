"""The merge logic is the product. Test it like it is.

    python -m pytest tests/ -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.geocode import assign_coordinates
from pipeline.models import Opportunity
from pipeline.normalize import parse_min_age, enrich
from pipeline.store import Store


def opp(title="Trail crew", org="Fremont Parks", url="https://x.test/1", **kw):
    return Opportunity(source="test", title=title, org=org, url=url, **kw)


def store(tmp_path):
    return Store(tmp_path / "data.json")


# --- identity ---------------------------------------------------------

def test_id_is_stable_across_description_edits():
    a = opp(description="Come help out!")
    b = opp(description="Come help out on Saturdays, gloves provided.")
    assert a.id == b.id


def test_id_ignores_tracking_params():
    a = opp(url="https://x.test/1")
    b = opp(url="https://x.test/1?utm_source=newsletter")
    assert a.id == b.id


def test_different_org_is_a_different_listing():
    assert opp(org="Fremont Parks").id != opp(org="Tri-City Volunteers").id


# --- lifecycle --------------------------------------------------------

def test_first_seen_is_never_overwritten(tmp_path):
    s = store(tmp_path)
    s.merge([opp()], "2026-09-07", ["test"], [])
    s.merge([opp(description="edited")], "2026-09-14", ["test"], [])
    assert s.opportunities[opp().id].first_seen == "2026-09-07"
    assert s.opportunities[opp().id].last_seen == "2026-09-14"


def test_new_only_counts_genuinely_new(tmp_path):
    s = store(tmp_path)
    s.merge([opp(title="A")], "2026-09-07", ["test"], [])
    report = s.merge(
        [opp(title="A"), opp(title="B", url="https://x.test/2")],
        "2026-09-14", ["test"], [],
    )
    assert [o.title for o in report.new] == ["B"]


def test_listing_expires_after_grace_period(tmp_path):
    s = store(tmp_path)
    s.merge([opp()], "2026-09-07", ["test"], [])
    s.merge([], "2026-09-14", ["test"], [])          # missing once: still shown
    assert s.opportunities[opp().id].status == "open"
    r = s.merge([], "2026-09-21", ["test"], [])       # missing twice: hidden
    assert s.opportunities[opp().id].status == "expired"
    assert len(r.expired) == 1


def test_failed_source_does_not_expire_its_listings(tmp_path):
    """The bug that would quietly empty the site. Guard it."""
    s = store(tmp_path)
    s.merge([opp()], "2026-09-07", ["test"], [])
    s.merge([], "2026-09-14", [], ["test"])
    s.merge([], "2026-09-21", [], ["test"])
    assert s.opportunities[opp().id].status == "open"


def test_returning_listing_is_reopened_not_duplicated(tmp_path):
    s = store(tmp_path)
    s.merge([opp()], "2026-09-07", ["test"], [])
    s.merge([], "2026-09-14", ["test"], [])
    s.merge([], "2026-09-21", ["test"], [])
    r = s.merge([opp()], "2026-09-28", ["test"], [])
    assert len(s.opportunities) == 1
    assert len(r.new) == 0
    assert len(r.returning) == 1
    assert s.opportunities[opp().id].first_seen == "2026-09-07"


def test_roundtrip_through_disk(tmp_path):
    s = store(tmp_path)
    s.merge([opp()], "2026-09-07", ["test"], [])
    s.save()
    again = Store(tmp_path / "data.json")
    assert again.opportunities[opp().id].first_seen == "2026-09-07"


# --- age parsing, the highest-value field -----------------------------

def test_age_parsing():
    cases = {
        "Age Requirement: 14+": 14,
        "Volunteers must be at least 16 years old": 16,
        "Open to ages 13 and up": 13,
        "Ages 12-17 welcome": 12,
        "Minimum age: 18": 18,
        "Great for high school students": 14,
        "Good For: Teens": 13,
        "Adults only please": 18,
    }
    for text, expected in cases.items():
        assert parse_min_age(text) == expected, text


def test_unstated_age_stays_none():
    assert parse_min_age("Help us sort donations on Saturday morning.") is None


def test_age_sanity_bound():
    assert parse_min_age("We need 100% reliable volunteers") is None


def test_scraper_supplied_age_wins_over_inference():
    o = opp(min_age=16, description="Great for high school students")
    enrich(o)
    assert o.min_age == 16


def test_assign_coordinates_uses_city_center_fallback():
    o = opp(city="Fremont")
    assign_coordinates(o)
    assert o.lat is not None
    assert o.lon is not None


def test_assign_coordinates_prefers_known_address():
    o = opp(city="Fremont", address="2400 Stevenson Blvd, Fremont, CA")
    assign_coordinates(o)
    assert (o.lat, o.lon) == (37.5478, -121.9687)
