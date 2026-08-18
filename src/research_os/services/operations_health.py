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
from research_os.services.cost_monitoring import monthly_cost_report
from research_os.services.discovery import due_channels
from research_os.services.durable_backup import (
    durable_latest_success_path,
    load_durable_backup_receipt,
)
from research_os.services.forecast_due import forecast_status_report
from research_os.services.indexing import (
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.ingestion import verify_source_assets_from_objects
from research_os.services.projects import objects_for_project
from research_os.services.recommendation import recommendation_freshness
from research_os.services.validation import validate_repository
from research_os.services.web_identity import load_web_identity

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


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else None


def _latest_durable_attempt(
    objects: list[ResearchObject],
) -> tuple[datetime, ResearchObject] | None:
    attempts = []
    for obj in objects:
        if obj.object_type != "job" or obj.metadata.get("job_name") != "backup-durable":
            continue
        started_at = _timestamp(obj.metadata.get("started_at"))
        if started_at is not None:
            attempts.append((started_at, obj))
    return max(attempts, key=lambda item: item[0]) if attempts else None


def _durable_backup_status(
    root: Path, now: datetime, objects: list[ResearchObject]
) -> dict[str, Any]:
    resolved_root = root.resolve()
    receipt_path = durable_latest_success_path(resolved_root)
    relative = str(receipt_path.relative_to(resolved_root))
    if not receipt_path.is_file():
        return {
            "status": "missing",
            "age_hours": None,
            "receipt": None,
            "backup_id": None,
            "created_at": None,
        }
    try:
        receipt = load_durable_backup_receipt(receipt_path)
        created_at = _timestamp(receipt.created_at)
        if created_at is None:
            raise ValueError("durable receipt timestamp must include timezone")
        age_hours = (
            now.astimezone(UTC) - created_at.astimezone(UTC)
        ).total_seconds() / 3600
        backup_sets = [item.backup_set for item in receipt.sets]
        if receipt.status == "failed":
            status = "failed"
        elif (
            receipt.status != "verified"
            or len(backup_sets) != 2
            or set(backup_sets) != {"candidate", "source_assets"}
        ):
            status = "invalid"
        else:
            status = "fresh" if age_hours <= 24 else "stale"
        latest_attempt = _latest_durable_attempt(objects)
        if (
            latest_attempt is not None
            and latest_attempt[0] > created_at
            and latest_attempt[1].metadata.get("status") == "failed"
        ):
            status = "failed"
        return {
            "status": status,
            "age_hours": round(age_hours, 2),
            "receipt": relative,
            "backup_id": receipt.backup_id,
            "created_at": receipt.created_at,
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {
            "status": "invalid",
            "age_hours": None,
            "receipt": relative,
            "backup_id": None,
            "created_at": None,
        }


def _durable_backup_alert(status: str) -> dict[str, str] | None:
    codes = {
        "missing": "BKP_DURABLE_MISSING",
        "failed": "BKP_DURABLE_FAILED",
        "invalid": "BKP_DURABLE_INVALID",
        "stale": "BKP_DURABLE_STALE",
    }
    code = codes.get(status)
    if code is None:
        return None
    return {
        "code": code,
        "priority": "P1",
        "status": status,
        "message": f"durable backup is {status}",
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
    assets = verify_source_assets_from_objects(root, objects)
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
    local_backup = _backup_status(root, now_dt)
    durable_backup = _durable_backup_status(root, now_dt, objects)
    durable_alert = _durable_backup_alert(str(durable_backup["status"]))
    cost_budget = os.environ.get("RESEARCH_OS_MODEL_COST_BUDGET")
    cost = monthly_cost_report(
        candidate_db_path(root),
        as_of=now_dt.date().isoformat(),
        budget=cost_budget,
    )
    web_identity = load_web_identity(root)
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
        "backup": {**local_backup, "durable": durable_backup},
        "alerts": [durable_alert] if durable_alert is not None else [],
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
        "web_identity": {
            "status": "ready" if web_identity is not None else "uninitialized",
            "researcher_id": web_identity.researcher_id if web_identity else None,
        },
        "model_cost": {
            "status": cost.status,
            "period_start": cost.period_start,
            "period_end": cost.period_end,
            "currency": cost.currency,
            "known_total": str(cost.known_total)
            if cost.known_total is not None
            else None,
            "utilization": str(cost.utilization)
            if cost.utilization is not None
            else None,
            "records": cost.record_count,
            "record_count": cost.record_count,
            "unknown_record_count": cost.unknown_record_count,
            "invalid_record_count": cost.invalid_record_count,
            "budget_configured": bool(cost_budget and cost_budget.strip()),
        },
    }
