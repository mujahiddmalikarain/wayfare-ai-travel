"""Listing embeddings (text-embedding-3-small) for semantic retrieval.

Idempotent via keyset pagination over rows where `embedding IS NULL` (or all
rows when --force). Embeds in batches, retries transient OpenAI errors, and
writes vectors back with executemany. We embed listings only — per-review
embeddings are deliberately skipped (see README trade-offs).
"""
from __future__ import annotations

import logging
from typing import Sequence

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..context import RunContext
from ..db import connect_async
from .base import Stage

log = logging.getLogger("stage.embeddings")


def _listing_text(row: Sequence) -> str:
    _id, name, room_type, neighbourhood, city, amenities = row
    amenities = amenities or []
    parts = [
        name or "",
        f"{room_type or 'place'} in {neighbourhood or city}, {city}",
        "Amenities: " + ", ".join(a.replace("_", " ") for a in amenities[:15]),
    ]
    return " | ".join(p for p in parts if p.strip())


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


class EmbeddingStage(Stage):
    name = "embeddings"

    async def run(self, ctx: RunContext) -> None:
        client = AsyncOpenAI(api_key=ctx.settings.openai_api_key)
        predicate = "" if ctx.force else "AND embedding IS NULL"
        batch = ctx.settings.embed_batch_size
        last_id, total = 0, 0

        async with connect_async(ctx.settings) as conn:
            while True:
                rows = await self._fetch_batch(conn, predicate, last_id, batch)
                if not rows:
                    break
                vectors = await self._embed(
                    client, ctx, [_listing_text(r) for r in rows]
                )
                await self._write(conn, rows, vectors)
                last_id = rows[-1][0]
                total += len(rows)
                log.info("embedded %d listings (through id=%d)", total, last_id)

        ctx.add_rows("embeddings", total)

    @staticmethod
    async def _fetch_batch(conn, predicate: str, last_id: int, batch: int):
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT id, name, room_type, neighbourhood, city, amenities
                FROM properties
                WHERE id > %s {predicate}
                ORDER BY id
                LIMIT %s
                """,
                (last_id, batch),
            )
            return await cur.fetchall()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _embed(self, client, ctx: RunContext, texts: list[str]) -> list[list[float]]:
        resp = await client.embeddings.create(
            model=ctx.settings.embedding_model, input=texts
        )
        ctx.embedding_tokens += resp.usage.total_tokens
        return [item.embedding for item in resp.data]

    @staticmethod
    async def _write(conn, rows, vectors: list[list[float]]) -> None:
        params = [(_vector_literal(v), row[0]) for row, v in zip(rows, vectors)]
        async with conn.cursor() as cur:
            await cur.executemany(
                "UPDATE properties SET embedding = %s::vector WHERE id = %s", params
            )
        await conn.commit()
