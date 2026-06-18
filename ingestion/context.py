"""Shared run context passed to every stage.

Carries config plus mutable run statistics (rows touched, tokens spent) so the
pipeline can print a single cost/throughput summary at the end — addressing the
brief's 'document any LLM costs' requirement.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings

# Public OpenAI list prices (USD per 1M tokens), kept in one place so the cost
# estimate is easy to audit and update.
_PRICE_PER_MTOK = {
    "text-embedding-3-small": 0.02,
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


@dataclass
class RunContext:
    settings: Settings
    force: bool = False
    rows: dict[str, int] = field(default_factory=dict)
    embedding_tokens: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0

    def add_rows(self, key: str, n: int) -> None:
        self.rows[key] = self.rows.get(key, 0) + n

    def estimated_cost_usd(self) -> float:
        emb = self._price("text-embedding-3-small") * self.embedding_tokens / 1_000_000
        chat = _PRICE_PER_MTOK["gpt-4o-mini"]
        llm = (
            chat["input"] * self.llm_input_tokens
            + chat["output"] * self.llm_output_tokens
        ) / 1_000_000
        return round(emb + llm, 4)

    @staticmethod
    def _price(model: str) -> float:
        value = _PRICE_PER_MTOK[model]
        return value if isinstance(value, (int, float)) else 0.0
