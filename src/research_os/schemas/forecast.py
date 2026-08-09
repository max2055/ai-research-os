"""Forecast metadata schema (v0.3, Phase 5).

A Forecast (FCT-YYYYMMDD-NNN) is a falsifiable, dated decision record
(RCP-v03-008, Phase 5 §3): it fixes a question, outcome type, outcome
definition, base rate, probability/range, horizon, resolution criteria and
falsification conditions at a point in time.

Rules encoded here and enforced at the service layer:
- ``open`` requires ``review_status=reviewed``;
- probability applies only to well-defined outcomes; a missing base rate is
  written ``unknown``, never fabricated;
- resolution criteria (outcome_definition / resolution_date /
  resolution_source_requirements) are IMMUTABLE after ``open`` — modifying a
  question creates a new Forecast and supersedes the old one;
- an expired forecast is never retro-edited; it must be closed by a
  ForecastResolution (RES-*).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import Confidence, DateString, ResearchObjectSchema

ForecastId = Annotated[str, StringConstraints(pattern=r"^FCT-\d{8}-\d{3}$")]

# Evidence a forecast may cite (sources/events/impacts/theses) and analysis runs
# that informed it. Cross-object existence is validate_refs' job.
EvidenceReference = Annotated[
    str,
    StringConstraints(
        pattern=r"^(SRC-\d{8}-\d{3}|"
        r"EVT-\d{8}-\d{3}|"
        r"IMP-\d{8}-\d{3}|"
        r"THS-\d{3})$"
    ),
]
RunReference = Annotated[str, StringConstraints(pattern=r"^ANL-\d{8}-\d{3}$")]

OutcomeType = Literal["binary", "categorical", "numeric_range"]
ForecastStatus = Literal["draft", "open", "resolved", "void", "superseded"]


class ForecastSchema(ResearchObjectSchema):
    """A falsifiable, dated forecast decision record."""

    schema_version: Literal[2]
    id: ForecastId
    type: Literal["forecast"]

    scope_ids: list[str] = Field(default_factory=list)
    question: str = Field(min_length=1)
    outcome_type: OutcomeType
    outcome_definition: str = Field(min_length=1)
    base_rate: str = "unknown"  # "unknown" when not computable, never fabricated
    probability: Confidence | None = None  # binary only
    range_low: float | None = None
    range_high: float | None = None
    unit: str = ""
    forecast_as_of: DateString
    horizon: str = ""  # e.g. "quarter", "year", "multi_year"
    resolution_date: DateString
    resolution_source_requirements: list[str] = Field(default_factory=list)
    evidence_ids: list[EvidenceReference] = Field(default_factory=list)
    analysis_run_ids: list[RunReference] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    alternative_outcomes: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(default_factory=list)
    status: ForecastStatus = "draft"

    # review_status inherited; open requires reviewed (validation.py).
