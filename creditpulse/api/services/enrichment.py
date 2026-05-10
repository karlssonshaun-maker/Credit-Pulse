from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from creditpulse.integrations import bank_apis, cipc, sars, transunion
from creditpulse.integrations.base import IntegrationOutcome
from creditpulse.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EnrichmentBundle:
    cipc: Optional[Dict[str, Any]]
    sars: Optional[Dict[str, Any]]
    bureau: Optional[Dict[str, Any]]
    bank_api: Optional[Dict[str, Any]]
    outcomes: Dict[str, IntegrationOutcome]
    available: List[str]
    unavailable: List[str]


async def enrich_all(
    registration_number: str,
    tax_number: Optional[str],
    bank_account_id: Optional[str] = None,
    include_bank_api: bool = False,
) -> EnrichmentBundle:
    tasks = {
        "cipc": asyncio.create_task(cipc.lookup_business(registration_number)),
        "sars": asyncio.create_task(sars.check_compliance(tax_number)),
        "transunion": asyncio.create_task(transunion.get_business_score(registration_number)),
    }
    if include_bank_api and bank_account_id:
        tasks["bank_api"] = asyncio.create_task(bank_apis.get_transactions(bank_account_id, 12))

    await asyncio.gather(*tasks.values(), return_exceptions=True)

    outcomes: Dict[str, IntegrationOutcome] = {}
    for source, task in tasks.items():
        try:
            outcomes[source] = task.result()
        except Exception as exc:
            logger.warning("enrichment_task_failed", source=source, error=str(exc))
            outcomes[source] = IntegrationOutcome(
                success=False, data=None, cache_hit=False, latency_ms=0, error=str(exc)
            )

    available = [s for s, o in outcomes.items() if o.success]
    unavailable = [s for s, o in outcomes.items() if not o.success]

    return EnrichmentBundle(
        cipc=outcomes["cipc"].data if outcomes.get("cipc") and outcomes["cipc"].success else None,
        sars=outcomes["sars"].data if outcomes.get("sars") and outcomes["sars"].success else None,
        bureau=outcomes["transunion"].data if outcomes.get("transunion") and outcomes["transunion"].success else None,
        bank_api=outcomes.get("bank_api").data if outcomes.get("bank_api") and outcomes["bank_api"].success else None,
        outcomes=outcomes,
        available=available,
        unavailable=unavailable,
    )
