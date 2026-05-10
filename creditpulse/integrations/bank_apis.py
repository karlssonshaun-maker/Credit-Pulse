from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from creditpulse.config import get_settings
from creditpulse.integrations.base import IntegrationOutcome, cached_call


def _seed_from(account_id: str) -> random.Random:
    seed = int(hashlib.sha256(f"bank:{account_id}".encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


INCOME_PAYERS = [
    "Kgotso Holdings (Pty) Ltd", "ABC Wholesalers", "Pick n Pay Store 142",
    "Standard Bank Card Settlement", "Yoco Settlement", "SnapScan Settlement",
    "Shoprite Checkers Supplier", "Woolworths SA", "Dischem Distribution",
    "Massmart Supplier Account", "Uber SA Driver Settlement",
]

EXPENSE_VENDORS = [
    "Makro Wholesale", "Builders Warehouse", "Eskom Municipal", "City of Joburg Rates",
    "Telkom Business", "Vodacom Business", "Shell Garage", "Engen Fuel", "Rent Payment",
    "Insurance Premium - Santam",
]


def _synthetic_transactions(account_id: str, months: int) -> Dict[str, Any]:
    rng = _seed_from(account_id)
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=30 * months)

    base_revenue = rng.choice([40000, 80000, 150000, 300000, 600000])
    payer_pool = rng.sample(INCOME_PAYERS, k=rng.randint(3, 8))
    vendor_pool = rng.sample(EXPENSE_VENDORS, k=rng.randint(3, 6))

    transactions: List[Dict[str, Any]] = []
    balance = rng.uniform(base_revenue * 0.1, base_revenue * 0.5)

    current_date = start
    while current_date < today:
        daily_income_draws = rng.randint(0, 3)
        for _ in range(daily_income_draws):
            amount = round(rng.uniform(base_revenue * 0.01, base_revenue * 0.15), 2)
            payer = rng.choice(payer_pool)
            balance += amount
            transactions.append({
                "date": current_date.isoformat(),
                "description": f"EFT CREDIT {payer} INV{rng.randint(1000, 9999)}",
                "amount": amount,
                "balance": round(balance, 2),
            })

        if rng.random() < 0.6:
            exp_amount = round(rng.uniform(base_revenue * 0.005, base_revenue * 0.08), 2)
            vendor = rng.choice(vendor_pool)
            balance -= exp_amount
            transactions.append({
                "date": current_date.isoformat(),
                "description": f"PAYMENT TO {vendor}",
                "amount": -exp_amount,
                "balance": round(balance, 2),
            })

        if current_date.day == 25 and rng.random() < 0.8:
            salary = round(base_revenue * rng.uniform(0.15, 0.3), 2)
            balance -= salary
            transactions.append({
                "date": current_date.isoformat(),
                "description": "STAFF SALARY PAYROLL",
                "amount": -salary,
                "balance": round(balance, 2),
            })

        current_date += timedelta(days=1)

    return {
        "account_id": account_id,
        "transactions": transactions,
        "account_summary": {
            "opening_balance": round(transactions[0]["balance"] - transactions[0]["amount"], 2) if transactions else 0,
            "closing_balance": round(balance, 2),
            "transaction_count": len(transactions),
            "period_start": start.isoformat(),
            "period_end": today.isoformat(),
        },
    }


async def get_transactions(account_id: str, months: int = 12) -> IntegrationOutcome:
    settings = get_settings()
    cache_key = f"bank_api:{account_id}:{months}"

    async def _fetch() -> Dict[str, Any]:
        await asyncio.sleep(random.uniform(0.2, 0.6))
        return _synthetic_transactions(account_id, months)

    return await cached_call(
        cache_key=cache_key,
        ttl_seconds=3600,
        fetcher=_fetch,
    )
