"""Report metadata schema."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateString, ResearchObjectSchema

ReportId = Annotated[
    str,
    StringConstraints(pattern=r"^RPT-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*$"),
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ReportSchema(ResearchObjectSchema):
    id: ReportId
    type: Literal["report"]
    report_type: Literal["daily", "weekly", "topic", "investment_memo"]
    period_start: DateString
    period_end: DateString
    thesis_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    version: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    generation_method: Literal["manual", "structured", "ai-assisted"] = "manual"
    generation_fingerprint: Sha256 | None = None
    baseline_snapshot: str | None = None
