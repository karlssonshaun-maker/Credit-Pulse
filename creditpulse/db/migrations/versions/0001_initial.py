"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    province_enum = sa.Enum(
        "gauteng", "western_cape", "kwazulu_natal", "eastern_cape", "free_state",
        "mpumalanga", "limpopo", "north_west", "northern_cape",
        name="province",
    )
    turnover_enum = sa.Enum(
        "under_1m", "1m_5m", "5m_20m", "20m_50m", "over_50m", name="turnover_band"
    )
    employee_enum = sa.Enum("1-5", "6-20", "21-50", "51-200", name="employee_band")
    risk_enum = sa.Enum("very_low", "low", "medium", "high", "very_high", name="risk_tier")
    recommendation_enum = sa.Enum("approve", "review", "decline", name="recommendation")
    confidence_enum = sa.Enum("low", "medium", "high", name="confidence")
    lender_tier_enum = sa.Enum("trial", "standard", "enterprise", name="lender_tier")
    enrichment_source_enum = sa.Enum(
        "cipc", "transunion", "sars", "bank_statement", "bank_api", name="enrichment_source"
    )

    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("registration_number", sa.String(32), unique=True, nullable=False),
        sa.Column("trading_name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("industry_code", sa.String(16), nullable=True),
        sa.Column("industry_description", sa.String(255), nullable=True),
        sa.Column("province", province_enum, nullable=True),
        sa.Column("registration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vat_number", sa.String(32), nullable=True),
        sa.Column("tax_number", sa.String(32), nullable=True),
        sa.Column("annual_turnover_band", turnover_enum, nullable=True),
        sa.Column("employee_count_band", employee_enum, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_businesses_registration_number", "businesses", ["registration_number"])
    op.create_index("ix_businesses_industry_code", "businesses", ["industry_code"])
    op.create_index("ix_businesses_industry_province", "businesses", ["industry_code", "province"])

    op.create_table(
        "lender_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("api_key_hash", sa.String(128), unique=True, nullable=False),
        sa.Column("api_key_prefix", sa.String(16), nullable=False),
        sa.Column("tier", lender_tier_enum, nullable=False),
        sa.Column("monthly_limit", sa.Integer, nullable=False, server_default="1000"),
        sa.Column("requests_this_month", sa.Integer, nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lender_accounts_api_key_hash", "lender_accounts", ["api_key_hash"])

    op.create_table(
        "scoring_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("lender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lender_accounts.id"), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("risk_tier", risk_enum, nullable=False),
        sa.Column("recommendation", recommendation_enum, nullable=False),
        sa.Column("confidence", confidence_enum, nullable=False, server_default="medium"),
        sa.Column("processing_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("loan_amount_requested", sa.Numeric(14, 2), nullable=True),
        sa.Column("loan_term_months", sa.Integer, nullable=True),
        sa.Column("signals", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enrichment_summary", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_scoring_requests_business_id", "scoring_requests", ["business_id"])
    op.create_index("ix_scoring_requests_lender_id", "scoring_requests", ["lender_id"])
    op.create_index("ix_scoring_requests_requested_at", "scoring_requests", ["requested_at"])
    op.create_index("ix_scoring_requests_lender_requested", "scoring_requests", ["lender_id", "requested_at"])

    op.create_table(
        "bank_statements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("statement_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("statement_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bank_name", sa.String(64), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("raw_transactions", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("computed_metrics", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_bank_statements_business_id", "bank_statements", ["business_id"])
    op.create_index("ix_bank_statements_file_hash", "bank_statements", ["file_hash"])

    op.create_table(
        "enrichment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scoring_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scoring_requests.id"),
            nullable=False,
        ),
        sa.Column("source", enrichment_source_enum, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("cache_hit", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("raw_response", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("normalised_signals", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_enrichment_results_scoring_request_id", "enrichment_results", ["scoring_request_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lender_accounts.id"), nullable=True
        ),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("request_summary", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("response_code", sa.Integer, nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(64), nullable=True),
    )
    op.create_index("ix_audit_log_lender_id", "audit_log", ["lender_id"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_lender_ts", "audit_log", ["lender_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("enrichment_results")
    op.drop_table("bank_statements")
    op.drop_table("scoring_requests")
    op.drop_table("lender_accounts")
    op.drop_table("businesses")
    for name in [
        "enrichment_source", "lender_tier", "confidence", "recommendation", "risk_tier",
        "employee_band", "turnover_band", "province",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
