from creditpulse.api.services.signals import (
    compute_all_signals,
    signal_average_monthly_revenue,
    signal_cipc_status,
    signal_revenue_consistency,
    signal_sars_compliance,
    signal_trading_age,
)
from creditpulse.ml.features import FeatureBundle


def _bundle(**overrides):
    defaults = dict(registration_number="2015/001234/07")
    defaults.update(overrides)
    return FeatureBundle(**defaults)


def test_trading_age_5_years_gives_full_weight():
    b = _bundle(trading_age_months=72)
    result = signal_trading_age(b)
    assert result.score_contribution == 30
    assert result.direction == "positive"


def test_trading_age_under_1_year_zero_points():
    b = _bundle(trading_age_months=6)
    result = signal_trading_age(b)
    assert result.score_contribution == 0
    assert result.direction == "negative"


def test_trading_age_missing_marks_unavailable():
    b = _bundle(trading_age_months=None)
    result = signal_trading_age(b)
    assert result.available is False
    assert result.score_contribution == 0


def test_cipc_status_active_full_weight():
    b = _bundle(cipc_status="active")
    assert signal_cipc_status(b).score_contribution == 8


def test_cipc_status_deregistered_zero_points():
    b = _bundle(cipc_status="deregistered")
    assert signal_cipc_status(b).score_contribution == 0


def test_sars_non_compliant_zero_points():
    b = _bundle(sars_tax_compliant=False, sars_outstanding_returns=3)
    assert signal_sars_compliance(b).score_contribution == 0


def test_sars_compliant_full_weight():
    b = _bundle(sars_tax_compliant=True, sars_outstanding_returns=0)
    assert signal_sars_compliance(b).score_contribution == 8


def test_revenue_consistency_low_cv_is_excellent():
    b = _bundle(revenue_coefficient_of_variation=0.15)
    result = signal_revenue_consistency(b)
    assert result.normalised == 1.0
    assert result.direction == "positive"


def test_revenue_consistency_high_cv_is_poor():
    b = _bundle(revenue_coefficient_of_variation=1.5)
    result = signal_revenue_consistency(b)
    assert result.normalised < 0.3
    assert result.direction == "negative"


def test_average_monthly_revenue_scales():
    low = signal_average_monthly_revenue(_bundle(average_monthly_revenue=10000))
    high = signal_average_monthly_revenue(_bundle(average_monthly_revenue=600000))
    assert high.normalised > low.normalised


def test_compute_all_signals_returns_all_categories():
    b = _bundle(
        trading_age_months=48, cipc_status="active", vat_registered=True,
        sars_tax_compliant=True, average_monthly_revenue=150000,
        revenue_coefficient_of_variation=0.25, credit_bureau_score=620,
    )
    signals = compute_all_signals(b)
    categories = {s.category for s in signals}
    assert "Business Stability" in categories
    assert "Cash Flow Health" in categories
    assert "Revenue Quality" in categories
    assert "Debt & Obligations" in categories
