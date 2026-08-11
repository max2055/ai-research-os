"""Research quality metrics, immutable snapshots and comparisons."""

from __future__ import annotations

import json
import re
import sqlite3
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import REVIEW_STATUSES, is_iso_date
from research_os.services import candidate_db
from research_os.services.discovery import due_channels_from_objects
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


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


def pipeline_metrics(
    root: Path,
    as_of: str | None = None,
    *,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Pipeline operational metrics (B-023): freshness/yield/noise/failure.

    Reads the Candidate operational store + repository to report discovery
    throughput, duplicate/noise rate, fetch failure rate and latency, Core
    entity coverage, triage yield (promoted/dismissed) and stale channels.
    Token/LLM cost is not yet tracked (reported as None).
    """
    objects, _ = validate_repository(root)
    return pipeline_metrics_from_objects(
        root,
        objects,
        as_of=as_of,
        db_path=db_path,
    )


def pipeline_metrics_from_objects(
    root: Path,
    objects: list[ResearchObject],
    as_of: str | None = None,
    *,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Compute pipeline metrics from one validated repository snapshot."""
    as_of = as_of or date.today().isoformat()
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    db_path = db_path or candidate_db.candidate_db_path(root)

    discovered_total = 0
    discovered_today = 0
    core_entity_ids: set[str] = set()
    rows: list[sqlite3.Row] = []
    cluster_rows: list[sqlite3.Row] = []
    run_rows: list[sqlite3.Row] = []
    promote_rows: list[sqlite3.Row] = []
    dismiss_rows: list[sqlite3.Row] = []
    inbound_total = 0
    rep_by_cluster: dict[str, tuple[str, str]] = {}
    # 7-day window: duplicate.rate measures duplicates among newly arrived
    # candidates (G4 "duplicate-in-queue" basis), not the store snapshot.
    window_start = (date.fromisoformat(as_of) - timedelta(days=6)).isoformat()
    if db_path.exists():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT candidate_id, discovered_at, status, "
                "duplicate_cluster_id, entity_proposals_json FROM candidates"
            ).fetchall()
            for row in rows:
                discovered_total += 1
                discovered_date = str(row["discovered_at"])[:10]
                if discovered_date == as_of:
                    discovered_today += 1
                if window_start <= discovered_date <= as_of:
                    inbound_total += 1
                entity = _proposal_json(row["entity_proposals_json"])
                if entity.get("status") == "matched" and entity.get("entity_id"):
                    core_entity_ids.add(str(entity["entity_id"]))
                cluster_id = row["duplicate_cluster_id"]
                if cluster_id:
                    cid = str(cluster_id)
                    prior = rep_by_cluster.get(cid)
                    if prior is None or str(row["discovered_at"]) < prior[0]:
                        rep_by_cluster[cid] = (
                            str(row["discovered_at"]),
                            str(row["candidate_id"]),
                        )
            cluster_rows = connection.execute(
                "SELECT duplicate_cluster_id, COUNT(*) AS members "
                "FROM candidates WHERE duplicate_cluster_id IS NOT NULL "
                "GROUP BY duplicate_cluster_id"
            ).fetchall()
            run_rows = connection.execute(
                "SELECT status, started_at, finished_at, http_errors, "
                "parse_errors, retries, cost_estimate FROM discovery_runs"
            ).fetchall()
            promote_rows = connection.execute(
                "SELECT candidate_id, acted_at FROM candidate_actions "
                "WHERE action = 'promote'"
            ).fetchall()
            dismiss_rows = connection.execute(
                "SELECT reason, COUNT(*) AS count FROM candidate_actions "
                "WHERE action = 'dismiss' GROUP BY reason"
            ).fetchall()
        finally:
            connection.close()

    inbound_dups = 0
    for row in rows:
        discovered_date = str(row["discovered_at"])[:10]
        if not (window_start <= discovered_date <= as_of):
            continue
        cluster_id = row["duplicate_cluster_id"]
        if cluster_id:
            rep = rep_by_cluster.get(str(cluster_id))
            if rep and rep[1] != str(row["candidate_id"]):
                inbound_dups += 1

    cluster_members = sum(int(row["members"]) for row in cluster_rows)
    distinct_clusters = len(cluster_rows)
    non_representative = cluster_members - distinct_clusters
    store_rate = (
        round(non_representative / discovered_total, 4) if discovered_total else 0.0
    )
    duplicate_rate = round(inbound_dups / inbound_total, 4) if inbound_total else 0.0

    runs = len(run_rows)
    succeeded = sum(1 for row in run_rows if row["status"] == "succeeded")
    failed = sum(1 for row in run_rows if row["status"] == "failed")
    failure_rate = round(failed / runs, 4) if runs else 0.0
    latencies = [
        (_parse_iso(row["finished_at"]) - _parse_iso(row["started_at"])).total_seconds()
        for row in run_rows
        if row["status"] == "succeeded" and row["finished_at"]
    ]
    median_latency = round(statistics.median(latencies), 1) if latencies else None
    http_errors = sum(int(row["http_errors"] or 0) for row in run_rows)
    parse_errors = sum(int(row["parse_errors"] or 0) for row in run_rows)
    retries = sum(int(row["retries"] or 0) for row in run_rows)
    costs = [float(row["cost_estimate"]) for row in run_rows if row["cost_estimate"]]
    cost_estimate = round(sum(costs), 6) if costs else None

    tier_by_entity = {
        obj.object_id: str(obj.metadata.get("coverage_tier") or "")
        for obj in objects
        if obj.object_type == "company"
    }
    core_matched = sum(
        1 for entity_id in core_entity_ids if tier_by_entity.get(entity_id) == "core"
    )

    # Triage counts come from the append-only action audit, which survives the
    # retention purge of dismissed/expired candidate rows (B-020/ADR retention).
    promoted = len(promote_rows)
    dismissed = sum(int(row["count"]) for row in dismiss_rows)
    triaged = promoted + dismissed
    promoted_rate = round(promoted / triaged, 4) if triaged else 0.0
    dismissed_rate = round(dismissed / triaged, 4) if triaged else 0.0
    top_dismiss = sorted(
        ((str(row["reason"]), int(row["count"])) for row in dismiss_rows),
        key=lambda item: item[1],
        reverse=True,
    )[:5]

    core_covered = {
        str(row["candidate_id"]): str(row["acted_at"]) for row in promote_rows
    }
    conversion_hours = []
    if db_path.exists():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        try:
            for row in connection.execute(
                "SELECT candidate_id, discovered_at FROM candidates "
                "WHERE status = 'promoted' AND promoted_source_id IS NOT NULL"
            ):
                acted_at = core_covered.get(str(row["candidate_id"]))
                if acted_at:
                    hours = (
                        _parse_iso(acted_at) - _parse_iso(str(row["discovered_at"]))
                    ).total_seconds() / 3600
                    conversion_hours.append(hours)
        finally:
            connection.close()
    median_conversion = (
        round(statistics.median(conversion_hours), 1) if conversion_hours else None
    )

    due = due_channels_from_objects(
        objects,
        as_of=f"{as_of}T23:59:59Z",
        db_path=db_path,
    )
    stale_ids = sorted(item["channel_id"] for item in due if item["last_run"])
    never_run = sorted(item["channel_id"] for item in due if not item["last_run"])

    return {
        "schema_version": 1,
        "as_of": as_of,
        "discovered": {"total": discovered_total, "today": discovered_today},
        "duplicate": {
            "clusters": distinct_clusters,
            "non_representative": non_representative,
            "window_days": 7,
            "inbound_total": inbound_total,
            "inbound_dups": inbound_dups,
            "rate": duplicate_rate,
            "store_rate": store_rate,
        },
        "discovery": {
            "runs": runs,
            "succeeded": succeeded,
            "failed": failed,
            "failure_rate": failure_rate,
            "median_latency_seconds": median_latency,
            "http_errors": http_errors,
            "parse_errors": parse_errors,
            "retries": retries,
            "cost_estimate": cost_estimate,
            "tokens": None,
        },
        "coverage": {
            "matched_entities": len(core_entity_ids),
            "core_matched": core_matched,
            "core_rate": (
                round(core_matched / discovered_total, 4) if discovered_total else 0.0
            ),
        },
        "triage": {
            "total": triaged,
            "promoted": promoted,
            "dismissed": dismissed,
            "promoted_rate": promoted_rate,
            "dismissed_rate": dismissed_rate,
            "top_dismiss_reasons": top_dismiss,
            "median_conversion_hours": median_conversion,
        },
        "stale_channels": {"stale": stale_ids, "never_run": never_run},
    }


def _proposal_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def render_pipeline_metrics(metrics: dict[str, Any]) -> str:
    discovered = metrics["discovered"]
    duplicate = metrics["duplicate"]
    discovery = metrics["discovery"]
    coverage = metrics["coverage"]
    triage = metrics["triage"]
    stale = metrics["stale_channels"]
    latency = discovery["median_latency_seconds"]
    latency_text = f"{latency}s" if latency is not None else "—"
    cost = discovery["cost_estimate"]
    cost_text = str(cost) if cost is not None else "—"
    token_text = "not tracked" if discovery["tokens"] is None else discovery["tokens"]
    conversion = triage["median_conversion_hours"]
    conversion_text = f"{conversion}h" if conversion is not None else "—"
    reasons = triage["top_dismiss_reasons"]
    reasons_text = ", ".join(f"{reason}×{count}" for reason, count in reasons) or "—"
    stale_text = ", ".join(stale["stale"]) or "—"
    never_text = ", ".join(stale["never_run"]) or "—"
    lines = [
        f"# Pipeline Metrics — {metrics['as_of']}",
        "",
        "## Discovery (freshness / failure)",
        f"- Runs: {discovery['runs']} "
        f"(succeeded {discovery['succeeded']}, failed {discovery['failed']})",
        f"- Failure rate: {discovery['failure_rate']:.2%}",
        f"- Median latency: {latency_text}",
        f"- HTTP/parse errors, retries: "
        f"{discovery['http_errors']}/{discovery['parse_errors']}/"
        f"{discovery['retries']}",
        f"- Cost estimate: {cost_text}; model tokens: {token_text}",
        "",
        "## Yield / noise",
        f"- Discovered: {discovered['total']} total, {discovered['today']} today",
        f"- Duplicate rate (inbound, {duplicate['window_days']}d window): "
        f"{duplicate['rate']:.2%} "
        f"({duplicate['inbound_dups']}/{duplicate['inbound_total']} "
        f"non-rep in window)",
        f"- Store snapshot: {duplicate['store_rate']:.2%} "
        f"({duplicate['non_representative']} non-rep in "
        f"{duplicate['clusters']} clusters)",
        f"- Core entity coverage: {coverage['core_matched']}/"
        f"{discovered['total']} ({coverage['core_rate']:.2%}); "
        f"{coverage['matched_entities']} distinct matched entities",
        "",
        "## Triage",
        f"- Triaged: {triage['total']}",
        f"- Promoted: {triage['promoted']} ({triage['promoted_rate']:.2%})",
        f"- Dismissed: {triage['dismissed']} ({triage['dismissed_rate']:.2%})",
        f"- Top dismiss reasons: {reasons_text}",
        f"- Median candidate→promote: {conversion_text}",
        "",
        "## Stale / coverage gap",
        f"- Stale channels: {len(stale['stale'])} ({stale_text})",
        f"- Never run: {len(stale['never_run'])} ({never_text})",
        "",
    ]
    return "\n".join(lines)


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


def universe_coverage(root: Path) -> dict[str, Any]:
    """A-018 Universe coverage: identity/source/relationship completeness.

    identity: Company has legal_name + headquarters + region_primary.
    source: Company is named in >=1 reviewed Event.
    relationship: Company is an endpoint of >=1 reviewed Ontology Assertion.
    """
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before coverage metrics")
    return universe_coverage_from_objects(objects)


def universe_coverage_from_objects(
    objects: list[ResearchObject],
) -> dict[str, Any]:
    """Compute Universe coverage from one validated repository snapshot."""
    companies = [obj for obj in objects if obj.object_type == "company"]
    company_ids = {obj.object_id for obj in companies}

    reviewed_events = [
        obj
        for obj in objects
        if obj.object_type == "event"
        and obj.metadata.get("review_status") == "reviewed"
    ]
    event_company_ids: set[str] = set()
    for event in reviewed_events:
        for company_id in event.metadata.get("companies", []):
            if company_id in company_ids:
                event_company_ids.add(company_id)

    reviewed_rels = [
        obj
        for obj in objects
        if obj.object_type == "ontology_assertion"
        and obj.metadata.get("review_status") == "reviewed"
    ]
    rel_endpoint_ids: set[str] = set()
    for rel in reviewed_rels:
        subject = rel.metadata.get("subject_id")
        object_id = rel.metadata.get("object_id")
        if subject in company_ids:
            rel_endpoint_ids.add(subject)
        if object_id in company_ids:
            rel_endpoint_ids.add(object_id)

    identity_complete = []
    source_complete = []
    relationship_complete = []
    per_company: list[dict[str, Any]] = []
    for company in companies:
        meta = company.metadata
        identity = (
            bool(meta.get("legal_name"))
            and bool(meta.get("headquarters"))
            and bool(meta.get("region_primary"))
        )
        sourced = company.object_id in event_company_ids
        related = company.object_id in rel_endpoint_ids
        if identity:
            identity_complete.append(company.object_id)
        if sourced:
            source_complete.append(company.object_id)
        if related:
            relationship_complete.append(company.object_id)
        per_company.append(
            {
                "company_id": company.object_id,
                "identity_complete": identity,
                "sourced": sourced,
                "related": related,
            }
        )

    total = len(companies)

    def rate(complete: list[str]) -> float:
        return round(len(complete) / total, 4) if total else 0.0

    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "as_of": date.today().isoformat(),
        "total_companies": total,
        "identity_completeness": {
            "complete": len(identity_complete),
            "rate": rate(identity_complete),
        },
        "source_completeness": {
            "complete": len(source_complete),
            "rate": rate(source_complete),
        },
        "relationship_completeness": {
            "complete": len(relationship_complete),
            "rate": rate(relationship_complete),
        },
        "companies": per_company,
    }


def render_universe_coverage(coverage: dict[str, Any]) -> str:
    lines = [
        "# Universe Coverage",
        "",
        f"Generated from repository state: {coverage['as_of']}",
        "",
        f"Total companies: {coverage['total_companies']}",
        "",
        "| Dimension | Complete | Rate |",
        "|---|---:|---:|",
    ]
    for key, label in (
        ("identity_completeness", "Identity (legal_name + HQ + region)"),
        ("source_completeness", "Source (named in reviewed Event)"),
        ("relationship_completeness", "Relationship (assertion endpoint)"),
    ):
        dim = coverage[key]
        lines.append(f"| {label} | {dim['complete']} | {dim['rate']:.1%} |")
    lines += [
        "",
        "## Per-company",
        "",
        "| Company | Identity | Source | Relationship |",
        "|---|---:|---:|---:|",
    ]
    for company in coverage["companies"]:
        cid = company["company_id"]
        idy = "Y" if company["identity_complete"] else "N"
        src = "Y" if company["sourced"] else "N"
        rel = "Y" if company["related"] else "N"
        lines.append(f"| {cid} | {idy} | {src} | {rel} |")
    return "\n".join(lines) + "\n"
