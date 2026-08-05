"""Company knowledge metadata schema."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import ResearchObjectSchema

CompanyId = Annotated[
    str,
    StringConstraints(pattern=r"^COM-[a-z0-9]+(?:-[a-z0-9]+)*$"),
]


class CompanySchema(ResearchObjectSchema):
    id: CompanyId
    type: Literal["company"]
    aliases: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
