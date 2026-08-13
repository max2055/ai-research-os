"""Web adapters for operational jobs and channel administration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_os.repositories.markdown import MarkdownDocument
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobRequest(_Strict):
    job_name: str = Field(min_length=1, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)
    target: str | None = Field(default=None, max_length=120)
    as_of: str = Field(min_length=10, max_length=10)


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


def _request_plan(
    root: Path,
    *,
    actor: str,
    operation: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any],
) -> PreparedRepositoryMutation:
    stamp = str(payload.get("as_of", ""))
    path = Path("05_Research/Operations/Requests") / (
        f"REQ-{operation.replace('.', '-')}-{target_id}-{stamp}.md"
    )
    content = (
        "---\n"
        f"id: {path.stem}\n"
        "type: operational_request\n"
        f"operation: {operation}\n"
        f"target_id: {target_id}\n"
        "status: pending\n"
        "review_status: pending\n"
        f"requested_at: {stamp}\n"
        "---\n\n"
        "# Operational Request\n\n"
        f"- Operation: {operation}\n"
        f"- Target: {target_id}\n"
        "- Execution: server-side service only\n"
    )
    return prepare_repository_mutation(
        root,
        operation=operation,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        writes={path: content.encode("utf-8")},
        normalized_input=payload,
        summary={"status_after": "pending", "authority": "operational_human"},
    )


def prepare_job_request(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, JobRequest)
    return _request_plan(
        root,
        actor=actor,
        operation="job.run",
        target_type="job_request",
        target_id=spec.job_name,
        payload=spec.model_dump(),
    )


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
) -> PreparedRepositoryMutation:
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
    document.set_metadata("enabled", spec.enabled)
    return prepare_repository_mutation(
        root,
        operation="channels.enable" if spec.enabled else "channels.disable",
        actor=actor,
        target_type="source_channel",
        target_id=spec.channel_id,
        writes={objects_path: document.render().encode("utf-8")},
        normalized_input=spec.model_dump(),
        summary={"enabled_after": spec.enabled},
    )
