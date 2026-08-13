"""Website adapters for registry and research-operation mutations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_os.services.actions import prepare_action_close, prepare_action_draft
from research_os.services.drafts import prepare_assertion_draft, prepare_entity_draft
from research_os.services.projects import prepare_project_draft
from research_os.services.review_cadence import prepare_review_date_update
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)
from research_os.services.workflow import prepare_company_update_proposal

_MAX_JSON_BYTES = 32_768


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProjectSpec(_StrictModel):
    title: str = Field(min_length=1, max_length=240)
    slug: str = Field(min_length=1, max_length=80)
    created_at: str = Field(min_length=10, max_length=10)
    owner: str = Field(min_length=1, max_length=120)
    research_question: str = Field(min_length=1, max_length=2000)
    charter_path: str = Field(min_length=1, max_length=240)
    queue_path: str = Field(min_length=1, max_length=240)
    review_cadence: str = Field(min_length=1, max_length=120)
    next_review_date: str = Field(min_length=10, max_length=10)
    tags: list[str] = Field(default_factory=list, max_length=40)


class ActionSpec(_StrictModel):
    title: str = Field(min_length=1, max_length=240)
    owner: str = Field(min_length=1, max_length=120)
    created_at: str = Field(min_length=10, max_length=10)
    due_date: str = Field(min_length=10, max_length=10)
    success_evidence: str = Field(min_length=1, max_length=4000)
    project_ids: list[str] = Field(min_length=1, max_length=20)
    source_review_id: str | None = Field(default=None, max_length=80)


class EntitySpec(_StrictModel):
    entity_type: Literal["sector", "company"]
    slug: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=240)
    created_at: str = Field(min_length=10, max_length=10)
    definition: str = Field(default="", max_length=4000)
    in_scope: list[str] = Field(default_factory=list, max_length=80)
    out_of_scope: list[str] = Field(default_factory=list, max_length=80)
    value_chain_position: str = Field(default="", max_length=1000)
    key_inputs: list[str] = Field(default_factory=list, max_length=80)
    key_outputs: list[str] = Field(default_factory=list, max_length=80)
    key_metrics: list[str] = Field(default_factory=list, max_length=80)
    core_company_ids: list[str] = Field(default_factory=list, max_length=80)
    tracked_company_ids: list[str] = Field(default_factory=list, max_length=80)
    source_channel_ids: list[str] = Field(default_factory=list, max_length=80)
    evidence_ids: list[str] = Field(default_factory=list, max_length=80)
    sector_ids: list[str] = Field(default_factory=list, max_length=80)
    region_primary: str | None = Field(default=None, max_length=120)
    coverage_tier: str | None = Field(default=None, max_length=40)
    legal_name: str | None = Field(default=None, max_length=240)
    company_stage: str | None = Field(default=None, max_length=80)
    headquarters: str | None = Field(default=None, max_length=240)
    aliases: list[str] = Field(default_factory=list, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=40)
    project_ids: list[str] = Field(default_factory=list, max_length=20)


class AssertionSpec(_StrictModel):
    subject_id: str = Field(min_length=1, max_length=80)
    predicate: str = Field(min_length=1, max_length=80)
    object_id: str = Field(min_length=1, max_length=80)
    created_at: str = Field(min_length=10, max_length=10)
    valid_from: str = Field(min_length=10, max_length=10)
    as_of: str = Field(min_length=10, max_length=10)
    title: str = Field(default="", max_length=240)
    scope: str = Field(default="", max_length=2000)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    qualifiers: dict[str, str] = Field(default_factory=dict, max_length=40)
    project_ids: list[str] = Field(default_factory=list, max_length=20)


class CompanyUpdateSpec(_StrictModel):
    company_id: str = Field(min_length=1, max_length=80)
    event_ids: list[str] = Field(min_length=1, max_length=80)
    created_at: str = Field(min_length=10, max_length=10)


def _payload(raw: str, model: type[_StrictModel]) -> _StrictModel:
    if len(raw.encode("utf-8")) > _MAX_JSON_BYTES:
        raise ValueError(f"{model.__name__} input exceeds {_MAX_JSON_BYTES} byte limit")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{model.__name__} input must be valid JSON") from exc
    try:
        return model.model_validate(value)
    except ValidationError as exc:
        raise ValueError(f"invalid {model.__name__} fields: {exc}") from exc


def _prepared(
    root: Path,
    *,
    actor: str,
    operation: str,
    target_type: str,
    target_id: str,
    path: Path,
    content: str,
    normalized_input: dict[str, Any],
    summary: dict[str, Any],
) -> PreparedRepositoryMutation:
    return prepare_repository_mutation(
        root,
        operation=operation,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        writes={path: content.encode("utf-8")},
        normalized_input=normalized_input,
        summary=summary,
    )


def prepare_project_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = ProjectSpec.model_validate(_payload(spec_json, ProjectSpec))
    path, content = prepare_project_draft(root, **spec.model_dump())
    target_id = "-".join(path.stem.split("-")[:2])
    return _prepared(
        root,
        actor=actor,
        operation="project.create",
        target_type="project",
        target_id=target_id,
        path=path,
        content=content,
        normalized_input=spec.model_dump(),
        summary={"status_after": "proposed", "next_review_date": spec.next_review_date},
    )


def prepare_project_review_advance(
    root: Path, *, actor: str, project_id: str, as_of: str
) -> PreparedRepositoryMutation:
    prepared = prepare_review_date_update(root, project_id, as_of)
    if prepared is None:
        raise ValueError("Project review date is already current")
    computed, path, content = prepared
    return _prepared(
        root,
        actor=actor,
        operation="project.advance-review",
        target_type="project",
        target_id=project_id,
        path=path,
        content=content,
        normalized_input={"as_of": as_of},
        summary={"next_review_date": computed},
    )


def prepare_action_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = ActionSpec.model_validate(_payload(spec_json, ActionSpec))
    path, content = prepare_action_draft(root, **spec.model_dump())
    return _prepared(
        root,
        actor=actor,
        operation="action.create",
        target_type="action",
        target_id=path.stem,
        path=path,
        content=content,
        normalized_input=spec.model_dump(),
        summary={"status_after": "open", "due_date": spec.due_date},
    )


def prepare_action_close_mutation(
    root: Path,
    *,
    actor: str,
    action_id: str,
    closed_at: str,
    success_evidence: str,
) -> PreparedRepositoryMutation:
    path, content = prepare_action_close(
        root,
        action_id,
        closed_at=closed_at,
        success_evidence=success_evidence,
    )
    return _prepared(
        root,
        actor=actor,
        operation="action.close",
        target_type="action",
        target_id=action_id,
        path=path,
        content=content,
        normalized_input={
            "closed_at": closed_at,
            "success_evidence": success_evidence,
        },
        summary={"status_after": "done"},
    )


def prepare_entity_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = EntitySpec.model_validate(_payload(spec_json, EntitySpec))
    path, content = prepare_entity_draft(root, **spec.model_dump())
    return _prepared(
        root,
        actor=actor,
        operation="entity.create",
        target_type=spec.entity_type,
        target_id=path.stem,
        path=path,
        content=content,
        normalized_input={
            "entity_type": spec.entity_type,
            "slug": spec.slug,
            "title": spec.title,
            "created_at": spec.created_at,
            "project_ids": spec.project_ids,
        },
        summary={"status_after": "pending", "entity_type": spec.entity_type},
    )


def prepare_assertion_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = AssertionSpec.model_validate(_payload(spec_json, AssertionSpec))
    path, content = prepare_assertion_draft(root, **spec.model_dump())
    return _prepared(
        root,
        actor=actor,
        operation="ontology-assertion.create",
        target_type="ontology_assertion",
        target_id=path.stem,
        path=path,
        content=content,
        normalized_input=spec.model_dump(),
        summary={"status_after": "pending", "predicate": spec.predicate},
    )


def prepare_company_update_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = CompanyUpdateSpec.model_validate(_payload(spec_json, CompanyUpdateSpec))
    path, content = prepare_company_update_proposal(root, **spec.model_dump())
    return _prepared(
        root,
        actor=actor,
        operation="company-update-proposal.create",
        target_type="company_update_proposal",
        target_id=path.stem,
        path=path,
        content=content,
        normalized_input=spec.model_dump(),
        summary={"status_after": "pending", "event_count": len(spec.event_ids)},
    )
