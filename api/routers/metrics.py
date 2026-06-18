"""Observability endpoint: per-request token usage, latency, and agent steps."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..observability import get_trace

router = APIRouter(prefix="/api", tags=["observability"])


@router.get("/metrics/{request_id}")
async def metrics(request_id: str):
    trace = get_trace(request_id)
    if trace is None:
        raise HTTPException(404, "unknown request id")
    return trace.as_dict()
