from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from creditpulse.api.middleware.auth import get_current_lender
from creditpulse.api.models.schemas import StatementUploadResponse
from creditpulse.api.services.statement_parser import (
    compute_file_hash,
    metrics_to_dict,
    parse_statement,
    transactions_to_dicts,
)
from creditpulse.db.models import BankStatement, Business, LenderAccount
from creditpulse.db.session import get_db

router = APIRouter(prefix="/v1/statements", tags=["statements"])


@router.post("/upload", response_model=StatementUploadResponse)
async def upload_statement(
    registration_number: str = Form(...),
    bank_hint: str | None = Form(default=None),
    file: UploadFile = File(...),
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
) -> StatementUploadResponse:
    result = await db.execute(
        select(Business).where(Business.registration_number == registration_number)
    )
    business = result.scalar_one_or_none()
    if business is None:
        business = Business(
            registration_number=registration_number,
            trading_name=f"Business {registration_number}",
            legal_name=f"Business {registration_number}",
        )
        db.add(business)
        await db.flush()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    transactions, metrics = parse_statement(content, file.filename or "statement.csv", bank_hint)
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions could be parsed from the file")

    stmt = BankStatement(
        business_id=business.id,
        file_hash=compute_file_hash(content),
        statement_period_start=datetime.fromisoformat(metrics.period_start) if metrics.period_start else datetime.now(timezone.utc),
        statement_period_end=datetime.fromisoformat(metrics.period_end) if metrics.period_end else datetime.now(timezone.utc),
        bank_name=metrics.bank_name,
        raw_transactions=transactions_to_dicts(transactions),
        computed_metrics=metrics_to_dict(metrics),
    )
    db.add(stmt)
    await db.commit()
    await db.refresh(stmt)

    return StatementUploadResponse(
        statement_id=stmt.id,
        business_id=business.id,
        bank_name=metrics.bank_name,
        period_start=metrics.period_start,
        period_end=metrics.period_end,
        transaction_count=metrics.transaction_count,
        metrics=metrics_to_dict(metrics),
    )
