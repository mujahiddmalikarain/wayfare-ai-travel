"""Stage contract.

Every stage exposes an async `run`, so the orchestrator has a uniform interface
whether the work is blocking IO (COPY loads, run via asyncio.to_thread) or
genuinely async (OpenAI calls).
"""
from __future__ import annotations

import abc

from ..context import RunContext


class Stage(abc.ABC):
    #: Stable identifier used for CLI selection (--only / --from / --skip).
    name: str

    @abc.abstractmethod
    async def run(self, ctx: RunContext) -> None:  # pragma: no cover - interface
        ...
