"""Generic review queue and atomic Review Decision application."""

from __future__ import annotations

import json
import re
from pathlib import Path

from research_os.domain.lifecycle import ReportLifecycle, transition_review
from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.schemas.common import ReviewStatus
from research_os.services.drafts import yaml_list
from research_os.services.projects import objects_for_project
from research_os.services.validation import validate_repository

REVIEWABLE_TYPES = frozenset(
    {
        "source",
        "event",
        "thesis",
        "company",
        "report",
        "sector",
        "ontology_assertion",
        "product",
        "security",
        "source_channel",
    }
)


def review_queue(
    root: Path,
    *,
    project_id: str | None = None,
    object_type: str | None = None,
    review_status: str = "pending",
) -> list[ResearchObject]:
    if object_type is not None and object_type not in REVIEWABLE_TYPES:
        raise ValueError(f"unsupported review object type {object_type}")
    ReviewStatus(review_status)
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before review operations")
    if project_id:
        objects = objects_for_project(objects, project_id)
    return sorted(
        (
            obj
            for obj in objects
            if obj.object_type in REVIEWABLE_TYPES
            and (object_type is None or obj.object_type == object_type)
            and obj.metadata.get("review_status") == review_status
        ),
        key=lambda obj: (obj.object_type, obj.object_id),
    )


def render_review_queue(
    root: Path,
    *,
    project_id: str | None = None,
    object_type: str | None = None,
    review_status: str = "pending",
) -> str:
    rows = review_queue(
        root,
        project_id=project_id,
        object_type=object_type,
        review_status=review_status,
    )
    scope = project_id or "all projects"
    lines = [
        f"# Review Queue — {scope}",
        "",
        "| ID | Type | Title | Review status | Projects |",
        "|---|---|---|---|---|",
    ]
    for obj in rows:
        lines.append(
            f"| {obj.object_id} | {obj.object_type} | "
            f"{obj.metadata['title']} | {obj.metadata['review_status']} | "
            f"{', '.join(obj.metadata.get('project_ids', []))} |"
        )
    if not rows:
        lines.append("| — | — | No matching objects | — | — |")
    return "\n".join(lines) + "\n"


def next_review_id(objects: list[ResearchObject], reviewed_at: str) -> str:
    compact = reviewed_at.replace("-", "")
    numbers = [
        int(match.group(1))
        for obj in objects
        if obj.object_type == "review"
        if (
            match := re.fullmatch(
                rf"REV-{re.escape(compact)}-(\d{{3}})",
                obj.object_id,
            )
        )
    ]
    number = max(numbers, default=0) + 1
    if number > 999:
        raise ValueError("review sequence exhausted")
    return f"REV-{compact}-{number:03d}"


def _target_status(decision: str) -> ReviewStatus:
    return {
        "approve": ReviewStatus.REVIEWED,
        "edit": ReviewStatus.PENDING,
        "reject": ReviewStatus.REJECTED,
    }[decision]


def prepare_review(
    root: Path,
    *,
    target_ids: list[str],
    decision: str,
    reviewer: str,
    reviewed_at: str,
    notes: str,
) -> tuple[Path, str, dict[Path, str]]:
    if decision not in {"approve", "edit", "reject"}:
        raise ValueError("decision must be approve, edit or reject")
    if not target_ids:
        raise ValueError("at least one target id is required")
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    if not is_iso_date(reviewed_at):
        raise ValueError("reviewed_at must be YYYY-MM-DD")
    if decision in {"edit", "reject"} and not notes.strip():
        raise ValueError(f"{decision} requires notes")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before review operations")
    by_id = {obj.object_id: obj for obj in objects}
    targets: list[ResearchObject] = []
    for target_id in target_ids:
        target = by_id.get(target_id)
        if target is None or target.object_type not in REVIEWABLE_TYPES:
            raise ValueError(f"unknown or non-reviewable target {target_id}")
        targets.append(target)

    target_status = _target_status(decision)
    updates: dict[Path, str] = {}
    for target in targets:
        if decision == "approve" and target.object_type in {"thesis", "report"}:
            evidence_ids = list(target.metadata.get("evidence_ids", []))
            if target.object_type == "thesis":
                evidence_ids = list(target.metadata.get("supporting_evidence", []))
                evidence_ids += list(target.metadata.get("contradicting_evidence", []))
            non_reviewed = [
                str(evidence_id)
                for evidence_id in evidence_ids
                if by_id[str(evidence_id)].metadata.get("review_status") != "reviewed"
            ]
            if non_reviewed:
                raise ValueError(
                    f"cannot approve {target.object_id}; non-reviewed Evidence: "
                    + ", ".join(non_reviewed)
                )
        current = ReviewStatus(target.metadata["review_status"])
        next_status = transition_review(current, target_status)
        document = MarkdownDocument.read(target.path)
        document.set_metadata("review_status", next_status.value)
        document.set_metadata("updated_at", reviewed_at)
        if target.object_type == "report" and decision == "approve":
            lifecycle = ReportLifecycle(str(target.metadata["status"]), current)
            document.set_metadata("status", lifecycle.publish().status)
            supersedes = target.metadata.get("supersedes")
            if supersedes:
                prior = by_id.get(str(supersedes))
                if prior is None or prior.object_type != "report":
                    raise ValueError(f"unknown superseded Report {supersedes}")
                if prior.object_id in target_ids:
                    raise ValueError(
                        "superseded Report must not be a target of the same review"
                    )
                if prior.path in updates:
                    raise ValueError(
                        f"multiple reviewed Reports cannot supersede {prior.object_id}"
                    )
                prior_lifecycle = ReportLifecycle(
                    str(prior.metadata["status"]),
                    ReviewStatus(str(prior.metadata["review_status"])),
                ).supersede()
                prior_document = MarkdownDocument.read(prior.path)
                prior_document.set_metadata("status", prior_lifecycle.status)
                prior_document.set_metadata(
                    "review_status",
                    prior_lifecycle.review_status.value,
                )
                prior_document.set_metadata("superseded_by", target.object_id)
                prior_document.set_metadata("updated_at", reviewed_at)
                updates[prior.path] = prior_document.render()
        updates[target.path] = document.render()

    review_id = next_review_id(objects, reviewed_at)
    project_ids = sorted(
        {
            str(project_id)
            for target in targets
            for project_id in target.metadata.get("project_ids", [])
        }
    )
    relative = Path("05_Research/Reviews/Decisions") / f"{review_id}.md"
    quoted_title = json.dumps(
        f"Review {decision}: {', '.join(target_ids)}",
        ensure_ascii=False,
    )
    quoted_notes = json.dumps(notes or "Approved", ensure_ascii=False)
    content = f"""---
id: {review_id}
type: review
title: {quoted_title}
created_at: {reviewed_at}
updated_at: {reviewed_at}
schema_version: 1
project_ids: {yaml_list(project_ids)}
status: applied
target_ids: {yaml_list(target_ids)}
decision: {decision}
reviewer: {reviewer}
reviewed_at: {reviewed_at}
notes: {quoted_notes}
tags: []
---

# {review_id}

## Decision

- Decision: {decision}
- Reviewer: {reviewer}
- Reviewed at: {reviewed_at}
- Targets: {", ".join(target_ids)}

## Notes

{notes or "Approved"}
"""
    return relative, content, updates


def apply_review(
    root: Path,
    *,
    target_ids: list[str],
    decision: str,
    reviewer: str,
    reviewed_at: str,
    notes: str,
) -> list[Path]:
    root = root.resolve()
    relative, content, updates = prepare_review(
        root,
        target_ids=target_ids,
        decision=decision,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        notes=notes,
    )
    transaction = FileTransaction(root)
    transaction.stage_create(relative, content)
    for path, updated in updates.items():
        transaction.stage_replace(path, updated)
    return transaction.commit()
