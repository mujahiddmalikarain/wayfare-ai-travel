"""Request/response contracts and the structured shapes the LLM must return."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


# ── Traditional search ────────────────────────────────────────────────────────
class SearchFilters(BaseModel):
    city: str
    checkin: date | None = None
    checkout: date | None = None
    guests: int | None = None          # total; derived from adults+children if unset
    adults: int | None = None
    children: int | None = None
    rooms: int | None = None           # min bedrooms
    min_price: float | None = None
    max_price: float | None = None
    min_rating: float | None = None
    room_type: str | None = None
    property_type: str | None = None
    amenities: list[str] = Field(default_factory=list)
    near_lat: float | None = None
    near_lng: float | None = None
    sort: str = "popularity"  # price | rating | distance | popularity
    page: int = 1
    page_size: int = 24

    @property
    def effective_guests(self) -> int | None:
        if self.guests is not None:
            return self.guests
        party = (self.adults or 0) + (self.children or 0)
        return party or None


# ── Structured LLM outputs (Structured Outputs / strict schema) ───────────────
class TravelQuery(BaseModel):
    """Parsed natural-language search intent."""

    city: str | None = None
    checkin: str | None = None
    checkout: str | None = None
    nights: int | None = None
    guests: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    room_type: str | None = None
    amenities: list[str] = Field(default_factory=list)
    exclude_neighbourhoods: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    multi_stop: bool = False


class Highlight(BaseModel):
    claim: str
    review_ids: list[int]


class ReviewInsight(BaseModel):
    summary: str
    highlights: list[Highlight]


class ItineraryStay(BaseModel):
    day: int
    property_id: int
    reason: str
    nightly_price: float


class ItineraryPlan(BaseModel):
    title: str
    stays: list[ItineraryStay]
    total_cost: float
    notes: str


# ── Concierge ─────────────────────────────────────────────────────────────────
class ConciergeRequest(BaseModel):
    message: str
    city: str | None = None
