from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from creditpulse.config import get_settings

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    client = get_redis()
    raw = await client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


async def cache_set(key: str, value: Any, ttl: int) -> None:
    client = get_redis()
    payload = json.dumps(value, default=str)
    await client.set(key, payload, ex=ttl)


async def cache_delete(key: str) -> None:
    client = get_redis()
    await client.delete(key)
