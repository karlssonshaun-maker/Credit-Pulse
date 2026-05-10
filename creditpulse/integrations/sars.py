from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Any, Dict, Optional

from creditpulse.config import get_settings
from creditpulse.integrations.base import IntegrationOutcome, cached_call


def _seed_from(tax: str) -> random.Random:
    seed = int(hashlib.sha256(f"sars:{tax}".encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _synthetic_sars(tax_number: str) -> Dict[str, Any]:
    rng = _seed_from(tax_number)
    compliant = rng.random() < 0.75
    outstanding = 0 if compliant else rng.randint(1, 4)
    vat_status = rng.choice(["active", "registered", "not_registered", "not_registered", "active"])

    bands = ["under_1m", "1m_5m", "5m_20m", "20m_50m", "over_50m"]
    turnover_band = rng.choices(bands, weights=[4, 4, 2, 1, 0.5], k=1)[0]

    return {
        "tax_number": tax_number,
        "compliance_status": "compliant" if compliant else "non_compliant",
        "last_return_filed": "2026-02-28" if compliant else "2025-10-31",
        "outstanding_returns": outstanding,
        "estimated_annual_turnover_band": turnover_band,
        "vat_status": vat_status,
        "paye_status": "active" if rng.random() < 0.6 else "not_registered",
    }


async def check_compliance(tax_number: Optional[str]) -> IntegrationOutcome:
    if not tax_number:
        return IntegrationOutcome(success=False, data=None, cache_hit=False, latency_ms=0, error="missing_tax_number")

    settings = get_settings()
    cache_key = f"sars:compliance:{tax_number}"

    async def _fetch() -> Dict[str, Any]:
        await asyncio.sleep(random.uniform(0.05, 0.3))
        return _synthetic_sars(tax_number)

    return await cached_call(
        cache_key=cache_key,
        ttl_seconds=settings.sars_cache_ttl_seconds,
        fetcher=_fetch,
    )


def normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "compliance_status": raw.get("compliance_status"),
        "outstanding_returns": raw.get("outstanding_returns"),
        "vat_status": raw.get("vat_status"),
        "estimated_annual_turnover_band": raw.get("estimated_annual_turnover_band"),
    }
