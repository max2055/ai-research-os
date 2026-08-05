"""Research quality metrics, immutable snapshots and comparisons."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from research_os.domain.policies import REVIEW_STATUSES, is_iso_date
from research_os.services.drafts import write_new_file
from research_os.services.indexing import (
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.projects import objects_for_project
from research_os.services.validation import validate_repository

METRICS_SCHEMA_VERSION = 1
SOURCE_GRADES = frozenset({"A", "B", "C", "D"})


def research_metrics(
    root: Path,
    as_of: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or date.today().isoformat()
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if project_id:
        objects = objects_for_project(objects, project_id)
        scoped_paths = {obj.path for obj in objects}
        findings = [finding for finding in findings if finding.path in scoped_paths]
    by_type = {
        object_type: [obj for obj in objects if obj.object_type == object_type]
        for object_type in ("source", "event", "thesis", "company", "report")
    }
    object_counts: dict[str, dict[str, int]] = {}
    for object_type, rows in by_type.items():
        object_counts[object_type] = {
            "total": len(rows),
            **{
                status: sum(obj.metadata.get("review_status") == status for obj in rows)
                for status in sorted(REVIEW_STATUSES)
            },
        }

    events = by_type["event"]
    sources = by_type["source"]
    used_source_ids = {
        str(source_id)
        for event in events
        for source_id in event.metadata.get("source_ids", [])
    }
    source_grades = {
        grade: sum(obj.metadata.get("source_grade") == grade for obj in sources)
        for grade in sorted(SOURCE_GRADES)
    }
    pending_source_refs = {
        str(source_id)
        for event in events
        if event.metadata.get("review_status") == "reviewed"
        for source_id in event.metadata.get("source_ids", [])
        if any(
            source.object_id == source_id
            and source.metadata.get("review_status") != "reviewed"
            for source in sources
        )
    }
    event_source_links = sum(len(obj.metadata.get("source_ids", [])) for obj in events)
    review_decisions = {"approve": 0, "reject": 0}
    for event in events:
        match = re.search(
            r"(?m)^- Decision:\s*(approve|reject)\s*$",
            event.body,
        )
        if match:
            review_decisions[match.group(1)] += 1

    theses = by_type["thesis"]
    thesis_rows: list[dict[str, Any]] = []
    for thesis in sorted(theses, key=lambda obj: obj.object_id):
        supporting = thesis.metadata.get("supporting_evidence", [])
        contradicting = thesis.metadata.get("contradicting_evidence", [])
        thesis_rows.append(
            {
                "id": thesis.object_id,
                "confidence": thesis.metadata.get("confidence"),
                "supporting": len(supporting),
                "contradicting": len(contradicting),
                "review_status": thesis.metadata.get("review_status"),
                "review_date": thesis.metadata.get("review_date"),
            }
        )

    companies = by_type["company"]
    reviewed_event_ids = {
        event.object_id
        for event in events
        if event.metadata.get("review_status") == "reviewed"
    }
    companies_with_reviewed_evidence = sum(
        bool(set(obj.metadata.get("evidence_ids", [])) & reviewed_event_ids)
        for obj in companies
    )
    rendered = (
        render_project_indexes(objects, project_id)
        if project_id
        else render_indexes(objects)
    )
    drift = index_drift(root, rendered)
    errors = [item for item in findings if item.level == "error"]
    warnings = [item for item in findings if item.level == "warning"]
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "as_of": as_of,
        "project_id": project_id,
        "state": {
            "reviewed_event_ids": sorted(
                event.object_id
                for event in events
                if event.metadata.get("review_status") == "reviewed"
            ),
        },
        "object_counts": object_counts,
        "review_queue_total": sum(
            obj.metadata.get("review_status") == "pending" for obj in objects
        ),
        "source_quality": {
            "grades": source_grades,
            "archived": sum(bool(obj.metadata.get("asset_paths")) for obj in sources),
            "processed": sum(
                obj.metadata.get("processing_status") == "processed" for obj in sources
            ),
            "used_by_event": len(used_source_ids),
            "unused": len(sources) - len(used_source_ids),
            "conversion_rate": (
                round(len(used_source_ids) / len(sources), 4) if sources else 0
            ),
            "pending_sources_used_by_reviewed_events": len(pending_source_refs),
        },
        "evidence_quality": {
            "event_source_links": event_source_links,
            "average_sources_per_event": (
                round(event_source_links / len(events), 4) if events else 0
            ),
            "events_without_thesis_links": sum(
                not obj.metadata.get("thesis_links") for obj in events
            ),
            "review_decisions": review_decisions,
        },
        "thesis_health": {
            "items": thesis_rows,
            "without_supporting": sum(row["supporting"] == 0 for row in thesis_rows),
            "without_contradicting": sum(
                row["contradicting"] == 0 for row in thesis_rows
            ),
            "average_confidence": (
                round(
                    sum(float(row["confidence"]) for row in thesis_rows)
                    / len(thesis_rows),
                    4,
                )
                if thesis_rows
                else 0
            ),
        },
        "knowledge_and_reports": {
            "companies_with_reviewed_evidence": (companies_with_reviewed_evidence),
            "company_coverage_rate": (
                round(companies_with_reviewed_evidence / len(companies), 4)
                if companies
                else 0
            ),
            "final_reviewed_reports": sum(
                obj.metadata.get("status") == "final"
                and obj.metadata.get("review_status") == "reviewed"
                for obj in by_type["report"]
            ),
        },
        "system_health": {
            "validation_errors": len(errors),
            "validation_warnings": len(warnings),
            "index_drift_files": len(drift),
        },
    }


def render_metrics_markdown(metrics: dict[str, Any]) -> str:
    counts = metrics["object_counts"]
    source = metrics["source_quality"]
    evidence = metrics["evidence_quality"]
    thesis = metrics["thesis_health"]
    knowledge = metrics["knowledge_and_reports"]
    health = metrics["system_health"]
    scope = f" — {metrics['project_id']}" if metrics.get("project_id") else ""
    lines = [
        f"# Research Quality Metrics{scope} — {metrics['as_of']}",
        "",
        f"Schema version: {metrics['schema_version']}",
        "",
        "## Objects",
        "",
        "| Type | Total | Pending | Reviewed | Rejected | Superseded |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for object_type in ("source", "event", "thesis", "company", "report"):
        row = counts[object_type]
        lines.append(
            f"| {object_type} | {row['total']} | {row['pending']} | "
            f"{row['reviewed']} | {row['rejected']} | "
            f"{row['superseded']} |"
        )
    lines += [
        "",
        "## Source and Evidence",
        "",
        f"- Source→Event conversion: {source['used_by_event']}/"
        f"{counts['source']['total']} ({source['conversion_rate']:.1%})",
        f"- Unused Sources: {source['unused']}",
        f"- Sources with archived assets: {source['archived']}",
        f"- Sources with processed text: {source['processed']}",
        "- Pending Sources used by reviewed Events: "
        f"{source['pending_sources_used_by_reviewed_events']}",
        f"- Average Sources per Event: {evidence['average_sources_per_event']:.2f}",
        f"- Events without Thesis links: {evidence['events_without_thesis_links']}",
        f"- Event review decisions: {evidence['review_decisions']}",
        "",
        "## Thesis health",
        "",
        "| Thesis | Confidence | Supporting | Contradicting | Review status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in thesis["items"]:
        lines.append(
            f"| {row['id']} | {float(row['confidence']):.2f} | "
            f"{row['supporting']} | {row['contradicting']} | "
            f"{row['review_status']} |"
        )
    lines += [
        "",
        f"- Theses without supporting Evidence: {thesis['without_supporting']}",
        f"- Theses without contradicting Evidence: {thesis['without_contradicting']}",
        f"- Average Thesis confidence: {thesis['average_confidence']:.2f}",
        "",
        "## Knowledge, reports and system",
        "",
        "- Companies with reviewed Evidence: "
        f"{knowledge['companies_with_reviewed_evidence']}/"
        f"{counts['company']['total']} "
        f"({knowledge['company_coverage_rate']:.1%})",
        f"- Final reviewed Reports: {knowledge['final_reviewed_reports']}",
        f"- Review queue: {metrics['review_queue_total']}",
        f"- Validation errors: {health['validation_errors']}",
        f"- Validation warnings: {health['validation_warnings']}",
        f"- Index drift files: {health['index_drift_files']}",
    ]
    return "\n".join(lines) + "\n"


def metrics_json(metrics: dict[str, Any]) -> str:
    return json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def metrics_snapshot_path(
    as_of: str,
    project_id: str | None = None,
) -> Path:
    scope = f"-{project_id}" if project_id else ""
    return (
        Path("05_Research")
        / "Reviews"
        / "Snapshots"
        / f"METRICS{scope}-{as_of.replace('-', '')}.json"
    )


def write_metrics_snapshot(root: Path, metrics: dict[str, Any]) -> Path:
    relative = metrics_snapshot_path(
        str(metrics["as_of"]),
        metrics.get("project_id"),
    )
    return write_new_file(root, relative, metrics_json(metrics))


def load_metrics_snapshot(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read metrics snapshot {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("metrics snapshot root must be an object")
    if value.get("schema_version") != METRICS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported metrics schema_version {value.get('schema_version')!r}"
        )
    if not is_iso_date(value.get("as_of")):
        raise ValueError("metrics snapshot has invalid as_of")
    return value


def metric_comparison_rows(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[tuple[str, float, float]]:
    rows: list[tuple[str, float, float]] = []
    for object_type in ("source", "event", "thesis", "company", "report"):
        for status in ("total", "pending", "reviewed"):
            rows.append(
                (
                    f"{object_type}.{status}",
                    float(baseline["object_counts"][object_type][status]),
                    float(current["object_counts"][object_type][status]),
                )
            )
    paths = (
        ("review_queue_total", ("review_queue_total",)),
        ("source.conversion_rate", ("source_quality", "conversion_rate")),
        (
            "source.pending_used_by_reviewed_events",
            ("source_quality", "pending_sources_used_by_reviewed_events"),
        ),
        (
            "evidence.events_without_thesis_links",
            ("evidence_quality", "events_without_thesis_links"),
        ),
        ("thesis.without_supporting", ("thesis_health", "without_supporting")),
        (
            "thesis.without_contradicting",
            ("thesis_health", "without_contradicting"),
        ),
        (
            "thesis.average_confidence",
            ("thesis_health", "average_confidence"),
        ),
        (
            "company.coverage_rate",
            ("knowledge_and_reports", "company_coverage_rate"),
        ),
        (
            "report.final_reviewed",
            ("knowledge_and_reports", "final_reviewed_reports"),
        ),
        ("system.validation_errors", ("system_health", "validation_errors")),
        (
            "system.validation_warnings",
            ("system_health", "validation_warnings"),
        ),
        (
            "system.index_drift_files",
            ("system_health", "index_drift_files"),
        ),
    )
    for label, path in paths:
        old: Any = baseline
        new: Any = current
        for key in path:
            old = old[key]
            new = new[key]
        rows.append((label, float(old), float(new)))
    return rows


def render_metrics_comparison(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> str:
    rows = metric_comparison_rows(baseline, current)
    lines = [
        f"# Metrics comparison: {baseline['as_of']} → {current['as_of']}",
        "",
        "| Metric | Baseline | Current | Delta |",
        "|---|---:|---:|---:|",
    ]
    for label, old, new in rows:
        delta = new - old
        lines.append(f"| {label} | {old:g} | {new:g} | {delta:+g} |")
    changed = sum(old != new for _, old, new in rows)
    lines += ["", f"Changed metrics: {changed}/{len(rows)}"]
    return "\n".join(lines) + "\n"
