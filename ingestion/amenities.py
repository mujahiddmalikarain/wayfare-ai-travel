"""Amenity normalization — a deterministic, zero-cost enrichment.

Inside Airbnb amenity strings are noisy and inconsistent ('Wifi', 'Wireless
Internet', 'Free wifi'). We fold them into a small canonical vocabulary so the
amenities filter and the `@>` array-contains queries behave predictably.
"""
from __future__ import annotations

import re

# Canonical token -> substrings that should map to it (checked in order).
_RULES: dict[str, tuple[str, ...]] = {
    "wifi": ("wifi", "wireless", "internet"),
    "kitchen": ("kitchen", "kitchenette", "cooking basics"),
    "parking": ("parking", "garage", "carport"),
    "pool": ("pool",),
    "hot_tub": ("hot tub", "jacuzzi"),
    "air_conditioning": ("air conditioning", "a/c", "ac unit"),
    "heating": ("heating",),
    "washer": ("washer", "washing machine"),
    "dryer": ("dryer",),
    "tv": ("tv", "television", "hdtv"),
    "elevator": ("elevator", "lift"),
    "gym": ("gym", "fitness"),
    "balcony": ("balcony", "patio", "terrace"),
    "workspace": ("workspace", "dedicated workspace"),
    "self_checkin": ("self check-in", "self checkin", "lockbox", "keypad"),
    "pets_allowed": ("pets allowed", "pet friendly"),
    "breakfast": ("breakfast",),
    "smoke_alarm": ("smoke alarm",),
    "crib": ("crib", "pack 'n play", "pack n play"),
    "ev_charger": ("ev charger", "electric vehicle"),
}

_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")


def _canonicalize(raw: str) -> str:
    text = _NON_ALNUM.sub(" ", raw.lower()).strip()
    for canonical, needles in _RULES.items():
        if any(needle in text for needle in needles):
            return canonical
    # Fall back to a slugified version so unknown amenities are still usable.
    return re.sub(r"\s+", "_", text)[:40] or "unknown"


def normalize_amenities(raw_amenities: list[str]) -> list[str]:
    """Map raw amenity strings to a sorted, de-duplicated canonical set."""
    return sorted({_canonicalize(a) for a in raw_amenities if a})
