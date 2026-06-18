"""Async Postgres connection pool (psycopg 3). Opened once in the app lifespan."""
from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import Settings


def make_pool(settings: Settings) -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
        kwargs={"row_factory": dict_row},
        open=False,
    )
