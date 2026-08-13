"""Website adapters for structured Event and Report draft creation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from research_os.services.drafts import source_extraction_updates
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)
from research_os.services.workflow import (
    EventDraftSpec,
    ReportDraftSpec,
    prepare_reviewable_event_draft,
    prepare_synthesized_report,
)


def _payload(raw: str) -> dict[str, Any]:
    if len(raw.encode("utf-8")) > 32_768:
        raise ValueError("structured draft input exceeds 32768 byte limit")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("structured draft input must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("structured draft input must be a JSON object")
    return value


def prepare_event_creation(
    root: Path,
    *,
    actor: str,
    spec_json: str,
) -> PreparedRepositoryMutation:
    try:
        spec = EventDraftSpec.model_validate(_payload(spec_json))
    except ValidationError as exc:
        raise ValueError(f"invalid Event fields: {exc}") from exc
    relative, content = prepare_reviewable_event_draft(root, spec)
    target_id = "-".join(relative.name.split("-")[:3])
    source_updates = source_extraction_updates(root, spec.source_ids, spec.created_at)
    writes = {relative: content.encode("utf-8")}
    writes.update(
        {
            path.relative_to(root.resolve()): updated.encode("utf-8")
            for path, updated in source_updates.items()
        }
    )
    return prepare_repository_mutation(
        root,
        operation="event.create",
        actor=actor,
        target_type="event",
        target_id=target_id,
        writes=writes,
        normalized_input={
            "title": spec.title,
            "event_date": spec.event_date,
            "source_ids": sorted(spec.source_ids),
            "fact_count": len(spec.facts),
            "inference_count": len(spec.inferences),
            "thesis_relationship_count": len(spec.thesis_impacts),
            "alternative_count": len(spec.alternative_explanations),
            "unknown_count": len(spec.unknowns),
            "confidence": spec.confidence,
        },
        summary={
            "status_after": "pending",
            "source_count": len(spec.source_ids),
            "fact_count": len(spec.facts),
            "unknown_count": len(spec.unknowns),
        },
    )


def prepare_report_creation(
    root: Path,
    *,
    actor: str,
    spec_json: str,
) -> PreparedRepositoryMutation:
    try:
        spec = ReportDraftSpec.model_validate(_payload(spec_json))
    except ValidationError as exc:
        raise ValueError(f"invalid Report fields: {exc}") from exc
    relative, content = prepare_synthesized_report(root, spec)
    target_id = relative.stem
    return prepare_repository_mutation(
        root,
        operation="report.create",
        actor=actor,
        target_type="report",
        target_id=target_id,
        writes={relative: content.encode("utf-8")},
        normalized_input={
            "title": spec.title,
            "period_start": spec.period_start,
            "period_end": spec.period_end,
            "evidence_ids": sorted(spec.evidence_ids),
            "thesis_ids": sorted(spec.thesis_ids),
            "report_type": spec.report_type,
            "version": spec.version,
            "supersedes": spec.supersedes,
        },
        summary={
            "status_after": "pending",
            "evidence_count": len(spec.evidence_ids),
            "report_type": spec.report_type,
            "version": spec.version,
        },
    )
