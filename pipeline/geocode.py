"""Local, no-key coordinate assignment for the static site.

This project stays keyless by resolving coordinates during data generation,
not in the browser. We prefer a curated lookup for known addresses and fall
back to coarse city centers when a listing only names the city.
"""

from __future__ import annotations

from .models import Opportunity

CITY_CENTERS: dict[str, tuple[float, float]] = {
    "fremont": (37.5483, -121.9886),
    "newark": (37.5297, -122.0402),
    "union city": (37.5934, -122.0438),
    "san jose": (37.3362, -121.8906),
    "milpitas": (37.4323, -121.8996),
    "hayward": (37.6688, -122.0808),
    "castro valley": (37.6941, -122.0863),
    "dublin": (37.7022, -121.9358),
    "pleasanton": (37.6624, -121.8747),
}

ADDRESS_COORDS: dict[str, tuple[float, float]] = {
    "2400 stevenson blvd, fremont, ca": (37.5478, -121.9687),
    "2450 stevenson blvd, fremont, ca": (37.5491, -121.9697),
    "36060 fremont blvd, fremont, ca": (37.5560, -122.0146),
    "36501 niles blvd, fremont, ca": (37.5768, -121.9708),
    "525 h st, union city, ca": (37.5956, -122.0686),
    "34009 alvarado-niles rd, union city, ca": (37.5870, -122.0663),
    "37365 ash st, newark, ca": (37.5225, -122.0325),
    "901 ames ave, milpitas, ca": (37.4156, -121.9098),
    "888 c st, hayward, ca": (37.6725, -122.0806),
    "1801 d st, hayward, ca": (37.6707, -122.0668),
    "3670 nevada st, pleasanton, ca": (37.6604, -121.8770),
    "5353 sunol blvd, pleasanton, ca": (37.6479, -121.8834),
}

ORG_CITY_COORDS: dict[tuple[str, str], tuple[float, float]] = {
    ("save (safe alternatives to violent environments)", "fremont"): (37.5509, -121.9828),
    ("urban forest friends", "fremont"): (37.5630, -121.9829),
    ("washington hospital", "fremont"): (37.5574, -121.9807),
    ("bountiful blossom", "fremont"): (37.5532, -121.9698),
    ("city of fremont environmental services", "fremont"): (37.5485, -121.9880),
    ("san josé public library", "san jose"): (37.3355, -121.8850),
    ("san jose public library", "san jose"): (37.3355, -121.8850),
    ("second harvest of silicon valley", "san jose"): (37.3051, -121.8515),
    ("city of san josé parks, recreation & neighborhood services", "san jose"): (37.3335, -121.9009),
    ("city of san jose parks, recreation & neighborhood services", "san jose"): (37.3335, -121.9009),
    ("league of volunteers", "newark"): (37.5263, -122.0322),
    ("newark police department", "newark"): (37.5322, -122.0381),
    ("newark unified school district", "newark"): (37.5269, -122.0304),
    ("tri-city volunteers", "fremont"): (37.5483, -121.9886),
    ("centro de servicios", "union city"): (37.5956, -122.0686),
    ("viola blythe community services", "newark"): (37.5225, -122.0325),
    ("union city community & recreation services", "union city"): (37.5870, -122.0663),
    # These three publish no street address on the pages we link to, so they
    # resolve by org instead of falling back to a city center.
    ("castro valley library", "castro valley"): (37.6960, -122.0757),
    ("dublin police services", "dublin"): (37.7061, -121.9298),
    ("city of dublin parks & community services", "dublin"): (37.7061, -121.9298),
}


def assign_coordinates(opportunity: Opportunity) -> Opportunity:
    """Fill lat/lon without any external API dependency."""
    if opportunity.lat is not None and opportunity.lon is not None:
        return opportunity

    address_key = _norm(opportunity.address)
    if address_key and address_key in ADDRESS_COORDS:
        opportunity.lat, opportunity.lon = ADDRESS_COORDS[address_key]
        return opportunity

    org_key = (_norm(opportunity.org), _norm(opportunity.city))
    if all(org_key) and org_key in ORG_CITY_COORDS:
        opportunity.lat, opportunity.lon = ORG_CITY_COORDS[org_key]
        return opportunity

    city_key = _norm(opportunity.city)
    if city_key in CITY_CENTERS:
        opportunity.lat, opportunity.lon = CITY_CENTERS[city_key]

    return opportunity


def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())