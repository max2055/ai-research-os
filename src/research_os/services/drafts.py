"""Transactional application of generated research drafts."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from research_os.domain.models import ResearchObject
from research_os.domain.policies import (
    checklist_item_checked,
    is_iso_date,
)
from research_os.repositories.transaction import FileTransaction, TransactionError
from research_os.services.validation import taxonomy_codes, validate_repository

SOURCE_TYPES = {
    "article",
    "report",
    "paper",
    "earnings",
    "transcript",
    "documentation",
    "other",
}
SOURCE_GRADES = {"A", "B", "C", "D"}


def split_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(values) + "]"


def yaml_scalar(value: str) -> str:
    """Render an arbitrary string as a YAML-safe scalar."""
    return json.dumps(value, ensure_ascii=False)


def validate_slug(slug: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError(
            "slug must contain lowercase ASCII letters, numbers and hyphens"
        )


def next_object_id(
    objects: Iterable[ResearchObject],
    object_type: str,
    object_date: str,
) -> str:
    if object_type not in {"source", "event"}:
        raise ValueError("next_object_id supports source and event")
    if not is_iso_date(object_date):
        raise ValueError("object_date must be YYYY-MM-DD")
    prefix = "SRC" if object_type == "source" else "EVT"
    suffixes: list[int] = []
    for obj in objects:
        if obj.object_type != object_type:
            continue
        match = re.fullmatch(rf"{prefix}-\d{{8}}-(\d{{3}})", obj.object_id)
        if match:
            suffixes.append(int(match.group(1)))
    number = max(suffixes, default=0) + 1
    if number > 999:
        raise ValueError(f"{object_type} sequence exhausted")
    compact_date = object_date.replace("-", "")
    return f"{prefix}-{compact_date}-{number:03d}"


def ensure_known_ids(
    values: list[str],
    expected_type: str,
    by_id: dict[str, ResearchObject],
    field: str,
) -> None:
    for value in values:
        target = by_id.get(value)
        if target is None:
            raise ValueError(f"{field} references missing object {value}")
        if target.object_type != expected_type:
            raise ValueError(
                f"{field} references {target.object_type} {value}, "
                f"expected {expected_type}"
            )


def ensure_taxonomy(
    values: list[str],
    codes: set[str],
    field: str,
) -> None:
    unknown = sorted(set(values) - codes)
    if unknown:
        raise ValueError(
            f"{field} contains unknown Taxonomy codes: {', '.join(unknown)}"
        )


def render_source_draft(
    *,
    object_id: str,
    title: str,
    created_at: str,
    source_type: str,
    publisher: str,
    published_at: str,
    url: str,
    local_path: str,
    source_grade: str,
    companies: list[str],
    technologies: list[str],
    products: list[str],
    tags: list[str],
    project_ids: list[str] | None = None,
) -> str:
    project_ids = project_ids or ["PRJ-001"]
    return f"""---
id: {object_id}
type: source
title: {yaml_scalar(title)}
created_at: {created_at}
updated_at: {created_at}
schema_version: 1
project_ids: {yaml_list(project_ids)}
status: active
review_status: pending
source_type: {source_type}
publisher: {yaml_scalar(publisher)}
authors: []
published_at: {published_at}
accessed_at: {created_at}
url: {yaml_scalar(url)}
local_path: {yaml_scalar(local_path)}
source_grade: {source_grade}
companies: {yaml_list(companies)}
technologies: {yaml_list(technologies)}
products: {yaml_list(products)}
canonical_url: {yaml_scalar(url)}
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered
processing_error:
published_date_proposal:
tags: {yaml_list(tags)}
---

# Source

## Source summary

TODO: summarize only what the Source directly supports.

## Why it matters

TODO: explain relevance without upgrading claims beyond the Source.

## Relevant sections

- TODO

## Reliability notes

TODO: record source limitations, incentives and missing context.

## Processing status

- [ ] Event extraction completed
- [ ] Entity links reviewed
- [ ] Thesis links reviewed
"""


def render_event_draft(
    *,
    object_id: str,
    title: str,
    created_at: str,
    event_date: str,
    source_ids: list[str],
    companies: list[str],
    technologies: list[str],
    products: list[str],
    thesis_links: list[str],
    confidence: float,
    tags: list[str],
    project_ids: list[str] | None = None,
) -> str:
    project_ids = project_ids or ["PRJ-001"]
    impact_rows = "\n".join(
        f"| {thesis_id} | contextual | "
        "TODO: explain the proposed relationship. | 0.00 |"
        for thesis_id in thesis_links
    )
    if impact_rows:
        impact_rows += "\n"
    return f"""---
id: {object_id}
type: event
title: {title}
created_at: {created_at}
updated_at: {created_at}
schema_version: 1
project_ids: {yaml_list(project_ids)}
status: active
review_status: pending
event_date: {event_date}
source_ids: {yaml_list(source_ids)}
companies: {yaml_list(companies)}
technologies: {yaml_list(technologies)}
products: {yaml_list(products)}
thesis_links: {yaml_list(thesis_links)}
confidence: {confidence:.2f}
tags: {yaml_list(tags)}
---

# Event

## Facts

TODO: include only claims directly supported by `source_ids`.

## Inferences

TODO: state the reasoning separately from facts.

## Research judgment

TODO: explain possible significance and uncertainty.

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
{impact_rows}

Relationship must be `supporting`, `contradicting` or `contextual`.

## Alternative explanations

- TODO

## Unknowns

- TODO

## Follow-up indicators

- TODO
"""


def render_report_draft(
    *,
    object_id: str,
    title: str,
    created_at: str,
    period_start: str,
    period_end: str,
    thesis_ids: list[str],
    evidence_ids: list[str],
    tags: list[str],
    project_ids: list[str] | None = None,
) -> str:
    project_ids = project_ids or ["PRJ-001"]
    return f"""---
id: {object_id}
type: report
title: {title}
created_at: {created_at}
updated_at: {created_at}
schema_version: 1
project_ids: {yaml_list(project_ids)}
status: draft
review_status: pending
report_type: topic
period_start: {period_start}
period_end: {period_end}
thesis_ids: {yaml_list(thesis_ids)}
evidence_ids: {yaml_list(evidence_ids)}
tags: {yaml_list(tags)}
---

# {title}

> 机器生成的研究骨架，必须经人工审核后才能成为权威输出。

## One-sentence conclusion

TODO

## Research question and scope

TODO

## Current value chain

TODO

## What is changing

TODO

## Thesis assessment

TODO: cite the selected Thesis and Event IDs.

## Incumbents versus AI Native challengers

TODO

## Potential beneficiaries and disadvantaged companies

TODO

## Contrarian view

TODO

## Falsification conditions

- TODO

## Key indicators

- TODO

## Investment implications

TODO: distinguish industry implications from security selection.

## Risks and unknowns

- TODO

## Next research actions

1. TODO
"""


def prepare_source_draft(
    root: Path,
    *,
    title: str,
    slug: str,
    created_at: str,
    source_type: str,
    publisher: str,
    published_at: str,
    url: str,
    local_path: str,
    source_grade: str,
    companies: list[str],
    technologies: list[str],
    products: list[str],
    tags: list[str],
    project_ids: list[str] | None = None,
) -> tuple[Path, str]:
    project_ids = project_ids or ["PRJ-001"]
    validate_slug(slug)
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
    if source_grade not in SOURCE_GRADES:
        raise ValueError(f"source_grade must be one of {sorted(SOURCE_GRADES)}")
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    if not is_iso_date(published_at, allow_unknown=True):
        raise ValueError("published_at must be YYYY-MM-DD or unknown")
    if not url and not local_path:
        raise ValueError("url or local_path is required")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating a Source")
    by_id = {obj.object_id: obj for obj in objects}
    ensure_known_ids(project_ids, "project", by_id, "project_ids")
    ensure_known_ids(companies, "company", by_id, "companies")
    ensure_taxonomy(
        technologies + tags,
        taxonomy_codes(root),
        "taxonomy fields",
    )
    object_id = next_object_id(objects, "source", created_at)
    folder = "Earnings" if source_type == "earnings" else "Articles"
    relative = Path("01_Inbox") / folder / f"{object_id}-{slug}.md"
    return relative, render_source_draft(
        object_id=object_id,
        title=title,
        created_at=created_at,
        source_type=source_type,
        publisher=publisher,
        published_at=published_at,
        url=url,
        local_path=local_path,
        source_grade=source_grade,
        companies=companies,
        technologies=technologies,
        products=products,
        tags=tags,
        project_ids=project_ids,
    )


def prepare_event_draft(
    root: Path,
    *,
    title: str,
    slug: str,
    created_at: str,
    event_date: str,
    source_ids: list[str],
    companies: list[str],
    technologies: list[str],
    products: list[str],
    thesis_links: list[str],
    confidence: float,
    tags: list[str],
    project_ids: list[str] | None = None,
) -> tuple[Path, str]:
    project_ids = project_ids or ["PRJ-001"]
    validate_slug(slug)
    if not is_iso_date(created_at) or not is_iso_date(event_date):
        raise ValueError("created_at and event_date must be YYYY-MM-DD")
    if not source_ids:
        raise ValueError("at least one source_id is required")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating an Event")
    by_id = {obj.object_id: obj for obj in objects}
    ensure_known_ids(project_ids, "project", by_id, "project_ids")
    ensure_known_ids(source_ids, "source", by_id, "source_ids")
    ensure_known_ids(companies, "company", by_id, "companies")
    ensure_known_ids(thesis_links, "thesis", by_id, "thesis_links")
    ensure_taxonomy(
        technologies + tags,
        taxonomy_codes(root),
        "taxonomy fields",
    )
    object_id = next_object_id(objects, "event", event_date)
    relative = Path("04_Evidence/Events") / f"{object_id}-{slug}.md"
    return relative, render_event_draft(
        object_id=object_id,
        title=title,
        created_at=created_at,
        event_date=event_date,
        source_ids=source_ids,
        companies=companies,
        technologies=technologies,
        products=products,
        thesis_links=thesis_links,
        confidence=confidence,
        tags=tags,
        project_ids=project_ids,
    )


def prepare_report_draft(
    root: Path,
    *,
    title: str,
    slug: str,
    created_at: str,
    period_start: str,
    period_end: str,
    thesis_ids: list[str],
    evidence_ids: list[str],
    tags: list[str],
    project_ids: list[str] | None = None,
) -> tuple[Path, str]:
    project_ids = project_ids or ["PRJ-001"]
    validate_slug(slug)
    for value in (created_at, period_start, period_end):
        if not is_iso_date(value):
            raise ValueError("report dates must be YYYY-MM-DD")
    if period_start > period_end:
        raise ValueError("period_start must not be after period_end")
    if not evidence_ids:
        raise ValueError("at least one evidence_id is required")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating a Report")
    by_id = {obj.object_id: obj for obj in objects}
    ensure_known_ids(project_ids, "project", by_id, "project_ids")
    ensure_known_ids(thesis_ids, "thesis", by_id, "thesis_ids")
    ensure_known_ids(evidence_ids, "event", by_id, "evidence_ids")
    ensure_taxonomy(tags, taxonomy_codes(root), "tags")
    object_id = f"RPT-{created_at.replace('-', '')}-{slug}"
    if object_id in by_id:
        raise ValueError(f"report id already exists: {object_id}")
    relative = Path("06_Reports/Topics") / f"{object_id}.md"
    return relative, render_report_draft(
        object_id=object_id,
        title=title,
        created_at=created_at,
        period_start=period_start,
        period_end=period_end,
        thesis_ids=thesis_ids,
        evidence_ids=evidence_ids,
        tags=tags,
        project_ids=project_ids,
    )


def write_new_file(root: Path, relative: Path, content: str) -> Path:
    target = relative if relative.is_absolute() else root / relative
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {target}")
    transaction = FileTransaction(root)
    transaction.stage_create(relative, content)
    try:
        return transaction.commit()[0]
    except TransactionError as exc:
        if "create target already exists" in str(exc):
            raise FileExistsError(
                f"refusing to overwrite existing file: {target}"
            ) from exc
        raise


def source_extraction_updates(
    root: Path,
    source_ids: list[str],
    updated_at: str,
) -> dict[Path, str]:
    if not is_iso_date(updated_at):
        raise ValueError("updated_at must be YYYY-MM-DD")
    objects, _ = validate_repository(root)
    by_id = {obj.object_id: obj for obj in objects}
    updates: dict[Path, str] = {}
    for source_id in source_ids:
        source = by_id.get(source_id)
        if source is None or source.object_type != "source":
            raise ValueError(f"source_ids references missing Source {source_id}")
        if checklist_item_checked(source.body, "Event extraction completed"):
            continue
        text = source.path.read_text(encoding="utf-8")
        unchecked = "- [ ] Event extraction completed"
        if unchecked not in text:
            raise ValueError(
                f"{source_id} is missing the Event extraction checklist item"
            )
        existing_value = source.metadata.get("updated_at")
        existing_updated_at = (
            str(existing_value) if is_iso_date(existing_value) else updated_at
        )
        effective_date = max(existing_updated_at, updated_at)
        text = text.replace(unchecked, "- [x] Event extraction completed", 1)
        text = re.sub(
            r"(?m)^updated_at:\s*.*$",
            f"updated_at: {effective_date}",
            text,
            count=1,
        )
        updates[source.path] = text
    return updates


def apply_event_draft(
    root: Path,
    relative: Path,
    content: str,
    source_ids: list[str],
    updated_at: str,
) -> list[Path]:
    root = root.resolve()
    updates = source_extraction_updates(root, source_ids, updated_at)
    transaction = FileTransaction(root)
    transaction.stage_create(relative, content)
    for path, updated_content in updates.items():
        transaction.stage_replace(path, updated_content)
    return transaction.commit()
