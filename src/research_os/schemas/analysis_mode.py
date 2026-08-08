"""Analysis Mode Definition metadata schema (v0.3, Phase 4).

An Analysis Mode (MOD-ANL-<slug>-vN) is a VERSIONED research-view contract
(RCP-v03-007, Phase 4 §2): it fixes the purpose, input/output contracts, the
Fact/Inference/Judgment separation and prohibited conclusions for one view of
the same evidence. Version changes bump vN — a mode that has produced runs must
never be silently mutated (an old run must stay reproducible under the exact
mode version it used).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateString, ResearchObjectSchema

ModeId = Annotated[
    str, StringConstraints(pattern=r"^MOD-ANL-[a-z0-9]+(?:-[a-z0-9]+)*-v\d+$")
]


class AnalysisModeSchema(ResearchObjectSchema):
    """A versioned analysis-view contract (not a free prompt)."""

    schema_version: Literal[2]
    id: ModeId
    type: Literal["analysis_mode"]

    name: str
    purpose: str
    applicable_scopes: list[str] = Field(default_factory=list)
    required_input_types: list[str] = Field(default_factory=list)
    optional_input_types: list[str] = Field(default_factory=list)
    required_questions: list[str] = Field(default_factory=list)
    required_output_sections: list[str] = Field(default_factory=list)
    assumption_policy: str = ""
    evidence_policy: str = ""
    counterevidence_policy: str = ""
    time_horizons: list[str] = Field(default_factory=list)
    prohibited_conclusions: list[str] = Field(default_factory=list)
    prompt_template_path: str = ""
    output_schema_path: str = ""
    evaluator_version: str = ""
    status: Literal["proposed", "active", "deprecated"] = "proposed"
    valid_from: DateString | None = None

    # review_status inherited from ResearchObjectSchema; active requires review.
