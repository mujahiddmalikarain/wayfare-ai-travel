"""Itinerary agent: multi-day, multi-property plans from the candidate set.

Integrity: the model may only reference candidate property_ids, but we don't
trust it — stays citing an unknown id are dropped and total_cost is recomputed
from the surviving stays. Results are cached on the candidate set + request,
mirroring the retrieval and review agents.
"""
from __future__ import annotations

from ..cache import cache_key
from ..schemas import ItineraryPlan
from .state import AgentState, Deps

_SYSTEM = (
    "You build a multi-day travel itinerary from the candidate stays provided. "
    "Respect the budget and any constraints. Assign each stay a day and a one-line "
    "reason, choose property_ids ONLY from the candidates, and compute total_cost "
    "from the nightly prices. Keep it realistic and within budget where possible."
)


def make_itinerary_agent(deps: Deps):
    async def itinerary_agent(state: AgentState) -> AgentState:
        candidates = state.get("candidates", [])[:8]
        if not candidates:
            return {"itinerary": {}, "answer": "No stays available to plan with.",
                    "trace": [{"agent": "itinerary", "summary": "no candidates"}]}

        intent = state.get("intent", {})
        valid_ids = {c["id"] for c in candidates}
        key = cache_key("itinerary", {
            "ids": sorted(valid_ids),
            "nights": intent.get("nights"),
            "budget": intent.get("max_price"),
            "message": state["message"],
        })
        cached = await deps.cache.get(key)
        if cached is None:
            catalogue = "\n".join(
                f"- {c['id']}: {c['name']} ({c['neighbourhood']}), "
                f"{c.get('price')}/night, rating {c.get('rating')}"
                for c in candidates
            )
            user = (
                f"Request: {state['message']}\n"
                f"Nights: {intent.get('nights')}  Budget: {intent.get('max_price')}\n"
                f"Candidates:\n{catalogue}"
            )
            plan = await deps.llm.parse(
                ItineraryPlan, _SYSTEM, user, model=deps.settings.synthesis_model
            )
            payload = plan.model_dump()
            # Drop hallucinated stays and recompute the total from what survives.
            payload["stays"] = [
                s for s in payload["stays"] if s["property_id"] in valid_ids
            ]
            payload["total_cost"] = round(
                sum(s.get("nightly_price") or 0 for s in payload["stays"]), 2
            )
            await deps.cache.set(key, payload)
            cached = payload

        stays = cached.get("stays", [])
        answer = f"{cached.get('title', 'Itinerary')} — {len(stays)} stays, " \
                 f"total {cached.get('total_cost', 0):.0f}."
        return {
            "itinerary": cached,
            "answer": answer,
            "trace": [{"agent": "itinerary", "summary": "built itinerary",
                       "data": {"stays": len(stays),
                                "total_cost": cached.get("total_cost", 0)}}],
        }

    return itinerary_agent
