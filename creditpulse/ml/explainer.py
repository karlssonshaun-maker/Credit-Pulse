from __future__ import annotations

from typing import Dict, List

from creditpulse.api.services.signals import SignalResult
from creditpulse.ml.rule_engine import ScoringResult


def build_signal_breakdown(result: ScoringResult) -> List[Dict]:
    return [
        {
            "category": s.category,
            "name": s.name,
            "key": s.key,
            "value": s.value,
            "normalised": round(s.normalised, 3),
            "weight": s.weight,
            "score_contribution": round(s.score_contribution, 2),
            "direction": s.direction,
            "explanation": s.explanation,
            "available": s.available,
        }
        for s in result.signals
    ]


def top_drivers(signals: List[SignalResult], limit: int = 3) -> Dict[str, List[Dict]]:
    positive = [s for s in signals if s.direction == "positive" and s.available]
    negative = [s for s in signals if s.direction == "negative" and s.available]

    positive.sort(key=lambda s: s.score_contribution, reverse=True)
    negative.sort(key=lambda s: s.weight - s.score_contribution, reverse=True)

    return {
        "top_strengths": [
            {"name": s.name, "explanation": s.explanation, "contribution": round(s.score_contribution, 2)}
            for s in positive[:limit]
        ],
        "top_concerns": [
            {
                "name": s.name,
                "explanation": s.explanation,
                "missed_points": round(s.weight - s.score_contribution, 2),
            }
            for s in negative[:limit]
        ],
    }
