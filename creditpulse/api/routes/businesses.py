from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from creditpulse.api.middleware.auth import get_current_lender
from creditpulse.api.models.schemas import BusinessCreate, BusinessRead
from creditpulse.db.models import Business, LenderAccount
from creditpulse.db.session import get_db

router = APIRouter(prefix="/v1/businesses", tags=["businesses"])


@router.get("", response_model=List[BusinessRead])
async def list_businesses(
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> List[BusinessRead]:
    result = await db.execute(select(Business).order_by(Business.created_at.desc()).limit(limit).offset(offset))
    return [BusinessRead.model_validate(b) for b in result.scalars().all()]


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: uuid.UUID,
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
) -> BusinessRead:
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return BusinessRead.model_validate(business)


@router.post("", response_model=BusinessRead, status_code=201)
async def create_business(
    payload: BusinessCreate,
    lender: LenderAccount = Depends(get_current_lender),
    db: AsyncSession = Depends(get_db),
) -> BusinessRead:
    existing = await db.execute(
        select(Business).where(Business.registration_number == payload.registration_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Business with this registration number already exists")

    business = Business(**payload.model_dump(exclude_none=True))
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return BusinessRead.model_validate(business)
