from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from creditpulse.db.enums import (
    Confidence,
    EmployeeBand,
    EnrichmentSource,
    LenderTier,
    Province,
    Recommendation,
    RiskTier,
    TurnoverBand,
)


class Base(DeclarativeBase):
    pass


def _pg_enum(enum_cls, *, name: str):
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [m.value for m in members],
        native_enum=True,
        create_type=False,
    )


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    trading_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    industry_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    province: Mapped[Optional[Province]] = mapped_column(_pg_enum(Province, name="province"), nullable=True)
    registration_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    vat_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tax_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    annual_turnover_band: Mapped[Optional[TurnoverBand]] = mapped_column(
        _pg_enum(TurnoverBand, name="turnover_band"), nullable=True
    )
    employee_count_band: Mapped[Optional[EmployeeBand]] = mapped_column(
        _pg_enum(EmployeeBand, name="employee_band"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    statements: Mapped[list["BankStatement"]] = relationship(back_populates="business")
    scoring_requests: Mapped[list["ScoringRequest"]] = relationship(back_populates="business")

    __table_args__ = (
        Index("ix_businesses_industry_province", "industry_code", "province"),
    )


class LenderAccount(Base):
    __tablename__ = "lender_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    api_key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    tier: Mapped[LenderTier] = mapped_column(
        _pg_enum(LenderTier, name="lender_tier"), default=LenderTier.STANDARD, nullable=False
    )
    monthly_limit: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    requests_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scoring_requests: Mapped[list["ScoringRequest"]] = relationship(back_populates="lender")


class ScoringRequest(Base):
    __tablename__ = "scoring_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    lender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lender_accounts.id"), nullable=False, index=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_tier: Mapped[RiskTier] = mapped_column(_pg_enum(RiskTier, name="risk_tier"), nullable=False)
    recommendation: Mapped[Recommendation] = mapped_column(
        _pg_enum(Recommendation, name="recommendation"), nullable=False
    )
    confidence: Mapped[Confidence] = mapped_column(
        _pg_enum(Confidence, name="confidence"), default=Confidence.MEDIUM, nullable=False
    )
    processing_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loan_amount_requested: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    loan_term_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    signals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enrichment_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    business: Mapped[Business] = relationship(back_populates="scoring_requests")
    lender: Mapped[LenderAccount] = relationship(back_populates="scoring_requests")
    enrichments: Mapped[list["EnrichmentResult"]] = relationship(back_populates="scoring_request")

    __table_args__ = (
        Index("ix_scoring_requests_lender_requested", "lender_id", "requested_at"),
    )


class BankStatement(Base):
    __tablename__ = "bank_statements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    statement_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    statement_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_transactions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    computed_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    business: Mapped[Business] = relationship(back_populates="statements")


class EnrichmentResult(Base):
    __tablename__ = "enrichment_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scoring_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scoring_requests.id"), nullable=False, index=True
    )
    source: Mapped[EnrichmentSource] = mapped_column(
        _pg_enum(EnrichmentSource, name="enrichment_source"), nullable=False
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_response: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    normalised_signals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    scoring_request: Mapped[ScoringRequest] = relationship(back_populates="enrichments")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("lender_accounts.id"), nullable=True, index=True
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    request_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_audit_log_lender_ts", "lender_id", "timestamp"),
    )
