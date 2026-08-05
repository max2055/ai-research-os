"""Thesis metadata schema."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import (
    Confidence,
    DateString,
    ResearchObjectSchema,
)

ThesisId = Annotated[str, StringConstraints(pattern=r"^THS-\d{3}$")]


class ThesisSchema(ResearchObjectSchema):
    id: ThesisId
    type: Literal["thesis"]
    thesis_status: Literal["active", "validated", "invalidated", "archived"]
    confidence: Confidence
    review_date: DateString | None = None
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
