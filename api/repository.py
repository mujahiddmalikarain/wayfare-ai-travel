"""Data access. All booking queries and the hybrid (filter + vector + geo)
retrieval live here, so the SQL is in one auditable place.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from psycopg_pool import AsyncConnectionPool

from .schemas import SearchFilters, TravelQuery

_LISTING_COLS = """
    id, name, property_type, room_type, city, neighbourhood, lat, lng,
    price, beds, bedrooms, accommodates, amenities, photo_url, rating,
    review_count, neighbourhood_price_pct, review_summary
"""

_SORTS = {
    "price": "price ASC NULLS LAST",
    "rating": "rating DESC NULLS LAST",
    "popularity": "review_count DESC",
}

# The intent LLM emits free text for room_type/amenities; map it to the values
# that actually exist in the data so hard filters don't silently zero out the
# result set. Anything we can't map is dropped (the embedding query still carries
# the vibe via the raw message), rather than applied as a filter that excludes all.
_ROOM_TYPE_CANON = {
    "entire home/apt": "Entire home/apt", "entire home": "Entire home/apt",
    "entire place": "Entire home/apt", "entire apartment": "Entire home/apt",
    "entire apt": "Entire home/apt", "entire flat": "Entire home/apt",
    "whole home": "Entire home/apt", "whole place": "Entire home/apt",
    "apartment": "Entire home/apt", "apt": "Entire home/apt", "flat": "Entire home/apt",
    "house": "Entire home/apt", "home": "Entire home/apt",
    "private room": "Private room", "private": "Private room", "room": "Private room",
    "shared room": "Shared room", "shared": "Shared room",
    "hotel room": "Hotel room", "hotel": "Hotel room",
}

_AMENITY_SYNONYMS = {
    "wi_fi": "wifi", "internet": "wifi", "wireless_internet": "wifi",
    "ac": "air_conditioning", "a_c": "air_conditioning", "aircon": "air_conditioning",
    "air_con": "air_conditioning", "free_parking": "parking", "car_park": "parking",
    "washing_machine": "washer", "laundry": "washer", "lift": "elevator",
    "fridge": "refrigerator", "coffee": "coffee_maker", "coffee_machine": "coffee_maker",
    "tv_television": "tv", "television": "tv",
}
# Noise/descriptor words the LLM tends to leak into amenities; never valid tokens.
_AMENITY_FILLER = {"good", "great", "fast", "free", "nice", "central", "modern",
                   "stylish", "cozy", "quiet", "spacious", "clean", "comfortable"}


def _norm_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


def _canon_room_type(rt: str | None) -> str | None:
    if not rt:
        return None
    return _ROOM_TYPE_CANON.get(rt.strip().lower())


class Repository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        self._amenity_vocab: set[str] | None = None

    # ── Traditional search ────────────────────────────────────────────────────
    async def search(self, f: SearchFilters) -> dict[str, Any]:
        where, params = ["city = %(city)s"], {"city": f.city}
        self._apply_common_filters(f, where, params)

        order = _SORTS.get(f.sort, _SORTS["popularity"])
        if f.sort == "distance" and f.near_lat is not None:
            order = "distance_m ASC NULLS LAST"

        params["limit"] = f.page_size
        params["offset"] = (f.page - 1) * f.page_size
        params["near_lat"] = f.near_lat
        params["near_lng"] = f.near_lng

        sql = f"""
            SELECT {_LISTING_COLS}, count(*) OVER() AS total_count,
                   CASE WHEN %(near_lng)s::float8 IS NOT NULL THEN
                        ST_Distance(geom, ST_SetSRID(
                            ST_MakePoint(%(near_lng)s::float8, %(near_lat)s::float8),
                            4326)::geography)
                   END AS distance_m
            FROM properties
            WHERE {" AND ".join(where)}
            ORDER BY {order}
            LIMIT %(limit)s OFFSET %(offset)s
        """
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
        total = rows[0]["total_count"] if rows else 0
        for r in rows:
            r.pop("total_count", None)
        return {"total": total, "page": f.page, "results": rows}

    async def get_property(self, property_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {_LISTING_COLS}, amenities_raw, review_aspects, host_name
            FROM properties WHERE id = %s
        """
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, (property_id,))
            return await cur.fetchone()

    async def get_reviews(self, property_id: int, *, language: str | None = None,
                          topic: str | None = None, sentiment: str | None = None,
                          limit: int = 30) -> list[dict[str, Any]]:
        where = ["property_id = %(pid)s", "text <> ''"]
        params: dict[str, Any] = {"pid": property_id, "limit": limit}
        if language:
            where.append("language = %(lang)s")
            params["lang"] = language
        if topic:
            where.append("aspects @> %(topic)s")
            params["topic"] = [topic]
        if sentiment:
            where.append("sentiment = %(sentiment)s")
            params["sentiment"] = sentiment
        sql = f"""
            SELECT id, date, reviewer, rating, text, language, aspects, sentiment
            FROM reviews WHERE {" AND ".join(where)}
            ORDER BY date DESC NULLS LAST LIMIT %(limit)s
        """
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()

    async def get_availability(self, property_id: int, start: date,
                               end: date) -> list[dict[str, Any]]:
        sql = """
            SELECT date, available, price FROM calendar
            WHERE property_id = %s AND date >= %s AND date < %s ORDER BY date
        """
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, (property_id, start, end))
            return await cur.fetchall()

    # ── AI retrieval (filter + vector + geo in one query) ─────────────────────
    async def _amenity_vocabulary(self) -> set[str]:
        if self._amenity_vocab is None:
            async with self._pool.connection() as conn, conn.cursor() as cur:
                await cur.execute(
                    "SELECT DISTINCT unnest(amenities) AS token FROM properties"
                )
                self._amenity_vocab = {row["token"] for row in await cur.fetchall()}
        return self._amenity_vocab

    async def _canon_amenities(self, raw: list[str]) -> list[str]:
        vocab = await self._amenity_vocabulary()
        out: set[str] = set()
        for item in raw:
            tok = _norm_token(item)
            if not tok or tok in _AMENITY_FILLER:
                continue
            tok = _AMENITY_SYNONYMS.get(tok, tok)
            if tok in vocab:
                out.add(tok)
        return sorted(out)

    async def normalize_intent_filters(
        self, room_type: str | None, amenities: list[str] | None
    ) -> tuple[str | None, list[str]]:
        """Map free-text intent room_type/amenities to values that exist in the
        data. Used by both nl-search and the concierge so a noisy LLM token
        (e.g. 'entire place', 'stylish') never silently zeroes out results."""
        return _canon_room_type(room_type), await self._canon_amenities(amenities or [])

    async def hybrid_retrieve(self, intent: TravelQuery, qvec_literal: str,
                              limit: int) -> list[dict[str, Any]]:
        where = ["city = %(city)s", "embedding IS NOT NULL"]
        params: dict[str, Any] = {"city": intent.city, "qvec": qvec_literal,
                                  "limit": limit}
        if intent.max_price is not None:
            where.append("price <= %(max_price)s")
            params["max_price"] = intent.max_price
        if intent.min_price is not None:
            where.append("price >= %(min_price)s")
            params["min_price"] = intent.min_price
        if intent.guests:
            where.append("accommodates >= %(guests)s")
            params["guests"] = intent.guests
        room_type, amenities = await self.normalize_intent_filters(
            intent.room_type, intent.amenities
        )
        if room_type:
            where.append("room_type = %(room_type)s")
            params["room_type"] = room_type
        if amenities:
            where.append("amenities @> %(amenities)s")
            params["amenities"] = amenities
        if intent.exclude_neighbourhoods:
            where.append("neighbourhood <> ALL(%(exclude)s)")
            params["exclude"] = intent.exclude_neighbourhoods
        if intent.checkin and intent.checkout:
            where.append(
                """NOT EXISTS (SELECT 1 FROM calendar c
                   WHERE c.property_id = properties.id
                     AND c.date >= %(checkin)s AND c.date < %(checkout)s
                     AND c.available = false)"""
            )
            params["checkin"], params["checkout"] = intent.checkin, intent.checkout

        sql = f"""
            SELECT {_LISTING_COLS},
                   1 - (embedding <=> %(qvec)s::vector) AS similarity
            FROM properties
            WHERE {" AND ".join(where)}
            ORDER BY 0.7 * (1 - (embedding <=> %(qvec)s::vector))
                   + 0.3 * (COALESCE(rating, 0) / 5.0) DESC
            LIMIT %(limit)s
        """
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()

    async def reviews_for_properties(self, ids: list[int],
                                     per_property: int = 8) -> dict[int, list[dict]]:
        sql = """
            SELECT id, property_id, text FROM reviews
            WHERE property_id = ANY(%s) AND text <> ''
            ORDER BY property_id, date DESC NULLS LAST
        """
        out: dict[int, list[dict]] = {}
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, (ids,))
            for row in await cur.fetchall():
                bucket = out.setdefault(row["property_id"], [])
                if len(bucket) < per_property:
                    bucket.append({"id": row["id"], "text": row["text"]})
        return out

    # ── Pricing + batch compare ───────────────────────────────────────────────
    async def quote(self, property_id: int, checkin: date, checkout: date,
                    tax_rate: float, cleaning_fee: float) -> dict[str, Any] | None:
        sql = """
            SELECT count(*) FILTER (WHERE available) AS nights,
                   COALESCE(avg(price) FILTER (WHERE available),
                            (SELECT price FROM properties WHERE id = %(pid)s)) AS nightly
            FROM calendar
            WHERE property_id = %(pid)s AND date >= %(ci)s AND date < %(co)s
        """
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, {"pid": property_id, "ci": checkin, "co": checkout})
            row = await cur.fetchone()
        if not row or not row["nightly"]:
            return None
        nights = row["nights"] or (checkout - checkin).days
        nightly = float(row["nightly"])
        subtotal = nights * nightly
        taxes = round(subtotal * tax_rate, 2)
        return {
            "nights": nights, "nightly": round(nightly, 2),
            "subtotal": round(subtotal, 2), "cleaning_fee": cleaning_fee,
            "taxes": taxes, "total": round(subtotal + cleaning_fee + taxes, 2),
        }

    async def compare(self, ids: list[int]) -> list[dict[str, Any]]:
        sql = f"SELECT {_LISTING_COLS}, review_aspects FROM properties WHERE id = ANY(%s)"
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, (ids,))
            return await cur.fetchall()

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_common_filters(f: SearchFilters, where: list[str],
                              params: dict[str, Any]) -> None:
        if f.min_price is not None:
            where.append("price >= %(min_price)s")
            params["min_price"] = f.min_price
        if f.max_price is not None:
            where.append("price <= %(max_price)s")
            params["max_price"] = f.max_price
        if f.min_rating is not None:
            where.append("rating >= %(min_rating)s")
            params["min_rating"] = f.min_rating
        if f.room_type:
            where.append("room_type = %(room_type)s")
            params["room_type"] = f.room_type
        if f.property_type:
            where.append("property_type = %(property_type)s")
            params["property_type"] = f.property_type
        guests = f.effective_guests
        if guests:
            where.append("accommodates >= %(guests)s")
            params["guests"] = guests
        if f.rooms:
            where.append("bedrooms >= %(rooms)s")
            params["rooms"] = f.rooms
        if f.amenities:
            where.append("amenities @> %(amenities)s")
            params["amenities"] = f.amenities
        if f.checkin and f.checkout:
            where.append(
                """NOT EXISTS (SELECT 1 FROM calendar c
                   WHERE c.property_id = properties.id
                     AND c.date >= %(checkin)s AND c.date < %(checkout)s
                     AND c.available = false)"""
            )
            params["checkin"], params["checkout"] = f.checkin, f.checkout
