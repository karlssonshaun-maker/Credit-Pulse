from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from creditpulse.api.middleware.auth import generate_api_key, get_current_lender
from creditpulse.api.models.schemas import LenderCreate, LenderCreated, LenderRead
from creditpulse.db.models import LenderAccount
from creditpulse.db.session import get_db

router = APIRouter(prefix="/v1/lenders", tags=["lenders"])


@router.post("", response_model=LenderCreated, status_code=201)
async def create_lender(payload: LenderCreate, db: AsyncSession = Depends(get_db)) -> LenderCreated:
    raw_key, prefix, digest = generate_api_key()
    lender = LenderAccount(
        name=payload.name,
        api_key_hash=digest,
        api_key_prefix=prefix,
        tier=payload.tier,
        monthly_limit=payload.monthly_limit,
    )
    db.add(lender)
    await db.commit()
    await db.refresh(lender)

    return LenderCreated(
        id=lender.id,
        name=lender.name,
        tier=lender.tier,
        monthly_limit=lender.monthly_limit,
        requests_this_month=lender.requests_this_month,
        active=lender.active,
        created_at=lender.created_at,
        api_key_prefix=lender.api_key_prefix,
        api_key=raw_key,
    )


@router.get("/me", response_model=LenderRead)
async def get_my_lender(
    lender: LenderAccount = Depends(get_current_lender),
) -> LenderRead:
    return LenderRead.model_validate(lender)
