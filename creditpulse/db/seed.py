from __future__ import annotations

import asyncio
import hashlib
import random
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import select

from creditpulse.api.middleware.auth import generate_api_key
from creditpulse.api.services.statement_parser import Transaction, compute_metrics, metrics_to_dict, transactions_to_dicts
from creditpulse.api.services.transaction_categoriser import categorise, extract_counterparty
from creditpulse.db.enums import (
    Confidence,
    EmployeeBand,
    LenderTier,
    Province,
    Recommendation,
    RiskTier,
    TurnoverBand,
)
from creditpulse.db.models import BankStatement, Business, LenderAccount, ScoringRequest
from creditpulse.db.session import AsyncSessionLocal
from creditpulse.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


SAMPLE_BUSINESSES: List[Dict[str, Any]] = [
    {
        "registration_number": "2015/001234/07", "trading_name": "Thabo's Electronics CC",
        "legal_name": "Thabo Electronics (Pty) Ltd", "industry_code": "4771",
        "industry_description": "Retail - Electronics", "province": Province.GAUTENG,
        "years_ago": 9, "turnover": TurnoverBand.BAND_1M_5M, "employees": EmployeeBand.SMALL,
        "profile": "strong", "tax_number": "9012345678",
    },
    {
        "registration_number": "2018/002345/07", "trading_name": "Cape Coastal Catering",
        "legal_name": "Cape Coastal Catering (Pty) Ltd", "industry_code": "5612",
        "industry_description": "Food Services - Catering", "province": Province.WESTERN_CAPE,
        "years_ago": 6, "turnover": TurnoverBand.BAND_1M_5M, "employees": EmployeeBand.SMALL,
        "profile": "strong", "tax_number": "9012345679",
    },
    {
        "registration_number": "2012/003456/07", "trading_name": "Durban Logistics Solutions",
        "legal_name": "Durban Logistics Solutions (Pty) Ltd", "industry_code": "4921",
        "industry_description": "Transport & Logistics", "province": Province.KWAZULU_NATAL,
        "years_ago": 12, "turnover": TurnoverBand.BAND_5M_20M, "employees": EmployeeBand.MEDIUM,
        "profile": "strong", "tax_number": "9012345680",
    },
    {
        "registration_number": "2019/004567/07", "trading_name": "Mzansi Construction Works",
        "legal_name": "Mzansi Construction Works CC", "industry_code": "4321",
        "industry_description": "Construction - General Contracting", "province": Province.GAUTENG,
        "years_ago": 5, "turnover": TurnoverBand.BAND_1M_5M, "employees": EmployeeBand.MEDIUM,
        "profile": "medium", "tax_number": "9012345681",
    },
    {
        "registration_number": "2020/005678/07", "trading_name": "Savanna IT Services",
        "legal_name": "Savanna IT Services (Pty) Ltd", "industry_code": "6201",
        "industry_description": "IT Services - Software", "province": Province.WESTERN_CAPE,
        "years_ago": 4, "turnover": TurnoverBand.BAND_1M_5M, "employees": EmployeeBand.SMALL,
        "profile": "medium", "tax_number": "9012345682",
    },
    {
        "registration_number": "2017/006789/07", "trading_name": "Eastern Spices Trading",
        "legal_name": "Eastern Spices Trading CC", "industry_code": "4711",
        "industry_description": "Retail - Food & Beverages", "province": Province.EASTERN_CAPE,
        "years_ago": 7, "turnover": TurnoverBand.UNDER_1M, "employees": EmployeeBand.MICRO,
        "profile": "medium", "tax_number": "9012345683",
    },
    {
        "registration_number": "2021/007890/07", "trading_name": "Highveld Plumbing",
        "legal_name": "Highveld Plumbing (Pty) Ltd", "industry_code": "4322",
        "industry_description": "Construction - Plumbing", "province": Province.MPUMALANGA,
        "years_ago": 3, "turnover": TurnoverBand.UNDER_1M, "employees": EmployeeBand.MICRO,
        "profile": "medium", "tax_number": "9012345684",
    },
    {
        "registration_number": "2022/008901/07", "trading_name": "Kalahari Coffee Co",
        "legal_name": "Kalahari Coffee Company CC", "industry_code": "5612",
        "industry_description": "Food Services - Coffee Shop", "province": Province.NORTHERN_CAPE,
        "years_ago": 2, "turnover": TurnoverBand.UNDER_1M, "employees": EmployeeBand.MICRO,
        "profile": "weak", "tax_number": "9012345685",
    },
    {
        "registration_number": "2023/009012/07", "trading_name": "Midrand Auto Repairs",
        "legal_name": "Midrand Auto Repairs (Pty) Ltd", "industry_code": "4530",
        "industry_description": "Automotive - Repair Services", "province": Province.GAUTENG,
        "years_ago": 1, "turnover": TurnoverBand.UNDER_1M, "employees": EmployeeBand.MICRO,
        "profile": "weak", "tax_number": "9012345686",
    },
    {
        "registration_number": "2024/010123/07", "trading_name": "Bloem Fashion Boutique",
        "legal_name": "Bloem Fashion Boutique CC", "industry_code": "4771",
        "industry_description": "Retail - Fashion", "province": Province.FREE_STATE,
        "years_ago": 1, "turnover": TurnoverBand.UNDER_1M, "employees": EmployeeBand.MICRO,
        "profile": "weak", "tax_number": "9012345687",
    },
]


PROFILE_CONFIG = {
    "strong": {"base_revenue": (200000, 500000), "cv": (0.08, 0.25), "bounce_rate": (0.0, 0.02), "salary": True, "payers": 10},
    "medium": {"base_revenue": (80000, 180000), "cv": (0.25, 0.55), "bounce_rate": (0.02, 0.1), "salary": True, "payers": 5},
    "weak":   {"base_revenue": (20000, 60000), "cv": (0.55, 1.1),  "bounce_rate": (0.1, 0.3), "salary": False, "payers": 2},
}


def _generate_statement(reg: str, profile: str) -> tuple[List[Transaction], Dict[str, Any]]:
    rng = random.Random(int(hashlib.sha256(reg.encode()).hexdigest(), 16) % (2**32))
    cfg = PROFILE_CONFIG[profile]

    base_revenue = rng.uniform(*cfg["base_revenue"])
    target_cv = rng.uniform(*cfg["cv"])
    bounce_rate = rng.uniform(*cfg["bounce_rate"])

    payer_names = [f"Customer {chr(65+i)} (Pty) Ltd" for i in range(cfg["payers"])]

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=365)
    transactions: List[Transaction] = []
    balance = base_revenue * rng.uniform(0.1, 0.4)

    current = start_date
    while current < today:
        monthly_factor = rng.gauss(1.0, target_cv)
        monthly_factor = max(0.2, monthly_factor)
        if current.day in (3, 12, 20, 27):
            num_payments = rng.randint(2, 5)
            for _ in range(num_payments):
                amount = round((base_revenue / 30) * monthly_factor * rng.uniform(0.5, 1.5), 2)
                payer = rng.choice(payer_names)
                balance += amount
                transactions.append(Transaction(
                    date=current.isoformat(),
                    description=f"EFT CREDIT {payer} INV{rng.randint(1000,9999)}",
                    amount=amount, balance=round(balance, 2),
                    category="INCOME", counterparty=extract_counterparty(payer),
                ))

        if rng.random() < 0.5:
            exp_amount = round(base_revenue * rng.uniform(0.005, 0.04), 2)
            vendor = rng.choice(["Makro Wholesale", "Eskom Municipal", "Shell Garage", "Telkom Business"])
            balance -= exp_amount
            cat = categorise(vendor, -exp_amount).value
            transactions.append(Transaction(
                date=current.isoformat(), description=f"PAYMENT TO {vendor}",
                amount=-exp_amount, balance=round(balance, 2), category=cat,
                counterparty=extract_counterparty(vendor),
            ))

        if current.day == 25 and cfg["salary"]:
            salary = round(base_revenue * rng.uniform(0.18, 0.28), 2)
            balance -= salary
            transactions.append(Transaction(
                date=current.isoformat(), description="STAFF SALARY PAYROLL",
                amount=-salary, balance=round(balance, 2), category="SALARY",
                counterparty="Payroll",
            ))

        if current.day == 1:
            rent = round(base_revenue * rng.uniform(0.05, 0.1), 2)
            balance -= rent
            transactions.append(Transaction(
                date=current.isoformat(), description="RENT PAYMENT PROPERTY",
                amount=-rent, balance=round(balance, 2), category="FIXED_COSTS",
                counterparty="Landlord",
            ))

        if rng.random() < bounce_rate:
            bounce_amount = round(base_revenue * rng.uniform(0.01, 0.05), 2)
            transactions.append(Transaction(
                date=current.isoformat(), description="UNPAID DEBIT ORDER RETURNED",
                amount=-bounce_amount, balance=round(balance, 2), category="FEES",
                counterparty="Bank", bounced=True,
            ))

        current += timedelta(days=1)

    metrics = compute_metrics(transactions, bank="FNB")
    return transactions, metrics_to_dict(metrics)


async def _lender_exists(session, name: str) -> bool:
    result = await session.execute(select(LenderAccount).where(LenderAccount.name == name))
    return result.scalar_one_or_none() is not None


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Business).limit(1))
        if existing.scalar_one_or_none():
            logger.info("seed_skipped_already_seeded")
            return

        lenders_created = []
        for name, tier, api_key_override in [
            ("FNB Business Demo", LenderTier.ENTERPRISE, "cp_demo_fnb_business_key_do_not_use_in_prod"),
            ("Test Bank", LenderTier.STANDARD, "cp_demo_test_bank_key_do_not_use_in_prod"),
        ]:
            prefix = api_key_override[:10]
            digest = hashlib.sha256(api_key_override.encode()).hexdigest()
            lender = LenderAccount(
                name=name,
                api_key_hash=digest,
                api_key_prefix=prefix,
                tier=tier,
                monthly_limit=5000,
            )
            session.add(lender)
            lenders_created.append((lender, api_key_override))

        await session.flush()

        businesses: List[Business] = []
        for spec in SAMPLE_BUSINESSES:
            reg_date = datetime.now(timezone.utc) - timedelta(days=365 * spec["years_ago"])
            business = Business(
                registration_number=spec["registration_number"],
                trading_name=spec["trading_name"],
                legal_name=spec["legal_name"],
                industry_code=spec["industry_code"],
                industry_description=spec["industry_description"],
                province=spec["province"],
                registration_date=reg_date,
                tax_number=spec["tax_number"],
                annual_turnover_band=spec["turnover"],
                employee_count_band=spec["employees"],
            )
            session.add(business)
            businesses.append(business)
        await session.flush()

        for business, spec in zip(businesses, SAMPLE_BUSINESSES):
            txs, metrics_dict = _generate_statement(business.registration_number, spec["profile"])
            stmt = BankStatement(
                business_id=business.id,
                file_hash=hashlib.sha256(f"{business.registration_number}-seed".encode()).hexdigest(),
                statement_period_start=datetime.fromisoformat(metrics_dict["period_start"]) if metrics_dict["period_start"] else datetime.now(timezone.utc),
                statement_period_end=datetime.fromisoformat(metrics_dict["period_end"]) if metrics_dict["period_end"] else datetime.now(timezone.utc),
                bank_name="FNB",
                raw_transactions=transactions_to_dicts(txs),
                computed_metrics=metrics_dict,
            )
            session.add(stmt)

        await session.flush()

        lender_fnb = lenders_created[0][0]

        sample_scoring = [
            (businesses[0], 82, RiskTier.VERY_LOW, Recommendation.APPROVE),
            (businesses[1], 76, RiskTier.LOW, Recommendation.APPROVE),
            (businesses[3], 58, RiskTier.MEDIUM, Recommendation.REVIEW),
            (businesses[8], 38, RiskTier.HIGH, Recommendation.DECLINE),
            (businesses[9], 29, RiskTier.VERY_HIGH, Recommendation.DECLINE),
        ]

        for business, score, tier, rec in sample_scoring:
            sr = ScoringRequest(
                business_id=business.id,
                lender_id=lender_fnb.id,
                score=score,
                risk_tier=tier,
                recommendation=rec,
                confidence=Confidence.HIGH,
                processing_ms=random.randint(400, 1200),
                loan_amount_requested=random.choice([50000, 100000, 250000, 500000]),
                loan_term_months=12,
                signals={"signals": [], "penalty_notes": []},
                enrichment_summary={
                    "available": ["cipc", "sars", "transunion", "bank_statement"],
                    "unavailable": [],
                    "confidence": "high",
                },
            )
            session.add(sr)

        await session.commit()

        logger.info("seed_complete", businesses=len(businesses), lenders=len(lenders_created))
        for _, key in lenders_created:
            logger.info("seed_api_key", api_key=key)


if __name__ == "__main__":
    asyncio.run(seed())
