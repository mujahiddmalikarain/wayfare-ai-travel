"""Application entrypoint:  uvicorn api.main:app --reload

Wires the connection pool, Redis cache, LLM client, and the compiled agent graph
into app state during the lifespan, mounts routers, and installs the
observability middleware that stamps every request with a trace.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .agents.graph import build_graph
from .agents.state import Deps
from .cache import Cache
from .config import get_settings
from .db import make_pool
from .llm import LLM
from .observability import current_trace, new_trace
from .repository import Repository
from .routers import batch, concierge, metrics, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = make_pool(settings)
    await pool.open()

    cache = Cache(settings)
    repo = Repository(pool)
    llm = LLM(settings)
    deps = Deps(repo=repo, llm=llm, cache=cache, settings=settings)

    app.state.settings = settings
    app.state.repo = repo
    app.state.cache = cache
    app.state.llm = llm
    app.state.graph = build_graph(deps)

    try:
        yield
    finally:
        await cache.close()
        await pool.close()


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace = new_trace()
        token = current_trace.set(trace)
        try:
            response = await call_next(request)
        finally:
            trace.finish()
            current_trace.reset(token)
        response.headers["X-Request-Id"] = trace.request_id
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="AI Travel Discovery API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(TraceMiddleware)
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
        allow_headers=["*"], expose_headers=["X-Request-Id"],
    )
    for module in (search, concierge, batch, metrics):
        app.include_router(module.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
