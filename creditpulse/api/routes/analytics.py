from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from creditpulse.api.middleware.auth import get_current_lender
from creditpulse.api.models.schemas import AnalyticsResponse
from creditpulse.db.enums import Recommendation
from creditpulse.db.models import Business, LenderAccount, ScoringRequest
from creditpulse.db.session import get_db

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsResponse)
async def analytics_overview(
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    result = await db.execute(
        select(ScoringRequest)
        .where(ScoringRequest.lender_id == lender.id)
        .options(selectinload(ScoringRequest.business))
        .order_by(ScoringRequest.requested_at.asc())
    )
    requests = result.scalars().all()

    bands = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]
    distribution: List[Dict[str, Any]] = []
    for low, high in bands:
        count = sum(1 for r in requests if low <= r.score < high)
        distribution.append({"range": f"{low}-{high if high < 100 else 100}", "count": count})

    daily_approvals: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "approved": 0})
    for r in requests:
        key = r.requested_at.date().isoformat()
        daily_approvals[key]["total"] += 1
        if r.recommendation == Recommendation.APPROVE:
            daily_approvals[key]["approved"] += 1

    approval_over_time = [
        {
            "date": day,
            "approval_rate": round(stats["approved"] / stats["total"], 3) if stats["total"] else 0,
            "count": stats["total"],
        }
        for day, stats in sorted(daily_approvals.items())
    ]

    industry_scores: Dict[str, List[int]] = defaultdict(list)
    for r in requests:
        industry = r.business.industry_description or r.business.industry_code or "Unclassified"
        industry_scores[industry].append(r.score)

    avg_by_industry = [
        {"industry": industry, "average_score": round(sum(scores) / len(scores), 1), "count": len(scores)}
        for industry, scores in industry_scores.items()
    ]
    avg_by_industry.sort(key=lambda item: item["average_score"], reverse=True)

    negative_counter: Counter = Counter()
    for r in requests:
        if r.recommendation == Recommendation.DECLINE:
            signals = (r.signals or {}).get("signals", [])
            for s in signals:
                if s.get("direction") == "negative":
                    negative_counter[s.get("name", "unknown")] += 1

    top_negative = [
        {"signal": name, "count": count}
        for name, count in negative_counter.most_common(5)
    ]

    total = len(requests)
    approvals = sum(1 for r in requests if r.recommendation == Recommendation.APPROVE)
    approval_rate = round(approvals / total, 3) if total else 0.0

    return AnalyticsResponse(
        score_distribution=distribution,
        approval_rate_over_time=approval_over_time,
        average_score_by_industry=avg_by_industry,
        top_negative_signals=top_negative,
        total_assessments=total,
        approval_rate=approval_rate,
    )
