"""Forecast Resolution metadata schema (v0.3, Phase 5).

A ForecastResolution (RES-YYYYMMDD-NNN) closes a Forecast by recording the
observed outcome against the frozen resolution criteria (RCP-v03-008,
Phase 5 §4). It is append-only: the resolved Forecast is never retro-edited —
the Resolution is a new object that references it.

``ambiguous`` and ``void`` must state a reason; they are not used to drop
failed forecasts to inflate accuracy. ``source_ids`` must reference reviewed
Sources (validation.py).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateString, ResearchObjectSchema

ResolutionId = Annotated[str, StringConstraints(pattern=r"^RES-\d{8}-\d{3}$")]
ForecastRef = Annotated[str, StringConstraints(pattern=r"^FCT-\d{8}-\d{3}$")]
SourceRef = Annotated[str, StringConstraints(pattern=r"^SRC-\d{8}-\d{3}$")]

ResolutionDecision = Literal["correct", "incorrect", "partial", "void", "ambiguous"]
ScoringMethod = Literal["brier", "log_score", "interval_coverage", "manual", "none"]


class ForecastResolutionSchema(ResearchObjectSchema):
    """Append-only record closing a Forecast against its frozen criteria."""

    schema_version: Literal[2]
    id: ResolutionId
    type: Literal["forecast_resolution"]

    forecast_id: ForecastRef
    resolved_at: DateString
    outcome: str = ""  # human-readable observed outcome
    observed_value: str | None = None
    source_ids: list[SourceRef] = Field(default_factory=list)
    decision: ResolutionDecision
    resolution_reason: str = Field(min_length=1)
    scoring_method: ScoringMethod = "manual"
    score: float | None = None
    reviewer: str = ""

    # review_status inherited; a reviewed resolution must have >=1 reviewed Source.
