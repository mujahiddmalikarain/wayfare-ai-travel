"""Load reviews, with an optional per-listing cap and language detection.

Inside Airbnb reviews carry no per-review rating, so `rating` stays null and the
listing-level `review_scores_rating` is used elsewhere. Language is detected at
ingest to power the 'filter reviews by language' feature; it's the slowest part
of loading, so it's gated behind DETECT_LANGUAGE. For very large corpora swap
langdetect for fastText's lid.176 model.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Iterator, Sequence

from ..bulk import stream_copy_upsert
from ..context import RunContext
from ..db import connect, parse_date, parse_int, read_csv_gz
from ..review_nlp import tag_aspects, tag_sentiment
from .base import Stage

log = logging.getLogger("stage.reviews")

_STAGING_DDL = """
CREATE TEMP TABLE stg_reviews (
    id BIGINT, property_id BIGINT, date DATE, reviewer TEXT, text TEXT,
    language TEXT, aspects TEXT[], sentiment TEXT
) ON COMMIT DROP;
"""

_COPY_SQL = (
    "COPY stg_reviews (id, property_id, date, reviewer, text, language, aspects, "
    "sentiment) FROM STDIN"
)

_UPSERT_SQL = """
INSERT INTO reviews (id, property_id, date, reviewer, text, language, aspects, sentiment)
SELECT s.id, s.property_id, s.date, s.reviewer, s.text, s.language, s.aspects, s.sentiment
FROM stg_reviews s
JOIN properties p ON p.id = s.property_id
ON CONFLICT (id) DO UPDATE SET
    text = EXCLUDED.text, language = EXCLUDED.language,
    aspects = EXCLUDED.aspects, sentiment = EXCLUDED.sentiment;
"""


class LoadReviewsStage(Stage):
    name = "load_reviews"

    async def run(self, ctx: RunContext) -> None:
        await asyncio.to_thread(self._run_sync, ctx)

    def _run_sync(self, ctx: RunContext) -> None:
        detect = self._language_detector() if ctx.settings.detect_language else None
        with connect(ctx.settings) as conn:
            for city in ctx.settings.cities:
                path = ctx.settings.city_file(city, "reviews")
                if not path.exists():
                    log.warning("missing reviews for %s (%s)", city, path)
                    continue
                n = stream_copy_upsert(
                    conn,
                    staging_ddl=_STAGING_DDL,
                    copy_sql=_COPY_SQL,
                    upsert_sql=_UPSERT_SQL,
                    rows=self._rows(path, ctx.settings.max_reviews_per_listing, detect),
                )
                ctx.add_rows("reviews", n)
                log.info("%s: upserted %d reviews", city, n)

    @staticmethod
    def _rows(path, cap: int, detect) -> Iterator[Sequence[object]]:
        seen: dict[int, int] = defaultdict(int)
        for r in read_csv_gz(path):
            pid = parse_int(r.get("listing_id"))
            if pid is None:
                continue
            if cap and seen[pid] >= cap:
                continue
            seen[pid] += 1
            text = r.get("comments") or ""
            yield (
                parse_int(r.get("id")),
                pid,
                parse_date(r.get("date")),
                r.get("reviewer_name"),
                text,
                detect(text) if detect else None,
                tag_aspects(text),
                tag_sentiment(text) if text.strip() else None,
            )

    @staticmethod
    def _language_detector():
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0  # deterministic

        def _detect(text: str) -> str | None:
            stripped = text.strip()
            if len(stripped) < 12:
                return None
            try:
                return detect(stripped)
            except Exception:  # langdetect raises on empty/garbage input
                return None

        return _detect
