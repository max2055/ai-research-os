"""Research Action metadata schema."""

from typing import Annotated, Literal

from pydantic import StringConstraints

from research_os.schemas.common import DateString, ManagedObjectSchema

ActionId = Annotated[
    str,
    StringConstraints(pattern=r"^ACT-\d{8}-\d{3}$"),
]


class ActionSchema(ManagedObjectSchema):
    id: ActionId
    type: Literal["action"]
    status: Literal["open", "in_progress", "done", "cancelled"]
    owner: str
    due_date: DateString
    success_evidence: str
    source_review_id: str | None = None
