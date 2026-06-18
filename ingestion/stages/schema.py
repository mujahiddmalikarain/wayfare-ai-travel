"""Ensure extensions, tables, and indexes exist before loading."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ..context import RunContext
from ..db import connect
from .base import Stage

log = logging.getLogger("stage.schema")

_SCHEMA_SQL = Path(__file__).resolve().parents[2] / "schema.sql"


class BootstrapSchemaStage(Stage):
    name = "schema"

    async def run(self, ctx: RunContext) -> None:
        await asyncio.to_thread(self._run_sync, ctx)

    def _run_sync(self, ctx: RunContext) -> None:
        sql = _SCHEMA_SQL.read_text(encoding="utf-8")
        with connect(ctx.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        log.info("schema ensured (extensions, tables, indexes)")
