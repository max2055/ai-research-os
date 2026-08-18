"""Typed schedule mutation commands used by the Web operations pages."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.services.operations_db import (
    ScheduleRecord,
    ScheduleSpec,
    create_run,
    create_schedule,
    update_schedule,
)


class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    job_name: Literal[
        "validate",
        "indexes",
        "metrics",
        "source-process",
        "refresh",
        "discover",
        "expire",
        "purge",
        "enrich",
        "daily-brief",
        "forecast-alerts",
        "backup-candidate",
        "backup-durable",
    ]
    target: str | None = Field(default=None, max_length=120)
    project_id: str | None = Field(default=None, max_length=80)
    interval_value: int = Field(ge=1, le=1000)
    interval_unit: Literal["minutes", "hours", "days", "weeks"]
    timezone: str = Field(min_length=1, max_length=64)
    retry_limit: int = Field(ge=0, le=5)
    retry_backoff_seconds: int = Field(ge=1, le=3600)
    timeout_seconds: int = Field(ge=30, le=86400)
    overlap_policy: Literal["skip"] = "skip"
    missed_run_policy: Literal["catch_up_once", "skip_missed"] = "catch_up_once"
    enabled: bool = False

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("invalid IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        if self.job_name == "discover" and not (self.target or "").startswith("CHN-"):
            raise ValueError("discover requires a Channel target")
        if self.job_name == "source-process" and not (self.target or "").startswith(
            "SRC-"
        ):
            raise ValueError("source-process requires a Source target")
        if self.job_name not in {"discover", "source-process"} and self.target:
            raise ValueError("this Job does not accept a target")
        return self

    @property
    def interval_seconds(self) -> int:
        multiplier = {"minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}[
            self.interval_unit
        ]
        return self.interval_value * multiplier


def to_spec(schedule_id: str, value: ScheduleInput) -> ScheduleSpec:
    return ScheduleSpec(
        schedule_id=schedule_id,
        name=value.name,
        job_name=value.job_name,
        target=value.target,
        project_id=value.project_id,
        interval_seconds=value.interval_seconds,
        timezone=value.timezone,
        enabled=value.enabled,
        retry_limit=value.retry_limit,
        retry_backoff_seconds=value.retry_backoff_seconds,
        timeout_seconds=value.timeout_seconds,
        overlap_policy=value.overlap_policy,
        missed_run_policy=value.missed_run_policy,
    )


def create_schedule_from_input(
    db: Path,
    value: ScheduleInput,
    *,
    actor: str,
    now: str,
    schedule_id: str | None = None,
) -> ScheduleRecord:
    return create_schedule(
        db,
        to_spec(schedule_id or f"SCH-{uuid4().hex[:12]}", value),
        actor=actor,
        now=now,
    )


def update_schedule_from_input(
    db: Path, current: ScheduleRecord, value: ScheduleInput, *, actor: str, now: str
) -> ScheduleRecord:
    spec = to_spec(current.schedule_id, value)
    return update_schedule(
        db,
        current.schedule_id,
        expected_version=current.version,
        changes=spec.__dict__,
        actor=actor,
        now=now,
    )


def queue_manual_run(
    db: Path, *, schedule: ScheduleRecord, actor: str, now: str
) -> str:
    run_id = f"RUN-manual-{uuid4().hex}"
    create_run(
        db,
        run_id=run_id,
        schedule_id=schedule.schedule_id,
        job_name=schedule.job_name,
        target=schedule.target,
        project_id=schedule.project_id,
        request_kind="manual",
        as_of=now,
        queued_at=now,
        max_attempts=schedule.retry_limit + 1,
        metadata={"actor": actor},
        actor=actor,
    )
    return run_id


__all__ = [
    "ScheduleInput",
    "create_schedule_from_input",
    "queue_manual_run",
    "to_spec",
    "update_schedule_from_input",
]
