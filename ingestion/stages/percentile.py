"""Neighbourhood price percentile — a free, deterministic enrichment.

Answers 'is this expensive for the area?' with a single window function. Powers
a 'great value' badge in the UI and a price-context signal for the AI layer.
"""
from __future__ import annotations

import logging

from ..context import RunContext
from ..db import connect_async
from .base import Stage

log = logging.getLogger("stage.percentile")

_SQL = """
UPDATE properties p SET neighbourhood_price_pct = s.pct
FROM (
    SELECT id,
           percent_rank() OVER (
               PARTITION BY city, neighbourhood ORDER BY price
           ) AS pct
    FROM properties
    WHERE price IS NOT NULL
) s
WHERE p.id = s.id;
"""


class NeighbourhoodPercentileStage(Stage):
    name = "percentile"

    async def run(self, ctx: RunContext) -> None:
        async with connect_async(ctx.settings) as conn:
            async with conn.cursor() as cur:
                await cur.execute(_SQL)
                ctx.add_rows("percentile", cur.rowcount)
            await conn.commit()
        log.info("computed neighbourhood price percentiles")
