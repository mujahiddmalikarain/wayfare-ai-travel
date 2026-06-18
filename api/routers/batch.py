"""Batch endpoints. Compare runs an AI verdict over 2-5 listings; the summaries
endpoint produces review syntheses for many listings concurrently.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..dependencies import get_llm, get_repo
from ..llm import LLM
from ..repository import Repository
from ..schemas import ReviewInsight

router = APIRouter(prefix="/api/batch", tags=["batch"])

_VERDICT_SYSTEM = (
    "Compare these stays for a traveller. Give a one-paragraph verdict naming the "
    "best pick for value and the best for comfort, citing concrete differences."
)


class CompareRequest(BaseModel):
    ids: list[int] = Field(min_length=2, max_length=5)


class SummariesRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=20)


@router.post("/compare")
async def compare(body: CompareRequest, repo: Repository = Depends(get_repo),
                  llm: LLM = Depends(get_llm)):
    rows = await repo.compare(body.ids)
    if not rows:
        raise HTTPException(404, "no listings found")
    catalogue = "\n".join(
        f"- {r['id']}: {r['name']}, {r.get('price')}/night, rating {r.get('rating')}, "
        f"amenities {sorted(r.get('amenities') or [])[:8]}" for r in rows
    )
    verdict = await llm.chat(_VERDICT_SYSTEM, catalogue)
    return {"listings": rows, "verdict": verdict}


@router.post("/summaries")
async def summaries(body: SummariesRequest, repo: Repository = Depends(get_repo),
                    llm: LLM = Depends(get_llm)):
    """Produce review syntheses for many listings in parallel."""
    reviews = await repo.reviews_for_properties(body.ids, per_property=8)
    sem = asyncio.Semaphore(8)

    async def one(pid: int):
        items = reviews.get(pid, [])
        if not items:
            return pid, None
        prompt = "\n".join(f"[review {r['id']}] {r['text'][:300]}" for r in items)
        async with sem:
            insight = await llm.parse(
                ReviewInsight,
                "Summarize these reviews. Cite review ids. Use only what is given.",
                prompt,
            )
        return pid, insight.model_dump()

    results = await asyncio.gather(*(one(pid) for pid in body.ids))
    return {pid: insight for pid, insight in results}
