from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from creditpulse.db.models import LenderAccount
from creditpulse.db.session import get_db


API_KEY_HEADER = "X-API-Key"


def generate_api_key() -> tuple[str, str, str]:
    raw = f"cp_{secrets.token_urlsafe(32)}"
    prefix = raw[:10]
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, digest


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_current_lender(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LenderAccount:
    api_key: Optional[str] = request.headers.get(API_KEY_HEADER)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    digest = hash_api_key(api_key)
    result = await db.execute(
        select(LenderAccount).where(LenderAccount.api_key_hash == digest)
    )
    lender = result.scalar_one_or_none()
    if lender is None or not lender.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if lender.requests_this_month >= lender.monthly_limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Monthly quota exceeded")
    request.state.lender_id = str(lender.id)
    return lender
