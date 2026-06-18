"""Shared graph state and the dependency bundle injected into each agent.

`trace` uses an additive reducer so every node appends its own step rather than
overwriting — this is what the SSE stream and the metrics endpoint surface.
"""
from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from ..cache import Cache
from ..config import Settings
from ..llm import LLM
from ..repository import Repository


@dataclass
class Deps:
    repo: Repository
    llm: LLM
    cache: Cache
    settings: Settings


class AgentState(TypedDict, total=False):
    message: str
    intent: dict[str, Any]
    candidates: list[dict[str, Any]]
    review_insights: dict[str, Any]
    itinerary: dict[str, Any]
    answer: str
    trace: Annotated[list[dict[str, Any]], operator.add]
