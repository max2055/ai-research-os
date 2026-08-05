"""Source metadata schema."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import (
    DateOrUnknown,
    DateString,
    DateTimeString,
    ResearchObjectSchema,
)

SourceId = Annotated[str, StringConstraints(pattern=r"^SRC-\d{8}-\d{3}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class SourceSchema(ResearchObjectSchema):
    id: SourceId
    type: Literal["source"]
    source_type: Literal[
        "article",
        "report",
        "paper",
        "earnings",
        "transcript",
        "documentation",
        "other",
    ]
    publisher: str
    authors: list[str] = Field(default_factory=list)
    published_at: DateOrUnknown
    accessed_at: DateString
    url: str | None = None
    local_path: str | None = None
    source_grade: Literal["A", "B", "C", "D"]
    companies: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    canonical_url: str | None
    asset_paths: list[str]
    content_sha256: Sha256 | None
    fetched_at: DateTimeString | None
    upstream_source_ids: list[str]
    processing_status: Literal[
        "registered",
        "captured",
        "processed",
        "failed",
    ]
    processing_error: str | None
    published_date_proposal: DateOrUnknown | None
