"""CLI entrypoint:  python -m ingestion [options]

Examples:
    python -m ingestion                       # full pipeline
    python -m ingestion --only embeddings     # re-embed only
    python -m ingestion --from percentile     # resume from a stage
    python -m ingestion --only review_summary --force   # rebuild summaries
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from .config import Settings
from .context import RunContext
from .logging_setup import configure_logging
from .pipeline import build_pipeline


def _parse_args(stage_names: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="ingestion", description=__doc__)
    p.add_argument("--only", nargs="*", choices=stage_names, metavar="STAGE",
                   help="run only these stages")
    p.add_argument("--skip", nargs="*", choices=stage_names, metavar="STAGE",
                   help="skip these stages")
    p.add_argument("--from", dest="start_from", choices=stage_names, metavar="STAGE",
                   help="start from this stage")
    p.add_argument("--force", action="store_true",
                   help="recompute enrichments even if already present")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


async def _main() -> None:
    pipeline = build_pipeline()
    args = _parse_args(pipeline.stage_names)
    configure_logging(logging.DEBUG if args.verbose else logging.INFO)

    settings = Settings()  # type: ignore[call-arg]  # values come from env/.env
    if not settings.cities:
        raise SystemExit("No CITIES configured. Set CITIES in your .env.")

    ctx = RunContext(settings=settings, force=args.force)
    stages = pipeline.select(
        only=set(args.only) if args.only else None,
        skip=set(args.skip) if args.skip else None,
        start_from=args.start_from,
    )
    await pipeline.run(ctx, stages)


if __name__ == "__main__":
    asyncio.run(_main())
