"""Common typed fields shared by research object schemas."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class ReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


ReviewStatusValue = Literal["pending", "reviewed", "rejected", "superseded"]


def validate_iso_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def validate_date_or_unknown(value: str) -> str:
    if value != "unknown":
        date.fromisoformat(value)
    return value


def validate_iso_datetime(value: str) -> str:
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


DateString = Annotated[str, AfterValidator(validate_iso_date)]
DateOrUnknown = Annotated[str, AfterValidator(validate_date_or_unknown)]
DateTimeString = Annotated[str, AfterValidator(validate_iso_datetime)]
Confidence = Annotated[float, Field(ge=0, le=1)]


class ManagedObjectSchema(BaseModel):
    """Common metadata contract for all managed Markdown objects."""

    model_config = ConfigDict(extra="allow", strict=True)

    id: str
    type: str
    title: str
    created_at: DateString
    updated_at: DateString | None = None
    schema_version: Literal[1]
    project_ids: list[str]
    tags: list[str] = Field(default_factory=list)

    def semantic_metadata(self) -> dict[str, Any]:
        # Preserve the distinction between an absent optional field and one
        # explicitly present with a null value in the Markdown source.
        return self.model_dump(mode="json", exclude_unset=True)


class ResearchObjectSchema(ManagedObjectSchema):
    """Metadata contract for human-reviewed research objects."""

    status: str
    review_status: ReviewStatusValue
