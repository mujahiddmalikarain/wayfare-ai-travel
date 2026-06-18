"""FastAPI dependencies that expose app-scoped singletons to routers."""
from __future__ import annotations

from fastapi import Request

from .cache import Cache
from .config import Settings
from .llm import LLM
from .repository import Repository


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_llm(request: Request) -> LLM:
    return request.app.state.llm


def get_graph(request: Request):
    return request.app.state.graph
