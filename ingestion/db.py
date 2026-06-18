"""Database access and small, well-tested parsing helpers.

We keep one driver (psycopg 3) for both sync bulk loads (COPY) and async
enrichment writes, so there's a single mental model for connections.
"""
from __future__ import annotations

import gzip
import json
from contextlib import asynccontextmanager, contextmanager
from datetime import date
from typing import Iterator, AsyncIterator

import psycopg

from .config import Settings


# ── Connections ───────────────────────────────────────────────────────────────
@contextmanager
def connect(settings: Settings) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(settings.database_url)
    try:
        yield conn
    finally:
        conn.close()


@asynccontextmanager
async def connect_async(settings: Settings) -> AsyncIterator[psycopg.AsyncConnection]:
    conn = await psycopg.AsyncConnection.connect(settings.database_url)
    try:
        yield conn
    finally:
        await conn.close()


# ── CSV helpers ───────────────────────────────────────────────────────────────
def read_csv_gz(path) -> Iterator[dict[str, str]]:
    """Stream rows from a CSV without loading it into memory.

    Transparently handles gzipped (`.csv.gz`) and plain (`.csv`) files, so the
    pipeline works whether the Inside Airbnb downloads are left compressed or
    already decompressed on disk.
    """
    import csv

    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, mode="rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def parse_price(raw: str | None) -> float | None:
    """Inside Airbnb prices look like '$1,234.00'."""
    if not raw:
        return None
    cleaned = raw.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int(raw: str | None) -> int | None:
    if raw in (None, "", "NaN"):
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def parse_float(raw: str | None) -> float | None:
    if raw in (None, "", "NaN"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def parse_amenities_raw(raw: str | None) -> list[str]:
    """Inside Airbnb stores amenities as a JSON array string."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return [str(a) for a in value] if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
