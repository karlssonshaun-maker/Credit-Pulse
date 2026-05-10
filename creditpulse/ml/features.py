from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class FeatureBundle:
    registration_number: str
    trading_name: Optional[str] = None
    industry_code: Optional[str] = None
    industry_description: Optional[str] = None
    province: Optional[str] = None

    trading_age_months: Optional[int] = None
    cipc_status: Optional[str] = None
    vat_registered: Optional[bool] = None
    director_count: Optional[int] = None
    director_adverse_flag: Optional[bool] = None

    sars_tax_compliant: Optional[bool] = None
    sars_outstanding_returns: Optional[int] = None
    vat_active: Optional[bool] = None

    credit_bureau_score: Optional[int] = None
    adverse_listings_count: Optional[int] = None
    active_credit_facilities: Optional[int] = None
    total_exposure: Optional[float] = None

    average_monthly_revenue: Optional[float] = None
    revenue_coefficient_of_variation: Optional[float] = None
    positive_cash_flow_months: Optional[float] = None
    months_with_negative_cashflow: Optional[int] = None
    average_closing_balance_3m: Optional[float] = None
    bounce_rate: Optional[float] = None
    salary_run_regularity: Optional[bool] = None
    detected_loan_repayments_monthly: Optional[float] = None
    revenue_source_diversity: Optional[int] = None
    largest_client_concentration: Optional[float] = None
    repeat_customer_rate: Optional[float] = None
    invoice_payment_lag_days: Optional[float] = None

    available_sources: List[str] = field(default_factory=list)
    unavailable_sources: List[str] = field(default_factory=list)

    loan_amount_requested: Optional[float] = None
    loan_term_months: Optional[int] = None

    raw: Dict[str, Any] = field(default_factory=dict)


def months_between(start: datetime, end: Optional[datetime] = None) -> int:
    end = end or datetime.now(timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def assemble_features(
    business: Dict[str, Any],
    cipc: Optional[Dict[str, Any]],
    sars: Optional[Dict[str, Any]],
    bureau: Optional[Dict[str, Any]],
    statement_metrics: Optional[Dict[str, Any]],
    available: List[str],
    unavailable: List[str],
    loan_amount: Optional[float] = None,
    loan_term_months: Optional[int] = None,
) -> FeatureBundle:
    bundle = FeatureBundle(
        registration_number=business.get("registration_number", ""),
        trading_name=business.get("trading_name"),
        industry_code=business.get("industry_code"),
        industry_description=business.get("industry_description"),
        province=business.get("province"),
        loan_amount_requested=loan_amount,
        loan_term_months=loan_term_months,
        available_sources=available,
        unavailable_sources=unavailable,
    )

    if cipc:
        reg_date_str = cipc.get("registration_date")
        if reg_date_str:
            if isinstance(reg_date_str, datetime):
                reg_date = reg_date_str
            else:
                try:
                    reg_date = datetime.fromisoformat(reg_date_str.replace("Z", "+00:00"))
                except ValueError:
                    reg_date = None
            if reg_date:
                bundle.trading_age_months = months_between(reg_date)
        bundle.cipc_status = cipc.get("registration_status")
        directors = cipc.get("directors") or []
        bundle.director_count = len(directors)
        bundle.director_adverse_flag = any(d.get("adverse_flag") for d in directors)

    if sars:
        bundle.sars_tax_compliant = sars.get("compliance_status") == "compliant"
        bundle.sars_outstanding_returns = sars.get("outstanding_returns", 0)
        bundle.vat_active = sars.get("vat_status") == "active"
        bundle.vat_registered = sars.get("vat_status") in ("active", "registered")

    if bureau:
        bundle.credit_bureau_score = bureau.get("commercial_score")
        bundle.adverse_listings_count = len(bureau.get("adverse_listings") or [])
        bundle.active_credit_facilities = bureau.get("active_credit_facilities")
        bundle.total_exposure = bureau.get("total_exposure")

    if statement_metrics:
        bundle.average_monthly_revenue = statement_metrics.get("average_monthly_revenue")
        bundle.revenue_coefficient_of_variation = statement_metrics.get("revenue_coefficient_of_variation")
        bundle.positive_cash_flow_months = statement_metrics.get("positive_cash_flow_months_ratio")
        bundle.months_with_negative_cashflow = statement_metrics.get("months_with_negative_cashflow")
        bundle.average_closing_balance_3m = statement_metrics.get("average_closing_balance_3m")
        bundle.bounce_rate = statement_metrics.get("bounce_rate")
        bundle.salary_run_regularity = statement_metrics.get("salary_run_regularity")
        bundle.detected_loan_repayments_monthly = statement_metrics.get("detected_loan_repayments_monthly")
        bundle.revenue_source_diversity = statement_metrics.get("revenue_source_diversity")
        bundle.largest_client_concentration = statement_metrics.get("largest_client_concentration")
        bundle.repeat_customer_rate = statement_metrics.get("repeat_customer_rate")
        bundle.invoice_payment_lag_days = statement_metrics.get("invoice_payment_lag_days")

    return bundle
