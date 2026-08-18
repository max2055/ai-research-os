"""Web adapters for operational jobs and channel administration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from research_os.repositories.markdown import MarkdownDocument
from research_os.services.operations_db import (
    create_run,
    get_schedule,
    operations_db_path,
    set_schedule_enabled,
)
from research_os.services.schedule_migration import migrate_operational_history
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobRequest(_Strict):
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
    project_id: str | None = Field(default=None, max_length=80)
    target: str | None = Field(default=None, max_length=120)
    as_of: str = Field(min_length=10, max_length=10)

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


class ChannelChange(_Strict):
    channel_id: str = Field(min_length=1, max_length=80)
    enabled: bool


class CadenceReview(_Strict):
    project_id: str = Field(min_length=1, max_length=80)
    cadence: Literal["Weekly", "Monthly"]
    review_date: str = Field(min_length=10, max_length=10)
    metrics_snapshot: str = Field(min_length=1, max_length=240)
    system_facts: str = Field(min_length=1, max_length=4000)
    evidence_changes: str = Field(min_length=1, max_length=4000)
    thesis_review: str = Field(min_length=1, max_length=4000)
    decisions: str = Field(min_length=1, max_length=4000)
    action_items: str = Field(min_length=1, max_length=4000)
    next_review: str = Field(min_length=10, max_length=10)


def _parse(raw: str, model: type[_Strict]) -> Any:
    try:
        return model.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("invalid operational fields") from exc


@dataclass(frozen=True)
class PreparedJobRequest:
    actor: str
    request: JobRequest


@dataclass(frozen=True)
class PreparedChannelChange:
    actor: str
    channel_id: str
    schedule_id: str
    enabled: bool
    expected_version: int


def prepare_job_request(
    root: Path, *, actor: str, spec_json: str
) -> PreparedJobRequest:
    spec = _parse(spec_json, JobRequest)
    try:
        date.fromisoformat(spec.as_of)
    except ValueError as exc:
        raise ValueError("invalid operational date") from exc
    objects, _ = __import__(
        "research_os.services.validation", fromlist=["validate_repository"]
    ).validate_repository(root)
    by_id = {item.object_id: item for item in objects}
    if spec.target:
        expected_type = "source_channel" if spec.job_name == "discover" else "source"
        target = by_id.get(spec.target)
        if target is None or target.object_type != expected_type:
            raise ValueError("unknown operational target")
    if spec.project_id:
        project = by_id.get(spec.project_id)
        if project is None or project.object_type != "project":
            raise ValueError("unknown operational project")
    return PreparedJobRequest(actor=actor, request=spec)


def enqueue_job_request(
    root: Path,
    prepared: PreparedJobRequest,
    *,
    now: str,
    run_id: str | None = None,
) -> str:
    spec = prepared.request
    effective_run_id = run_id or f"RUN-manual-{uuid4().hex}"
    create_run(
        operations_db_path(root),
        run_id=effective_run_id,
        schedule_id=None,
        job_name=spec.job_name,
        target=spec.target or None,
        project_id=spec.project_id or None,
        request_kind="manual",
        as_of=spec.as_of,
        queued_at=now,
        metadata={"actor": prepared.actor},
        actor=prepared.actor,
    )
    return effective_run_id


def prepare_cadence_review(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, CadenceReview)
    try:
        from datetime import date

        date.fromisoformat(spec.review_date)
        date.fromisoformat(spec.next_review)
    except ValueError as exc:
        raise ValueError("invalid cadence review date") from exc
    project_path = root / "05_Research" / "Projects" / spec.project_id
    if not project_path.is_dir():
        raise ValueError(f"unknown project {spec.project_id}")
    prefix = "WK" if spec.cadence == "Weekly" else "MO"
    relative = (
        Path("05_Research/Projects")
        / spec.project_id
        / "Reviews"
        / spec.cadence
        / f"{prefix}-{spec.review_date}-{spec.project_id.lower()}.md"
    )
    content = (
        f"# {spec.project_id} {spec.cadence} Research Review — {spec.review_date}\n\n"
        f"Project ID: {spec.project_id}\n\n"
        "Scope: v0.3 F-021\n\n"
        "Review status: completed\n\n"
        f"Reviewer: {actor}\n\nReview date: {spec.review_date}\n\n"
        f"Metrics snapshot: `{spec.metrics_snapshot}`\n\n"
        "## System facts\n\n"
        f"{spec.system_facts}\n\n"
        "## Evidence changes\n\n"
        f"{spec.evidence_changes}\n\n"
        "## Thesis review\n\n"
        f"{spec.thesis_review}\n\n"
        "## Human decisions\n\n"
        f"{spec.decisions}\n\n"
        "## Action items\n\n"
        f"{spec.action_items}\n\n"
        "## Next review\n\n"
        f"{spec.next_review}\n"
    )
    return prepare_repository_mutation(
        root,
        operation="review.cadence",
        actor=actor,
        target_type="cadence_review",
        target_id=relative.stem,
        writes={relative: content.encode("utf-8")},
        normalized_input=spec.model_dump(),
        summary={"status_after": "completed", "authority": "named_human"},
    )


def prepare_channel_change(
    root: Path, *, actor: str, spec_json: str
) -> PreparedChannelChange:
    spec = _parse(spec_json, ChannelChange)
    # Validate policy at preview, but defer the file write to the frozen plan.
    objects_path = next(
        (
            obj.path
            for obj in __import__(
                "research_os.services.validation", fromlist=["validate_repository"]
            ).validate_repository(root)[0]
            if obj.object_id == spec.channel_id
        ),
        None,
    )
    if objects_path is None:
        raise ValueError(f"unknown source_channel {spec.channel_id}")
    document = MarkdownDocument.read(objects_path)
    if spec.enabled and document.metadata.get("review_status") != "reviewed":
        raise ValueError("channel must be reviewed before enabling")
    if spec.enabled and document.metadata.get("license_status") == "restricted":
        raise ValueError("restricted channel cannot be enabled")
    schedule_id = f"SCH-channel-{spec.channel_id.removeprefix('CHN-')}"
    db = operations_db_path(root)
    schedule = get_schedule(db, schedule_id)
    if schedule is None:
        migrate_operational_history(
            root, actor="system:migration", now=date.today().isoformat() + "T00:00:00Z"
        )
        schedule = get_schedule(db, schedule_id)
    if schedule is None:
        raise ValueError(f"channel schedule is unavailable for {spec.channel_id}")
    return PreparedChannelChange(
        actor=actor,
        channel_id=spec.channel_id,
        schedule_id=schedule_id,
        enabled=spec.enabled,
        expected_version=schedule.version,
    )


def commit_channel_change(
    root: Path, prepared: PreparedChannelChange, *, now: str
) -> None:
    set_schedule_enabled(
        operations_db_path(root),
        prepared.schedule_id,
        enabled=prepared.enabled,
        expected_version=prepared.expected_version,
        actor=prepared.actor,
        now=now,
    )
