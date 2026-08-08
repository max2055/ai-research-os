"""Transactional application of generated research drafts."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from research_os.domain.models import ResearchObject
from research_os.domain.policies import (
    ONTOLOGY_PREDICATES,
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
    if object_type not in {
        "source",
        "event",
        "ontology_assertion",
        "impact_assertion",
        "analysis_run",
    }:
        raise ValueError(
            "next_object_id supports source, event, ontology_assertion, "
            "impact_assertion and analysis_run"
        )
    if not is_iso_date(object_date):
        raise ValueError("object_date must be YYYY-MM-DD")
    prefix = {
        "source": "SRC",
        "event": "EVT",
        "ontology_assertion": "REL",
        "impact_assertion": "IMP",
        "analysis_run": "ANL",
    }[object_type]
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


ENTITY_TYPES = frozenset({"sector", "company"})

# v0.3 extension fields (RCP-v03-003) on a Company; Sector shares the core
# set. All optional; pending by default. No backfill (R1) — these are set
# per-object by humans (WP-120) or by this draft flow.
_COMPANY_EXTRA_FIELDS = (
    "legal_name",
    "company_stage",
    "headquarters",
    "region_primary",
    "coverage_tier",
)


def prepare_entity_draft(
    root: Path,
    *,
    entity_type: str,
    slug: str,
    title: str,
    created_at: str,
    definition: str = "",
    in_scope: list[str] | None = None,
    out_of_scope: list[str] | None = None,
    value_chain_position: str = "",
    key_inputs: list[str] | None = None,
    key_outputs: list[str] | None = None,
    key_metrics: list[str] | None = None,
    core_company_ids: list[str] | None = None,
    tracked_company_ids: list[str] | None = None,
    source_channel_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    sector_ids: list[str] | None = None,
    region_primary: str | None = None,
    coverage_tier: str | None = None,
    legal_name: str | None = None,
    company_stage: str | None = None,
    headquarters: str | None = None,
    aliases: list[str] | None = None,
    tags: list[str] | None = None,
    project_ids: list[str] | None = None,
) -> tuple[Path, str]:
    """Prepare a v0.3 Sector or Company draft (dry-run preview; --apply writes).

    Entity IDs are slug-based (SEG-<slug> / COM-<slug>), permanent and
    unique. A slug already in use is rejected — IDs are never reused
    (RCP-v03-003). project_ids default to []: Sectors and Companies are
    cross-project Universe primitives.
    """
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"entity_type must be one of {sorted(ENTITY_TYPES)}")
    validate_slug(slug)
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating an entity")
    by_id = {obj.object_id: obj for obj in objects}
    prefix = "SEG" if entity_type == "sector" else "COM"
    object_id = f"{prefix}-{slug}"
    if object_id in by_id:
        raise ValueError(f"entity ID already exists: {object_id}")
    # Reference-integrity check (WP-103 owns cross-object existence) is NOT
    # enforced here for sector_ids etc. — the empty-Universe phase must not
    # block creating Companies before Sectors exist. Only format is checked
    # by the schema at validate time.
    project_ids = project_ids or []
    tags = tags or []
    aliases = aliases or []
    if entity_type == "sector":
        relative = Path("02_Knowledge/Sectors") / f"{object_id}.md"
        return relative, render_entity_draft(
            object_id=object_id,
            entity_type="sector",
            title=title,
            created_at=created_at,
            definition=definition,
            in_scope=in_scope or [],
            out_of_scope=out_of_scope or [],
            value_chain_position=value_chain_position,
            key_inputs=key_inputs or [],
            key_outputs=key_outputs or [],
            key_metrics=key_metrics or [],
            core_company_ids=core_company_ids or [],
            tracked_company_ids=tracked_company_ids or [],
            source_channel_ids=source_channel_ids or [],
            evidence_ids=evidence_ids or [],
            sector_ids=[],
            region_primary=region_primary,
            coverage_tier=coverage_tier,
            legal_name=legal_name,
            company_stage=company_stage,
            headquarters=headquarters,
            aliases=aliases,
            tags=tags,
            project_ids=project_ids,
        )
    relative = Path("02_Knowledge/Companies") / f"{object_id}.md"
    return relative, render_entity_draft(
        object_id=object_id,
        entity_type="company",
        title=title,
        created_at=created_at,
        definition=definition,
        in_scope=in_scope or [],
        out_of_scope=out_of_scope or [],
        value_chain_position=value_chain_position,
        key_inputs=key_inputs or [],
        key_outputs=key_outputs or [],
        key_metrics=key_metrics or [],
        core_company_ids=core_company_ids or [],
        tracked_company_ids=tracked_company_ids or [],
        source_channel_ids=source_channel_ids or [],
        evidence_ids=evidence_ids or [],
        sector_ids=sector_ids or [],
        region_primary=region_primary,
        coverage_tier=coverage_tier,
        legal_name=legal_name,
        company_stage=company_stage,
        headquarters=headquarters,
        aliases=aliases,
        tags=tags,
        project_ids=project_ids,
    )


def render_entity_draft(
    *,
    object_id: str,
    entity_type: str,
    title: str,
    created_at: str,
    definition: str,
    in_scope: list[str],
    out_of_scope: list[str],
    value_chain_position: str,
    key_inputs: list[str],
    key_outputs: list[str],
    key_metrics: list[str],
    core_company_ids: list[str],
    tracked_company_ids: list[str],
    source_channel_ids: list[str],
    evidence_ids: list[str],
    sector_ids: list[str],
    region_primary: str | None,
    coverage_tier: str | None,
    legal_name: str | None,
    company_stage: str | None,
    headquarters: str | None,
    aliases: list[str],
    tags: list[str],
    project_ids: list[str],
) -> str:
    if entity_type == "sector":
        extra = (
            f"definition: {yaml_scalar(definition)}\n"
            f"in_scope: {yaml_list(in_scope)}\n"
            f"out_of_scope: {yaml_list(out_of_scope)}\n"
            f"value_chain_position: {yaml_scalar(value_chain_position)}\n"
            f"key_inputs: {yaml_list(key_inputs)}\n"
            f"key_outputs: {yaml_list(key_outputs)}\n"
            f"key_metrics: {yaml_list(key_metrics)}\n"
            f"core_company_ids: {yaml_list(core_company_ids)}\n"
            f"tracked_company_ids: {yaml_list(tracked_company_ids)}\n"
            f"source_channel_ids: {yaml_list(source_channel_ids)}\n"
            f"evidence_ids: {yaml_list(evidence_ids)}\n"
        )
        body = f"""# Sector

## Definition

{definition}

## Value chain position

{value_chain_position}

## In scope

- TODO

## Out of scope

- TODO

## Key inputs / outputs

- Inputs: {", ".join(key_inputs) if key_inputs else "TBD"}
- Outputs: {", ".join(key_outputs) if key_outputs else "TBD"}

## Key metrics

- TODO

## Core companies

- TODO

## Tracked companies

- TODO

## Evidence

- TODO
"""
    else:
        extra = (
            f"aliases: {yaml_list(aliases)}\n"
            f"sector_ids: {yaml_list(sector_ids)}\n"
            f"region_primary: {region_primary if region_primary else ''}\n"
            f"coverage_tier: {coverage_tier if coverage_tier else ''}\n"
            f"legal_name: {yaml_scalar(legal_name) if legal_name else ''}\n"
            f"company_stage: {company_stage if company_stage else ''}\n"
            f"headquarters: {yaml_scalar(headquarters) if headquarters else ''}\n"
            f"key_metric_ids: {yaml_list(key_metrics)}\n"
            f"source_channel_ids: {yaml_list(source_channel_ids)}\n"
            f"evidence_ids: {yaml_list(evidence_ids)}\n"
        )
        body = f"""# Company Profile

## Company role in the value chain

{definition}

## Products

TODO: register product entities (WP-120+).

## Customers and distribution

TODO

## Business model

TODO

## Revenue and profitability

TODO

## Technology strategy

TODO

## Competitive advantages

TODO (label as hypotheses until reviewed)

## Management

TODO

## Risks

TODO

## Valuation context

TODO

## Catalysts

TODO

## Related Thesis

TODO

## Evidence timeline

{evidence_ids if evidence_ids else "None yet"}
"""
    return f"""---
id: {object_id}
type: {entity_type}
title: {yaml_scalar(title)}
created_at: {created_at}
updated_at: {created_at}
schema_version: 2
project_ids: {yaml_list(project_ids)}
status: active
review_status: pending
tags: {yaml_list(tags)}
{extra}---

{body}"""


def prepare_assertion_draft(
    root: Path,
    *,
    subject_id: str,
    predicate: str,
    object_id: str,
    created_at: str,
    valid_from: str,
    as_of: str,
    title: str = "",
    scope: str = "",
    confidence: float = 0.5,
    qualifiers: dict[str, str] | None = None,
    project_ids: list[str] | None = None,
) -> tuple[Path, str]:
    """Prepare an Ontology Assertion (REL-YYYYMMDD-NNN) draft.

    Dry-run preview; --apply writes via output_draft. All assertions are
    created review_status: pending — approving one without reviewed Evidence
    would trip REF003/REF004 (WP-103 rule), so human approval happens only
    after the evidence WP lands.
    """
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    if not is_iso_date(valid_from):
        raise ValueError("valid_from must be YYYY-MM-DD")
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    if predicate not in ONTOLOGY_PREDICATES:
        raise ValueError(f"predicate must be one of {sorted(ONTOLOGY_PREDICATES)}")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError("confidence must be between 0 and 1")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating an assertion")
    by_id = {obj.object_id: obj for obj in objects}
    if subject_id not in by_id:
        raise ValueError(f"subject {subject_id!r} does not exist")
    if object_id not in by_id:
        raise ValueError(f"object {object_id!r} does not exist")
    object_id_full = next_object_id(objects, "ontology_assertion", created_at)
    project_ids = project_ids or []
    relative = Path("05_Research/Assertions") / f"{object_id_full}.md"
    return relative, render_assertion_draft(
        object_id=object_id_full,
        subject_id=subject_id,
        predicate=predicate,
        object_id_target=object_id,
        created_at=created_at,
        valid_from=valid_from,
        as_of=as_of,
        title=title or f"{subject_id} {predicate} {object_id}",
        scope=scope,
        confidence=confidence,
        qualifiers=qualifiers or {},
        project_ids=project_ids,
    )


def render_assertion_draft(
    *,
    object_id: str,
    subject_id: str,
    predicate: str,
    object_id_target: str,
    created_at: str,
    valid_from: str,
    as_of: str,
    title: str,
    scope: str,
    confidence: float,
    qualifiers: dict[str, str],
    project_ids: list[str],
) -> str:
    if qualifiers:
        qualifier_lines = "".join(
            f"    {key}: {yaml_scalar(value)}\n"
            for key, value in sorted(qualifiers.items())
        )
        qualifiers_block = f"qualifiers:\n{qualifier_lines}"
    else:
        qualifiers_block = "qualifiers: {}"
    return f"""---
id: {object_id}
type: ontology_assertion
title: {yaml_scalar(title)}
created_at: {created_at}
updated_at: {created_at}
schema_version: 2
project_ids: {yaml_list(project_ids)}
status: active
review_status: pending
subject_id: {subject_id}
predicate: {predicate}
object_id: {object_id_target}
valid_from: {valid_from}
as_of: {as_of}
evidence_ids: []
source_ids: []
confidence: {confidence}
scope: {yaml_scalar(scope)}
{qualifiers_block}
tags: []
---

# Ontology Assertion

## Assertion

- Subject: {subject_id}
- Predicate: {predicate}
- Object: {object_id_target}
- Valid from: {valid_from}
- As of: {as_of}
- Confidence: {confidence}
- Scope: {scope}

## Evidence

Pending — no Evidence yet. Human approval (review apply --decision approve)
is deferred until the Compute Chain evidence WP lands (reviewed assertions
require >=1 reviewed Evidence, REF003/REF004).

## Notes

- Relation direction is explicit; symmetric predicates (COMPETES_WITH,
  SUBSTITUTES, COMPLEMENTS, PARTNERS_WITH) get reverse edges derived in the
  export layer, not duplicated as authoritative objects (Phase 0-1 §5).
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
