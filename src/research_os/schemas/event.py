"""Event metadata schema."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from research_os.schemas.common import (
    Confidence,
    DateString,
    ResearchObjectSchema,
)

EventId = Annotated[str, StringConstraints(pattern=r"^EVT-\d{8}-\d{3}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class CitationAnchorSchema(BaseModel):
    fact_id: Annotated[str, StringConstraints(pattern=r"^F[1-9]\d*$")]
    source_id: Annotated[str, StringConstraints(pattern=r"^SRC-\d{8}-\d{3}$")]
    asset_path: str
    locator: Annotated[str, StringConstraints(pattern=r"^L[1-9]\d*(?:-L?[1-9]\d*)?$")]
    quote: str
    quote_sha256: Sha256


class EventSchema(ResearchObjectSchema):
    id: EventId
    type: Literal["event"]
    event_date: DateString
    source_ids: list[str] = Field(min_length=1)
    companies: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    thesis_links: list[str] = Field(default_factory=list)
    confidence: Confidence
    generation_method: Literal["manual", "structured", "ai-assisted"] = "manual"
    generation_fingerprint: Sha256 | None = None
    citation_anchors: list[CitationAnchorSchema] = Field(default_factory=list)
    source_independence_groups: list[list[str]] = Field(default_factory=list)
