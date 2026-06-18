"""Async OpenAI wrapper.

Centralizes embeddings, structured intent parsing, and chat synthesis, and
attributes token usage to the active request trace for observability.
"""
from __future__ import annotations

from typing import Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings
from .observability import current_trace

T = TypeVar("T", bound=BaseModel)


class LLM:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._settings = settings

    @retry(stop=stop_after_attempt(4),
           wait=wait_exponential(multiplier=1, min=1, max=15), reraise=True)
    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(
            model=self._settings.embedding_model, input=text
        )
        if (t := current_trace.get()) is not None:
            t.add_tokens(emb=resp.usage.total_tokens)
        return resp.data[0].embedding

    @retry(stop=stop_after_attempt(4),
           wait=wait_exponential(multiplier=1, min=1, max=15), reraise=True)
    async def parse(self, schema: Type[T], system: str, user: str,
                    model: str | None = None) -> T:
        completion = await self._client.beta.chat.completions.parse(
            model=model or self._settings.intent_model,
            temperature=0,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format=schema,
        )
        self._account(completion)
        return completion.choices[0].message.parsed

    @retry(stop=stop_after_attempt(4),
           wait=wait_exponential(multiplier=1, min=1, max=15), reraise=True)
    async def chat(self, system: str, user: str, model: str | None = None) -> str:
        completion = await self._client.chat.completions.create(
            model=model or self._settings.synthesis_model,
            temperature=0.3,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        self._account(completion)
        return completion.choices[0].message.content or ""

    @staticmethod
    def _account(completion) -> None:
        if (t := current_trace.get()) is not None and completion.usage:
            t.add_tokens(
                inp=completion.usage.prompt_tokens,
                out=completion.usage.completion_tokens,
            )

    @staticmethod
    def vector_literal(values: list[float]) -> str:
        return "[" + ",".join(f"{v:.6f}" for v in values) + "]"
