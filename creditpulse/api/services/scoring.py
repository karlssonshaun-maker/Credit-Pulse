from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from creditpulse.api.models.schemas import BusinessSummary, ScoreRequest, ScoreResponse, SignalPayload
from creditpulse.api.services.enrichment import enrich_all
from creditpulse.api.services.statement_parser import compute_metrics, parse_statement
from creditpulse.db.enums import EnrichmentSource
from creditpulse.db.models import BankStatement, Business, EnrichmentResult, ScoringRequest
from creditpulse.integrations import cipc as cipc_integration
from creditpulse.integrations import sars as sars_integration
from creditpulse.integrations import transunion as tu_integration
from creditpulse.integrations.base import IntegrationOutcome
from creditpulse.ml.explainer import build_signal_breakdown, top_drivers
from creditpulse.ml.features import assemble_features
from creditpulse.ml.rule_engine import calculate_score


async def _latest_statement_metrics(db: AsyncSession, business_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    result = await db.execute(
        select(BankStatement)
        .where(BankStatement.business_id == business_id)
        .order_by(BankStatement.parsed_at.desc())
        .limit(1)
    )
    stmt = result.scalar_one_or_none()
    return stmt.computed_metrics if stmt else None


async def _get_or_create_business(
    db: AsyncSession,
    registration_number: str,
    cipc_data: Optional[Dict[str, Any]],
    tax_number: Optional[str],
) -> Business:
    result = await db.execute(
        select(Business).where(Business.registration_number == registration_number)
    )
    business = result.scalar_one_or_none()
    if business:
        if tax_number and not business.tax_number:
            business.tax_number = tax_number
        return business

    registration_date = None
    if cipc_data and cipc_data.get("registration_date"):
        try:
            registration_date = datetime.fromisoformat(cipc_data["registration_date"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            registration_date = None

    business = Business(
        registration_number=registration_number,
        trading_name=f"Business {registration_number}",
        legal_name=f"Business {registration_number}",
        industry_code=cipc_data.get("sic_code") if cipc_data else None,
        tax_number=tax_number,
        registration_date=registration_date,
    )
    db.add(business)
    await db.flush()
    return business


async def _record_enrichment(
    db: AsyncSession,
    scoring_request_id: uuid.UUID,
    source: EnrichmentSource,
    outcome: IntegrationOutcome,
    normaliser,
) -> None:
    normalised: Dict[str, Any] = {}
    if outcome.success and outcome.data and normaliser:
        try:
            normalised = normaliser(outcome.data)
        except Exception:
            normalised = {}

    record = EnrichmentResult(
        scoring_request_id=scoring_request_id,
        source=source,
        cache_hit=outcome.cache_hit,
        success=outcome.success,
        latency_ms=outcome.latency_ms,
        error_message=outcome.error,
        raw_response=outcome.data or {},
        normalised_signals=normalised,
    )
    db.add(record)


async def execute_scoring(
    db: AsyncSession,
    lender_id: uuid.UUID,
    payload: ScoreRequest,
) -> ScoreResponse:
    started = time.perf_counter()

    enrichment = await enrich_all(
        registration_number=payload.registration_number,
        tax_number=payload.tax_number,
        bank_account_id=payload.registration_number if payload.use_mock_bank_api else None,
        include_bank_api=payload.use_mock_bank_api,
    )

    business = await _get_or_create_business(
        db=db,
        registration_number=payload.registration_number,
        cipc_data=enrichment.cipc,
        tax_number=payload.tax_number,
    )

    statement_metrics = await _latest_statement_metrics(db, business.id)
    if statement_metrics is None and enrichment.bank_api:
        from creditpulse.api.services.statement_parser import Transaction, compute_metrics as _compute

        txs = [
            Transaction(
                date=t["date"],
                description=t["description"],
                amount=t["amount"],
                balance=t.get("balance"),
                category="",
                counterparty=None,
            )
            for t in enrichment.bank_api.get("transactions", [])
        ]
        from creditpulse.api.services.transaction_categoriser import categorise, extract_counterparty, is_bounced_debit
        for t in txs:
            t.bounced = is_bounced_debit(t.description)
            cat = categorise(t.description, t.amount)
            t.category = cat.value
            t.counterparty = extract_counterparty(t.description)
        statement_metrics = _compute(txs).__dict__

    available = list(enrichment.available)
    unavailable = list(enrichment.unavailable)
    if statement_metrics:
        if "bank_statement" not in available:
            available.append("bank_statement")
    else:
        if "bank_statement" not in unavailable:
            unavailable.append("bank_statement")

    features = assemble_features(
        business={
            "registration_number": business.registration_number,
            "trading_name": business.trading_name,
            "industry_code": business.industry_code,
            "industry_description": business.industry_description,
            "province": business.province.value if business.province else None,
        },
        cipc=enrichment.cipc,
        sars=enrichment.sars,
        bureau=enrichment.bureau,
        statement_metrics=statement_metrics,
        available=available,
        unavailable=unavailable,
        loan_amount=payload.loan_amount_requested,
        loan_term_months=payload.loan_term_months,
    )

    result = calculate_score(features)
    processing_ms = int((time.perf_counter() - started) * 1000)

    scoring_request = ScoringRequest(
        business_id=business.id,
        lender_id=lender_id,
        score=result.score,
        risk_tier=result.risk_tier,
        recommendation=result.recommendation,
        confidence=result.confidence,
        processing_ms=processing_ms,
        loan_amount_requested=payload.loan_amount_requested,
        loan_term_months=payload.loan_term_months,
        signals={"signals": build_signal_breakdown(result), "penalty_notes": result.penalty_notes},
        enrichment_summary={
            "available": available,
            "unavailable": unavailable,
            "confidence": result.confidence.value,
        },
    )
    db.add(scoring_request)
    await db.flush()

    await _record_enrichment(db, scoring_request.id, EnrichmentSource.CIPC, enrichment.outcomes.get("cipc") or IntegrationOutcome(False, None, False, 0, "skipped"), cipc_integration.normalise)
    await _record_enrichment(db, scoring_request.id, EnrichmentSource.SARS, enrichment.outcomes.get("sars") or IntegrationOutcome(False, None, False, 0, "skipped"), sars_integration.normalise)
    await _record_enrichment(db, scoring_request.id, EnrichmentSource.TRANSUNION, enrichment.outcomes.get("transunion") or IntegrationOutcome(False, None, False, 0, "skipped"), tu_integration.normalise)

    from sqlalchemy import update
    from creditpulse.db.models import LenderAccount
    await db.execute(
        update(LenderAccount)
        .where(LenderAccount.id == lender_id)
        .values(requests_this_month=LenderAccount.requests_this_month + 1)
    )

    await db.commit()

    drivers = top_drivers(result.signals)

    return ScoreResponse(
        scoring_request_id=scoring_request.id,
        score=result.score,
        risk_tier=result.risk_tier,
        recommendation=result.recommendation,
        confidence=result.confidence,
        business=BusinessSummary(
            id=business.id,
            name=business.trading_name,
            registration_number=business.registration_number,
            trading_age_months=features.trading_age_months,
            industry=business.industry_description or business.industry_code,
            province=business.province.value if business.province else None,
        ),
        signals=[SignalPayload(**s) for s in build_signal_breakdown(result)],
        top_strengths=drivers["top_strengths"],
        top_concerns=drivers["top_concerns"],
        penalty_notes=result.penalty_notes,
        data_sources_used=available,
        data_sources_unavailable=unavailable,
        processing_ms=processing_ms,
        score_generated_at=datetime.now(timezone.utc),
    )
