"""Graph wiring + a streaming runner that turns node updates into SSE events.

Flow:  intent → retrieval → (review | itinerary)

Routing is intent-driven: multi-stop trips go to the itinerary agent, everything
else to review intelligence. The runner streams each agent's step as it
completes (LangGraph 'updates' mode), then a final result event.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from langgraph.graph import END, START, StateGraph

from ..observability import RequestTrace
from .intent import make_intent_agent
from .itinerary import make_itinerary_agent
from .retrieval import make_retrieval_agent
from .review import make_review_agent
from .state import AgentState, Deps


def _route(state: AgentState) -> str:
    return "itinerary" if state.get("intent", {}).get("multi_stop") else "review"


def build_graph(deps: Deps):
    g = StateGraph(AgentState)
    g.add_node("intent", make_intent_agent(deps))
    g.add_node("retrieval", make_retrieval_agent(deps))
    g.add_node("review", make_review_agent(deps))
    g.add_node("itinerary", make_itinerary_agent(deps))

    g.add_edge(START, "intent")
    g.add_edge("intent", "retrieval")
    g.add_conditional_edges("retrieval", _route,
                            {"review": "review", "itinerary": "itinerary"})
    g.add_edge("review", END)
    g.add_edge("itinerary", END)
    return g.compile()


def _slim(candidates: list[dict]) -> list[dict]:
    keep = ("id", "name", "neighbourhood", "price", "rating", "photo_url",
            "amenities", "similarity", "rationale")
    return [{k: c.get(k) for k in keep} for c in (candidates or [])[:12]]


async def run_stream(graph, message: str,
                     trace: RequestTrace) -> AsyncIterator[dict[str, Any]]:
    final: AgentState = {}
    try:
        async for update in graph.astream({"message": message},
                                          stream_mode="updates"):
            for node, delta in update.items():
                final.update(delta)  # type: ignore[arg-type]
                for step in delta.get("trace", []):
                    trace.add_step(node, step)
                    yield {"type": "step", "node": node, **step}
    except Exception as exc:  # noqa: BLE001 — surface failure to the client, don't drop the stream
        logging.getLogger("concierge").exception("agent run failed")
        yield {
            "type": "error",
            "request_id": trace.request_id,
            "message": "The concierge hit an error. Please try rephrasing.",
            "detail": str(exc),
        }
        return

    yield {
        "type": "result",
        "request_id": trace.request_id,
        "answer": final.get("answer", ""),
        "candidates": _slim(final.get("candidates", [])),
        "review_insights": final.get("review_insights"),
        "itinerary": final.get("itinerary"),
    }
