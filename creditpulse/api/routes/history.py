from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from creditpulse.api.middleware.auth import get_current_lender
from creditpulse.api.models.schemas import ScoringHistoryItem, ScoringHistoryPage
from creditpulse.db.enums import Recommendation, RiskTier
from creditpulse.db.models import Business, LenderAccount, ScoringRequest
from creditpulse.db.session import get_db

router = APIRouter(prefix="/v1/history", tags=["history"])


@router.get("", response_model=ScoringHistoryPage)
async def list_scoring_history(
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    recommendation: Optional[Recommendation] = None,
    risk_tier: Optional[RiskTier] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> ScoringHistoryPage:
    conditions = [ScoringRequest.lender_id == lender.id]
    if min_score is not None:
        conditions.append(ScoringRequest.score >= min_score)
    if max_score is not None:
        conditions.append(ScoringRequest.score <= max_score)
    if recommendation:
        conditions.append(ScoringRequest.recommendation == recommendation)
    if risk_tier:
        conditions.append(ScoringRequest.risk_tier == risk_tier)
    if from_date:
        conditions.append(ScoringRequest.requested_at >= from_date)
    if to_date:
        conditions.append(ScoringRequest.requested_at <= to_date)

    total_q = select(func.count(ScoringRequest.id)).where(and_(*conditions))
    total_result = await db.execute(total_q)
    total = total_result.scalar_one()

    query = (
        select(ScoringRequest)
        .where(and_(*conditions))
        .options(selectinload(ScoringRequest.business))
        .order_by(ScoringRequest.requested_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    result = await db.execute(query)
    items = [
        ScoringHistoryItem(
            id=sr.id,
            business_id=sr.business_id,
            business_name=sr.business.trading_name,
            registration_number=sr.business.registration_number,
            score=sr.score,
            risk_tier=sr.risk_tier,
            recommendation=sr.recommendation,
            requested_at=sr.requested_at,
            processing_ms=sr.processing_ms,
        )
        for sr in result.scalars().all()
    ]
    return ScoringHistoryPage(items=items, total=total, page=page, page_size=page_size)
