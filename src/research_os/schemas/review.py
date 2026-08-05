"""Immutable Review Decision metadata schema."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateString, ManagedObjectSchema

ReviewId = Annotated[
    str,
    StringConstraints(pattern=r"^REV-\d{8}-\d{3}$"),
]


class ReviewSchema(ManagedObjectSchema):
    id: ReviewId
    type: Literal["review"]
    status: Literal["applied", "superseded"]
    target_ids: list[str] = Field(min_length=1)
    decision: Literal["approve", "edit", "reject"]
    reviewer: str
    reviewed_at: DateString
    notes: str
