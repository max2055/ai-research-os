"""Reviewable Event, Report and knowledge-proposal generation workflows."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.drafts import (
    ensure_known_ids,
    ensure_taxonomy,
    next_object_id,
    validate_slug,
    write_new_file,
    yaml_list,
)
from research_os.services.validation import taxonomy_codes, validate_repository


class StrictSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FactSpec(StrictSpec):
    text: str
    source_id: str
    quote: str
    asset_path: str | None = None


class ThesisImpactSpec(StrictSpec):
    thesis_id: str
    relationship: Literal["supporting", "contradicting", "contextual"]
    explanation: str
    proposed_confidence_change: str = "0.00"


class EventDraftSpec(StrictSpec):
    title: str
    slug: str
    created_at: str
    event_date: str
    source_ids: list[str] = Field(min_length=1)
    companies: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    facts: list[FactSpec] = Field(min_length=1)
    inferences: list[str] = Field(min_length=1)
    research_judgment: str
    thesis_impacts: list[ThesisImpactSpec] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(min_length=1)
    unknowns: list[str] = Field(min_length=1)
    follow_up_indicators: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=lambda: ["PRJ-001"])


class ReportDraftSpec(StrictSpec):
    title: str
    slug: str
    created_at: str
    period_start: str
    period_end: str
    evidence_ids: list[str] = Field(default_factory=list)
    thesis_ids: list[str] = Field(default_factory=list)
    report_type: Literal["daily", "weekly", "topic", "investment_memo"] = "topic"
    version: str
    supersedes: str | None = None
    tags: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=lambda: ["PRJ-001"])


class CitationAnchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_id: str
    source_id: str
    asset_path: str
    locator: str
    quote: str
    quote_sha256: str


def load_spec[SpecType: BaseModel](
    path: Path,
    model: type[SpecType],
) -> SpecType:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read workflow spec {path}: {exc}") from exc
    return model.model_validate(payload)


def _repository_objects(
    root: Path,
) -> tuple[list[ResearchObject], dict[str, ResearchObject]]:
    objects, findings = validate_repository(root)
    errors = [finding for finding in findings if finding.level == "error"]
    if errors:
        raise ValueError("repository validation must pass before draft generation")
    return objects, {obj.object_id: obj for obj in objects}


def _non_placeholder(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized or "TODO" in normalized.upper():
        raise ValueError(f"{field} must be substantive and cannot contain TODO")
    return normalized


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _yaml_scalar(value: str | None) -> str:
    return "" if value is None else json.dumps(value, ensure_ascii=False)


def _extracted_asset(source: ResearchObject, requested: str | None) -> Path:
    paths = [Path(str(value)) for value in source.metadata.get("asset_paths", [])]
    extracted = [path for path in paths if str(path).endswith(".extracted.txt")]
    if requested:
        selected = Path(requested)
        if selected not in extracted:
            raise ValueError(
                f"{source.object_id} does not own extracted asset {requested}"
            )
        return selected
    if not extracted:
        raise ValueError(f"{source.object_id} has no processed text asset")
    return extracted[-1]


def _anchor_for_fact(
    root: Path,
    fact_id: str,
    fact: FactSpec,
    source: ResearchObject,
) -> CitationAnchor:
    if source.metadata.get("processing_status") != "processed":
        raise ValueError(f"{fact.source_id} must be processed before Event generation")
    relative = _extracted_asset(source, fact.asset_path)
    text = (root / relative).read_text(encoding="utf-8")
    quote = _non_placeholder(fact.quote, f"{fact_id}.quote")
    offset = text.find(quote)
    if offset < 0:
        raise ValueError(f"{fact_id} quote is not present in {relative}")
    start = text.count("\n", 0, offset) + 1
    end = start + quote.count("\n")
    return CitationAnchor(
        fact_id=fact_id,
        source_id=fact.source_id,
        asset_path=str(relative),
        locator=f"L{start}" if start == end else f"L{start}-L{end}",
        quote=quote,
        quote_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
    )


def source_independence_groups(
    source_ids: list[str],
    by_id: dict[str, ResearchObject],
) -> list[list[str]]:
    selected = set(source_ids)

    def roots(source_id: str, trail: frozenset[str]) -> frozenset[str]:
        if source_id in trail:
            raise ValueError(f"Source upstream cycle includes {source_id}")
        source = by_id[source_id]
        upstream = [
            str(value) for value in source.metadata.get("upstream_source_ids", [])
        ]
        if not upstream:
            return frozenset({source_id})
        result: set[str] = set()
        for upstream_id in upstream:
            if upstream_id not in by_id:
                raise ValueError(f"unknown upstream Source {upstream_id}")
            result.update(roots(upstream_id, trail | {source_id}))
        return frozenset(result)

    root_sets = {source_id: roots(source_id, frozenset()) for source_id in selected}
    groups: list[set[str]] = []
    for source_id in sorted(selected):
        overlapping = [
            group
            for group in groups
            if any(root_sets[item] & root_sets[source_id] for item in group)
        ]
        if not overlapping:
            groups.append({source_id})
            continue
        merged = {source_id}
        for group in overlapping:
            merged.update(group)
            groups.remove(group)
        groups.append(merged)
    return sorted([sorted(group) for group in groups], key=lambda row: row[0])


def _render_anchor_metadata(anchors: list[CitationAnchor]) -> str:
    lines = ["citation_anchors:"]
    for anchor in anchors:
        lines += [
            f"- fact_id: {anchor.fact_id}",
            f"  source_id: {anchor.source_id}",
            f"  asset_path: {_yaml_scalar(anchor.asset_path)}",
            f"  locator: {anchor.locator}",
            f"  quote: {_yaml_scalar(anchor.quote)}",
            f"  quote_sha256: {anchor.quote_sha256}",
        ]
    return "\n".join(lines)


def _bullet_lines(values: list[str]) -> str:
    return "\n".join(f"- {_non_placeholder(value, 'list item')}" for value in values)


def prepare_reviewable_event_draft(
    root: Path,
    spec: EventDraftSpec,
) -> tuple[Path, str]:
    root = root.resolve()
    validate_slug(spec.slug)
    if not is_iso_date(spec.created_at) or not is_iso_date(spec.event_date):
        raise ValueError("created_at and event_date must be YYYY-MM-DD")
    objects, by_id = _repository_objects(root)
    ensure_known_ids(spec.project_ids, "project", by_id, "project_ids")
    ensure_known_ids(spec.source_ids, "source", by_id, "source_ids")
    ensure_known_ids(spec.companies, "company", by_id, "companies")
    ensure_taxonomy(
        spec.technologies + spec.tags,
        taxonomy_codes(root),
        "taxonomy fields",
    )
    fact_source_ids = {fact.source_id for fact in spec.facts}
    if fact_source_ids - set(spec.source_ids):
        raise ValueError("every Fact source must be included in source_ids")
    impacts = {impact.thesis_id: impact for impact in spec.thesis_impacts}
    if len(impacts) != len(spec.thesis_impacts):
        raise ValueError("each Thesis may appear only once in thesis_impacts")
    thesis_links = sorted(impacts)
    ensure_known_ids(thesis_links, "thesis", by_id, "thesis_links")
    _non_placeholder(spec.research_judgment, "research_judgment")
    anchors = [
        _anchor_for_fact(root, f"F{index}", fact, by_id[fact.source_id])
        for index, fact in enumerate(spec.facts, start=1)
    ]
    groups = source_independence_groups(spec.source_ids, by_id)
    fingerprint = _fingerprint(
        {
            "event_date": spec.event_date,
            "source_ids": sorted(spec.source_ids),
            "facts": [fact.model_dump(mode="json") for fact in spec.facts],
            "thesis_impacts": [
                impact.model_dump(mode="json") for impact in spec.thesis_impacts
            ],
        }
    )
    duplicate = next(
        (
            obj.object_id
            for obj in objects
            if obj.object_type == "event"
            and obj.metadata.get("generation_fingerprint") == fingerprint
        ),
        None,
    )
    if duplicate:
        raise ValueError(f"duplicate generated Event matches {duplicate}")
    object_id = next_object_id(objects, "event", spec.event_date)
    relative = Path("04_Evidence/Events") / f"{object_id}-{spec.slug}.md"
    facts: list[str] = []
    for fact, anchor in zip(spec.facts, anchors, strict=True):
        facts += [
            f"- **{anchor.fact_id}** — {_non_placeholder(fact.text, anchor.fact_id)}",
            f"  - Source: `{anchor.source_id}`",
            f"  - Anchor: `{anchor.asset_path}#{anchor.locator}`",
            f"  - Quote: {_yaml_scalar(anchor.quote)}",
        ]
    impact_rows: list[str] = []
    for impact in spec.thesis_impacts:
        explanation = _non_placeholder(
            impact.explanation,
            "impact explanation",
        )
        confidence_proposal = _non_placeholder(
            impact.proposed_confidence_change,
            "confidence proposal",
        )
        impact_rows.append(
            f"| {impact.thesis_id} | {impact.relationship} | "
            f"{explanation} | {confidence_proposal} |"
        )
    if not impact_rows:
        impact_rows = ["| — | contextual | No Thesis relationship proposed. | 0.00 |"]
    group_rows = [
        f"| IG-{index:02d} | {', '.join(group)} | "
        f"{'shared upstream; count once' if len(group) > 1 else 'independent root'} |"
        for index, group in enumerate(groups, start=1)
    ]
    content = f"""---
id: {object_id}
type: event
title: {_yaml_scalar(spec.title)}
created_at: {spec.created_at}
updated_at: {spec.created_at}
schema_version: 1
project_ids: {yaml_list(spec.project_ids)}
status: active
review_status: pending
event_date: {spec.event_date}
source_ids: {yaml_list(spec.source_ids)}
companies: {yaml_list(spec.companies)}
technologies: {yaml_list(spec.technologies)}
products: {yaml_list(spec.products)}
thesis_links: {yaml_list(thesis_links)}
confidence: {spec.confidence:.2f}
generation_method: structured
generation_fingerprint: {fingerprint}
{_render_anchor_metadata(anchors)}
source_independence_groups: {json.dumps(groups)}
tags: {yaml_list(spec.tags)}
---

# Event

> Structured draft. Facts and anchors require human review before authority.

## Facts

{chr(10).join(facts)}

## Inferences

{_bullet_lines(spec.inferences)}

## Research judgment

{_non_placeholder(spec.research_judgment, "research_judgment")}

## Thesis impact

| Thesis ID | Relationship | Explanation | Proposed confidence change |
|---|---|---|---|
{chr(10).join(impact_rows)}

## Source independence

| Group | Sources | Treatment |
|---|---|---|
{chr(10).join(group_rows)}

## Alternative explanations

{_bullet_lines(spec.alternative_explanations)}

## Unknowns

{_bullet_lines(spec.unknowns)}

## Follow-up indicators

{_bullet_lines(spec.follow_up_indicators)}
"""
    return relative, content


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _impact_rows(event: ResearchObject) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in _section(event.body, "Thesis impact").splitlines():
        match = re.match(
            r"^\|\s*(THS-\d{3})\s*\|\s*"
            r"(supporting|contradicting|contextual)\s*\|\s*(.*?)\s*\|",
            line,
        )
        if match:
            rows.append((match.group(1), match.group(2), match.group(3)))
    return rows


def incremental_reviewed_event_ids(
    events: list[ResearchObject],
    baseline: dict[str, Any],
) -> list[str]:
    prior = {
        str(value) for value in baseline.get("state", {}).get("reviewed_event_ids", [])
    }
    reviewed = [
        event for event in events if event.metadata.get("review_status") == "reviewed"
    ]
    if prior:
        return sorted(
            event.object_id for event in reviewed if event.object_id not in prior
        )
    as_of = baseline.get("as_of")
    if not is_iso_date(as_of):
        raise ValueError("baseline snapshot lacks valid as_of")
    return sorted(
        event.object_id
        for event in reviewed
        if str(event.metadata.get("created_at", "")) > str(as_of)
        or str(event.metadata.get("updated_at", "")) > str(as_of)
    )


def prepare_synthesized_report(
    root: Path,
    spec: ReportDraftSpec,
    *,
    baseline: dict[str, Any] | None = None,
) -> tuple[Path, str]:
    root = root.resolve()
    validate_slug(spec.slug)
    if not re.fullmatch(r"v\d+\.\d+(?:\.\d+)?", spec.version):
        raise ValueError("version must use vMAJOR.MINOR or vMAJOR.MINOR.PATCH")
    if not all(
        is_iso_date(value)
        for value in (spec.created_at, spec.period_start, spec.period_end)
    ):
        raise ValueError("report dates must be YYYY-MM-DD")
    if spec.period_start > spec.period_end:
        raise ValueError("period_start must not be after period_end")
    objects, by_id = _repository_objects(root)
    evidence_ids = list(spec.evidence_ids)
    events = [obj for obj in objects if obj.object_type == "event"]
    if baseline is not None:
        incremental = incremental_reviewed_event_ids(events, baseline)
        evidence_ids = (
            incremental
            if not evidence_ids
            else [event_id for event_id in evidence_ids if event_id in incremental]
        )
    if not evidence_ids:
        raise ValueError("no reviewed Evidence selected for report synthesis")
    ensure_known_ids(spec.project_ids, "project", by_id, "project_ids")
    ensure_known_ids(evidence_ids, "event", by_id, "evidence_ids")
    ensure_known_ids(spec.thesis_ids, "thesis", by_id, "thesis_ids")
    ensure_taxonomy(spec.tags, taxonomy_codes(root), "tags")
    selected = [by_id[event_id] for event_id in evidence_ids]
    non_reviewed = [
        event.object_id
        for event in selected
        if event.metadata.get("review_status") != "reviewed"
    ]
    if non_reviewed:
        raise ValueError(
            "report synthesis requires reviewed Evidence: " + ", ".join(non_reviewed)
        )
    if spec.supersedes:
        prior = by_id.get(spec.supersedes)
        if prior is None or prior.object_type != "report":
            raise ValueError(f"supersedes references unknown Report {spec.supersedes}")
        if prior.metadata.get("review_status") != "reviewed":
            raise ValueError("superseded Report must be reviewed")
    inferred_theses = sorted(
        {
            thesis_id
            for event in selected
            for thesis_id in event.metadata.get("thesis_links", [])
        }
    )
    thesis_ids = sorted(set(spec.thesis_ids) | set(inferred_theses))
    source_ids = sorted(
        {
            str(source_id)
            for event in selected
            for source_id in event.metadata.get("source_ids", [])
        }
    )
    groups = source_independence_groups(source_ids, by_id)
    fingerprint = _fingerprint(
        {
            "report_type": spec.report_type,
            "version": spec.version,
            "evidence_ids": sorted(evidence_ids),
            "baseline_as_of": baseline.get("as_of") if baseline else None,
        }
    )
    duplicate = next(
        (
            obj.object_id
            for obj in objects
            if obj.object_type == "report"
            and obj.metadata.get("generation_fingerprint") == fingerprint
        ),
        None,
    )
    if duplicate:
        raise ValueError(f"duplicate generated Report matches {duplicate}")
    object_id = f"RPT-{spec.created_at.replace('-', '')}-{spec.slug}"
    if object_id in by_id:
        raise ValueError(f"report id already exists: {object_id}")
    relative = Path("06_Reports/Topics") / f"{object_id}.md"
    facts = "\n\n".join(
        f"### {event.object_id} — {event.metadata['title']}\n\n"
        f"{_section(event.body, 'Facts')}"
        for event in selected
    )
    inferences = "\n\n".join(
        f"- **{event.object_id}:** "
        f"{_section(event.body, 'Inferences').replace(chr(10), ' ')}"
        for event in selected
    )
    judgments = "\n\n".join(
        f"- **{event.object_id}:** "
        f"{_section(event.body, 'Research judgment').replace(chr(10), ' ')}"
        for event in selected
    )
    impact_rows = [
        f"| {thesis_id} | {relationship} | {event.object_id} | {explanation} |"
        for event in selected
        for thesis_id, relationship, explanation in _impact_rows(event)
    ]
    contradicting = [row for row in impact_rows if "| contradicting |" in row]
    alternatives = [
        f"- **{event.object_id}:** "
        f"{_section(event.body, 'Alternative explanations').replace(chr(10), ' ')}"
        for event in selected
    ]
    unknowns = [
        f"- **{event.object_id}:** "
        f"{_section(event.body, 'Unknowns').replace(chr(10), ' ')}"
        for event in selected
    ]
    indicators = [
        f"- **{event.object_id}:** "
        f"{_section(event.body, 'Follow-up indicators').replace(chr(10), ' ')}"
        for event in selected
    ]
    group_rows = [
        f"| IG-{index:02d} | {', '.join(group)} | "
        f"{'count once' if len(group) > 1 else 'independent'} |"
        for index, group in enumerate(groups, start=1)
    ]
    impact_table = (
        "\n".join(impact_rows)
        if impact_rows
        else "| — | contextual | — | No Thesis proposal. |"
    )
    contradicting_text = (
        "\n".join(contradicting)
        if contradicting
        else (
            "No selected Event proposes a contradicting relationship; "
            "this absence is a research gap."
        )
    )
    content = f"""---
id: {object_id}
type: report
title: {_yaml_scalar(spec.title)}
created_at: {spec.created_at}
updated_at: {spec.created_at}
schema_version: 1
project_ids: {yaml_list(spec.project_ids)}
status: draft
review_status: pending
report_type: {spec.report_type}
period_start: {spec.period_start}
period_end: {spec.period_end}
thesis_ids: {yaml_list(thesis_ids)}
evidence_ids: {yaml_list(evidence_ids)}
version: {spec.version}
supersedes: {spec.supersedes or ""}
superseded_by:
generation_method: structured
generation_fingerprint: {fingerprint}
baseline_snapshot: {_yaml_scalar(str(baseline.get("as_of")) if baseline else None)}
tags: {yaml_list(spec.tags)}
---

# {spec.title}

> Structured synthesis from reviewed Evidence. This draft remains pending human review.

## One-sentence conclusion

The selected {len(selected)} reviewed Events show material change signals, while
their alternative explanations and unknowns prevent an automatic investment conclusion.

## Research question and scope

This {spec.report_type} draft covers {spec.period_start} through {spec.period_end}
and only the explicitly selected reviewed Evidence IDs.

## Facts

{facts}

## Inferences

{inferences}

## Research judgment

{judgments}

## Thesis assessment

| Thesis | Relationship | Evidence | Explanation |
|---|---|---|---|
{impact_table}

## Contradicting Evidence

{contradicting_text}

## Source independence

| Group | Sources | Counting treatment |
|---|---|---|
{chr(10).join(group_rows)}

## Contrarian view

{chr(10).join(alternatives)}

## Falsification conditions

The proposed interpretations should be weakened if the listed alternative
explanations are supported or if the follow-up indicators fail to confirm change.

## Key indicators

{chr(10).join(indicators)}

## Investment implications

The Evidence supports research prioritization only. Security selection still requires
valuation, expectations, unit economics and independently reviewed company evidence.

## Risks and unknowns

{chr(10).join(unknowns)}

## Next research actions

{chr(10).join(indicators)}
"""
    return relative, content


def prepare_company_update_proposal(
    root: Path,
    *,
    company_id: str,
    event_ids: list[str],
    created_at: str,
) -> tuple[Path, str]:
    root = root.resolve()
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    _, by_id = _repository_objects(root)
    company = by_id.get(company_id)
    if company is None or company.object_type != "company":
        raise ValueError(f"unknown Company {company_id}")
    if not event_ids:
        raise ValueError("at least one reviewed Event is required")
    ensure_known_ids(event_ids, "event", by_id, "event_ids")
    events = [by_id[event_id] for event_id in event_ids]
    invalid = [
        event.object_id
        for event in events
        if event.metadata.get("review_status") != "reviewed"
        or company_id not in event.metadata.get("companies", [])
    ]
    if invalid:
        raise ValueError(
            "company proposal requires reviewed, company-linked Events: "
            + ", ".join(invalid)
        )
    folder = root / "05_Research" / "Reviews" / "Knowledge_Proposals"
    numbers = [
        int(match.group(1))
        for path in folder.glob(f"KUP-{created_at.replace('-', '')}-*.md")
        if (match := re.match(r"^KUP-\d{8}-(\d{3})", path.name))
    ]
    proposal_id = f"KUP-{created_at.replace('-', '')}-{max(numbers, default=0) + 1:03d}"
    relative = Path("05_Research/Reviews/Knowledge_Proposals") / f"{proposal_id}.md"
    evidence = "\n\n".join(
        f"### {event.object_id}\n\n{_section(event.body, 'Facts')}" for event in events
    )
    interpretations = "\n".join(
        f"- **{event.object_id}:** "
        f"{_section(event.body, 'Research judgment').replace(chr(10), ' ')}"
        for event in events
    )
    content = f"""---
id: {proposal_id}
type: company_update_proposal
title: {_yaml_scalar(f"Company update proposal: {company_id}")}
created_at: {created_at}
status: pending
target_company_id: {company_id}
evidence_ids: {yaml_list(event_ids)}
---

# Company update proposal: {company_id}

> Non-authoritative proposal. Apply edits to the Company only after human review.

## Reviewed facts

{evidence}

## Proposed interpretation

{interpretations}

## Human decision

- Decision: pending
- Reviewer:
- Notes:
"""
    return relative, content


def apply_company_update_proposal(
    root: Path,
    relative: Path,
    content: str,
) -> Path:
    return write_new_file(root, relative, content)
