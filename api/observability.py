"""Per-request observability: token usage, latency, and agent step traces.

A `RequestTrace` is created per HTTP request and stored in a bounded in-memory
registry, exposed via GET /api/metrics/{request_id}. The active trace is held in
a contextvar so the LLM client can attribute token usage without threading the
request object through every call.
"""
from __future__ import annotations

import time
import uuid
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

_MAX_TRACES = 1000
_REGISTRY: "OrderedDict[str, RequestTrace]" = OrderedDict()

current_trace: ContextVar["RequestTrace | None"] = ContextVar(
    "current_trace", default=None
)


@dataclass
class RequestTrace:
    request_id: str
    started: float = field(default_factory=time.perf_counter)
    input_tokens: int = 0
    output_tokens: int = 0
    embedding_tokens: int = 0
    latency_ms: float | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)

    def add_tokens(self, *, inp: int = 0, out: int = 0, emb: int = 0) -> None:
        self.input_tokens += inp
        self.output_tokens += out
        self.embedding_tokens += emb

    def add_step(self, name: str, data: dict[str, Any] | None = None) -> None:
        self.steps.append(
            {"step": name, "at_ms": round((time.perf_counter() - self.started) * 1000),
             "data": data or {}}
        )

    def finish(self) -> None:
        self.latency_ms = round((time.perf_counter() - self.started) * 1000, 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "latency_ms": self.latency_ms,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "embedding": self.embedding_tokens,
            },
            "steps": self.steps,
        }


def new_trace() -> RequestTrace:
    trace = RequestTrace(request_id=uuid.uuid4().hex[:12])
    _REGISTRY[trace.request_id] = trace
    while len(_REGISTRY) > _MAX_TRACES:
        _REGISTRY.popitem(last=False)
    return trace


def get_trace(request_id: str) -> RequestTrace | None:
    return _REGISTRY.get(request_id)
