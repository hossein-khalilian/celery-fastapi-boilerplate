"""Async Redis client for webhook inbox state and pub/sub (multi-replica API)."""

from __future__ import annotations

import os

import redis.asyncio as aioredis
from redis.asyncio import Redis

_redis: Redis | None = None


def webhook_redis_url() -> str:
    return os.environ.get("WEBHOOK_REDIS_URL", "redis://redis:6379/2")


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            webhook_redis_url(),
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
