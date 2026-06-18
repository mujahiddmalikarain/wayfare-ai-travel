"""Precomputed per-property review summaries + aspect scores (gpt-4o-mini).

Done once at ingest so the detail page and AI layer read a cached field instead
of paying for synthesis per request. Uses Structured Outputs for a guaranteed
schema, bounded concurrency for throughput, and a strict 'use only the supplied
reviews' instruction for hallucination control.

Concurrency model: process properties in chunks. LLM calls within a chunk run
concurrently under a semaphore; DB reads/writes happen sequentially on the
single async connection (psycopg connections aren't safe for concurrent use).
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_random_exponential

from ..context import RunContext
from ..db import connect_async
from .base import Stage

log = logging.getLogger("stage.review_summary")

_SYSTEM = (
    "You summarize guest reviews for a travel listing. Use ONLY the reviews "
    "provided — never invent details. Write one or two sentences in the form "
    "'Guests consistently praise X; some mention Y.' Score each aspect from 1 "
    "(poor) to 5 (excellent) based strictly on the reviews; use null when an "
    "aspect is not discussed."
)


class ReviewAspects(BaseModel):
    cleanliness: float | None
    location: float | None
    value: float | None
    staff: float | None
    noise: float | None


class ReviewDigest(BaseModel):
    summary: str
    aspects: ReviewAspects


class ReviewSummaryStage(Stage):
    name = "review_summary"

    async def run(self, ctx: RunContext) -> None:
        client = AsyncOpenAI(api_key=ctx.settings.openai_api_key)
        sem = asyncio.Semaphore(ctx.settings.summary_concurrency)
        predicate = "" if ctx.force else "AND review_summary IS NULL"
        chunk = max(ctx.settings.summary_concurrency * 6, 30)
        cap = ctx.settings.summary_max_listings
        total = 0

        async with connect_async(ctx.settings) as conn:
            if cap > 0:
                # Bounded run: prioritize the most-reviewed listings (those most
                # likely to surface), select them once, then process in chunks.
                ids_all = await self._top_property_ids(conn, ctx, predicate, cap)
                log.info("review summaries capped at %d listings", cap)
                batches = [
                    ids_all[i : i + chunk] for i in range(0, len(ids_all), chunk)
                ]
            else:
                batches = None  # signal keyset streaming below

            if batches is not None:
                for ids in batches:
                    total += await self._process_ids(conn, client, ctx, sem, ids)
                    log.info("summarized %d listings", total)
            else:
                last_id = 0
                while True:
                    ids = await self._next_property_ids(
                        conn, ctx, predicate, last_id, chunk
                    )
                    if not ids:
                        break
                    total += await self._process_ids(conn, client, ctx, sem, ids)
                    last_id = ids[-1]
                    log.info("summarized %d listings (through id=%d)", total, last_id)

        ctx.add_rows("review_summary", total)

    async def _process_ids(self, conn, client, ctx, sem, ids: list[int]) -> int:
        reviews = await self._reviews_for(conn, ids, ctx)
        tasks = [
            self._digest(client, ctx, sem, pid, reviews.get(pid, [])) for pid in ids
        ]
        results = await asyncio.gather(*tasks)
        written = [r for r in results if r]
        await self._write(conn, written)
        return len(written)

    async def _next_property_ids(self, conn, ctx, predicate, last_id, chunk) -> list[int]:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT id FROM properties
                WHERE id > %s AND review_count >= %s {predicate}
                ORDER BY id LIMIT %s
                """,
                (last_id, ctx.settings.summary_min_reviews, chunk),
            )
            return [row[0] for row in await cur.fetchall()]

    async def _top_property_ids(self, conn, ctx, predicate, cap) -> list[int]:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT id FROM properties
                WHERE review_count >= %s {predicate}
                ORDER BY review_count DESC, id LIMIT %s
                """,
                (ctx.settings.summary_min_reviews, cap),
            )
            return [row[0] for row in await cur.fetchall()]

    async def _reviews_for(self, conn, ids, ctx) -> dict[int, list[str]]:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT property_id, text FROM reviews
                WHERE property_id = ANY(%s) AND text <> ''
                ORDER BY property_id, date DESC NULLS LAST
                """,
                (ids,),
            )
            grouped: dict[int, list[str]] = defaultdict(list)
            limit = ctx.settings.summary_reviews_per_prompt
            for pid, text in await cur.fetchall():
                if len(grouped[pid]) < limit:
                    grouped[pid].append(text)
            return grouped

    async def _digest(self, client, ctx, sem, pid: int, reviews: list[str]):
        if not reviews:
            return None
        async with sem:
            digest = await self._call(client, ctx, reviews)
        return (
            digest.summary,
            json.dumps(digest.aspects.model_dump()),
            pid,
        )

    # Resilient to sustained 429s: at a fixed TPM ceiling the whole batch can
    # stay rate-limited for several seconds, so we need enough attempts and a
    # long-enough backoff for the per-minute token window to drain. Jitter
    # de-syncs concurrent workers so they don't retry in lockstep.
    @retry(
        stop=stop_after_attempt(8),
        wait=wait_random_exponential(multiplier=1, min=2, max=60),
        reraise=True,
    )
    async def _call(self, client, ctx: RunContext, reviews: list[str]) -> ReviewDigest:
        joined = "\n".join(f"- {r[:600]}" for r in reviews)
        completion = await client.beta.chat.completions.parse(
            model=ctx.settings.summary_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Reviews:\n{joined}"},
            ],
            response_format=ReviewDigest,
        )
        if completion.usage:
            ctx.llm_input_tokens += completion.usage.prompt_tokens
            ctx.llm_output_tokens += completion.usage.completion_tokens
        return completion.choices[0].message.parsed

    @staticmethod
    async def _write(conn, rows) -> None:
        if not rows:
            return
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                UPDATE properties
                SET review_summary = %s, review_aspects = %s::jsonb
                WHERE id = %s
                """,
                rows,
            )
        await conn.commit()
