"""Project creation, lookup and object scoping."""

from __future__ import annotations

import json
import re
from pathlib import Path

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.drafts import validate_slug, write_new_file, yaml_list
from research_os.services.validation import validate_repository


def objects_for_project(
    objects: list[ResearchObject],
    project_id: str,
) -> list[ResearchObject]:
    projects = {obj.object_id for obj in objects if obj.object_type == "project"}
    if project_id not in projects:
        raise ValueError(f"unknown project id {project_id}")
    return [
        obj
        for obj in objects
        if obj.object_id == project_id
        or project_id in obj.metadata.get("project_ids", [])
    ]


def project_objects(root: Path) -> list[ResearchObject]:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before project operations")
    return sorted(
        (obj for obj in objects if obj.object_type == "project"),
        key=lambda obj: obj.object_id,
    )


def next_project_id(objects: list[ResearchObject]) -> str:
    numbers = [
        int(match.group(1))
        for obj in objects
        if obj.object_type == "project"
        if (match := re.fullmatch(r"PRJ-(\d{3})", obj.object_id))
    ]
    number = max(numbers, default=0) + 1
    if number > 999:
        raise ValueError("project sequence exhausted")
    return f"PRJ-{number:03d}"


def render_project_draft(
    *,
    project_id: str,
    title: str,
    created_at: str,
    owner: str,
    research_question: str,
    charter_path: str,
    queue_path: str,
    review_cadence: str,
    next_review_date: str,
    tags: list[str],
) -> str:
    quoted_title = json.dumps(title, ensure_ascii=False)
    quoted_question = json.dumps(research_question, ensure_ascii=False)
    return f"""---
id: {project_id}
type: project
title: {quoted_title}
created_at: {created_at}
updated_at: {created_at}
schema_version: 1
project_ids: [{project_id}]
status: proposed
owner: {owner}
research_question: {quoted_question}
charter_path: {charter_path}
queue_path: {queue_path}
current_report_id:
review_cadence: {review_cadence}
next_review_date: {next_review_date}
tags: {yaml_list(tags)}
---

# {title}

## Research question

{research_question}

## Scope

TODO: define included entities, time horizon and evidence boundary.

## Success criteria

TODO: define measurable research completion and quality criteria.

## Active Thesis

- TODO

## Open actions

- TODO

## Review history

- {created_at}: Project draft created; human activation required.
"""


def prepare_project_draft(
    root: Path,
    *,
    title: str,
    slug: str,
    created_at: str,
    owner: str,
    research_question: str,
    charter_path: str,
    queue_path: str,
    review_cadence: str,
    next_review_date: str,
    tags: list[str],
) -> tuple[Path, str]:
    validate_slug(slug)
    if not is_iso_date(created_at) or not is_iso_date(next_review_date):
        raise ValueError("project dates must be YYYY-MM-DD")
    if not all(
        value.strip()
        for value in (
            title,
            owner,
            research_question,
            charter_path,
            queue_path,
            review_cadence,
        )
    ):
        raise ValueError("project text fields must not be blank")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating a Project")
    project_id = next_project_id(objects)
    relative = Path("05_Research/Projects") / f"{project_id}-{slug}.md"
    return relative, render_project_draft(
        project_id=project_id,
        title=title,
        created_at=created_at,
        owner=owner,
        research_question=research_question,
        charter_path=charter_path,
        queue_path=queue_path,
        review_cadence=review_cadence,
        next_review_date=next_review_date,
        tags=tags,
    )


def render_project_list(root: Path) -> str:
    rows = project_objects(root)
    lines = [
        "# Research Projects",
        "",
        "| ID | Question | Owner | Status | Next review |",
        "|---|---|---|---|---|",
    ]
    for obj in rows:
        lines.append(
            f"| {obj.object_id} | {obj.metadata['research_question']} | "
            f"{obj.metadata['owner']} | {obj.metadata['status']} | "
            f"{obj.metadata['next_review_date']} |"
        )
    if not rows:
        lines.append("| — | No projects | — | — | — |")
    return "\n".join(lines) + "\n"


def render_project_status(root: Path, project_id: str) -> str:
    objects, findings = validate_repository(root)
    scoped = objects_for_project(objects, project_id)
    project = next(obj for obj in scoped if obj.object_id == project_id)
    counts: dict[str, int] = {}
    for obj in scoped:
        counts[obj.object_type] = counts.get(obj.object_type, 0) + 1
    count_text = ", ".join(
        f"{object_type}={counts[object_type]}" for object_type in sorted(counts)
    )
    scoped_paths = {obj.path for obj in scoped}
    errors = sum(
        finding.level == "error" and finding.path in scoped_paths
        for finding in findings
    )
    return (
        f"# Project Status — {project_id}\n\n"
        f"- Question: {project.metadata['research_question']}\n"
        f"- Owner: {project.metadata['owner']}\n"
        f"- Status: {project.metadata['status']}\n"
        f"- Next review: {project.metadata['next_review_date']}\n"
        f"- Objects: {count_text}\n"
        f"- Validation errors: {errors}\n"
    )


__all__ = [
    "objects_for_project",
    "prepare_project_draft",
    "project_objects",
    "render_project_list",
    "render_project_status",
    "write_new_file",
]
