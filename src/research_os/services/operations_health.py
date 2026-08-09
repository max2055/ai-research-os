"""Unified, read-only Operations and System Health snapshots (WP-603)."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.actions import action_rows
from research_os.services.candidate_db import (
    candidate_db_health,
    candidate_db_path,
)
from research_os.services.discovery import due_channels
from research_os.services.forecast_due import forecast_status_report
from research_os.services.indexing import (
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.ingestion import verify_source_assets
from research_os.services.projects import objects_for_project
from research_os.services.recommendation import recommendation_freshness
from research_os.services.validation import validate_repository

_SECRET_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
)
_BACKUP_GLOB = "09_Automation/operational/backups/candidate/*.manifest.json"


def _row(obj: ResearchObject) -> dict[str, Any]:
    return {
        "id": obj.object_id,
        "title": str(obj.metadata.get("title") or ""),
        "status": str(obj.metadata.get("status") or ""),
    }


def _validated(root: Path) -> tuple[list[ResearchObject], list[Any]]:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before operations queries")
    return objects, findings


def operations_snapshot(
    root: Path,
    *,
    as_of: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Return schedules, Jobs, Actions, reviews and decision work queues."""
    as_of = as_of or date.today().isoformat()
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects, _ = _validated(root)
    scoped = objects_for_project(objects, project_id) if project_id else objects

    due = due_channels(
        root,
        as_of=f"{as_of}T23:59:59Z",
        db_path=candidate_db_path(root),
    )
    schedules = [
        {
            **item,
            "status": "due",
            "next_due": "due now",
        }
        for item in due
    ]
    jobs = [
        {
            **_row(obj),
            "job_name": str(obj.metadata.get("job_name") or ""),
            "started_at": str(obj.metadata.get("started_at") or ""),
            "finished_at": str(obj.metadata.get("finished_at") or ""),
            "message": str(obj.metadata.get("message") or ""),
        }
        for obj in sorted(
            (item for item in scoped if item.object_type == "job"),
            key=lambda item: str(item.metadata.get("started_at") or ""),
            reverse=True,
        )[:50]
    ]
    actions = []
    for status in ("open", "in_progress"):
        for obj in action_rows(root, project_id=project_id, status=status):
            due_date = str(obj.metadata.get("due_date") or "")
            actions.append(
                {
                    **_row(obj),
                    "owner": str(obj.metadata.get("owner") or ""),
                    "due_date": due_date,
                    "timing": "overdue" if due_date < as_of else "open",
                }
            )
    actions.sort(key=lambda row: (row["due_date"], row["id"]))
    reviews = [
        {
            **_row(obj),
            "review_cadence": str(obj.metadata.get("review_cadence") or ""),
            "next_review_date": str(obj.metadata.get("next_review_date") or ""),
            "timing": "due",
        }
        for obj in scoped
        if obj.object_type == "project"
        and str(obj.metadata.get("next_review_date") or "") <= as_of
    ]
    forecast_report = forecast_status_report(root, as_of=as_of)
    overdue_ids = {row["id"] for row in forecast_report["overdue_rows"]}
    forecasts = [
        {
            **row,
            "timing": "overdue" if row["id"] in overdue_ids else "due",
        }
        for row in forecast_report["due_rows"]
    ]
    recommendations = []
    for obj in scoped:
        if (
            obj.object_type != "recommendation"
            or obj.metadata.get("status") != "active"
        ):
            continue
        freshness = recommendation_freshness(root, rec_id=obj.object_id, as_of=as_of)
        if not freshness["fresh"]:
            recommendations.append(
                {
                    **_row(obj),
                    "company_id": str(obj.metadata.get("company_id") or ""),
                    "age_days": freshness["age_days"],
                    "freshness": "stale",
                }
            )
    return {
        "as_of": as_of,
        "project_id": project_id,
        "schedules": schedules,
        "jobs": jobs,
        "actions": actions,
        "reviews": reviews,
        "forecasts": forecasts,
        "recommendations": recommendations,
    }


def _backup_status(root: Path, now: datetime) -> dict[str, Any]:
    manifests = sorted(
        root.glob(_BACKUP_GLOB),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not manifests:
        return {"status": "missing", "age_hours": None, "manifest": None}
    manifest = manifests[0]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        created_at = datetime.fromisoformat(
            str(data.get("created_at") or "").replace("Z", "+00:00")
        )
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        age_hours = (
            now.astimezone(UTC) - created_at.astimezone(UTC)
        ).total_seconds() / 3600
        return {
            "status": "fresh" if age_hours <= 24 else "stale",
            "age_hours": round(age_hours, 2),
            "manifest": str(manifest.relative_to(root)),
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {
            "status": "invalid",
            "age_hours": None,
            "manifest": str(manifest.relative_to(root)),
        }


def health_snapshot(
    root: Path,
    *,
    project_id: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Return repository, store, Channel, backup, host and config health."""
    objects, findings = validate_repository(root)
    now_dt = (
        datetime.fromisoformat(now.replace("Z", "+00:00"))
        if now
        else datetime.now().astimezone()
    )
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=UTC)

    rendered = (
        render_project_indexes(objects, project_id)
        if project_id
        else render_indexes(objects)
    )
    drift = index_drift(root, rendered)
    assets = verify_source_assets(root)
    asset_failures = [
        {
            "source_id": item.source_id,
            "status": item.status,
            "message": item.message,
        }
        for item in assets
        if item.status in {"missing", "invalid", "hash_mismatch"}
    ]
    channels = [
        {
            "channel_id": obj.object_id,
            "enabled": bool(obj.metadata.get("enabled")),
            "review_status": str(obj.metadata.get("review_status") or ""),
            "license_status": str(obj.metadata.get("license_status") or ""),
            "license_notes_present": bool(obj.metadata.get("license_notes")),
            "robots_checked_at": str(obj.metadata.get("robots_checked_at") or ""),
        }
        for obj in objects
        if obj.object_type == "source_channel"
    ]
    failed_runs = [
        {
            **_row(obj),
            "type": obj.object_type,
            "message": str(obj.metadata.get("message") or ""),
        }
        for obj in objects
        if obj.object_type in {"job", "analysis_run"}
        and obj.metadata.get("status") == "failed"
    ]
    disk = shutil.disk_usage(root)
    timezone = getattr(now_dt.tzinfo, "key", None) or str(now_dt.tzinfo)
    config = {
        key: "present" if bool(os.environ.get(key)) else "missing"
        for key in _SECRET_KEYS
    }
    costs = [
        str(obj.metadata.get("cost_estimate") or "")
        for obj in objects
        if obj.object_type == "job" and obj.metadata.get("cost_estimate")
    ]
    return {
        "generated_at": now_dt.isoformat(),
        "validation": {
            "status": "error"
            if any(item.level == "error" for item in findings)
            else "warning"
            if findings
            else "ok",
            "errors": sum(item.level == "error" for item in findings),
            "warnings": sum(item.level == "warning" for item in findings),
            "findings": [
                {
                    "level": item.level,
                    "code": item.code,
                    "path": str(item.path.relative_to(root)),
                    "message": item.message,
                }
                for item in findings
            ],
        },
        "indexes": {
            "status": "drift" if drift else "ok",
            "scope": project_id or "global",
            "drift": [str(path) for path in drift],
        },
        "assets": {
            "status": "failed" if asset_failures else "ok",
            "failures": asset_failures,
        },
        "candidate_db": candidate_db_health(candidate_db_path(root)),
        "channels": channels,
        "failed_runs": failed_runs,
        "backup": _backup_status(root, now_dt),
        "host": {
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "status": "low" if disk.free < 5 * 1024**3 else "ok",
            },
            "timezone": timezone,
        },
        "config": config,
        "model_cost": {
            "status": "recorded" if costs else "unknown",
            "records": len(costs),
            "budget_configured": bool(
                os.environ.get("RESEARCH_OS_MODEL_COST_BUDGET")
            ),
        },
    }
