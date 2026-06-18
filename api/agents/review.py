"""Review intelligence agent: synthesizes insights with citations to real reviews.

Hallucination control: the model is given an explicit id→text map and instructed
to cite only those ids; we additionally drop any hallucinated id post-hoc.
"""
from __future__ import annotations

from ..cache import cache_key
from ..schemas import ReviewInsight
from .state import AgentState, Deps

_SYSTEM = (
    "You analyze guest reviews across candidate stays. Produce a concise summary "
    "and 3-5 highlights. Every highlight must cite the review ids it is based on. "
    "Use ONLY the provided reviews and ids — never invent ids or claims."
)


def make_review_agent(deps: Deps):
    async def review_agent(state: AgentState) -> AgentState:
        candidates = state.get("candidates", [])[:5]
        if not candidates:
            return {"review_insights": {}, "answer": "No matching stays found.",
                    "trace": [{"agent": "review", "summary": "no candidates"}]}

        ids = [c["id"] for c in candidates]
        key = cache_key("review_synthesis", ids)
        cached = await deps.cache.get(key)
        if cached is None:
            reviews = await deps.repo.reviews_for_properties(ids)
            review_to_property = {
                r["id"]: pid for pid, rs in reviews.items() for r in rs
            }
            valid_ids = set(review_to_property)
            user = _build_prompt(candidates, reviews)
            insight = await deps.llm.parse(
                ReviewInsight, _SYSTEM, user, model=deps.settings.synthesis_model
            )
            payload = insight.model_dump()
            cited: set[int] = set()
            for h in payload["highlights"]:
                h["review_ids"] = [i for i in h["review_ids"] if i in valid_ids]
                cited.update(h["review_ids"])
            # review_id -> property_id, so the UI can deep-link each citation.
            payload["citations"] = {str(i): review_to_property[i] for i in cited}
            await deps.cache.set(key, payload)
            cached = payload

        return {
            "review_insights": cached,
            "answer": cached["summary"],
            "trace": [{"agent": "review", "summary": "synthesized review insights",
                       "data": {"highlights": len(cached["highlights"])}}],
        }

    return review_agent


def _build_prompt(candidates: list[dict], reviews: dict[int, list[dict]]) -> str:
    blocks = []
    for c in candidates:
        lines = [f"Property {c['id']} — {c['name']}"]
        for r in reviews.get(c["id"], []):
            lines.append(f"  [review {r['id']}] {r['text'][:300]}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
