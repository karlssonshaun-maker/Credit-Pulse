from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from creditpulse.api.middleware.auth import get_current_lender
from creditpulse.api.models.schemas import (
    BusinessSummary,
    ScoreRequest,
    ScoreResponse,
    SignalPayload,
)
from creditpulse.api.services.scoring import execute_scoring
from creditpulse.db.models import LenderAccount, ScoringRequest
from creditpulse.db.session import get_db

router = APIRouter(prefix="/v1/score", tags=["scoring"])


@router.post("", response_model=ScoreResponse)
async def create_score(
    payload: ScoreRequest,
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    return await execute_scoring(db=db, lender_id=lender.id, payload=payload)


@router.get("/{scoring_request_id}", response_model=ScoreResponse)
async def get_score(
    scoring_request_id: uuid.UUID,
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    result = await db.execute(
        select(ScoringRequest)
        .where(ScoringRequest.id == scoring_request_id, ScoringRequest.lender_id == lender.id)
        .options(selectinload(ScoringRequest.business))
    )
    sr = result.scalar_one_or_none()
    if sr is None:
        raise HTTPException(status_code=404, detail="Scoring request not found")

    signals_data = sr.signals or {}
    return ScoreResponse(
        scoring_request_id=sr.id,
        score=sr.score,
        risk_tier=sr.risk_tier,
        recommendation=sr.recommendation,
        confidence=sr.confidence,
        business=BusinessSummary(
            id=sr.business.id,
            name=sr.business.trading_name,
            registration_number=sr.business.registration_number,
            industry=sr.business.industry_description or sr.business.industry_code,
            province=sr.business.province.value if sr.business.province else None,
        ),
        signals=[SignalPayload(**s) for s in signals_data.get("signals", [])],
        top_strengths=[],
        top_concerns=[],
        penalty_notes=signals_data.get("penalty_notes", []),
        data_sources_used=(sr.enrichment_summary or {}).get("available", []),
        data_sources_unavailable=(sr.enrichment_summary or {}).get("unavailable", []),
        processing_ms=sr.processing_ms,
        score_generated_at=sr.requested_at or datetime.now(timezone.utc),
    )
