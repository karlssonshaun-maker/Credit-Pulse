from __future__ import annotations

import asyncio
import json
import signal
from typing import Any, Dict

from creditpulse.api.services.enrichment import enrich_all
from creditpulse.db.redis_client import get_redis
from creditpulse.logging_config import configure_logging, get_logger

QUEUE_NAME = "creditpulse:enrichment:queue"
RESULT_PREFIX = "creditpulse:enrichment:result:"

configure_logging()
logger = get_logger(__name__)

_shutdown = False


def _handle_signal(signum, frame) -> None:
    global _shutdown
    logger.info("worker_shutdown_signal", signum=signum)
    _shutdown = True


async def handle_job(payload: Dict[str, Any]) -> None:
    job_id = payload.get("job_id")
    registration_number = payload.get("registration_number")
    tax_number = payload.get("tax_number")

    logger.info("worker_job_received", job_id=job_id, registration_number=registration_number)
    bundle = await enrich_all(
        registration_number=registration_number,
        tax_number=tax_number,
        bank_account_id=registration_number,
        include_bank_api=payload.get("use_mock_bank_api", True),
    )

    result = {
        "job_id": job_id,
        "registration_number": registration_number,
        "available": bundle.available,
        "unavailable": bundle.unavailable,
        "cipc": bundle.cipc,
        "sars": bundle.sars,
        "bureau": bundle.bureau,
    }
    redis = get_redis()
    await redis.set(f"{RESULT_PREFIX}{job_id}", json.dumps(result, default=str), ex=3600)
    logger.info("worker_job_complete", job_id=job_id, available=bundle.available)


async def main() -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    redis = get_redis()
    logger.info("worker_started", queue=QUEUE_NAME)

    while not _shutdown:
        try:
            item = await redis.blpop(QUEUE_NAME, timeout=5)
        except Exception as exc:
            logger.error("worker_poll_failed", error=str(exc))
            await asyncio.sleep(2)
            continue

        if item is None:
            continue

        _, raw = item
        try:
            payload = json.loads(raw)
            await handle_job(payload)
        except Exception as exc:
            logger.error("worker_job_failed", error=str(exc), raw=raw)


if __name__ == "__main__":
    asyncio.run(main())
