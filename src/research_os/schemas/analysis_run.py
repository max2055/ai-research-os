"""Analysis Run metadata schema (v0.3, Phase 4).

An Analysis Run (ANL-YYYYMMDD-NNN) is the frozen product of one mode execution
(RCP-v03-007, Phase 4 §3): it records the mode version, inputs, as-of snapshot,
model provider/id/parameters, and prompt/output hashes so the run is
reproducible and auditable. A run is NOT a Thesis or Recommendation; only a
reviewed run may feed a Report.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateOrUnknown, ResearchObjectSchema

RunId = Annotated[str, StringConstraints(pattern=r"^ANL-\d{8}-\d{3}$")]


class AnalysisRunSchema(ResearchObjectSchema):
    """A frozen, mode-versioned execution of one analysis view."""

    schema_version: Literal[2]
    id: RunId
    type: Literal["analysis_run"]

    mode_id: str  # MOD-ANL-<slug>-vN
    scope_ids: list[str] = Field(default_factory=list)
    as_of: DateOrUnknown
    input_source_ids: list[str] = Field(default_factory=list)
    input_event_ids: list[str] = Field(default_factory=list)
    input_impact_ids: list[str] = Field(default_factory=list)
    input_thesis_ids: list[str] = Field(default_factory=list)
    input_snapshot_hash: str = ""
    model_provider: str = ""
    model_id: str = ""
    model_parameters: dict[str, str] = Field(default_factory=dict)
    prompt_hash: str = ""
    output_hash: str = ""
    generation_method: str = ""
    status: Literal["draft", "completed", "failed", "superseded"] = "draft"

    # review_status inherited; only a reviewed run may enter a Report.
