"""Pipeline orchestrator.

Holds the ordered list of stages and runs a selected subset, timing each and
printing a single throughput + cost summary at the end.
"""
from __future__ import annotations

import logging
import time

from .context import RunContext
from .stages.base import Stage
from .stages.embeddings import EmbeddingStage
from .stages.load_calendar import LoadCalendarStage
from .stages.load_listings import LoadListingsStage
from .stages.load_reviews import LoadReviewsStage
from .stages.percentile import NeighbourhoodPercentileStage
from .stages.review_summary import ReviewSummaryStage
from .stages.schema import BootstrapSchemaStage

log = logging.getLogger("pipeline")


def build_pipeline() -> "Pipeline":
    """Default ordered pipeline. Loads must precede their enrichments."""
    return Pipeline(
        [
            BootstrapSchemaStage(),
            LoadListingsStage(),
            LoadCalendarStage(),
            LoadReviewsStage(),
            NeighbourhoodPercentileStage(),
            EmbeddingStage(),
            ReviewSummaryStage(),
        ]
    )


class Pipeline:
    def __init__(self, stages: list[Stage]) -> None:
        self._stages = stages

    @property
    def stage_names(self) -> list[str]:
        return [s.name for s in self._stages]

    def select(
        self,
        *,
        only: set[str] | None = None,
        skip: set[str] | None = None,
        start_from: str | None = None,
    ) -> list[Stage]:
        stages = self._stages
        if start_from:
            idx = self.stage_names.index(start_from)
            stages = stages[idx:]
        if only:
            stages = [s for s in stages if s.name in only]
        if skip:
            stages = [s for s in stages if s.name not in skip]
        return stages

    async def run(self, ctx: RunContext, stages: list[Stage]) -> None:
        log.info("running stages: %s", ", ".join(s.name for s in stages))
        started = time.perf_counter()
        for stage in stages:
            t0 = time.perf_counter()
            log.info("▶ %s", stage.name)
            await stage.run(ctx)
            log.info("✓ %s (%.1fs)", stage.name, time.perf_counter() - t0)
        self._summary(ctx, time.perf_counter() - started)

    @staticmethod
    def _summary(ctx: RunContext, elapsed: float) -> None:
        log.info("─" * 60)
        for key, n in ctx.rows.items():
            log.info("  %-16s %d", key, n)
        log.info("  embedding_tokens %d", ctx.embedding_tokens)
        log.info("  llm_tokens       %d in / %d out",
                 ctx.llm_input_tokens, ctx.llm_output_tokens)
        log.info("  est. cost        $%.4f", ctx.estimated_cost_usd())
        log.info("  total time       %.1fs", elapsed)
        log.info("─" * 60)
