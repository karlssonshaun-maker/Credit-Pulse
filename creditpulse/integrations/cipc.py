from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from creditpulse.config import get_settings
from creditpulse.integrations.base import IntegrationOutcome, cached_call


def _seed_from(reg: str) -> random.Random:
    seed = int(hashlib.sha256(reg.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _synthetic_cipc(registration_number: str) -> Dict[str, Any]:
    rng = _seed_from(registration_number)
    years_ago = rng.randint(1, 18)
    reg_date = datetime.now(timezone.utc) - timedelta(days=365 * years_ago + rng.randint(0, 365))

    status_roll = rng.random()
    if status_roll < 0.85:
        status = "active"
    elif status_roll < 0.93:
        status = "in_business"
    elif status_roll < 0.98:
        status = "deregistered"
    else:
        status = "in_liquidation"

    company_types = ["Pty Ltd", "CC", "Inc", "Pty Ltd"]
    directors_count = rng.randint(1, 4)
    directors: List[Dict[str, Any]] = []
    for i in range(directors_count):
        directors.append({
            "id_number": f"{rng.randint(60, 99)}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}{rng.randint(1000000, 9999999)}",
            "full_name": f"Director {i + 1}",
            "appointed_at": (reg_date + timedelta(days=rng.randint(0, 365))).date().isoformat(),
            "adverse_flag": rng.random() < 0.05,
        })

    return {
        "registration_number": registration_number,
        "registration_status": status,
        "registration_date": reg_date.isoformat(),
        "company_type": rng.choice(company_types),
        "directors": directors,
        "registered_address": f"{rng.randint(1, 999)} Example Street, Sandton, Gauteng, 2196",
        "annual_return_status": "up_to_date" if rng.random() < 0.8 else "outstanding",
        "sic_code": rng.choice(["4711", "4321", "5612", "4921", "6201", "4530", "4771"]),
    }


async def lookup_business(registration_number: str) -> IntegrationOutcome:
    settings = get_settings()
    cache_key = f"cipc:business:{registration_number}"

    async def _fetch() -> Dict[str, Any]:
        await asyncio.sleep(random.uniform(0.05, 0.25))
        return _synthetic_cipc(registration_number)

    return await cached_call(
        cache_key=cache_key,
        ttl_seconds=settings.cipc_cache_ttl_seconds,
        fetcher=_fetch,
    )


def normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "registration_status": raw.get("registration_status"),
        "registration_date": raw.get("registration_date"),
        "directors": raw.get("directors", []),
        "company_type": raw.get("company_type"),
        "annual_return_status": raw.get("annual_return_status"),
        "sic_code": raw.get("sic_code"),
    }
