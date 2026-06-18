"""Load calendar availability, streamed and windowed.

Calendar files are the largest input (≈365 rows per listing). We stream them
flat (no DataFrame) and keep only the next `CALENDAR_DAYS` so the booking
search stays fast and the table stays bounded. Rows for listings we didn't load
are discarded by the FK-safe join in the upsert.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Iterator, Sequence

from ..bulk import stream_copy_upsert
from ..context import RunContext
from ..db import connect, parse_date, parse_int, parse_price, read_csv_gz
from .base import Stage

log = logging.getLogger("stage.calendar")

_STAGING_DDL = """
CREATE TEMP TABLE stg_calendar (
    property_id BIGINT, date DATE, available BOOLEAN, price NUMERIC
) ON COMMIT DROP;
"""

_COPY_SQL = "COPY stg_calendar (property_id, date, available, price) FROM STDIN"

# Join against properties so we never insert calendar rows for unknown listings.
_UPSERT_SQL = """
INSERT INTO calendar (property_id, date, available, price)
SELECT s.property_id, s.date, s.available, s.price
FROM stg_calendar s
JOIN properties p ON p.id = s.property_id
ON CONFLICT (property_id, date) DO UPDATE SET
    available = EXCLUDED.available, price = EXCLUDED.price;
"""


class LoadCalendarStage(Stage):
    name = "load_calendar"

    async def run(self, ctx: RunContext) -> None:
        await asyncio.to_thread(self._run_sync, ctx)

    def _run_sync(self, ctx: RunContext) -> None:
        start = date.today()
        # Inclusive window: today + (calendar_days - 1).
        horizon = start + timedelta(days=max(ctx.settings.calendar_days - 1, 0))
        with connect(ctx.settings) as conn:
            for city in ctx.settings.cities:
                path = ctx.settings.city_file(city, "calendar")
                if not path.exists():
                    log.warning("missing calendar for %s (%s)", city, path)
                    continue
                n = stream_copy_upsert(
                    conn,
                    staging_ddl=_STAGING_DDL,
                    copy_sql=_COPY_SQL,
                    upsert_sql=_UPSERT_SQL,
                    rows=self._rows(path, start, horizon),
                )
                ctx.add_rows("calendar", n)
                log.info("%s: upserted %d calendar rows", city, n)

    @staticmethod
    def _rows(path, start: date, horizon: date) -> Iterator[Sequence[object]]:
        for r in read_csv_gz(path):
            d = parse_date(r.get("date"))
            if d is None or d < start or d > horizon:
                continue
            yield (
                parse_int(r.get("listing_id")),
                d,
                (r.get("available") or "").strip().lower() == "t",
                parse_price(r.get("price")),
            )
