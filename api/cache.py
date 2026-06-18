"""Thin JSON cache over Redis.

Travel queries cluster heavily, so caching retrievals and review syntheses is
high-leverage. Keys are deterministic hashes of the semantically relevant inputs.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

from .config import Settings

log = logging.getLogger("cache")


def cache_key(prefix: str, payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha1(blob.encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


class Cache:
    def __init__(self, settings: Settings) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        self._ttl = settings.cache_ttl_seconds

    async def get(self, key: str) -> Any | None:
        # Best-effort: a Redis outage must degrade to a cache miss, never 500.
        try:
            raw = await self._redis.get(key)
        except redis.RedisError:
            log.warning("cache get failed (key=%s) — degrading to miss", key)
            return None
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            await self._redis.set(
                key, json.dumps(value, default=str), ex=ttl or self._ttl
            )
        except redis.RedisError:
            log.warning("cache set failed (key=%s) — skipping", key)

    async def close(self) -> None:
        try:
            await self._redis.aclose()
        except redis.RedisError:
            pass
