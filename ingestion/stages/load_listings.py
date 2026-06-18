"""Load + clean listings, one configured city at a time.

Cleaning (price, ints, amenities JSON) and amenity normalization happen in the
streaming transform, so only typed Python values reach COPY. The upsert computes
`geom` from lat/lng and deliberately leaves enrichment columns untouched so a
re-load never wipes embeddings or review summaries.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterator, Sequence

from psycopg.types.json import Jsonb

from ..amenities import normalize_amenities
from ..bulk import stream_copy_upsert
from ..context import RunContext
from ..db import (
    connect,
    parse_amenities_raw,
    parse_float,
    parse_int,
    parse_price,
    read_csv_gz,
)
from .base import Stage

log = logging.getLogger("stage.listings")

_STAGING_DDL = """
CREATE TEMP TABLE stg_listings (
    id BIGINT, name TEXT, property_type TEXT, room_type TEXT, city TEXT,
    neighbourhood TEXT, lat DOUBLE PRECISION, lng DOUBLE PRECISION, price NUMERIC,
    beds INT, bedrooms INT, accommodates INT, amenities TEXT[], amenities_raw JSONB,
    photo_url TEXT, host_id BIGINT, host_name TEXT, review_count INT, rating NUMERIC
) ON COMMIT DROP;
"""

_COPY_SQL = """
COPY stg_listings (id, name, property_type, room_type, city, neighbourhood, lat,
    lng, price, beds, bedrooms, accommodates, amenities, amenities_raw, photo_url,
    host_id, host_name, review_count, rating) FROM STDIN
"""

_UPSERT_SQL = """
INSERT INTO properties AS p (id, name, property_type, room_type, city, neighbourhood,
    lat, lng, geom, price, beds, bedrooms, accommodates, amenities, amenities_raw,
    photo_url, host_id, host_name, review_count, rating)
SELECT id, name, property_type, room_type, city, neighbourhood, lat, lng,
       ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
       price, beds, bedrooms, accommodates, amenities, amenities_raw, photo_url,
       host_id, host_name, review_count, rating
FROM stg_listings
WHERE lat IS NOT NULL AND lng IS NOT NULL
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name, property_type = EXCLUDED.property_type,
    room_type = EXCLUDED.room_type, city = EXCLUDED.city,
    neighbourhood = EXCLUDED.neighbourhood, lat = EXCLUDED.lat, lng = EXCLUDED.lng,
    geom = EXCLUDED.geom, price = EXCLUDED.price, beds = EXCLUDED.beds,
    bedrooms = EXCLUDED.bedrooms, accommodates = EXCLUDED.accommodates,
    amenities = EXCLUDED.amenities, amenities_raw = EXCLUDED.amenities_raw,
    photo_url = EXCLUDED.photo_url, host_id = EXCLUDED.host_id,
    host_name = EXCLUDED.host_name, review_count = EXCLUDED.review_count,
    rating = EXCLUDED.rating;
    -- embedding, review_summary, review_aspects, neighbourhood_price_pct preserved
"""


class LoadListingsStage(Stage):
    name = "load_listings"

    async def run(self, ctx: RunContext) -> None:
        await asyncio.to_thread(self._run_sync, ctx)

    def _run_sync(self, ctx: RunContext) -> None:
        with connect(ctx.settings) as conn:
            for city in ctx.settings.cities:
                path = ctx.settings.city_file(city, "listings")
                if not path.exists():
                    log.warning("missing listings for %s (%s)", city, path)
                    continue
                n = stream_copy_upsert(
                    conn,
                    staging_ddl=_STAGING_DDL,
                    copy_sql=_COPY_SQL,
                    upsert_sql=_UPSERT_SQL,
                    rows=self._rows(path, city.title()),
                )
                ctx.add_rows("listings", n)
                log.info("%s: upserted %d listings", city, n)

    @staticmethod
    def _rows(path, city: str) -> Iterator[Sequence[object]]:
        for r in read_csv_gz(path):
            raw_amenities = parse_amenities_raw(r.get("amenities"))
            yield (
                parse_int(r.get("id")),
                r.get("name"),
                r.get("property_type"),
                r.get("room_type"),
                city,
                r.get("neighbourhood_cleansed") or r.get("neighbourhood"),
                parse_float(r.get("latitude")),
                parse_float(r.get("longitude")),
                parse_price(r.get("price")),
                parse_int(r.get("beds")),
                parse_int(r.get("bedrooms")),
                parse_int(r.get("accommodates")),
                normalize_amenities(raw_amenities),
                Jsonb(raw_amenities),
                r.get("picture_url"),
                parse_int(r.get("host_id")),
                r.get("host_name"),
                parse_int(r.get("number_of_reviews")) or 0,
                parse_float(r.get("review_scores_rating")),
            )
