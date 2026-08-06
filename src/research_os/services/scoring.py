"""B-017 Candidate scoring v1.

Deterministic, explainable scoring across 8 dimensions. Scores are
proposals only (Phase 2 §5.3): sub-scores and reason codes are preserved,
never a bare total. Weights are configurable and versioned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SCORING_VERSION = 1

# Configurable, versioned weights (Phase 2 §5.3: 权重必须配置化、版本化).
# Positive dimensions sum to 1.0; penalties are subtracted after weighting.
DEFAULT_WEIGHTS: dict[str, float] = {
    "scope_relevance": 0.30,
    "source_quality": 0.20,
    "novelty": 0.15,
    "materiality": 0.15,
    "time_sensitivity": 0.10,
    "evidence_potential": 0.10,
}
_PENALTY_KEYS = ("duplication_penalty", "uncertainty_penalty")

_GRADE_SCORE = {"A": 1.0, "B": 0.8, "C": 0.5, "D": 0.2}
_MATERIALITY_WORDS = (
    "revenue",
    "earnings",
    "contract",
    "billion",
    "million",
    "production",
    "capacity",
    "price",
    "acquisition",
    "partnership",
    "supply",
    "regulation",
    "export",
    "guidance",
    "record",
)
_TIME_SENSITIVE_WORDS = ("8-k", "10-q", "earnings", "guidance", "recall", "breach")


@dataclass(frozen=True)
class ScoreWeights:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def weighted(self, subscores: dict[str, float]) -> float:
        positive = sum(
            self.weights.get(key, 0.0) * value
            for key, value in subscores.items()
            if key not in _PENALTY_KEYS
        )
        penalties = sum(subscores.get(key, 0.0) for key in _PENALTY_KEYS)
        return round(max(0.0, positive - penalties), 4)


def score_candidate(
    *,
    title: str,
    source_grade: str = "B",
    entity_status: str = "unknown",
    sector_count: int = 0,
    is_duplicate_representative: bool = True,
    cluster_size: int = 1,
    channel_type: str = "web_page",
    weights: ScoreWeights | None = None,
) -> dict[str, Any]:
    """Score one candidate. Returns sub-scores, priority, reasons, version."""
    weights = weights or ScoreWeights()
    title_lower = title.lower()

    # scope_relevance: matched entity/sector coverage
    scope_relevance = 0.2
    reasons: list[str] = []
    if entity_status == "matched":
        scope_relevance = 0.8
        reasons.append("scope_relevance: matched entity")
    elif entity_status == "ambiguous":
        scope_relevance = 0.5
        reasons.append("scope_relevance: ambiguous entity")
    if sector_count > 0:
        scope_relevance = min(1.0, scope_relevance + 0.2)
        reasons.append(f"scope_relevance: {sector_count} sector(s)")

    # source_quality: channel grade
    source_quality = _GRADE_SCORE.get(source_grade.upper(), 0.5)
    reasons.append(f"source_quality: grade {source_grade.upper()}")

    # novelty: representative of a large duplicate cluster is lower novelty
    novelty = 0.8 if cluster_size == 1 else max(0.2, 0.8 - 0.15 * (cluster_size - 1))
    reasons.append(f"novelty: cluster_size={cluster_size}")

    # materiality: keyword presence in title
    materiality_hits = [w for w in _MATERIALITY_WORDS if w in title_lower]
    materiality = min(1.0, 0.2 + 0.2 * len(materiality_hits))
    if materiality_hits:
        reasons.append(f"materiality: {materiality_hits}")

    # time_sensitivity: earnings/regulatory filings
    time_hits = [w for w in _TIME_SENSITIVE_WORDS if w in title_lower]
    time_sensitivity = min(1.0, 0.2 + 0.3 * len(time_hits))
    if time_hits:
        reasons.append(f"time_sensitivity: {time_hits}")

    # evidence_potential: concrete numbers or announcement verbs
    has_number = bool(re.search(r"\d", title))
    evidence_potential = 0.5 if has_number else 0.3
    reasons.append(f"evidence_potential: has_number={has_number}")

    # duplication_penalty: non-representative member of a cluster
    duplication_penalty = 0.0 if is_duplicate_representative else 0.5
    if not is_duplicate_representative:
        reasons.append("duplication_penalty: non-representative in cluster")

    # uncertainty_penalty: unknown/ambiguous entity or no sector
    uncertainty_penalty = 0.0
    if entity_status == "unknown":
        uncertainty_penalty += 0.5
        reasons.append("uncertainty_penalty: unknown entity")
    if sector_count == 0:
        uncertainty_penalty += 0.3
        reasons.append("uncertainty_penalty: no sector")

    subscores: dict[str, float] = {
        "scope_relevance": round(scope_relevance, 3),
        "source_quality": round(source_quality, 3),
        "novelty": round(novelty, 3),
        "materiality": round(materiality, 3),
        "time_sensitivity": round(time_sensitivity, 3),
        "evidence_potential": round(evidence_potential, 3),
        "duplication_penalty": round(duplication_penalty, 3),
        "uncertainty_penalty": round(uncertainty_penalty, 3),
    }
    priority = weights.weighted(subscores)
    return {
        "scoring_version": SCORING_VERSION,
        "subscores": subscores,
        "priority_score": priority,
        "reason_codes": reasons,
        "model": "deterministic-v1",
    }
