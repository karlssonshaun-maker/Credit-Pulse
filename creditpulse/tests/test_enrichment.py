from unittest.mock import AsyncMock, patch

import pytest

from creditpulse.api.services import enrichment as enrichment_mod
from creditpulse.integrations.base import IntegrationOutcome


@pytest.mark.asyncio
async def test_enrich_all_handles_cipc_timeout(fake_redis):
    async def good():
        return IntegrationOutcome(success=True, data={"registration_status": "active"}, cache_hit=False, latency_ms=10)

    async def bad():
        return IntegrationOutcome(success=False, data=None, cache_hit=False, latency_ms=5000, error="timeout")

    with patch("creditpulse.api.services.enrichment.cipc.lookup_business", new=AsyncMock(side_effect=lambda x: bad())), \
         patch("creditpulse.api.services.enrichment.sars.check_compliance", new=AsyncMock(side_effect=lambda x: good())), \
         patch("creditpulse.api.services.enrichment.transunion.get_business_score", new=AsyncMock(side_effect=lambda x: good())):
        bundle = await enrichment_mod.enrich_all(
            registration_number="2015/001234/07",
            tax_number="9012345678",
            include_bank_api=False,
        )
        assert "cipc" in bundle.unavailable
        assert "sars" in bundle.available
        assert "transunion" in bundle.available


@pytest.mark.asyncio
async def test_enrich_all_all_sources_succeed(fake_redis):
    async def ok(_):
        return IntegrationOutcome(success=True, data={"commercial_score": 700}, cache_hit=True, latency_ms=2)

    with patch("creditpulse.api.services.enrichment.cipc.lookup_business", new=AsyncMock(side_effect=ok)), \
         patch("creditpulse.api.services.enrichment.sars.check_compliance", new=AsyncMock(side_effect=ok)), \
         patch("creditpulse.api.services.enrichment.transunion.get_business_score", new=AsyncMock(side_effect=ok)):
        bundle = await enrichment_mod.enrich_all(
            registration_number="2015/001234/07",
            tax_number="9012345678",
        )
        assert set(bundle.available) == {"cipc", "sars", "transunion"}
        assert bundle.unavailable == []
