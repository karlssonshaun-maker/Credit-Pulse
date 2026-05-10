from creditpulse.db.enums import Recommendation, RiskTier
from creditpulse.ml.features import FeatureBundle
from creditpulse.ml.rule_engine import calculate_score, derive_risk_tier


def _strong_bundle():
    return FeatureBundle(
        registration_number="2015/001234/07",
        trading_age_months=96,
        cipc_status="active",
        vat_registered=True,
        sars_tax_compliant=True,
        sars_outstanding_returns=0,
        director_adverse_flag=False,
        credit_bureau_score=780,
        adverse_listings_count=0,
        active_credit_facilities=1,
        average_monthly_revenue=350000,
        revenue_coefficient_of_variation=0.15,
        positive_cash_flow_months=0.92,
        months_with_negative_cashflow=1,
        average_closing_balance_3m=120000,
        bounce_rate=0.005,
        salary_run_regularity=True,
        revenue_source_diversity=12,
        largest_client_concentration=0.15,
        repeat_customer_rate=0.75,
        invoice_payment_lag_days=14,
        detected_loan_repayments_monthly=15000,
        available_sources=["cipc", "sars", "transunion", "bank_statement"],
    )


def _weak_bundle():
    return FeatureBundle(
        registration_number="2023/999999/07",
        trading_age_months=8,
        cipc_status="active",
        vat_registered=False,
        sars_tax_compliant=False,
        sars_outstanding_returns=3,
        director_adverse_flag=True,
        credit_bureau_score=320,
        adverse_listings_count=3,
        active_credit_facilities=6,
        average_monthly_revenue=25000,
        revenue_coefficient_of_variation=1.2,
        positive_cash_flow_months=0.3,
        months_with_negative_cashflow=8,
        average_closing_balance_3m=1500,
        bounce_rate=0.25,
        salary_run_regularity=False,
        revenue_source_diversity=1,
        largest_client_concentration=0.85,
        repeat_customer_rate=0.1,
        invoice_payment_lag_days=90,
        detected_loan_repayments_monthly=18000,
        available_sources=["cipc", "sars", "transunion", "bank_statement"],
    )


def test_strong_business_scores_high():
    result = calculate_score(_strong_bundle())
    assert result.score >= 70
    assert result.risk_tier in (RiskTier.LOW, RiskTier.VERY_LOW)
    assert result.recommendation == Recommendation.APPROVE


def test_weak_business_scores_low_and_declines():
    result = calculate_score(_weak_bundle())
    assert result.score < 40
    assert result.recommendation == Recommendation.DECLINE
    assert any("non-compliant" in note.lower() for note in result.penalty_notes)


def test_deregistered_cipc_applies_severe_penalty():
    bundle = _strong_bundle()
    bundle.cipc_status = "deregistered"
    result = calculate_score(bundle)
    assert result.score < 50
    assert any("deregistered" in note.lower() for note in result.penalty_notes)


def test_missing_signals_still_produces_score():
    bundle = FeatureBundle(
        registration_number="2015/001234/07",
        cipc_status="active",
        available_sources=["cipc"],
    )
    result = calculate_score(bundle)
    assert 0 <= result.score <= 100
    assert result.confidence.value == "low"


def test_derive_risk_tier_boundaries():
    assert derive_risk_tier(90) == RiskTier.VERY_LOW
    assert derive_risk_tier(70) == RiskTier.LOW
    assert derive_risk_tier(55) == RiskTier.MEDIUM
    assert derive_risk_tier(40) == RiskTier.HIGH
    assert derive_risk_tier(20) == RiskTier.VERY_HIGH


def test_large_loan_downgrades_tier():
    bundle = _strong_bundle()
    bundle.loan_amount_requested = 800000
    bundle.loan_term_months = 6
    result = calculate_score(bundle)
    assert any("loan" in note.lower() for note in result.penalty_notes)
