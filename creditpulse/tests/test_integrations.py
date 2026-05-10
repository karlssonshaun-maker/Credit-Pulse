import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from creditpulse.integrations import cipc, sars, transunion
from creditpulse.integrations.base import cached_call


@pytest.mark.asyncio
async def test_cipc_returns_deterministic_data(fake_redis):
    r1 = await cipc.lookup_business("2015/001234/07")
    r2 = await cipc.lookup_business("2015/001234/07")
    assert r1.success
    assert r2.success
    assert r1.data["registration_number"] == r2.data["registration_number"]


@pytest.mark.asyncio
async def test_sars_returns_outcome_for_missing_tax_number(fake_redis):
    outcome = await sars.check_compliance(None)
    assert outcome.success is False
    assert outcome.error == "missing_tax_number"


@pytest.mark.asyncio
async def test_sars_returns_synthetic_for_valid_tax(fake_redis):
    outcome = await sars.check_compliance("9012345678")
    assert outcome.success
    assert outcome.data["compliance_status"] in ("compliant", "non_compliant")


@pytest.mark.asyncio
async def test_transunion_score_in_range(fake_redis):
    outcome = await transunion.get_business_score("2015/001234/07")
    assert outcome.success
    assert 200 <= outcome.data["commercial_score"] <= 950


@pytest.mark.asyncio
async def test_cached_call_timeout_returns_unsuccessful(fake_redis):
    async def slow_fetcher():
        await asyncio.sleep(2)
        return {"ok": True}

    outcome = await cached_call(
        cache_key="test:timeout:1",
        ttl_seconds=60,
        fetcher=slow_fetcher,
        timeout_seconds=0.1,
    )
    assert outcome.success is False
    assert outcome.error == "timeout"


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_data(fake_redis):
    fake_redis["test:hit:1"] = '{"cached": true}'

    async def fetcher():
        return {"cached": False}

    outcome = await cached_call("test:hit:1", 60, fetcher)
    assert outcome.cache_hit is True
    assert outcome.data == {"cached": True}
