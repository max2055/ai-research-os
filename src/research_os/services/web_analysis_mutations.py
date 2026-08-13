"""Website adapters for Impact and Analysis workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_os.services.analysis_runner import prepare_run
from research_os.services.impact_draft import prepare_impact_draft
from research_os.services.impact_proposal import propose_direct_impacts
from research_os.services.insight_proposal import prepare_thesis_proposal
from research_os.services.validation import validate_repository
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)

_MAX_JSON_BYTES = 32_768


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ImpactSpec(_StrictModel):
    event_id: str = Field(min_length=1, max_length=80)
    created_at: str = Field(min_length=10, max_length=10)
    proposal_index: int = Field(default=0, ge=0, le=999)


class AnalysisRunSpec(_StrictModel):
    mode_id: str = Field(min_length=1, max_length=120)
    as_of: str = Field(min_length=1, max_length=20)
    scope_ids: list[str] = Field(default_factory=list, max_length=80)
    input_source_ids: list[str] = Field(default_factory=list, max_length=80)
    input_event_ids: list[str] = Field(default_factory=list, max_length=80)
    input_impact_ids: list[str] = Field(default_factory=list, max_length=80)
    input_thesis_ids: list[str] = Field(default_factory=list, max_length=80)
    model_provider: str = Field(default="echo", max_length=80)
    model_id: str = Field(default="echo", max_length=160)
    model_parameters: dict[str, str] = Field(default_factory=dict, max_length=40)


class AnalysisReplaySpec(_StrictModel):
    run_id: str = Field(min_length=1, max_length=80)
    model_provider: str = Field(default="echo", max_length=80)
    model_id: str = Field(default="echo", max_length=160)
    model_parameters: dict[str, str] = Field(default_factory=dict, max_length=40)


class ThesisProposalSpec(_StrictModel):
    run_id: str = Field(min_length=1, max_length=80)
    created_at: str = Field(min_length=10, max_length=10)


def _payload(raw: str, model: type[_StrictModel]) -> _StrictModel:
    if len(raw.encode("utf-8")) > _MAX_JSON_BYTES:
        raise ValueError("analysis input exceeds 32768 byte limit")
    try:
        value = json.loads(raw)
        return model.model_validate(value)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"invalid {model.__name__} fields") from exc


def _wrap(
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


def prepare_impact_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = ImpactSpec.model_validate(_payload(spec_json, ImpactSpec))
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before Impact operations")
    proposals = propose_direct_impacts(objects, event_id=spec.event_id)
    if spec.proposal_index >= len(proposals):
        raise ValueError("Impact proposal index is out of range")
    proposal = proposals[spec.proposal_index]
    path, content = prepare_impact_draft(
        root, proposal=proposal, created_at=spec.created_at
    )
    return _wrap(
        root,
        actor=actor,
        operation="impact.create",
        target_type="impact_assertion",
        target_id=path.stem,
        path=path,
        content=content,
        normalized_input={
            "event_id": spec.event_id,
            "proposal_index": spec.proposal_index,
            "impact_type": proposal.get("impact_type"),
            "target_id": proposal.get("target_id"),
        },
        summary={"status_after": "pending", "event_id": spec.event_id},
    )


def prepare_analysis_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = AnalysisRunSpec.model_validate(_payload(spec_json, AnalysisRunSpec))
    plan = prepare_run(root, **spec.model_dump())
    return _wrap(
        root,
        actor=actor,
        operation="analysis.run",
        target_type="analysis_run",
        target_id=plan.run_id,
        path=plan.relative_path,
        content=plan.content,
        normalized_input={
            "mode_id": spec.mode_id,
            "as_of": spec.as_of,
            "scope_ids": spec.scope_ids,
            "input_source_ids": spec.input_source_ids,
            "input_event_ids": spec.input_event_ids,
            "input_impact_ids": spec.input_impact_ids,
            "input_thesis_ids": spec.input_thesis_ids,
            "model_provider": spec.model_provider,
            "model_id": spec.model_id,
            "input_snapshot_hash": plan.input_snapshot_hash,
            "prompt_hash": plan.prompt_hash,
            "output_hash": plan.output_hash,
        },
        summary={"status_after": "completed", "review_status_after": "pending"},
    )


def prepare_analysis_replay(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = AnalysisReplaySpec.model_validate(_payload(spec_json, AnalysisReplaySpec))
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before Analysis replay")
    source = next(
        (obj for obj in objects if obj.object_id == spec.run_id),
        None,
    )
    if source is None or source.object_type != "analysis_run":
        raise ValueError(f"unknown analysis run {spec.run_id}")
    plan = prepare_run(
        root,
        mode_id=str(source.metadata.get("mode_id", "")),
        as_of=str(source.metadata.get("as_of", "")),
        scope_ids=list(source.metadata.get("scope_ids", []) or []),
        input_source_ids=list(source.metadata.get("input_source_ids", []) or []),
        input_event_ids=list(source.metadata.get("input_event_ids", []) or []),
        input_impact_ids=list(source.metadata.get("input_impact_ids", []) or []),
        input_thesis_ids=list(source.metadata.get("input_thesis_ids", []) or []),
        model_provider=spec.model_provider,
        model_id=spec.model_id,
        model_parameters=spec.model_parameters,
    )
    return _wrap(
        root,
        actor=actor,
        operation="analysis.replay",
        target_type="analysis_run",
        target_id=plan.run_id,
        path=plan.relative_path,
        content=plan.content,
        normalized_input={
            "source_run_id": spec.run_id,
            "input_snapshot_hash": plan.input_snapshot_hash,
        },
        summary={"status_after": "completed", "replayed_from": spec.run_id},
    )


def prepare_thesis_proposal_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = ThesisProposalSpec.model_validate(_payload(spec_json, ThesisProposalSpec))
    path, content = prepare_thesis_proposal(
        root, run_id=spec.run_id, created_at=spec.created_at
    )
    return _wrap(
        root,
        actor=actor,
        operation="analysis.propose-thesis",
        target_type="thesis_proposal",
        target_id=path.stem,
        path=path,
        content=content,
        normalized_input={"run_id": spec.run_id, "created_at": spec.created_at},
        summary={"status_after": "pending", "authoritative_thesis_write": False},
    )
