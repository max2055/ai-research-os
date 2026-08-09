"""Industry Home read model (WP-600 F-002): compose the Phase 6 §3 snapshot.

This is a read-only aggregate over existing services; it never writes to the
repository or the Candidate store.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.actions import action_rows
from research_os.services.analysis_compare import compare_runs
from research_os.services.analysis_evaluator import evaluate_run
from research_os.services.brief import daily_brief
from research_os.services.calibration import calibration_report
from research_os.services.candidate_db import candidate_db_path
from research_os.services.discovery import due_channels
from research_os.services.forecast_due import forecast_status_report
from research_os.services.impact_path import (
    dedup_paths,
    detect_contradictions,
    expand_impact_paths,
    path_confidence,
)
from research_os.services.metrics import pipeline_metrics, universe_coverage
from research_os.services.mode_metrics import mode_metrics
from research_os.services.recommendation import recommendation_freshness
from research_os.services.validation import validate_repository
from research_os.services.valuation import valuation_freshness

RECENT_EVENT_DAYS = 30
_ANALYSIS_INPUT_FIELDS = (
    "input_source_ids",
    "input_event_ids",
    "input_impact_ids",
    "input_thesis_ids",
)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _validated_objects(root: Path, label: str) -> list[ResearchObject]:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(f"repository validation must pass before {label} queries")
    return objects


def _string_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _action_row(obj: ResearchObject) -> dict[str, Any]:
    return {
        "id": obj.object_id,
        "title": str(obj.metadata.get("title") or ""),
        "owner": str(obj.metadata.get("owner") or ""),
        "due_date": str(obj.metadata.get("due_date") or ""),
        "status": str(obj.metadata.get("status") or ""),
    }


def _company_channel_ids(
    company: ResearchObject,
    channel_by_id: dict[str, ResearchObject],
) -> set[str]:
    linked = set(_str_list(company.metadata.get("source_channel_ids")))
    for channel in channel_by_id.values():
        if company.object_id in _str_list(channel.metadata.get("entity_ids")):
            linked.add(channel.object_id)
    return linked


def _stale_core_companies(
    objects: list[ResearchObject],
    stale: set[str],
    never_run: set[str],
) -> list[dict[str, Any]]:
    companies = [obj for obj in objects if obj.object_type == "company"]
    channels = [obj for obj in objects if obj.object_type == "source_channel"]
    channel_by_id = {obj.object_id: obj for obj in channels}
    degraded = stale | never_run
    rows = []
    for company in companies:
        if company.metadata.get("coverage_tier") != "core":
            continue
        if _company_channel_ids(company, channel_by_id) & degraded:
            rows.append(
                {
                    "object_id": company.object_id,
                    "title": str(company.metadata.get("title") or ""),
                }
            )
    return sorted(rows, key=lambda row: row["object_id"])


def _sector_heatmap(
    objects: list[ResearchObject],
    as_of: str,
    stale: set[str],
    never_run: set[str],
) -> list[dict[str, Any]]:
    sectors = [obj for obj in objects if obj.object_type == "sector"]
    companies = [obj for obj in objects if obj.object_type == "company"]
    company_sector_ids: dict[str, set[str]] = {
        obj.object_id: set(_str_list(obj.metadata.get("sector_ids")))
        for obj in companies
    }
    events = [obj for obj in objects if obj.object_type == "event"]
    impacts = [obj for obj in objects if obj.object_type == "impact_assertion"]
    channels = [obj for obj in objects if obj.object_type == "source_channel"]
    channel_by_sector: dict[str, list[str]] = {}
    for channel in channels:
        for sector_id in _str_list(channel.metadata.get("sector_ids")):
            channel_by_sector.setdefault(sector_id, []).append(channel.object_id)
    window_start = (
        date.fromisoformat(as_of) - timedelta(days=RECENT_EVENT_DAYS)
    ).isoformat()

    def members(sector_id: str, core_ids: set[str], tracked_ids: set[str]) -> set[str]:
        company_ids = {
            obj.object_id
            for obj in companies
            if sector_id in company_sector_ids[obj.object_id]
        }
        return core_ids | tracked_ids | company_ids

    rows = []
    for sector in sectors:
        core_ids = set(_str_list(sector.metadata.get("core_company_ids")))
        tracked_ids = set(_str_list(sector.metadata.get("tracked_company_ids")))
        sector_members = members(sector.object_id, core_ids, tracked_ids)
        event_count_recent = sum(
            1
            for event in events
            if event.metadata.get("review_status") == "reviewed"
            and str(event.metadata.get("updated_at") or "")[:10] >= window_start
            and set(_str_list(event.metadata.get("companies"))) & sector_members
        )
        impact_count_reviewed = sum(
            1
            for impact in impacts
            if impact.metadata.get("review_status") == "reviewed"
            and str(impact.metadata.get("target_id") or "") in sector_members
        )
        sector_channels = set(channel_by_sector.get(sector.object_id, []))
        rows.append(
            {
                "sector_id": sector.object_id,
                "title": str(sector.metadata.get("title") or ""),
                "entity_count": len(sector_members),
                "event_count_recent": event_count_recent,
                "impact_count_reviewed": impact_count_reviewed,
                "fresh_channels": len(sector_channels - stale - never_run),
                "stale_channels": len(sector_channels & (stale | never_run)),
            }
        )
    return sorted(rows, key=lambda row: row["sector_id"])


def industry_home_snapshot(
    root: Path,
    *,
    as_of: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Collect every Industry Home section for one date (no writes).

    Composes :func:`daily_brief` with forecast/action/freshness/impact/sector
    aggregates. Raises ``ValueError`` if the repository has validation errors.
    """
    as_of = as_of or date.today().isoformat()
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before Industry Home queries"
        )
    db_path = db_path or candidate_db_path(root)

    brief = daily_brief(root, as_of, db_path=db_path)
    report = forecast_status_report(root, as_of=as_of)
    actions = action_rows(root, status="open", overdue_as_of=as_of) + action_rows(
        root, status="in_progress", overdue_as_of=as_of
    )

    stale = set(brief["stale"])
    never_run = set(brief["never_run"])

    impacts_today = [
        {
            "object_id": obj.object_id,
            "title": str(obj.metadata.get("title") or ""),
        }
        for obj in objects
        if obj.object_type == "impact_assertion"
        and str(obj.metadata.get("updated_at") or "")[:10] == as_of
        and obj.metadata.get("review_status") == "reviewed"
    ]

    pm = pipeline_metrics(root, as_of, db_path=db_path)
    discovery = pm.get("discovery", {})
    freshness = {
        "failure_rate": discovery.get("failure_rate"),
        "median_latency_seconds": discovery.get("median_latency_seconds"),
        "http_errors": discovery.get("http_errors"),
        "parse_errors": discovery.get("parse_errors"),
        "retries": discovery.get("retries"),
        "cost_estimate": discovery.get("cost_estimate"),
    }

    return {
        "as_of": as_of,
        "generated_at": _utc_now(),
        "top_candidates": brief["top"],
        "high_priority_candidates": brief["high_priority"],
        "events_today": brief["events_today"],
        "sources_today": brief["sources_today"],
        "impacts_today": impacts_today,
        "conflicts": brief["conflicts"],
        "stale_core_companies": _stale_core_companies(objects, stale, never_run),
        "stale_channels": brief["stale"],
        "never_run_channels": brief["never_run"],
        "due_forecasts": report["due_rows"],
        "overdue_forecasts": report["overdue_rows"],
        "due_actions": [_action_row(obj) for obj in actions],
        "sector_heatmap": _sector_heatmap(objects, as_of, stale, never_run),
        "freshness": freshness,
        "failed_runs": brief["failed_runs"],
    }


def _coverage_index(root: Path) -> dict[str, dict[str, Any]]:
    coverage = universe_coverage(root)
    return {
        str(row["company_id"]): row for row in coverage.get("companies", [])
    }


def _object_title(obj: ResearchObject) -> str:
    return str(obj.metadata.get("title") or obj.object_id)


def company_snapshot(root: Path, company_id: str) -> dict[str, Any]:
    """Industry radar snapshot for one company (WP-601 F-005, no writes)."""
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before Company queries"
        )
    company = next((o for o in objects if o.object_id == company_id), None)
    if company is None:
        raise KeyError(company_id)

    securities = [
        obj
        for obj in objects
        if obj.object_type == "security"
        and obj.metadata.get("issuer_company_id") == company_id
    ]
    products = [
        obj
        for obj in objects
        if obj.object_type == "product"
        and company_id in _str_list(obj.metadata.get("owner_company_ids"))
    ]
    technologies = [
        obj
        for obj in objects
        if obj.object_type == "technology"
        and company_id in _str_list(obj.metadata.get("owner_company_ids"))
    ]
    sectors = [
        obj
        for obj in objects
        if obj.object_type == "sector"
        and (
            company_id in _str_list(obj.metadata.get("core_company_ids"))
            or company_id in _str_list(obj.metadata.get("tracked_company_ids"))
            or obj.object_id in _str_list(company.metadata.get("sector_ids"))
        )
    ]
    assertions = [
        obj
        for obj in objects
        if obj.object_type == "ontology_assertion"
        and (
            obj.metadata.get("subject_id") == company_id
            or obj.metadata.get("object_id") == company_id
        )
    ]
    channel_by_id = {
        obj.object_id: obj
        for obj in objects
        if obj.object_type == "source_channel"
    }
    linked_channels = sorted(_company_channel_ids(company, channel_by_id))
    due = due_channels(root, db_path=candidate_db_path(root))
    degraded = {item["channel_id"] for item in due if item["last_run"]}
    never_run = {item["channel_id"] for item in due if not item["last_run"]}
    channels = [
        {
            "channel_id": channel_id,
            "title": _object_title(channel_by_id[channel_id])
            if channel_id in channel_by_id
            else channel_id,
            "freshness": (
                "stale"
                if channel_id in degraded
                else "never_run"
                if channel_id in never_run
                else "fresh"
            ),
        }
        for channel_id in linked_channels
    ]

    events = [
        obj
        for obj in objects
        if obj.object_type == "event"
        and company_id in _str_list(obj.metadata.get("companies"))
    ]
    events.sort(
        key=lambda obj: str(obj.metadata.get("event_date") or ""), reverse=True
    )
    event_ids = {obj.object_id for obj in events}
    analysis_runs = [
        obj
        for obj in objects
        if obj.object_type == "analysis_run"
        and (
            company_id in _str_list(obj.metadata.get("scope_ids"))
            or set(_str_list(obj.metadata.get("input_event_ids"))) & event_ids
        )
    ]
    forecasts = [
        obj
        for obj in objects
        if obj.object_type == "forecast"
        and company_id in _str_list(obj.metadata.get("scope_ids"))
    ]
    valuations = [
        obj
        for obj in objects
        if obj.object_type == "valuation_snapshot"
        and obj.metadata.get("company_id") == company_id
    ]
    recommendations = [
        obj
        for obj in objects
        if obj.object_type == "recommendation"
        and obj.metadata.get("company_id") == company_id
    ]
    theses = [
        obj
        for obj in objects
        if obj.object_type == "thesis"
        and company_id in _str_list(obj.metadata.get("companies"))
    ]
    metrics = [
        obj
        for obj in objects
        if obj.object_type == "metric"
        and (
            company_id in _str_list(obj.metadata.get("owner_entity_ids"))
            or obj.object_id in _str_list(company.metadata.get("key_metric_ids"))
        )
    ]
    coverage = _coverage_index(root).get(company_id, {})

    return {
        "company_id": company_id,
        "identity": company.metadata,
        "securities": securities,
        "products": products,
        "technologies": technologies,
        "sectors": sectors,
        "assertions": assertions,
        "channels": channels,
        "metrics": metrics,
        "events": events,
        "analysis_runs": analysis_runs,
        "forecasts": forecasts,
        "valuations": valuations,
        "recommendations": recommendations,
        "theses": theses,
        "coverage": coverage,
    }


def sector_snapshot(root: Path, sector_id: str) -> dict[str, Any]:
    """Industry radar snapshot for one sector (WP-601 F-004, no writes)."""
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before Sector queries"
        )
    sector = next((o for o in objects if o.object_id == sector_id), None)
    if sector is None:
        raise KeyError(sector_id)

    companies = [obj for obj in objects if obj.object_type == "company"]
    core_ids = set(_str_list(sector.metadata.get("core_company_ids")))
    tracked_ids = set(_str_list(sector.metadata.get("tracked_company_ids")))
    by_sector = {
        obj.object_id
        for obj in companies
        if sector_id in _str_list(obj.metadata.get("sector_ids"))
    }
    members = core_ids | tracked_ids | by_sector
    member_objects = [obj for obj in companies if obj.object_id in members]
    member_objects.sort(key=lambda obj: obj.object_id)

    products = [
        obj
        for obj in objects
        if obj.object_type == "product"
        and (
            sector_id in _str_list(obj.metadata.get("sector_ids"))
            or set(_str_list(obj.metadata.get("owner_company_ids"))) & members
        )
    ]
    technologies = [
        obj
        for obj in objects
        if obj.object_type == "technology"
        and (
            sector_id in _str_list(obj.metadata.get("sector_ids"))
            or set(_str_list(obj.metadata.get("owner_company_ids"))) & members
        )
    ]
    metrics = [
        obj
        for obj in objects
        if obj.object_type == "metric"
        and (
            sector_id in _str_list(obj.metadata.get("owner_entity_ids"))
            or obj.object_id in _str_list(sector.metadata.get("key_metrics"))
        )
    ]
    assertions = [
        obj
        for obj in objects
        if obj.object_type == "ontology_assertion"
        and (
            obj.metadata.get("subject_id") == sector_id
            or obj.metadata.get("object_id") == sector_id
        )
    ]
    events = [
        obj
        for obj in objects
        if obj.object_type == "event"
        and set(_str_list(obj.metadata.get("companies"))) & members
    ]
    events.sort(
        key=lambda obj: str(obj.metadata.get("event_date") or ""), reverse=True
    )
    impacts = [
        obj
        for obj in objects
        if obj.object_type == "impact_assertion"
        and obj.metadata.get("review_status") == "reviewed"
        and (
            obj.metadata.get("target_id") == sector_id
            or str(obj.metadata.get("target_id") or "") in members
        )
    ]
    theses = [
        obj
        for obj in objects
        if obj.object_type == "thesis"
        and set(_str_list(obj.metadata.get("companies"))) & members
    ]
    forecasts = [
        obj
        for obj in objects
        if obj.object_type == "forecast"
        and (
            sector_id in _str_list(obj.metadata.get("scope_ids"))
            or set(_str_list(obj.metadata.get("scope_ids"))) & members
        )
    ]

    coverage = _coverage_index(root)
    member_flags = [
        {"company_id": company_id, **coverage.get(company_id, {})}
        for company_id in sorted(members)
    ]

    def rate(flag: str) -> float:
        if not members:
            return 0.0
        complete = sum(
            1
            for row in member_flags
            if row.get(flag) is True
        )
        return round(complete / len(members), 4)

    return {
        "sector_id": sector_id,
        "identity": sector.metadata,
        "members": members,
        "companies": member_objects,
        "products": products,
        "technologies": technologies,
        "metrics": metrics,
        "assertions": assertions,
        "events": events,
        "impacts": impacts,
        "theses": theses,
        "forecasts": forecasts,
        "coverage_rollup": {
            "identity_rate": rate("identity_complete"),
            "source_rate": rate("sourced"),
            "relationship_rate": rate("related"),
        },
        "member_flags": member_flags,
    }


def _impact_row(obj: ResearchObject) -> dict[str, Any]:
    return {
        "assertion_id": obj.object_id,
        "title": str(obj.metadata.get("title") or ""),
        "source_id": str(obj.metadata.get("subject_id") or ""),
        "target_id": str(obj.metadata.get("target_id") or ""),
        "predicate": str(obj.metadata.get("predicate") or ""),
        "impact_type": str(obj.metadata.get("impact_type") or ""),
        "mechanism": str(obj.metadata.get("mechanism") or ""),
        "evidence_ids": _str_list(obj.metadata.get("evidence_ids")),
        "direction": str(obj.metadata.get("direction") or ""),
        "horizon": str(obj.metadata.get("horizon") or ""),
        "confidence": obj.metadata.get("confidence"),
        "review_status": str(obj.metadata.get("review_status") or ""),
    }


def impact_explorer_snapshot(
    root: Path,
    *,
    start_id: str | None = None,
    max_depth: int = 3,
) -> dict[str, Any]:
    """Return reviewed direct assertions and explainable 1-3 hop paths."""
    if max_depth < 1 or max_depth > 3:
        raise ValueError("max_depth must be between 1 and 3")
    objects = _validated_objects(root, "Impact Explorer")
    by_id = {obj.object_id: obj for obj in objects}
    if start_id is not None:
        start = by_id.get(start_id)
        if start is None or start.object_type != "event":
            raise KeyError(start_id)

    assertions = sorted(
        (
            obj
            for obj in objects
            if obj.object_type == "impact_assertion"
            and obj.metadata.get("review_status") == "reviewed"
            and (
                start_id is None
                or str(obj.metadata.get("subject_id") or "") == start_id
            )
        ),
        key=lambda obj: obj.object_id,
    )
    direct = [_impact_row(obj) for obj in assertions]
    event_ids = [start_id] if start_id is not None else sorted(
        {
            str(evidence_id)
            for obj in objects
            if obj.object_type == "ontology_assertion"
            and obj.metadata.get("review_status") == "reviewed"
            for evidence_id in _str_list(obj.metadata.get("evidence_ids"))
            if evidence_id in by_id
            and by_id[evidence_id].object_type == "event"
            and by_id[evidence_id].metadata.get("review_status") == "reviewed"
        }
    )
    paths: list[dict[str, Any]] = []
    pruning: list[dict[str, Any]] = []
    for event_id in event_ids:
        event = by_id.get(event_id)
        if event is None or event.object_type != "event":
            pruning.append({"reason": "unknown-trigger-event", "at": event_id})
            continue
        if event.metadata.get("review_status") != "reviewed":
            pruning.append({"reason": "trigger-event-not-reviewed", "at": event_id})
            continue
        expanded, event_pruning = expand_impact_paths(
            objects,
            event_id=event_id,
            max_depth=max_depth,
        )
        paths.extend(expanded)
        pruning.extend(event_pruning)

    normalized_paths = []
    for path in dedup_paths(paths):
        hops = []
        for hop in path["hops"]:
            relation = by_id.get(str(hop.get("rel_id") or ""))
            evidence_ids = (
                _str_list(relation.metadata.get("evidence_ids"))
                if relation is not None
                else []
            )
            hops.append(
                {
                    "assertion_id": str(hop.get("rel_id") or ""),
                    "source_id": str(hop.get("from_id") or ""),
                    "target_id": str(hop.get("to_id") or ""),
                    "predicate": str(hop.get("predicate") or ""),
                    "mechanism": str(hop.get("mechanism") or ""),
                    "evidence_ids": evidence_ids,
                    "direction": str(hop.get("direction") or ""),
                    "horizon": str(hop.get("horizon") or ""),
                    "confidence": hop.get("confidence"),
                }
            )
        normalized_paths.append(
            {
                "trigger_event_id": path["trigger_event_id"],
                "terminal_id": path["terminal_id"],
                "entity_sequence": path["entity_sequence"],
                "hops": hops,
                "weakest_confidence": path_confidence(path),
                "variant_count": path.get("variant_count", 1),
                "pruned": path.get("pruned", []),
            }
        )
        pruning.extend(path.get("pruned", []))

    conflict_inputs = direct + [
        {
            "target_id": path["terminal_id"],
            "direction": path["hops"][-1]["direction"],
            "horizon": path["hops"][-1]["horizon"],
        }
        for path in normalized_paths
        if path["hops"]
    ]
    return {
        "start_id": start_id,
        "max_depth": max_depth,
        "total_assertions": sum(
            1 for obj in objects if obj.object_type == "impact_assertion"
        ),
        "pending_assertions": sum(
            1
            for obj in objects
            if obj.object_type == "impact_assertion"
            and obj.metadata.get("review_status") == "pending"
        ),
        "direct_assertions": direct,
        "paths": normalized_paths,
        "pruning_reasons": pruning,
        "conflicts": detect_contradictions(conflict_inputs),
        "countervailing_factors": sorted(
            {
                value
                for obj in assertions
                for value in _string_values(
                    obj.metadata.get("countervailing_factors")
                )
            }
        ),
        "alternative_explanations": sorted(
            {
                value
                for obj in assertions
                for value in _string_values(
                    obj.metadata.get("alternative_explanations")
                )
            }
        ),
    }


def _evaluation_row(objects: list[ResearchObject], run_id: str) -> dict[str, Any]:
    scorecard = evaluate_run(objects, run_id)
    return {
        "overall": scorecard.overall,
        "gate_pass": scorecard.gate_pass,
        "dimensions": [
            {
                "key": dimension.key,
                "label": dimension.label,
                "score": dimension.score,
                "target": dimension.target,
                "passed": dimension.passed,
                "detail": dimension.detail,
            }
            for dimension in scorecard.dimensions
        ],
    }


def analysis_workspace_snapshot(
    root: Path,
    *,
    run_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return immutable Run provenance, evaluation, metrics, and comparison."""
    objects = _validated_objects(root, "Analysis Workspace")
    by_id = {obj.object_id: obj for obj in objects}
    available = sorted(
        (obj for obj in objects if obj.object_type == "analysis_run"),
        key=lambda obj: obj.object_id,
        reverse=True,
    )
    if run_ids is None:
        selected = available
    else:
        unique_ids = list(dict.fromkeys(run_ids))
        missing = [
            run_id
            for run_id in unique_ids
            if run_id not in by_id or by_id[run_id].object_type != "analysis_run"
        ]
        if missing:
            raise KeyError(missing[0])
        selected = [by_id[run_id] for run_id in unique_ids]

    rows = []
    for run in selected:
        mode_id = str(run.metadata.get("mode_id") or "")
        mode = by_id.get(mode_id)
        inputs = {
            field: _str_list(run.metadata.get(field))
            for field in _ANALYSIS_INPUT_FIELDS
        }
        rows.append(
            {
                "run_id": run.object_id,
                "title": str(run.metadata.get("title") or ""),
                "as_of": str(run.metadata.get("as_of") or ""),
                "status": str(run.metadata.get("status") or ""),
                "review_status": str(run.metadata.get("review_status") or ""),
                "input_ids": inputs,
                "mode_id": mode_id,
                "mode_version": mode_id.rsplit("-v", 1)[-1]
                if "-v" in mode_id
                else "unknown",
                "model_version": str(run.metadata.get("model_id") or "unknown"),
                "template_version": str(
                    mode.metadata.get("prompt_template_path") or "unknown"
                    if mode is not None
                    else "unknown"
                ),
                "input_snapshot_hash": str(
                    run.metadata.get("input_snapshot_hash") or ""
                ),
                "prompt_hash": str(run.metadata.get("prompt_hash") or ""),
                "output_hash": str(run.metadata.get("output_hash") or ""),
                "evaluator_scores": _evaluation_row(objects, run.object_id),
            }
        )

    comparison = None
    if run_ids is not None and selected:
        report = compare_runs(objects, [run.object_id for run in selected])
        comparison = {
            "run_ids": report.run_ids,
            "modes": report.modes,
            "time_horizons": report.time_horizons,
            "questions": report.questions,
            "shared_facts": report.shared_facts,
            "evidence_omitted": report.evidence_omitted,
            "conflicting_signals": report.conflicting_signals,
        }
    return {
        "runs": rows,
        "comparison": comparison,
        "mode_metrics": mode_metrics(objects),
    }


def _object_metadata_row(obj: ResearchObject) -> dict[str, Any]:
    return {"id": obj.object_id, "title": str(obj.metadata.get("title") or "")}


def decision_desk_snapshot(
    root: Path,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Compose Forecast, calibration, valuation, and Recommendation state."""
    as_of = as_of or date.today().isoformat()
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects = _validated_objects(root, "Decision Desk")
    report = forecast_status_report(root, as_of=as_of)
    forecasts = sorted(
        (obj for obj in objects if obj.object_type == "forecast"),
        key=lambda obj: obj.object_id,
    )
    open_rows = [
        {
            **_object_metadata_row(obj),
            "question": str(obj.metadata.get("question") or ""),
            "resolution_date": str(obj.metadata.get("resolution_date") or ""),
            "horizon": str(obj.metadata.get("horizon") or ""),
            "scenario_references": _str_list(obj.metadata.get("scenario_ids")),
        }
        for obj in forecasts
        if obj.metadata.get("status") == "open"
    ]

    calibration = calibration_report(root)
    calibration["status"] = (
        "insufficient_sample"
        if int(calibration.get("n_resolutions") or 0) < 10
        else "descriptive_only"
    )

    valuations = []
    valuation_by_id: dict[str, ResearchObject] = {}
    for obj in objects:
        if obj.object_type != "valuation_snapshot":
            continue
        valuation_by_id[obj.object_id] = obj
        freshness = valuation_freshness(root, val_id=obj.object_id, as_of=as_of)
        valuations.append(
            {
                **_object_metadata_row(obj),
                "company_id": str(obj.metadata.get("company_id") or ""),
                "age_days": freshness["age_days"],
                "threshold_days": freshness["threshold_days"],
                "freshness": "fresh" if freshness["fresh"] else "stale",
                "scenario_references": _string_values(
                    obj.metadata.get("scenario_set")
                ),
            }
        )

    recommendations = []
    for obj in sorted(
        (item for item in objects if item.object_type == "recommendation"),
        key=lambda item: item.object_id,
    ):
        freshness = recommendation_freshness(
            root,
            rec_id=obj.object_id,
            as_of=as_of,
        )
        valuation = valuation_by_id.get(
            str(obj.metadata.get("valuation_snapshot_id") or "")
        )
        recommendations.append(
            {
                **_object_metadata_row(obj),
                "company_id": str(obj.metadata.get("company_id") or ""),
                "research_posture": str(
                    obj.metadata.get("research_posture") or ""
                ),
                "direction": str(obj.metadata.get("direction") or ""),
                "freshness": "fresh" if freshness["fresh"] else "stale",
                "age_days": freshness["age_days"],
                "catalysts": _str_list(obj.metadata.get("catalysts")),
                "falsification_conditions": _str_list(
                    obj.metadata.get("falsification_conditions")
                ),
                "risks": _str_list(obj.metadata.get("key_risks")),
                "unknowns": _str_list(obj.metadata.get("unknowns")),
                "scenario_references": _string_values(
                    valuation.metadata.get("scenario_set")
                    if valuation is not None
                    else None
                ),
            }
        )

    resolutions = [
        {
            **_object_metadata_row(obj),
            "forecast_id": str(obj.metadata.get("forecast_id") or ""),
            "resolved_at": str(obj.metadata.get("resolved_at") or ""),
            "decision": str(obj.metadata.get("decision") or ""),
            "resolution_source_ids": _str_list(
                obj.metadata.get("resolution_source_ids")
            ),
        }
        for obj in sorted(
            (
                item
                for item in objects
                if item.object_type == "forecast_resolution"
            ),
            key=lambda item: item.object_id,
            reverse=True,
        )
    ]
    return {
        "as_of": as_of,
        "open_forecasts": open_rows,
        "due_forecasts": report["due_rows"],
        "overdue_forecasts": report["overdue_rows"],
        "calibration": calibration,
        "valuations": valuations,
        "recommendations": recommendations,
        "resolution_history": resolutions,
    }
