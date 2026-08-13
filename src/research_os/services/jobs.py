"""Idempotent scheduler entrypoints with Markdown Job Run audit records."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from research_os.adapters.backup_remote import GitHubPrivateReleaseBackend
from research_os.domain.models import ResearchObject
from research_os.repositories.transaction import FileTransaction
from research_os.services.backup import create_candidate_snapshot
from research_os.services.brief import (
    daily_brief,
    render_daily_brief,
    write_daily_brief,
)
from research_os.services.decision_alerts import decision_alerts
from research_os.services.discovery import run_discovery
from research_os.services.durable_backup import (
    DurableBackupRequest,
    create_durable_backup,
)
from research_os.services.indexing import (
    apply_indexes,
    render_indexes,
    render_project_indexes,
)
from research_os.services.ingestion import process_source_asset
from research_os.services.metrics import (
    metrics_json,
    metrics_snapshot_path,
    research_metrics,
)
from research_os.services.redaction import redact_secrets
from research_os.services.triage import expire_candidates, purge_candidates
from research_os.services.validation import validate_repository

JOB_NAMES = frozenset(
    {
        "validate",
        "indexes",
        "metrics",
        "source-process",
        "refresh",
        "discover",
        "expire",
        "purge",
        "enrich",
        "daily-brief",
        "forecast-alerts",
        "backup-candidate",
        "backup-durable",
    }
)


@dataclass(frozen=True)
class JobRunResult:
    job_id: str
    status: str
    message: str
    path: Path


def load_durable_backup_request(
    root: Path,
    config_path: Path,
    *,
    apply: bool,
) -> DurableBackupRequest:
    """Load the minimal ignored durable-backup configuration without echoing it."""
    root = root.resolve()
    expanded = config_path.expanduser()
    resolved = (
        expanded.resolve() if expanded.is_absolute() else (root / expanded).resolve()
    )
    try:
        payload: object = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError(
            "durable backup configuration is unavailable or invalid"
        ) from None
    if not isinstance(payload, dict) or set(payload) != {
        "repository",
        "recipients",
    }:
        raise ValueError("durable backup configuration is unavailable or invalid")
    repository = payload.get("repository")
    recipients = payload.get("recipients")
    if (
        not isinstance(repository, str)
        or not repository
        or not isinstance(recipients, list)
        or not recipients
        or any(not isinstance(item, str) or not item for item in recipients)
    ):
        raise ValueError("durable backup configuration is unavailable or invalid")
    try:
        backend = GitHubPrivateReleaseBackend(repository)
    except ValueError:
        raise ValueError(
            "durable backup configuration is unavailable or invalid"
        ) from None
    return DurableBackupRequest(
        root=root,
        recipients=tuple(recipients),
        backend=backend,
        apply=apply,
    )


def _next_job_id(root: Path, started_at: datetime) -> str:
    compact = started_at.strftime("%Y%m%d%H%M%S")
    folder = root / "05_Research" / "Operations" / "Jobs"
    numbers = [
        int(match.group(1))
        for path in folder.glob(f"JOB-{compact}-*.md")
        if (match := re.match(rf"^JOB-{compact}-(\d{{3}})", path.name))
    ]
    number = max(numbers, default=0) + 1
    if number > 999:
        raise ValueError("Job Run sequence exhausted for this second")
    return f"JOB-{compact}-{number:03d}"


def _project_ids_for_job(
    root: Path,
    *,
    project_id: str | None,
    target: str | None,
) -> list[str]:
    objects, _ = validate_repository(root)
    if project_id:
        return [project_id]
    if target:
        item = next((obj for obj in objects if obj.object_id == target), None)
        if item:
            return sorted(str(value) for value in item.metadata.get("project_ids", []))
    return sorted(
        obj.object_id
        for obj in objects
        if obj.object_type == "project" and obj.metadata.get("status") == "active"
    )


def _execute_job(
    root: Path,
    job_name: str,
    *,
    project_id: str | None,
    target: str | None,
    as_of: str,
    durable_config: Path | None,
) -> str:
    objects, findings = validate_repository(root)
    errors = [finding for finding in findings if finding.level == "error"]
    if errors:
        raise ValueError(f"repository has {len(errors)} validation errors")
    if job_name == "validate":
        return f"validation passed with {len(findings)} warnings/findings"
    if job_name == "source-process":
        if not target:
            raise ValueError("source-process requires --target SRC-ID")
        changed = process_source_asset(root, target)
        return (
            f"{target} already processed; no changes"
            if not changed
            else f"{target} processed; {len(changed)} paths changed"
        )
    if job_name == "discover":
        if not target:
            raise ValueError("discover requires --target CHN-ID")
        result = run_discovery(root, target, apply=True)
        message = (
            f"discovery run {result['run_id']} for {target}: "
            f"{result['candidate_count']} candidates, "
            f"{result['inserted']} inserted"
        )
        if result.get("skipped"):
            message += f", {result['skipped']} skipped (already sourced)"
        return message
    if job_name == "expire":
        expired = expire_candidates(root, apply=True)
        purged = purge_candidates(root, apply=True)
        return (
            f"retention sweep: {len(expired['expired'])} expired, "
            f"{len(purged['purged'])} purged"
        )
    if job_name == "purge":
        purged = purge_candidates(root, apply=True)
        return f"retention purge: {len(purged['purged'])} purged"
    if job_name == "enrich":
        from research_os.services.candidate_queue import enrich_candidates

        enriched = enrich_candidates(root, apply=True)
        return f"candidate enrichment: {len(enriched)} enriched"
    if job_name == "backup-candidate":
        destination = (
            Path(target).expanduser()
            if target
            else root
            / "09_Automation"
            / "operational"
            / "backups"
            / "candidate"
            / f"candidates-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.db"
        )
        manifest = create_candidate_snapshot(root, destination)
        return (
            f"Candidate DB snapshot created: {destination}; sha256={manifest['sha256']}"
        )
    if job_name == "backup-durable":
        if durable_config is None:
            raise ValueError("durable backup configuration is required")
        request = load_durable_backup_request(root, durable_config, apply=True)
        receipt = create_durable_backup(request)
        return (
            f"durable backup verified: backup_id={receipt.backup_id}; "
            f"sets={len(receipt.sets)}"
        )
    if job_name == "daily-brief":
        content = render_daily_brief(daily_brief(root, as_of))
        try:
            path = write_daily_brief(root, as_of, content)
        except FileExistsError:
            return f"daily brief already exists: Daily_Brief_{as_of}.md"
        return f"daily brief created: {path.name}"
    if job_name == "forecast-alerts":
        report = decision_alerts(root, as_of=as_of)
        return (
            f"decision alerts: {report['due_count']} due "
            f"({report['overdue_count']} overdue), "
            f"{report['active_recommendations']} active recommendations; "
            + "; ".join(report["alerts"])
        )
    if job_name in {"indexes", "refresh"}:
        apply_indexes(root, render_indexes(objects))
        projects = [
            obj.object_id
            for obj in objects
            if obj.object_type == "project"
            and (project_id is None or obj.object_id == project_id)
        ]
        for item in projects:
            apply_indexes(root, render_project_indexes(objects, item))
        if job_name == "indexes":
            return f"rebuilt global and {len(projects)} project index sets"
    if job_name in {"metrics", "refresh"}:
        metrics = research_metrics(root, as_of, project_id)
        relative = metrics_snapshot_path(as_of, project_id)
        expected = metrics_json(metrics)
        absolute = root / relative
        if absolute.exists():
            if absolute.read_text(encoding="utf-8") != expected:
                raise ValueError(
                    f"metrics snapshot exists with different content: {relative}"
                )
            snapshot_result = f"metrics snapshot unchanged: {relative}"
        else:
            transaction = FileTransaction(root)
            transaction.stage_create(relative, expected)
            transaction.commit()
            snapshot_result = f"metrics snapshot created: {relative}"
        if job_name == "metrics":
            return snapshot_result
        return f"indexes rebuilt; {snapshot_result}"
    raise ValueError(f"unsupported job {job_name}")


def _write_job_record(
    root: Path,
    *,
    job_id: str,
    job_name: str,
    started_at: datetime,
    finished_at: datetime,
    project_ids: list[str],
    target: str | None,
    status: str,
    message: str,
) -> Path:
    relative = Path("05_Research") / "Operations" / "Jobs" / f"{job_id}-{job_name}.md"
    content = f"""---
id: {job_id}
type: job
title: {json.dumps(f"Job {job_name}", ensure_ascii=False)}
created_at: {started_at.date().isoformat()}
updated_at: {finished_at.date().isoformat()}
schema_version: 1
project_ids: [{", ".join(project_ids)}]
status: {status}
job_name: {job_name}
started_at: {started_at.isoformat()}
finished_at: {finished_at.isoformat()}
target: {target or ""}
message: {json.dumps(message, ensure_ascii=False)}
tags: []
---

# {job_id}

## Job

- Name: {job_name}
- Target: {target or "—"}
- Projects: {", ".join(project_ids) or "global"}

## Result

- Status: {status}
- Message: {message}
"""
    transaction = FileTransaction(root)
    transaction.stage_create(relative, content)
    return transaction.commit()[0]


def run_job(
    root: Path,
    job_name: str,
    *,
    project_id: str | None = None,
    target: str | None = None,
    as_of: str | None = None,
    started_at: datetime | None = None,
    durable_config: Path | None = None,
) -> JobRunResult:
    root = root.resolve()
    if job_name not in JOB_NAMES:
        raise ValueError(f"unsupported job {job_name}")
    started = started_at or datetime.now(UTC)
    if started.tzinfo is None:
        raise ValueError("started_at must include timezone")
    effective_as_of = as_of or started.date().isoformat()
    job_id = _next_job_id(root, started)
    project_ids = _project_ids_for_job(
        root,
        project_id=project_id,
        target=target,
    )
    try:
        message = _execute_job(
            root,
            job_name,
            project_id=project_id,
            target=target,
            as_of=effective_as_of,
            durable_config=durable_config,
        )
        status = "success"
    except Exception as exc:
        status = "failed"
        message = f"{type(exc).__name__}: {exc}"
    message = redact_secrets(message)
    finished = datetime.now(UTC)
    if started_at is not None:
        finished = started
    path = _write_job_record(
        root,
        job_id=job_id,
        job_name=job_name,
        started_at=started,
        finished_at=finished,
        project_ids=project_ids,
        target=target,
        status=status,
        message=message,
    )
    objects, findings = validate_repository(root)
    if not any(finding.level == "error" for finding in findings):
        apply_indexes(root, render_indexes(objects))
        for item in (obj for obj in objects if obj.object_type == "project"):
            apply_indexes(
                root,
                render_project_indexes(objects, item.object_id),
            )
    return JobRunResult(job_id, status, message, path)


def job_rows(
    root: Path,
    *,
    project_id: str | None = None,
    status: str | None = None,
) -> list[ResearchObject]:
    objects, _ = validate_repository(root)
    return sorted(
        (
            obj
            for obj in objects
            if obj.object_type == "job"
            and (
                project_id is None or project_id in obj.metadata.get("project_ids", [])
            )
            and (status is None or obj.metadata.get("status") == status)
        ),
        key=lambda obj: str(obj.metadata.get("started_at")),
        reverse=True,
    )
