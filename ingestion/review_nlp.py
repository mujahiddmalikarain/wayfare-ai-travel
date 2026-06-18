"""Deterministic, no-LLM per-review enrichment.

Inside Airbnb ships ~1M+ reviews per city with no per-review score, so running an
LLM over every review is neither affordable nor necessary just to power review
filters. Instead we tag each review at load time with:

  * aspects   — which topics it touches (cleanliness, location, value, staff,
                noise), via keyword lexicons. Powers "filter reviews by topic".
  * sentiment — positive / negative / neutral, via a small polarity lexicon with
                simple negation handling. Powers "filter reviews by sentiment"
                (the explicit positive/negative idea from the Booking dataset).

This is fast (pure Python, no network), deterministic, and good enough for
filtering UX. Aspect *scores* (1-5) remain a per-property LLM enrichment.
"""
from __future__ import annotations

import re

ASPECT_LEXICON: dict[str, tuple[str, ...]] = {
    "cleanliness": (
        "clean", "cleanliness", "spotless", "tidy", "dirty", "dust", "stain",
        "hygiene", "immaculate", "filthy", "mess",
    ),
    "location": (
        "location", "located", "central", "centre", "center", "neighbourhood",
        "neighborhood", "walk", "metro", "station", "restaurant", "beach",
        "close to", "near", "transport",
    ),
    "value": (
        "value", "price", "worth", "cheap", "expensive", "affordable", "money",
        "overpriced", "bargain", "cost",
    ),
    "staff": (
        "host", "staff", "responsive", "helpful", "communication", "welcoming",
        "rude", "friendly", "checkin", "check-in", "check in", "service",
    ),
    "noise": (
        "noise", "noisy", "quiet", "loud", "silent", "soundproof", "street noise",
        "party", "peaceful",
    ),
}

_POSITIVE = (
    "great", "good", "excellent", "amazing", "wonderful", "perfect", "lovely",
    "comfortable", "clean", "friendly", "helpful", "recommend", "fantastic",
    "beautiful", "spacious", "cosy", "cozy", "spotless", "quiet", "enjoyed",
    "loved", "nice", "best", "convenient", "stunning",
)
_NEGATIVE = (
    "dirty", "noisy", "rude", "bad", "terrible", "awful", "poor", "broken",
    "uncomfortable", "smell", "smelly", "disappointing", "disappointed", "worst",
    "problem", "issue", "cold", "small", "cramped", "filthy", "unhelpful",
    "overpriced", "avoid", "horrible",
)
_NEGATORS = ("not", "no", "never", "n't", "without", "hardly", "barely")

_WORD = re.compile(r"[a-z']+")


def tag_aspects(text: str) -> list[str]:
    """Topics mentioned in the review (subset of the five aspects)."""
    low = text.lower()
    return [a for a, kws in ASPECT_LEXICON.items() if any(k in low for k in kws)]


def tag_sentiment(text: str) -> str:
    """Coarse polarity with light negation handling: positive|negative|neutral."""
    tokens = _WORD.findall(text.lower())
    score = 0
    for i, tok in enumerate(tokens):
        if tok in _POSITIVE:
            delta = 1
        elif tok in _NEGATIVE:
            delta = -1
        else:
            continue
        window = tokens[max(0, i - 3) : i]
        if any(n in window or tok.endswith("n't") for n in _NEGATORS):
            delta = -delta
        score += delta
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"
