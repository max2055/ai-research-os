"""One-time, idempotent import adapter for legacy Channel and Job Markdown."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from research_os.repositories.markdown import MarkdownDocument
from research_os.services.operations_db import (
    RunStatus,
    ScheduleSpec,
    apply_migrations,
    create_run,
    create_schedule,
    get_run,
    get_schedule,
    operations_db_path,
)
from research_os.services.schedule import interval_from_schedule


@dataclass(frozen=True)
class MigrationResult:
    channels_imported: int
    jobs_imported: int
    warnings: tuple[str, ...]
    files_changed: tuple[Path, ...] = ()


def _iso(value: object, fallback: str) -> str:
    if value is None or not str(value).strip():
        return fallback
    text = str(value)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _job_id(path: Path) -> str:
    try:
        doc = MarkdownDocument.read(path)
        value = str(doc.metadata.get("id") or path.stem)
    except (OSError, ValueError):
        value = path.stem
    return value


def migrate_operational_history(root: Path, *, actor: str, now: str) -> MigrationResult:
    root = Path(root).resolve()
    db = operations_db_path(root)
    apply_migrations(db)
    warnings: list[str] = []
    channels = 0
    jobs = 0
    channel_dir = root / "02_Knowledge" / "Channels"
    for path in sorted(channel_dir.glob("CHN-*.md")):
        try:
            document = MarkdownDocument.read(path)
        except (OSError, ValueError) as exc:
            warnings.append(f"{path}: cannot import channel ({exc})")
            continue
        meta = document.metadata
        channel_id = str(meta.get("id") or path.stem)
        schedule_text = str(meta.get("schedule") or "")
        interval = interval_from_schedule(schedule_text)
        enabled = bool(meta.get("enabled"))
        if (
            str(meta.get("review_status") or "") != "reviewed"
            or str(meta.get("license_status") or "") == "restricted"
        ):
            enabled = False
        if interval is None:
            enabled = False
            warnings.append(f"{channel_id}: unparseable schedule {schedule_text!r}")
            continue_interval = 3600
        else:
            continue_interval = max(1, int(interval.total_seconds()))
        schedule_id = f"SCH-channel-{channel_id.removeprefix('CHN-')}"
        if get_schedule(db, schedule_id) is not None:
            continue
        project_ids = meta.get("project_ids")
        project_id = (
            str(project_ids[0])
            if isinstance(project_ids, list) and project_ids
            else None
        )
        spec = ScheduleSpec(
            schedule_id=schedule_id,
            name=str(meta.get("name") or meta.get("title") or channel_id),
            job_name="discover",
            target=channel_id,
            project_id=project_id,
            interval_seconds=continue_interval,
            timezone=str(meta.get("timezone") or "UTC"),
            enabled=enabled,
            retry_limit=2,
            retry_backoff_seconds=30,
            timeout_seconds=1800,
            missed_run_policy="catch_up_once",
        )
        try:
            create_schedule(db, spec, actor=actor, now=now)
        except ValueError as exc:
            warnings.append(f"{channel_id}: schedule not imported ({exc})")
            continue
        channels += 1

    jobs_dir = root / "05_Research" / "Operations" / "Jobs"
    for path in sorted(jobs_dir.glob("JOB-*.md")):
        run_id = _job_id(path)
        if get_run(db, run_id) is not None:
            continue
        try:
            doc = MarkdownDocument.read(path)
            meta = doc.metadata
        except (OSError, ValueError) as exc:
            warnings.append(f"{path}: cannot import job ({exc})")
            continue
        status = str(meta.get("status") or "failed")
        if status not in {"success", "failed", "cancelled", "skipped"}:
            status = "failed"
        queued_at = _iso(meta.get("started_at"), now)
        create_run(
            db,
            run_id=run_id,
            schedule_id=None,
            job_name=str(meta.get("job_name") or "unknown"),
            target=str(meta.get("target")) if meta.get("target") else None,
            project_id=None,
            request_kind="historical",
            as_of=queued_at,
            queued_at=queued_at,
            metadata={
                "legacy_path": str(path.relative_to(root)),
                "dedupe_key": hashlib.sha256(str(path).encode()).hexdigest(),
            },
        )
        from research_os.services.operations_db import finalize_run

        finalize_run(
            db,
            run_id,
            status=cast(RunStatus, status),
            message=str(meta.get("message") or ""),
            finished_at=_iso(meta.get("finished_at"), queued_at),
        )
        jobs += 1
    return MigrationResult(channels, jobs, tuple(warnings))


__all__ = ["MigrationResult", "migrate_operational_history"]
