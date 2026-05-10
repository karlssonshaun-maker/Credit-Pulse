from __future__ import annotations

from dataclasses import dataclass
from typing import List

from creditpulse.api.services.signals import SignalResult, compute_all_signals
from creditpulse.db.enums import Confidence, Recommendation, RiskTier
from creditpulse.ml.features import FeatureBundle


@dataclass
class ScoringResult:
    score: int
    risk_tier: RiskTier
    recommendation: Recommendation
    confidence: Confidence
    signals: List[SignalResult]
    penalty_notes: List[str]


HARD_PENALTY_MULTIPLIERS = {
    "deregistered_cipc": 0.3,
    "liquidation_cipc": 0.2,
    "tax_noncompliant": 0.75,
    "director_adverse": 0.85,
    "severe_adverse_listings": 0.7,
}


def derive_risk_tier(score: int) -> RiskTier:
    if score >= 80:
        return RiskTier.VERY_LOW
    if score >= 65:
        return RiskTier.LOW
    if score >= 50:
        return RiskTier.MEDIUM
    if score >= 35:
        return RiskTier.HIGH
    return RiskTier.VERY_HIGH


def derive_recommendation(tier: RiskTier, features: FeatureBundle) -> Recommendation:
    if tier in (RiskTier.VERY_LOW, RiskTier.LOW):
        return Recommendation.APPROVE
    if tier == RiskTier.MEDIUM:
        return Recommendation.REVIEW
    return Recommendation.DECLINE


def derive_confidence(features: FeatureBundle) -> Confidence:
    sources = set(features.available_sources)
    has_statement = "bank_statement" in sources
    has_cipc = "cipc" in sources
    has_sars = "sars" in sources
    has_bureau = "transunion" in sources
    count = sum([has_statement, has_cipc, has_sars, has_bureau])
    if count >= 4:
        return Confidence.HIGH
    if count >= 3 and has_statement:
        return Confidence.HIGH
    if count >= 2:
        return Confidence.MEDIUM
    return Confidence.LOW


def calculate_score(features: FeatureBundle) -> ScoringResult:
    signals = compute_all_signals(features)
    raw_score = sum(s.score_contribution for s in signals)

    penalty_notes: List[str] = []
    multiplier = 1.0

    cipc_status = (features.cipc_status or "").lower()
    if cipc_status == "deregistered" or cipc_status == "final_deregistration":
        multiplier *= HARD_PENALTY_MULTIPLIERS["deregistered_cipc"]
        penalty_notes.append("CIPC deregistered — severe penalty applied")
    elif cipc_status == "in_liquidation":
        multiplier *= HARD_PENALTY_MULTIPLIERS["liquidation_cipc"]
        penalty_notes.append("In liquidation — severe penalty applied")

    if features.sars_tax_compliant is False:
        multiplier *= HARD_PENALTY_MULTIPLIERS["tax_noncompliant"]
        penalty_notes.append("Tax non-compliant — 25% penalty applied")

    if features.director_adverse_flag:
        multiplier *= HARD_PENALTY_MULTIPLIERS["director_adverse"]
        penalty_notes.append("Adverse director history — 15% penalty applied")

    if (features.adverse_listings_count or 0) >= 3:
        multiplier *= HARD_PENALTY_MULTIPLIERS["severe_adverse_listings"]
        penalty_notes.append("Multiple adverse listings — 30% penalty applied")

    final_score = int(round(max(0.0, min(100.0, raw_score * multiplier))))

    tier = derive_risk_tier(final_score)
    if features.loan_amount_requested and features.average_monthly_revenue:
        monthly_payment_est = features.loan_amount_requested / max(1, features.loan_term_months or 12)
        revenue_ratio = monthly_payment_est / features.average_monthly_revenue
        if revenue_ratio > 0.5 and tier == RiskTier.LOW:
            tier = RiskTier.MEDIUM
            penalty_notes.append("Loan payment exceeds 50% of monthly revenue — tier adjusted to medium")
        elif revenue_ratio > 0.75:
            tier = RiskTier.HIGH
            penalty_notes.append("Loan payment exceeds 75% of monthly revenue — tier adjusted to high")

    recommendation = derive_recommendation(tier, features)
    confidence = derive_confidence(features)

    return ScoringResult(
        score=final_score,
        risk_tier=tier,
        recommendation=recommendation,
        confidence=confidence,
        signals=signals,
        penalty_notes=penalty_notes,
    )
