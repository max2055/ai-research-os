"""Research Project metadata schema."""

from typing import Annotated, Literal

from pydantic import StringConstraints

from research_os.schemas.common import DateString, ManagedObjectSchema

ProjectId = Annotated[str, StringConstraints(pattern=r"^PRJ-\d{3}$")]


class ProjectSchema(ManagedObjectSchema):
    id: ProjectId
    type: Literal["project"]
    status: Literal["proposed", "active", "paused", "archived"]
    owner: str
    research_question: str
    charter_path: str
    queue_path: str
    current_report_id: str | None = None
    review_cadence: str
    next_review_date: DateString
