from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from creditpulse.db.enums import (
    Confidence,
    EmployeeBand,
    LenderTier,
    Province,
    Recommendation,
    RiskTier,
    TurnoverBand,
)


class ScoreRequest(BaseModel):
    registration_number: str = Field(..., min_length=4, max_length=32)
    tax_number: Optional[str] = Field(default=None, max_length=32)
    statement_months: int = Field(default=6, ge=1, le=24)
    loan_amount_requested: Optional[float] = Field(default=None, ge=0)
    loan_term_months: Optional[int] = Field(default=None, ge=1, le=240)
    use_mock_bank_api: bool = Field(default=True)


class BusinessSummary(BaseModel):
    id: Optional[UUID] = None
    name: str
    registration_number: str
    trading_age_months: Optional[int] = None
    industry: Optional[str] = None
    province: Optional[str] = None


class SignalPayload(BaseModel):
    category: str
    name: str
    key: str
    value: Any
    normalised: float
    weight: float
    score_contribution: float
    direction: str
    explanation: str
    available: bool


class ScoreResponse(BaseModel):
    scoring_request_id: UUID
    score: int
    risk_tier: RiskTier
    recommendation: Recommendation
    confidence: Confidence
    business: BusinessSummary
    signals: List[SignalPayload]
    top_strengths: List[Dict[str, Any]]
    top_concerns: List[Dict[str, Any]]
    penalty_notes: List[str]
    data_sources_used: List[str]
    data_sources_unavailable: List[str]
    processing_ms: int
    score_generated_at: datetime


class BusinessCreate(BaseModel):
    registration_number: str
    trading_name: str
    legal_name: str
    industry_code: Optional[str] = None
    industry_description: Optional[str] = None
    province: Optional[Province] = None
    registration_date: Optional[datetime] = None
    vat_number: Optional[str] = None
    tax_number: Optional[str] = None
    annual_turnover_band: Optional[TurnoverBand] = None
    employee_count_band: Optional[EmployeeBand] = None


class BusinessRead(BusinessCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LenderCreate(BaseModel):
    name: str
    tier: LenderTier = LenderTier.STANDARD
    monthly_limit: int = 1000


class LenderRead(BaseModel):
    id: UUID
    name: str
    tier: LenderTier
    monthly_limit: int
    requests_this_month: int
    active: bool
    created_at: datetime
    api_key_prefix: str

    class Config:
        from_attributes = True


class LenderCreated(LenderRead):
    api_key: str


class StatementUploadResponse(BaseModel):
    statement_id: UUID
    business_id: UUID
    bank_name: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    transaction_count: int
    metrics: Dict[str, Any]


class ScoringHistoryItem(BaseModel):
    id: UUID
    business_id: UUID
    business_name: str
    registration_number: str
    score: int
    risk_tier: RiskTier
    recommendation: Recommendation
    requested_at: datetime
    processing_ms: int


class ScoringHistoryPage(BaseModel):
    items: List[ScoringHistoryItem]
    total: int
    page: int
    page_size: int


class AnalyticsResponse(BaseModel):
    score_distribution: List[Dict[str, Any]]
    approval_rate_over_time: List[Dict[str, Any]]
    average_score_by_industry: List[Dict[str, Any]]
    top_negative_signals: List[Dict[str, Any]]
    total_assessments: int
    approval_rate: float
