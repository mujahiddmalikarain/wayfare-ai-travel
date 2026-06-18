"""Bulk-load primitive: stream rows into a TEMP staging table via COPY, then
upsert into the target. This is the scalable, idempotent pattern — COPY is far
faster than row inserts, and the ON CONFLICT upsert makes re-runs safe.
"""
from __future__ import annotations

from typing import Iterable, Sequence

import psycopg


def stream_copy_upsert(
    conn: psycopg.Connection,
    *,
    staging_ddl: str,
    copy_sql: str,
    upsert_sql: str,
    rows: Iterable[Sequence[object]],
) -> int:
    """Returns the number of rows streamed.

    All work happens in one transaction; the TEMP table is dropped on commit.
    """
    count = 0
    with conn.cursor() as cur:
        cur.execute(staging_ddl)
        with cur.copy(copy_sql) as copy:
            for row in rows:
                copy.write_row(row)
                count += 1
        if count:
            cur.execute(upsert_sql)
    conn.commit()
    return count
