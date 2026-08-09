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
from research_os.services.brief import daily_brief
from research_os.services.candidate_db import candidate_db_path
from research_os.services.forecast_due import forecast_status_report
from research_os.services.metrics import pipeline_metrics
from research_os.services.validation import validate_repository

RECENT_EVENT_DAYS = 30


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


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
