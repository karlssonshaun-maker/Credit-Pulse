from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Any, Dict, List

from creditpulse.config import get_settings
from creditpulse.integrations.base import IntegrationOutcome, cached_call


def _seed_from(reg: str) -> random.Random:
    seed = int(hashlib.sha256(f"tu:{reg}".encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _synthetic_bureau(registration_number: str) -> Dict[str, Any]:
    rng = _seed_from(registration_number)
    score = int(rng.gauss(580, 140))
    score = max(200, min(950, score))

    behaviour = (
        "excellent" if score >= 750
        else "good" if score >= 620
        else "average" if score >= 480
        else "sub_prime"
    )

    adverse_roll = rng.random()
    adverse_listings: List[Dict[str, Any]] = []
    if adverse_roll > 0.7:
        for _ in range(rng.randint(1, 4)):
            adverse_listings.append({
                "type": rng.choice(["judgement", "default", "administration_order"]),
                "amount": round(rng.uniform(5000, 200000), 2),
                "date": f"2024-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                "creditor": rng.choice(["ABC Finance", "Quick Loans SA", "Supplier Co", "Retail Credit"]),
            })

    facilities = rng.randint(0, 8)
    total_exposure = round(rng.uniform(0, 2_500_000), 2) if facilities else 0.0

    return {
        "registration_number": registration_number,
        "commercial_score": score,
        "payment_behaviour": behaviour,
        "adverse_listings": adverse_listings,
        "active_credit_facilities": facilities,
        "total_exposure": total_exposure,
        "report_date": "2026-04-21",
    }


async def get_business_score(registration_number: str) -> IntegrationOutcome:
    settings = get_settings()
    cache_key = f"transunion:business:{registration_number}"

    async def _fetch() -> Dict[str, Any]:
        await asyncio.sleep(random.uniform(0.1, 0.4))
        return _synthetic_bureau(registration_number)

    return await cached_call(
        cache_key=cache_key,
        ttl_seconds=settings.bureau_cache_ttl_seconds,
        fetcher=_fetch,
    )


def normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "commercial_score": raw.get("commercial_score"),
        "payment_behaviour": raw.get("payment_behaviour"),
        "adverse_listings": raw.get("adverse_listings", []),
        "active_credit_facilities": raw.get("active_credit_facilities"),
        "total_exposure": raw.get("total_exposure"),
    }
