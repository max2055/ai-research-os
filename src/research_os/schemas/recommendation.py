"""Recommendation metadata schema (v0.3, Phase 5).

A Recommendation (REC-YYYYMMDD-NNN) is the highest-tier research output
(RCP-v03-009, Phase 5 §7). Design rules:

- Company-level posture and security-level direction are separated; a
  Recommendation references a company and optionally a security.
- The highest default posture is ``investment_candidate`` — v0.3 does NOT emit
  buy/sell/position size; that requires a separate Portfolio & Execution RCP.
- ``active`` requires human review; the system never trades.
- ``falsification_conditions`` and ``catalysts`` are monitoring hooks so a
  recommendation can be closed/superseded by evidence, not by fiat.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateString, ResearchObjectSchema

RecommendationId = Annotated[str, StringConstraints(pattern=r"^REC-\d{8}-\d{3}$")]
CompanyRef = Annotated[
    str, StringConstraints(pattern=r"^COM-[a-z0-9]+(?:-[a-z0-9]+)*$")
]
SecurityRef = Annotated[
    str,
    StringConstraints(pattern=r"^INS-[A-Z]{2,6}-[A-Z0-9][A-Z0-9.\-]*$"),
]
ValuationRef = Annotated[str, StringConstraints(pattern=r"^VAL-\d{8}-\d{3}$")]
ForecastRef = Annotated[str, StringConstraints(pattern=r"^FCT-\d{8}-\d{3}$")]
ThesisRef = Annotated[str, StringConstraints(pattern=r"^THS-\d{3}$")]
EvidenceRef = Annotated[
    str,
    StringConstraints(pattern=r"^(SRC-\d{8}-\d{3}|EVT-\d{8}-\d{3}|IMP-\d{8}-\d{3})$"),
]
RunRef = Annotated[str, StringConstraints(pattern=r"^ANL-\d{8}-\d{3}$")]

Posture = Literal["avoid", "watch", "research", "investment_candidate"]
Direction = Literal["positive", "neutral", "negative", "uncertain"]
Conviction = Literal["low", "medium", "high"]
RecommendationStatus = Literal["draft", "active", "closed", "superseded"]


class RecommendationSchema(ResearchObjectSchema):
    """A human-approved, evidence-backed research posture on a company/security."""

    schema_version: Literal[2]
    id: RecommendationId
    type: Literal["recommendation"]

    company_id: CompanyRef
    security_id: SecurityRef | None = None
    as_of: DateString
    time_horizon: str = ""
    research_posture: Posture = "research"
    direction: Direction = "uncertain"
    conviction: Conviction = "low"
    valuation_snapshot_id: ValuationRef | None = None
    forecast_ids: list[ForecastRef] = Field(default_factory=list)
    thesis_ids: list[ThesisRef] = Field(default_factory=list)
    evidence_ids: list[EvidenceRef] = Field(default_factory=list)
    analysis_run_ids: list[RunRef] = Field(default_factory=list)
    expected_case: str = ""
    downside_case: str = ""
    upside_case: str = ""
    catalysts: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    freshness_date: DateString
    status: RecommendationStatus = "draft"

    # review_status inherited; active requires reviewed (validation.py).
