"""Project review cadence: auto-roll ``next_review_date`` forward.

The dashboard was showing a stale ``next_review_date`` (PRJ-001 still 2026-08-05)
because it is a stored frontmatter field with no advancement logic. This module
derives the CURRENT next review date by rolling the stored date forward by the
project's cadence until it is in the future — so the site is correct without
manual edits — and provides an atomic ``--apply`` command to persist the
advanced date back into the project file.

Rule (deterministic): if the stored ``next_review_date`` is past/equal to today,
advance it by the cadence period (Weekly → 7d, Monthly → 30d, default 7d)
repeatedly until the result is in the future. A ``Weekly + Monthly`` cadence uses
the tighter weekly period for the "next review" display (the deeper monthly
review is a separate longer cycle).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from research_os.domain.models import ResearchObject
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.services.validation import validate_repository


def cadence_days(cadence: str) -> int:
    if "Weekly" in cadence:
        return 7
    if "Monthly" in cadence:
        return 30
    return 7


def current_next_review_date(project: ResearchObject, today: str | None = None) -> str:
    """The next review date the project should show, rolling an overdue stored
    date forward by the cadence. Pure — never writes."""
    stored = project.metadata.get("next_review_date")
    if not stored:
        return ""
    today = today or date.today().isoformat()
    if str(stored) > today:
        return str(stored)
    days = cadence_days(str(project.metadata.get("review_cadence", "")))
    current = date.fromisoformat(str(stored))
    while current.isoformat() <= today:
        current = current + timedelta(days=days)
    return current.isoformat()


def _find_project(objects: list[ResearchObject], project_id: str) -> ResearchObject:
    for obj in objects:
        if obj.object_type == "project" and obj.object_id == project_id:
            return obj
    raise ValueError(f"unknown project {project_id!r}")


def prepare_review_date_update(
    root: Path,
    project_id: str,
    today: str | None = None,
) -> tuple[str, Path, str] | None:
    """Dry-run: compute the advanced date and the updated project content.

    Returns ``(computed_date, relative_path, rendered_content)`` or ``None``
    when the stored date is already current. Pure — no writes.
    """
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before advancing a review date"
        )
    project = _find_project(objects, project_id)
    computed = current_next_review_date(project, today)
    if computed == project.metadata.get("next_review_date"):
        return None
    updated_at = today or date.today().isoformat()
    doc = MarkdownDocument.read(project.path)
    doc.set_metadata("next_review_date", computed)
    doc.set_metadata("updated_at", updated_at)
    return computed, project.path, doc.render()


def advance_review_date(
    root: Path,
    project_id: str,
    today: str | None = None,
) -> Path | None:
    """Atomically persist the advanced ``next_review_date``; returns the written
    path or ``None`` if already current."""
    prepared = prepare_review_date_update(root, project_id, today)
    if prepared is None:
        return None
    _, relative, content = prepared
    transaction = FileTransaction(root)
    transaction.stage_replace(relative, content)
    return transaction.commit()[0]
