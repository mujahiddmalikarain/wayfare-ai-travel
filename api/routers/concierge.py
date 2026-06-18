"""AI endpoints: natural-language search (chips + results) and the streaming
multi-agent concierge.
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..agents.graph import run_stream
from ..dependencies import get_graph, get_llm, get_repo
from ..llm import LLM
from ..observability import current_trace
from ..repository import Repository
from ..schemas import ConciergeRequest, SearchFilters, TravelQuery

router = APIRouter(prefix="/api", tags=["ai"])

_INTENT_SYSTEM = (
    "Convert the search box text into a structured query. Dates as ISO "
    "yyyy-mm-dd. Amenities as lowercase tokens. Leave unknown fields null."
)


def _as_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


@router.post("/nl-search")
async def nl_search(
    body: ConciergeRequest,
    repo: Repository = Depends(get_repo),
    llm: LLM = Depends(get_llm),
):
    """Parse free text into filters, return the chips AND the matching results."""
    intent = await llm.parse(TravelQuery, _INTENT_SYSTEM, body.message)
    city = intent.city or body.city
    if not city:
        raise HTTPException(422, "could not determine a city from the query")

    # The LLM emits free text; map room_type/amenities to values that actually
    # exist so a noisy token doesn't zero out the result set.
    room_type, amenities = await repo.normalize_intent_filters(
        intent.room_type, intent.amenities
    )
    filters = SearchFilters(
        city=city,
        checkin=_as_date(intent.checkin),
        checkout=_as_date(intent.checkout),
        guests=intent.guests,
        min_price=intent.min_price,
        max_price=intent.max_price,
        room_type=room_type,
        amenities=amenities,
    )
    results = await repo.search(filters)
    return {"intent": intent.model_dump(exclude_none=True),
            "applied_filters": filters.model_dump(exclude_none=True),
            **results}


@router.post("/concierge/stream")
async def concierge_stream(
    body: ConciergeRequest,
    graph=Depends(get_graph),
):
    """Server-Sent Events stream of agent steps, then a final result event."""
    trace = current_trace.get()

    async def event_source():
        async for event in run_stream(graph, body.message, trace):
            yield f"data: {json.dumps(event, default=str)}\n\n"
        yield "data: [DONE]\n\n"
        # The trace middleware finishes when the response object is returned —
        # i.e. before the body streams — so for SSE it records only time-to-headers.
        # Re-finish here, after the full stream, to capture true end-to-end latency.
        if trace:
            trace.finish()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"X-Request-Id": trace.request_id if trace else "",
                 "Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
