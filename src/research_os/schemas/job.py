"""Operational scheduler Job Run schema."""

from typing import Annotated, Literal

from pydantic import StringConstraints

from research_os.schemas.common import DateTimeString, ManagedObjectSchema

JobId = Annotated[
    str,
    StringConstraints(pattern=r"^JOB-\d{14}-\d{3}$"),
]


class JobSchema(ManagedObjectSchema):
    id: JobId
    type: Literal["job"]
    status: Literal["success", "failed"]
    job_name: Literal[
        "validate",
        "indexes",
        "metrics",
        "source-process",
        "refresh",
        "discover",
        "expire",
        "daily-brief",
        "forecast-alerts",
        "backup-candidate",
    ]
    started_at: DateTimeString
    finished_at: DateTimeString
    target: str | None = None
    message: str
