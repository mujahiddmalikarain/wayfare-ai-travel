"""Intent agent: natural language -> structured TravelQuery."""
from __future__ import annotations

from ..schemas import TravelQuery
from .state import AgentState, Deps

_SYSTEM = (
    "You convert a traveller's request into a structured search query. Extract "
    "city, dates (ISO yyyy-mm-dd), nights, guests, price bounds, room_type, "
    "amenities (lowercase tokens like 'wifi','balcony','pool'), neighbourhoods to "
    "exclude, soft_preferences (vibe words like 'quiet','near restaurants'), and "
    "hard_constraints. Set multi_stop=true when the trip spans multiple "
    "properties or splits nights across stays. Leave unknown fields null."
)


def make_intent_agent(deps: Deps):
    async def intent_agent(state: AgentState) -> AgentState:
        intent = await deps.llm.parse(TravelQuery, _SYSTEM, state["message"])
        return {
            "intent": intent.model_dump(),
            "trace": [{"agent": "intent", "summary": "parsed query",
                       "data": intent.model_dump(exclude_none=True)}],
        }

    return intent_agent
