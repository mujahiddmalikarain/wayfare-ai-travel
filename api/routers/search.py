"""Traditional booking endpoints — the non-AI product surface."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import Settings
from ..dependencies import get_repo, get_settings
from ..repository import Repository
from ..schemas import SearchFilters

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search(
    city: str,
    checkin: date | None = None,
    checkout: date | None = None,
    guests: int | None = None,
    adults: int | None = None,
    children: int | None = None,
    rooms: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    room_type: str | None = None,
    property_type: str | None = None,
    amenities: list[str] = Query(default=[]),
    near_lat: float | None = None,
    near_lng: float | None = None,
    sort: str = "popularity",
    page: int = 1,
    page_size: int = 24,
    repo: Repository = Depends(get_repo),
):
    filters = SearchFilters(
        city=city, checkin=checkin, checkout=checkout, guests=guests,
        adults=adults, children=children, rooms=rooms,
        min_price=min_price, max_price=max_price, min_rating=min_rating,
        room_type=room_type, property_type=property_type, amenities=amenities,
        near_lat=near_lat, near_lng=near_lng, sort=sort, page=page,
        page_size=page_size,
    )
    return await repo.search(filters)


@router.get("/properties/{property_id}")
async def property_detail(property_id: int, repo: Repository = Depends(get_repo)):
    prop = await repo.get_property(property_id)
    if prop is None:
        raise HTTPException(404, "property not found")
    return prop


@router.get("/properties/{property_id}/reviews")
async def property_reviews(
    property_id: int,
    language: str | None = None,
    topic: str | None = None,        # cleanliness | location | value | staff | noise
    sentiment: str | None = None,    # positive | negative | neutral
    limit: int = 30,
    repo: Repository = Depends(get_repo),
):
    return await repo.get_reviews(
        property_id, language=language, topic=topic, sentiment=sentiment, limit=limit
    )


@router.get("/properties/{property_id}/availability")
async def property_availability(
    property_id: int, start: date, end: date,
    repo: Repository = Depends(get_repo),
):
    return await repo.get_availability(property_id, start, end)


@router.get("/properties/{property_id}/quote")
async def property_quote(
    property_id: int, checkin: date, checkout: date,
    repo: Repository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
):
    quote = await repo.quote(
        property_id, checkin, checkout, settings.tax_rate, settings.cleaning_fee
    )
    if quote is None:
        raise HTTPException(404, "no pricing available for those dates")
    return quote
