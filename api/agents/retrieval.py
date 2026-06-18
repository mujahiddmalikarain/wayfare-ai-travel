"""Retrieval agent: semantic + filtered + geo search, with a rationale per hit.

Caches candidate sets keyed by the parsed intent, since travel queries repeat.
"""
from __future__ import annotations

from ..cache import cache_key
from ..schemas import TravelQuery
from .state import AgentState, Deps


def _rationale(intent: TravelQuery, row: dict) -> str:
    bits = [f"similarity {row['similarity']:.2f}"]
    matched = sorted(set(intent.amenities) & set(row.get("amenities") or []))
    if matched:
        bits.append("has " + ", ".join(matched))
    if row.get("neighbourhood_price_pct") is not None:
        pct = round(row["neighbourhood_price_pct"] * 100)
        bits.append(f"{pct}th price percentile for {row['neighbourhood']}")
    return "; ".join(bits)


def make_retrieval_agent(deps: Deps):
    async def retrieval_agent(state: AgentState) -> AgentState:
        intent = TravelQuery(**state["intent"])
        if not intent.city:
            return {"candidates": [],
                    "trace": [{"agent": "retrieval", "summary": "no city resolved"}]}

        key = cache_key("retrieval", intent.model_dump())
        cached = await deps.cache.get(key)
        if cached is not None:
            return {"candidates": cached,
                    "trace": [{"agent": "retrieval", "summary": "cache hit",
                               "data": {"count": len(cached)}}]}

        query_text = " ".join(
            filter(None, [state["message"], *intent.soft_preferences])
        )
        qvec = deps.llm.vector_literal(await deps.llm.embed(query_text))
        rows = await deps.repo.hybrid_retrieve(
            intent, qvec, deps.settings.retrieval_limit
        )
        for r in rows:
            r["rationale"] = _rationale(intent, r)
        await deps.cache.set(key, rows)
        return {
            "candidates": rows,
            "trace": [{"agent": "retrieval", "summary": "ranked candidates",
                       "data": {"count": len(rows),
                                "top": [r["name"] for r in rows[:3]]}}],
        }

    return retrieval_agent
