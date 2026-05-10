from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from creditpulse.config import get_settings
from creditpulse.db.redis_client import cache_get, cache_set
from creditpulse.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class IntegrationOutcome:
    success: bool
    data: Optional[dict]
    cache_hit: bool
    latency_ms: int
    error: Optional[str] = None


async def cached_call(
    cache_key: str,
    ttl_seconds: int,
    fetcher: Callable[[], Awaitable[dict]],
    timeout_seconds: Optional[float] = None,
) -> IntegrationOutcome:
    settings = get_settings()
    timeout = timeout_seconds or settings.enrichment_timeout_seconds
    started = time.perf_counter()

    try:
        cached = await cache_get(cache_key)
    except Exception as exc:
        logger.warning("cache_read_failed", key=cache_key, error=str(exc))
        cached = None

    if cached is not None:
        latency = int((time.perf_counter() - started) * 1000)
        return IntegrationOutcome(success=True, data=cached, cache_hit=True, latency_ms=latency)

    try:
        data = await asyncio.wait_for(fetcher(), timeout=timeout)
    except asyncio.TimeoutError:
        latency = int((time.perf_counter() - started) * 1000)
        return IntegrationOutcome(
            success=False, data=None, cache_hit=False, latency_ms=latency, error="timeout"
        )
    except Exception as exc:
        latency = int((time.perf_counter() - started) * 1000)
        logger.error("integration_fetch_failed", key=cache_key, error=str(exc))
        return IntegrationOutcome(
            success=False, data=None, cache_hit=False, latency_ms=latency, error=str(exc)
        )

    try:
        await cache_set(cache_key, data, ttl_seconds)
    except Exception as exc:
        logger.warning("cache_write_failed", key=cache_key, error=str(exc))

    latency = int((time.perf_counter() - started) * 1000)
    return IntegrationOutcome(success=True, data=data, cache_hit=False, latency_ms=latency)
