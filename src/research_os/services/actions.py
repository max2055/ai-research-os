"""Structured Action creation, querying and closure."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.services.drafts import yaml_list
from research_os.services.projects import objects_for_project
from research_os.services.validation import validate_repository

ACTION_STATUSES = frozenset({"open", "in_progress", "done", "cancelled"})


def action_rows(
    root: Path,
    *,
    project_id: str | None = None,
    owner: str | None = None,
    status: str | None = None,
    overdue_as_of: str | None = None,
) -> list[ResearchObject]:
    if status is not None and status not in ACTION_STATUSES:
        raise ValueError(f"unknown action status {status}")
    if overdue_as_of is not None and not is_iso_date(overdue_as_of):
        raise ValueError("overdue date must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before Action operations")
    if project_id:
        objects = objects_for_project(objects, project_id)
    return sorted(
        (
            obj
            for obj in objects
            if obj.object_type == "action"
            and (owner is None or obj.metadata.get("owner") == owner)
            and (status is None or obj.metadata.get("status") == status)
            and (
                overdue_as_of is None
                or (
                    obj.metadata.get("status") in {"open", "in_progress"}
                    and str(obj.metadata.get("due_date")) < overdue_as_of
                )
            )
        ),
        key=lambda obj: (str(obj.metadata.get("due_date")), obj.object_id),
    )


def render_actions(
    root: Path,
    **filters: str | None,
) -> str:
    rows = action_rows(root, **filters)
    lines = [
        "# Research Actions",
        "",
        "| ID | Action | Owner | Due | Status | Projects |",
        "|---|---|---|---|---|---|",
    ]
    for obj in rows:
        lines.append(
            f"| {obj.object_id} | {obj.metadata['title']} | "
            f"{obj.metadata['owner']} | {obj.metadata['due_date']} | "
            f"{obj.metadata['status']} | "
            f"{', '.join(obj.metadata.get('project_ids', []))} |"
        )
    if not rows:
        lines.append("| — | No matching actions | — | — | — | — |")
    return "\n".join(lines) + "\n"


def next_action_id(objects: list[ResearchObject], created_at: str) -> str:
    compact = created_at.replace("-", "")
    numbers = [
        int(match.group(1))
        for obj in objects
        if obj.object_type == "action"
        if (
            match := re.fullmatch(
                rf"ACT-{re.escape(compact)}-(\d{{3}})",
                obj.object_id,
            )
        )
    ]
    number = max(numbers, default=0) + 1
    if number > 999:
        raise ValueError("action sequence exhausted")
    return f"ACT-{compact}-{number:03d}"


def prepare_action_draft(
    root: Path,
    *,
    title: str,
    owner: str,
    created_at: str,
    due_date: str,
    success_evidence: str,
    project_ids: list[str],
    source_review_id: str | None = None,
) -> tuple[Path, str]:
    if not is_iso_date(created_at) or not is_iso_date(due_date):
        raise ValueError("Action dates must be YYYY-MM-DD")
    if not title.strip() or not owner.strip() or not success_evidence.strip():
        raise ValueError("Action text fields must not be blank")
    if not project_ids:
        raise ValueError("Action requires at least one project")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before Action operations")
    by_id = {obj.object_id: obj for obj in objects}
    for project_id in project_ids:
        if project_id not in by_id or by_id[project_id].object_type != "project":
            raise ValueError(f"unknown project id {project_id}")
    if source_review_id and (
        source_review_id not in by_id or by_id[source_review_id].object_type != "review"
    ):
        raise ValueError(f"unknown Review Decision {source_review_id}")
    action_id = next_action_id(objects, created_at)
    relative = Path("05_Research/Reviews/Actions") / f"{action_id}.md"
    quoted_title = json.dumps(title, ensure_ascii=False)
    quoted_evidence = json.dumps(success_evidence, ensure_ascii=False)
    source_line = source_review_id or ""
    content = f"""---
id: {action_id}
type: action
title: {quoted_title}
created_at: {created_at}
updated_at: {created_at}
schema_version: 1
project_ids: {yaml_list(project_ids)}
status: open
owner: {owner}
due_date: {due_date}
success_evidence: {quoted_evidence}
source_review_id: {source_line}
tags: []
---

# {action_id}

## Action

{title}

## Success evidence

{success_evidence}

## History

- {created_at}: created as open.
"""
    return relative, content


def close_action(
    root: Path,
    action_id: str,
    *,
    closed_at: str | None = None,
    success_evidence: str,
) -> Path:
    closed_at = closed_at or date.today().isoformat()
    if not is_iso_date(closed_at):
        raise ValueError("closed_at must be YYYY-MM-DD")
    if not success_evidence.strip():
        raise ValueError("closing an Action requires success evidence")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before Action operations")
    target = next(
        (
            obj
            for obj in objects
            if obj.object_id == action_id and obj.object_type == "action"
        ),
        None,
    )
    if target is None:
        raise ValueError(f"unknown Action {action_id}")
    if target.metadata.get("status") not in {"open", "in_progress"}:
        raise ValueError(f"Action {action_id} is not open")
    document = MarkdownDocument.read(target.path)
    document.set_metadata("status", "done")
    document.set_metadata("updated_at", closed_at)
    document.set_metadata("success_evidence", success_evidence)
    body = document.body.rstrip()
    document.set_body(f"{body}\n\n- {closed_at}: closed; {success_evidence}\n")
    transaction = FileTransaction(root)
    transaction.stage_replace(target.path, document.render())
    return transaction.commit()[0]
