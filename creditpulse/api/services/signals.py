from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from creditpulse.ml.features import FeatureBundle


@dataclass
class SignalResult:
    category: str
    name: str
    key: str
    value: float
    normalised: float
    weight: float
    score_contribution: float
    direction: str
    explanation: str
    available: bool = True


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _direction(normalised: float, available: bool) -> str:
    if not available:
        return "unknown"
    if normalised >= 0.66:
        return "positive"
    if normalised >= 0.33:
        return "neutral"
    return "negative"


def signal_trading_age(b: FeatureBundle) -> SignalResult:
    months = b.trading_age_months
    if months is None:
        return SignalResult(
            category="Business Stability",
            name="Trading age",
            key="trading_age",
            value=0.0,
            normalised=0.5,
            weight=10,
            score_contribution=0.0,
            direction="unknown",
            explanation="Trading age unavailable — CIPC registration date not found",
            available=False,
        )
    years = months / 12.0
    if years < 1:
        norm, pts = 0.0, 0
    elif years < 2:
        norm, pts = 0.33, 10
    elif years < 5:
        norm, pts = 0.66, 20
    else:
        norm, pts = 1.0, 30
    explanation = (
        f"Business has been trading for {years:.1f} years — "
        + ("less than 1 year is high risk" if years < 1
           else "established but still building track record" if years < 2
           else "well-established" if years < 5
           else "mature business with long track record")
    )
    return SignalResult(
        category="Business Stability",
        name="Trading age",
        key="trading_age",
        value=years,
        normalised=norm,
        weight=10,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_cipc_status(b: FeatureBundle) -> SignalResult:
    status = (b.cipc_status or "").lower()
    available = status != ""
    if not available:
        norm = 0.5
        explanation = "CIPC status unavailable"
    elif status == "active" or status == "in_business":
        norm = 1.0
        explanation = "Business is active and in good standing on CIPC"
    elif status in ("deregistered", "in_liquidation", "final_deregistration"):
        norm = 0.0
        explanation = f"CIPC status is {status} — hard negative signal"
    else:
        norm = 0.3
        explanation = f"CIPC status is {status} — review required"
    pts = norm * 8
    return SignalResult(
        category="Business Stability",
        name="CIPC status",
        key="cipc_status",
        value=1.0 if norm == 1.0 else 0.0,
        normalised=norm,
        weight=8,
        score_contribution=pts,
        direction=_direction(norm, available),
        explanation=explanation,
        available=available,
    )


def signal_vat_registered(b: FeatureBundle) -> SignalResult:
    if b.vat_registered is None:
        return SignalResult(
            category="Business Stability",
            name="VAT registration",
            key="vat_registered",
            value=0.0,
            normalised=0.5,
            weight=2,
            score_contribution=0.0,
            direction="unknown",
            explanation="VAT registration status unavailable",
            available=False,
        )
    registered = bool(b.vat_registered)
    norm = 1.0 if registered else 0.3
    pts = 2 if registered else 0
    explanation = (
        "VAT registered — indicates turnover above R1m threshold"
        if registered
        else "Not VAT registered — either under R1m turnover or non-compliant"
    )
    return SignalResult(
        category="Business Stability",
        name="VAT registration",
        key="vat_registered",
        value=1.0 if registered else 0.0,
        normalised=norm,
        weight=2,
        score_contribution=pts,
        direction="positive" if registered else "neutral",
        explanation=explanation,
    )


def signal_sars_compliance(b: FeatureBundle) -> SignalResult:
    if b.sars_tax_compliant is None:
        return SignalResult(
            category="Business Stability",
            name="SARS tax compliance",
            key="sars_tax_compliant",
            value=0.0,
            normalised=0.5,
            weight=8,
            score_contribution=0.0,
            direction="unknown",
            explanation="SARS compliance could not be verified",
            available=False,
        )
    compliant = b.sars_tax_compliant
    outstanding = b.sars_outstanding_returns or 0
    if compliant:
        norm, pts = 1.0, 8
        explanation = "Business is tax compliant with no outstanding returns"
    else:
        norm, pts = 0.0, 0
        explanation = f"Tax non-compliant — {outstanding} outstanding return(s). Penalty will be applied."
    return SignalResult(
        category="Business Stability",
        name="SARS tax compliance",
        key="sars_tax_compliant",
        value=1.0 if compliant else 0.0,
        normalised=norm,
        weight=8,
        score_contribution=pts,
        direction="positive" if compliant else "negative",
        explanation=explanation,
    )


def signal_director_history(b: FeatureBundle) -> SignalResult:
    if b.director_adverse_flag is None:
        return SignalResult(
            category="Business Stability",
            name="Director history",
            key="director_history",
            value=0.0,
            normalised=0.5,
            weight=2,
            score_contribution=0.0,
            direction="unknown",
            explanation="Director background check unavailable",
            available=False,
        )
    clean = not b.director_adverse_flag
    norm = 1.0 if clean else 0.1
    pts = 2 if clean else 0
    explanation = (
        "Directors have clean record — no prior liquidations or adverse findings"
        if clean
        else "One or more directors flagged with adverse history (prior liquidation / judgement)"
    )
    return SignalResult(
        category="Business Stability",
        name="Director history",
        key="director_history",
        value=1.0 if clean else 0.0,
        normalised=norm,
        weight=2,
        score_contribution=pts,
        direction="positive" if clean else "negative",
        explanation=explanation,
    )


def signal_average_monthly_revenue(b: FeatureBundle) -> SignalResult:
    revenue = b.average_monthly_revenue
    if revenue is None:
        return SignalResult(
            category="Cash Flow Health",
            name="Average monthly revenue",
            key="average_monthly_revenue",
            value=0.0,
            normalised=0.5,
            weight=8,
            score_contribution=0.0,
            direction="unknown",
            explanation="Revenue data unavailable — no bank statement provided",
            available=False,
        )
    if revenue < 20000:
        norm = 0.15
    elif revenue < 100000:
        norm = 0.45
    elif revenue < 500000:
        norm = 0.75
    else:
        norm = 1.0
    pts = norm * 8
    explanation = f"Average monthly revenue of R{revenue:,.0f} "
    explanation += (
        "— very small operation, limited repayment capacity" if revenue < 20000
        else "— small but viable cash flow" if revenue < 100000
        else "— healthy revenue base" if revenue < 500000
        else "— strong revenue base"
    )
    return SignalResult(
        category="Cash Flow Health",
        name="Average monthly revenue",
        key="average_monthly_revenue",
        value=revenue,
        normalised=norm,
        weight=8,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_revenue_consistency(b: FeatureBundle) -> SignalResult:
    cv = b.revenue_coefficient_of_variation
    if cv is None:
        return SignalResult(
            category="Cash Flow Health",
            name="Revenue consistency",
            key="revenue_consistency",
            value=0.0,
            normalised=0.5,
            weight=8,
            score_contribution=0.0,
            direction="unknown",
            explanation="Revenue consistency unavailable — no statement data",
            available=False,
        )
    if cv < 0.3:
        norm = 1.0
        quality = "excellent — highly consistent"
    elif cv < 0.6:
        norm = 0.7
        quality = "good — moderate variation"
    elif cv < 1.0:
        norm = 0.4
        quality = "variable — worth investigating"
    else:
        norm = 0.15
        quality = "poor — highly erratic"
    pts = norm * 8
    explanation = f"Monthly revenue varied by {cv * 100:.0f}% — {quality}"
    return SignalResult(
        category="Cash Flow Health",
        name="Revenue consistency",
        key="revenue_consistency",
        value=cv,
        normalised=norm,
        weight=8,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_positive_cashflow_months(b: FeatureBundle) -> SignalResult:
    ratio = b.positive_cash_flow_months
    if ratio is None:
        return SignalResult(
            category="Cash Flow Health",
            name="Positive cash flow months",
            key="positive_cashflow_months",
            value=0.0,
            normalised=0.5,
            weight=7,
            score_contribution=0.0,
            direction="unknown",
            explanation="Cash flow history unavailable",
            available=False,
        )
    norm = _clamp01(ratio)
    pts = norm * 7
    pct = ratio * 100
    explanation = (
        f"{pct:.0f}% of months showed positive net cash flow — "
        + ("very healthy" if pct >= 80
           else "acceptable" if pct >= 60
           else "concerning — frequent loss-making months")
    )
    return SignalResult(
        category="Cash Flow Health",
        name="Positive cash flow months",
        key="positive_cashflow_months",
        value=ratio,
        normalised=norm,
        weight=7,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_average_bank_balance(b: FeatureBundle) -> SignalResult:
    balance = b.average_closing_balance_3m
    revenue = b.average_monthly_revenue
    if balance is None or revenue is None or revenue <= 0:
        return SignalResult(
            category="Cash Flow Health",
            name="Average bank balance",
            key="average_bank_balance",
            value=0.0,
            normalised=0.5,
            weight=5,
            score_contribution=0.0,
            direction="unknown",
            explanation="Bank balance data unavailable",
            available=balance is not None,
        )
    ratio = balance / revenue if revenue else 0
    if ratio < 0.05:
        norm = 0.15
    elif ratio < 0.2:
        norm = 0.5
    elif ratio < 0.5:
        norm = 0.85
    else:
        norm = 1.0
    pts = norm * 5
    explanation = (
        f"3-month average closing balance of R{balance:,.0f} "
        f"({ratio * 100:.0f}% of monthly turnover) — "
        + ("very thin cash buffer" if ratio < 0.05
           else "adequate working capital" if ratio < 0.2
           else "strong cash reserves")
    )
    return SignalResult(
        category="Cash Flow Health",
        name="Average bank balance",
        key="average_bank_balance",
        value=balance,
        normalised=norm,
        weight=5,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_bounce_rate(b: FeatureBundle) -> SignalResult:
    br = b.bounce_rate
    if br is None:
        return SignalResult(
            category="Cash Flow Health",
            name="Debit order bounce rate",
            key="bounce_rate",
            value=0.0,
            normalised=0.5,
            weight=4,
            score_contribution=0.0,
            direction="unknown",
            explanation="Bounce rate unavailable",
            available=False,
        )
    if br < 0.01:
        norm = 1.0
    elif br < 0.05:
        norm = 0.7
    elif br < 0.15:
        norm = 0.3
    else:
        norm = 0.05
    pts = norm * 4
    explanation = (
        f"{br * 100:.1f}% of debit orders bounced in the last 6 months — "
        + ("clean record" if br < 0.01
           else "minor disruption" if br < 0.05
           else "frequent bounces, cash flow management issues" if br < 0.15
           else "severe payment reliability issues")
    )
    return SignalResult(
        category="Cash Flow Health",
        name="Debit order bounce rate",
        key="bounce_rate",
        value=br,
        normalised=norm,
        weight=4,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_salary_run_regularity(b: FeatureBundle) -> SignalResult:
    if b.salary_run_regularity is None:
        return SignalResult(
            category="Cash Flow Health",
            name="Salary run regularity",
            key="salary_run_regularity",
            value=0.0,
            normalised=0.5,
            weight=3,
            score_contribution=0.0,
            direction="unknown",
            explanation="Salary run pattern unavailable",
            available=False,
        )
    regular = bool(b.salary_run_regularity)
    norm = 1.0 if regular else 0.4
    pts = 3 if regular else 1
    explanation = (
        "Regular monthly staff payments detected — signals real operating business"
        if regular
        else "No regular salary run detected — could be owner-operated or non-employing"
    )
    return SignalResult(
        category="Cash Flow Health",
        name="Salary run regularity",
        key="salary_run_regularity",
        value=1.0 if regular else 0.0,
        normalised=norm,
        weight=3,
        score_contribution=pts,
        direction="positive" if regular else "neutral",
        explanation=explanation,
    )


def signal_revenue_source_diversity(b: FeatureBundle) -> SignalResult:
    n = b.revenue_source_diversity
    if n is None:
        return SignalResult(
            category="Revenue Quality",
            name="Revenue source diversity",
            key="revenue_source_diversity",
            value=0.0,
            normalised=0.5,
            weight=6,
            score_contribution=0.0,
            direction="unknown",
            explanation="Customer diversity data unavailable",
            available=False,
        )
    if n <= 1:
        norm = 0.1
    elif n <= 3:
        norm = 0.4
    elif n <= 7:
        norm = 0.75
    else:
        norm = 1.0
    pts = norm * 6
    explanation = (
        f"{n} distinct revenue sources in last 6 months — "
        + ("single-client concentration risk" if n <= 1
           else "limited diversity, some concentration risk" if n <= 3
           else "well diversified" if n <= 7
           else "highly diversified customer base")
    )
    return SignalResult(
        category="Revenue Quality",
        name="Revenue source diversity",
        key="revenue_source_diversity",
        value=n,
        normalised=norm,
        weight=6,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_largest_client_concentration(b: FeatureBundle) -> SignalResult:
    conc = b.largest_client_concentration
    if conc is None:
        return SignalResult(
            category="Revenue Quality",
            name="Largest client concentration",
            key="largest_client_concentration",
            value=0.0,
            normalised=0.5,
            weight=5,
            score_contribution=0.0,
            direction="unknown",
            explanation="Client concentration unavailable",
            available=False,
        )
    if conc < 0.2:
        norm = 1.0
    elif conc < 0.4:
        norm = 0.7
    elif conc < 0.6:
        norm = 0.35
    else:
        norm = 0.1
    pts = norm * 5
    explanation = (
        f"Largest single client accounts for {conc * 100:.0f}% of revenue — "
        + ("well distributed" if conc < 0.2
           else "some concentration" if conc < 0.4
           else "material concentration risk" if conc < 0.6
           else "severe concentration — loss of top client would be catastrophic")
    )
    return SignalResult(
        category="Revenue Quality",
        name="Largest client concentration",
        key="largest_client_concentration",
        value=conc,
        normalised=norm,
        weight=5,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_repeat_customer_rate(b: FeatureBundle) -> SignalResult:
    rate = b.repeat_customer_rate
    if rate is None:
        return SignalResult(
            category="Revenue Quality",
            name="Repeat customer rate",
            key="repeat_customer_rate",
            value=0.0,
            normalised=0.5,
            weight=5,
            score_contribution=0.0,
            direction="unknown",
            explanation="Repeat customer data unavailable",
            available=False,
        )
    norm = _clamp01(rate)
    pts = norm * 5
    explanation = (
        f"{rate * 100:.0f}% of customers have paid in multiple months — "
        + ("high stickiness, recurring revenue pattern" if rate >= 0.6
           else "moderate recurring base" if rate >= 0.3
           else "mostly one-off or project revenue")
    )
    return SignalResult(
        category="Revenue Quality",
        name="Repeat customer rate",
        key="repeat_customer_rate",
        value=rate,
        normalised=norm,
        weight=5,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_invoice_payment_lag(b: FeatureBundle) -> SignalResult:
    lag = b.invoice_payment_lag_days
    if lag is None:
        return SignalResult(
            category="Revenue Quality",
            name="Invoice payment lag",
            key="invoice_payment_lag",
            value=0.0,
            normalised=0.5,
            weight=4,
            score_contribution=0.0,
            direction="unknown",
            explanation="Invoice payment timing unavailable",
            available=False,
        )
    if lag <= 15:
        norm = 1.0
    elif lag <= 30:
        norm = 0.75
    elif lag <= 60:
        norm = 0.4
    else:
        norm = 0.15
    pts = norm * 4
    explanation = (
        f"Average invoice payment lag of {lag:.0f} days — "
        + ("excellent, customers pay quickly" if lag <= 15
           else "standard terms honoured" if lag <= 30
           else "slow payment cycle — stretches working capital" if lag <= 60
           else "very slow collections — liquidity pressure")
    )
    return SignalResult(
        category="Revenue Quality",
        name="Invoice payment lag",
        key="invoice_payment_lag",
        value=lag,
        normalised=norm,
        weight=4,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_credit_bureau_score(b: FeatureBundle) -> SignalResult:
    s = b.credit_bureau_score
    if s is None:
        return SignalResult(
            category="Debt & Obligations",
            name="Credit bureau score",
            key="credit_bureau_score",
            value=0.0,
            normalised=0.5,
            weight=6,
            score_contribution=0.0,
            direction="unknown",
            explanation="Credit bureau score unavailable",
            available=False,
        )
    norm = _clamp01(s / 1000.0)
    pts = norm * 6
    explanation = (
        f"Commercial bureau score of {s}/1000 — "
        + ("excellent" if s >= 750
           else "good" if s >= 600
           else "average" if s >= 450
           else "sub-prime — historical repayment issues")
    )
    return SignalResult(
        category="Debt & Obligations",
        name="Credit bureau score",
        key="credit_bureau_score",
        value=s,
        normalised=norm,
        weight=6,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_existing_loan_obligations(b: FeatureBundle) -> SignalResult:
    monthly = b.detected_loan_repayments_monthly
    if monthly is None:
        return SignalResult(
            category="Debt & Obligations",
            name="Existing loan obligations",
            key="existing_loan_obligations",
            value=0.0,
            normalised=0.5,
            weight=3,
            score_contribution=0.0,
            direction="unknown",
            explanation="Existing loan obligations could not be detected",
            available=False,
        )
    revenue = b.average_monthly_revenue or 0
    ratio = monthly / revenue if revenue else 0
    if ratio == 0:
        norm = 0.9
        explanation = "No existing loan repayments detected — unencumbered cash flow"
    elif ratio < 0.1:
        norm = 0.8
        explanation = f"Manageable debt service — R{monthly:,.0f}/month ({ratio * 100:.0f}% of revenue)"
    elif ratio < 0.3:
        norm = 0.5
        explanation = f"Moderate debt service — R{monthly:,.0f}/month ({ratio * 100:.0f}% of revenue)"
    else:
        norm = 0.15
        explanation = f"Heavy debt load — R{monthly:,.0f}/month ({ratio * 100:.0f}% of revenue)"
    pts = norm * 3
    return SignalResult(
        category="Debt & Obligations",
        name="Existing loan obligations",
        key="existing_loan_obligations",
        value=monthly,
        normalised=norm,
        weight=3,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_debt_service_coverage(b: FeatureBundle) -> SignalResult:
    revenue = b.average_monthly_revenue
    monthly = b.detected_loan_repayments_monthly
    if revenue is None or monthly is None:
        return SignalResult(
            category="Debt & Obligations",
            name="Debt service coverage",
            key="debt_service_coverage",
            value=0.0,
            normalised=0.5,
            weight=3,
            score_contribution=0.0,
            direction="unknown",
            explanation="Debt service coverage cannot be computed",
            available=False,
        )
    if monthly <= 0:
        norm = 1.0
        coverage = float("inf")
        explanation = "No current debt service — full cash flow available"
    else:
        coverage = revenue / monthly
        if coverage >= 10:
            norm = 1.0
        elif coverage >= 4:
            norm = 0.75
        elif coverage >= 2:
            norm = 0.4
        else:
            norm = 0.1
        explanation = (
            f"Debt service coverage ratio of {coverage:.1f}x — "
            + ("very strong" if coverage >= 10
               else "healthy buffer" if coverage >= 4
               else "tight coverage" if coverage >= 2
               else "stressed coverage, high repayment risk")
        )
    pts = norm * 3
    return SignalResult(
        category="Debt & Obligations",
        name="Debt service coverage",
        key="debt_service_coverage",
        value=0 if coverage == float("inf") else coverage,
        normalised=norm,
        weight=3,
        score_contribution=pts,
        direction=_direction(norm, True),
        explanation=explanation,
    )


def signal_judgements_liens(b: FeatureBundle) -> SignalResult:
    n = b.adverse_listings_count
    if n is None:
        return SignalResult(
            category="Debt & Obligations",
            name="Judgements & adverse listings",
            key="judgements_liens",
            value=0.0,
            normalised=0.5,
            weight=3,
            score_contribution=0.0,
            direction="unknown",
            explanation="Adverse listings data unavailable",
            available=False,
        )
    if n == 0:
        norm, pts = 1.0, 3
        explanation = "No judgements, defaults or adverse listings on record"
    elif n <= 2:
        norm, pts = 0.3, 1
        explanation = f"{n} adverse listing(s) — merits investigation"
    else:
        norm, pts = 0.0, 0
        explanation = f"{n} adverse listings — serious credit history concerns"
    return SignalResult(
        category="Debt & Obligations",
        name="Judgements & adverse listings",
        key="judgements_liens",
        value=n,
        normalised=norm,
        weight=3,
        score_contribution=pts,
        direction="positive" if n == 0 else "negative",
        explanation=explanation,
    )


SIGNAL_FUNCTIONS: List[Callable[[FeatureBundle], SignalResult]] = [
    signal_trading_age,
    signal_cipc_status,
    signal_vat_registered,
    signal_sars_compliance,
    signal_director_history,
    signal_average_monthly_revenue,
    signal_revenue_consistency,
    signal_positive_cashflow_months,
    signal_average_bank_balance,
    signal_bounce_rate,
    signal_salary_run_regularity,
    signal_revenue_source_diversity,
    signal_largest_client_concentration,
    signal_repeat_customer_rate,
    signal_invoice_payment_lag,
    signal_credit_bureau_score,
    signal_existing_loan_obligations,
    signal_debt_service_coverage,
    signal_judgements_liens,
]


def compute_all_signals(features: FeatureBundle) -> List[SignalResult]:
    return [fn(features) for fn in SIGNAL_FUNCTIONS]
