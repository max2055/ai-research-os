"""SQLite control plane for the Web-hosted scheduler.

The research Markdown tree remains authoritative for research facts.  This
database owns operational state only: schedules, queued/running jobs, worker
heartbeats and a redacted mutation audit trail.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

OverlapPolicy = Literal["skip"]
MissedRunPolicy = Literal["catch_up_once", "skip_missed"]
RunStatus = Literal[
    "queued", "claimed", "running", "success", "failed", "cancelled", "skipped"
]

_OVERLAP = {"skip"}
_MISSED = {"catch_up_once", "skip_missed"}
_RUN_STATUSES = {
    "queued",
    "claimed",
    "running",
    "success",
    "failed",
    "cancelled",
    "skipped",
}


class ScheduleConflictError(RuntimeError):
    """The caller attempted to update an old schedule version."""


class ScheduleNotFoundError(KeyError):
    pass


def operations_db_path(root: Path) -> Path:
    """Return the stable database location under a repository root."""
    root = Path(root)
    if root.name == "operations.db":
        return root
    return root / "09_Automation" / "operational" / "operations.db"


def _utc(value: str | datetime) -> str:
    dt = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if dt.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ScheduleSpec:
    schedule_id: str
    name: str
    job_name: str
    target: str | None
    project_id: str | None
    interval_seconds: int
    timezone: str
    enabled: bool
    retry_limit: int
    retry_backoff_seconds: int
    timeout_seconds: int
    overlap_policy: OverlapPolicy = "skip"
    missed_run_policy: MissedRunPolicy = "catch_up_once"

    def validate(self) -> None:
        if not self.schedule_id or not self.name or not self.job_name:
            raise ValueError("schedule_id, name and job_name are required")
        if not 1 <= self.interval_seconds <= 31_536_000:
            raise ValueError("interval_seconds must be between 1 and 31536000")
        if not 0 <= self.retry_limit <= 5:
            raise ValueError("retry_limit must be between 0 and 5")
        if not 1 <= self.retry_backoff_seconds <= 86_400:
            raise ValueError("retry_backoff_seconds must be between 1 and 86400")
        if not 30 <= self.timeout_seconds <= 86_400:
            raise ValueError("timeout_seconds must be between 30 and 86400")
        if self.overlap_policy not in _OVERLAP:
            raise ValueError("invalid overlap_policy")
        if self.missed_run_policy not in _MISSED:
            raise ValueError("invalid missed_run_policy")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("invalid IANA timezone") from exc


@dataclass(frozen=True)
class ScheduleRecord(ScheduleSpec):
    next_run_at: str | None = None
    version: int = 1
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ScheduleRunRecord:
    run_id: str
    schedule_id: str | None
    job_name: str
    target: str | None
    project_id: str | None
    request_kind: str
    as_of: str
    status: RunStatus
    attempt: int
    max_attempts: int
    message: str | None
    metadata: Mapping[str, Any]
    queued_at: str
    started_at: str | None
    finished_at: str | None
    lease_owner: str | None
    lease_expires_at: str | None


def _connect(db: Path) -> sqlite3.Connection:
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db, timeout=5.0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def apply_migrations(db: Path) -> None:
    with _connect(Path(db)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS schedules (
                schedule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                job_name TEXT NOT NULL,
                target TEXT,
                project_id TEXT,
                interval_seconds INTEGER NOT NULL,
                timezone TEXT NOT NULL,
                enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                retry_limit INTEGER NOT NULL,
                retry_backoff_seconds INTEGER NOT NULL,
                timeout_seconds INTEGER NOT NULL,
                overlap_policy TEXT NOT NULL,
                missed_run_policy TEXT NOT NULL,
                next_run_at TEXT,
                version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS schedule_runs (
                run_id TEXT PRIMARY KEY,
                schedule_id TEXT REFERENCES schedules(schedule_id) ON DELETE SET NULL,
                job_name TEXT NOT NULL,
                target TEXT,
                project_id TEXT,
                request_kind TEXT NOT NULL,
                as_of TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 1,
                message TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                queued_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                lease_owner TEXT,
                lease_expires_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_run_per_schedule
                ON schedule_runs(schedule_id)
                WHERE schedule_id IS NOT NULL AND status IN ('claimed', 'running');
            CREATE INDEX IF NOT EXISTS due_runs ON schedule_runs(status, queued_at);
            CREATE TABLE IF NOT EXISTS worker_state (
                worker_id TEXT PRIMARY KEY,
                pid INTEGER,
                status TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL,
                started_at TEXT,
                stopped_at TEXT,
                last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS service_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                details_json TEXT NOT NULL DEFAULT '{}'
            );
            INSERT INTO schema_meta(key, value) VALUES ('schema_version', '1')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """
        )


def _row_schedule(row: sqlite3.Row) -> ScheduleRecord:
    values = dict(row)
    values["enabled"] = bool(values["enabled"])
    return ScheduleRecord(
        **{field.name: values[field.name] for field in fields(ScheduleRecord)}
    )


def _row_run(row: sqlite3.Row) -> ScheduleRunRecord:
    values = dict(row)
    values["metadata"] = json.loads(values.pop("metadata_json") or "{}")
    return ScheduleRunRecord(**values)


def _event(
    connection: sqlite3.Connection,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    details: Mapping[str, Any] | None,
    now: str,
) -> None:
    connection.execute(
        "INSERT INTO service_events(occurred_at, actor, action, resource_type, "
        "resource_id, details_json) VALUES(?,?,?,?,?,?)",
        (
            _utc(now),
            actor,
            action,
            resource_type,
            resource_id,
            json.dumps(dict(details or {}), sort_keys=True),
        ),
    )


def create_schedule(
    db: Path, spec: ScheduleSpec, *, actor: str, now: str
) -> ScheduleRecord:
    spec.validate()
    timestamp = _utc(now)
    record = ScheduleRecord(
        **{**spec.__dict__, "created_at": timestamp, "updated_at": timestamp}
    )
    with _connect(Path(db)) as connection:
        apply_migrations(Path(db))
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                "INSERT INTO schedules VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.schedule_id,
                    record.name,
                    record.job_name,
                    record.target,
                    record.project_id,
                    record.interval_seconds,
                    record.timezone,
                    int(record.enabled),
                    record.retry_limit,
                    record.retry_backoff_seconds,
                    record.timeout_seconds,
                    record.overlap_policy,
                    record.missed_run_policy,
                    record.next_run_at,
                    record.version,
                    record.created_at,
                    record.updated_at,
                ),
            )
            _event(
                connection,
                actor=actor,
                action="schedule.create",
                resource_type="schedule",
                resource_id=record.schedule_id,
                details={"version": 1},
                now=timestamp,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return record


def get_schedule(db: Path, schedule_id: str) -> ScheduleRecord | None:
    apply_migrations(Path(db))
    with _connect(Path(db)) as connection:
        row = connection.execute(
            "SELECT * FROM schedules WHERE schedule_id=?", (schedule_id,)
        ).fetchone()
    return _row_schedule(row) if row else None


def list_schedules(db: Path, *, enabled: bool | None = None) -> list[ScheduleRecord]:
    apply_migrations(Path(db))
    query = "SELECT * FROM schedules"
    args: tuple[Any, ...] = ()
    if enabled is not None:
        query += " WHERE enabled=?"
        args = (int(enabled),)
    query += " ORDER BY schedule_id"
    with _connect(Path(db)) as connection:
        rows = connection.execute(query, args).fetchall()
    return [_row_schedule(row) for row in rows]


def update_schedule(
    db: Path,
    schedule_id: str,
    *,
    expected_version: int,
    changes: Mapping[str, Any],
    actor: str,
    now: str,
) -> ScheduleRecord:
    current = get_schedule(Path(db), schedule_id)
    if current is None:
        raise ScheduleNotFoundError(schedule_id)
    values = current.__dict__.copy()
    allowed = {field.name for field in fields(ScheduleSpec)}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unknown schedule fields: {sorted(unknown)}")
    values.update(changes)
    candidate = ScheduleSpec(**{name: values[name] for name in allowed})
    candidate.validate()
    timestamp = _utc(now)
    with _connect(Path(db)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT version FROM schedules WHERE schedule_id=?", (schedule_id,)
        ).fetchone()
        if row is None:
            connection.rollback()
            raise ScheduleNotFoundError(schedule_id)
        if int(row[0]) != expected_version:
            connection.rollback()
            raise ScheduleConflictError(schedule_id)
        new_version = expected_version + 1
        connection.execute(
            "UPDATE schedules SET name=?, job_name=?, target=?, project_id=?, "
            "interval_seconds=?, timezone=?, enabled=?, retry_limit=?, "
            "retry_backoff_seconds=?, timeout_seconds=?, overlap_policy=?, "
            "missed_run_policy=?, next_run_at=?, version=?, updated_at=? "
            "WHERE schedule_id=?",
            (
                candidate.name,
                candidate.job_name,
                candidate.target,
                candidate.project_id,
                candidate.interval_seconds,
                candidate.timezone,
                int(candidate.enabled),
                candidate.retry_limit,
                candidate.retry_backoff_seconds,
                candidate.timeout_seconds,
                candidate.overlap_policy,
                candidate.missed_run_policy,
                values.get("next_run_at"),
                new_version,
                timestamp,
                schedule_id,
            ),
        )
        _event(
            connection,
            actor=actor,
            action="schedule.update",
            resource_type="schedule",
            resource_id=schedule_id,
            details={"version": new_version, "fields": sorted(changes)},
            now=timestamp,
        )
        connection.commit()
    result = get_schedule(Path(db), schedule_id)
    assert result is not None
    return result


def set_schedule_enabled(
    db: Path,
    schedule_id: str,
    *,
    enabled: bool,
    expected_version: int,
    actor: str,
    now: str,
) -> ScheduleRecord:
    return update_schedule(
        db,
        schedule_id,
        expected_version=expected_version,
        changes={"enabled": enabled},
        actor=actor,
        now=now,
    )


def set_schedule_next_run(db: Path, schedule_id: str, next_run_at: str | None) -> None:
    with _connect(Path(db)) as connection:
        connection.execute(
            "UPDATE schedules SET next_run_at=?, updated_at=? WHERE schedule_id=?",
            (
                _utc(next_run_at) if next_run_at else None,
                _utc(datetime.now(UTC)),
                schedule_id,
            ),
        )


def requeue_run(db: Path, run_id: str, *, queued_at: str) -> None:
    with _connect(Path(db)) as connection:
        connection.execute(
            "UPDATE schedule_runs SET status='queued', queued_at=?, "
            "lease_owner=NULL, lease_expires_at=NULL WHERE run_id=?",
            (_utc(queued_at), run_id),
        )


def create_run(
    db: Path,
    *,
    run_id: str,
    schedule_id: str | None,
    job_name: str,
    target: str | None,
    project_id: str | None,
    request_kind: str,
    as_of: str,
    queued_at: str | datetime,
    max_attempts: int = 1,
    metadata: Mapping[str, Any] | None = None,
    actor: str | None = None,
) -> ScheduleRunRecord:
    if request_kind not in {"scheduled", "manual", "historical"}:
        raise ValueError("invalid request_kind")
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    timestamp = _utc(queued_at)
    apply_migrations(Path(db))
    with _connect(Path(db)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                "INSERT INTO schedule_runs(run_id,schedule_id,job_name,target,"
                "project_id,request_kind,as_of,status,attempt,max_attempts,"
                "metadata_json,queued_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    schedule_id,
                    job_name,
                    target,
                    project_id,
                    request_kind,
                    as_of,
                    "queued",
                    0,
                    max_attempts,
                    json.dumps(dict(metadata or {}), sort_keys=True),
                    timestamp,
                ),
            )
            if actor:
                _event(
                    connection,
                    actor=actor,
                    action="run.enqueue",
                    resource_type="schedule_run",
                    resource_id=run_id,
                    details={"job_name": job_name, "request_kind": request_kind},
                    now=timestamp,
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    result = get_run(Path(db), run_id)
    assert result is not None
    return result


def get_run(db: Path, run_id: str) -> ScheduleRunRecord | None:
    apply_migrations(Path(db))
    with _connect(Path(db)) as connection:
        row = connection.execute(
            "SELECT * FROM schedule_runs WHERE run_id=?", (run_id,)
        ).fetchone()
    return _row_run(row) if row else None


def latest_run(db: Path, schedule_id: str) -> ScheduleRunRecord | None:
    apply_migrations(Path(db))
    with _connect(Path(db)) as connection:
        row = connection.execute(
            "SELECT * FROM schedule_runs WHERE schedule_id=? "
            "ORDER BY queued_at DESC LIMIT 1",
            (schedule_id,),
        ).fetchone()
    return _row_run(row) if row else None


def list_runs(db: Path, *, limit: int = 50, offset: int = 0) -> list[ScheduleRunRecord]:
    apply_migrations(Path(db))
    with _connect(Path(db)) as connection:
        rows = connection.execute(
            "SELECT * FROM schedule_runs ORDER BY queued_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [_row_run(row) for row in rows]


def claim_run(
    db: Path, run_id: str, *, worker_id: str, now: str, lease_seconds: int = 300
) -> ScheduleRunRecord | None:
    timestamp = _utc(now)
    expiry = _utc(
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        + timedelta(seconds=lease_seconds)
    )
    with _connect(Path(db)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM schedule_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None or row["status"] not in {"queued", "claimed", "running"}:
            connection.rollback()
            return None
        if (
            row["status"] in {"claimed", "running"}
            and row["lease_expires_at"]
            and row["lease_expires_at"] > timestamp
            and row["lease_owner"] != worker_id
        ):
            connection.rollback()
            return None
        try:
            connection.execute(
                "UPDATE schedule_runs SET status='claimed', attempt=attempt+1, "
                "lease_owner=?, lease_expires_at=?, "
                "started_at=COALESCE(started_at, ?) WHERE run_id=?",
                (worker_id, expiry, timestamp, run_id),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            connection.rollback()
            return None
    return get_run(Path(db), run_id)


def mark_run_running(db: Path, run_id: str, *, worker_id: str) -> None:
    with _connect(Path(db)) as connection:
        cursor = connection.execute(
            "UPDATE schedule_runs SET status='running' "
            "WHERE run_id=? AND status='claimed' AND lease_owner=?",
            (run_id, worker_id),
        )
        if cursor.rowcount != 1:
            raise ScheduleConflictError(run_id)


def reclaim_stale_leases(db: Path, *, now: str) -> int:
    timestamp = _utc(now)
    with _connect(Path(db)) as connection:
        cursor = connection.execute(
            "UPDATE schedule_runs SET status='queued', lease_owner=NULL, "
            "lease_expires_at=NULL WHERE status IN ('claimed','running') "
            "AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?",
            (timestamp,),
        )
        return int(cursor.rowcount)


def finalize_run(
    db: Path,
    run_id: str,
    *,
    status: RunStatus,
    message: str | None,
    finished_at: str | datetime,
) -> ScheduleRunRecord:
    if status not in _RUN_STATUSES - {"queued", "claimed", "running"}:
        raise ValueError("invalid terminal run status")
    with _connect(Path(db)) as connection:
        connection.execute(
            "UPDATE schedule_runs SET status=?, message=?, finished_at=?, "
            "lease_owner=NULL, lease_expires_at=NULL WHERE run_id=?",
            (status, message, _utc(finished_at), run_id),
        )
    result = get_run(Path(db), run_id)
    if result is None:
        raise ScheduleNotFoundError(run_id)
    return result


def refresh_worker_heartbeat(
    db_or_root: Path,
    worker_id: str,
    heartbeat_at: str,
    *,
    pid: int | None = None,
    status: str = "ready",
    started_at: str | None = None,
) -> None:
    db = operations_db_path(db_or_root)
    timestamp = _utc(heartbeat_at)
    with _connect(db) as connection:
        connection.execute(
            "INSERT INTO worker_state(worker_id,pid,status,heartbeat_at,started_at) "
            "VALUES(?,?,?,?,?) ON CONFLICT(worker_id) DO UPDATE SET "
            "pid=COALESCE(excluded.pid,worker_state.pid), "
            "status=excluded.status, heartbeat_at=excluded.heartbeat_at, "
            "started_at=COALESCE(worker_state.started_at, excluded.started_at)",
            (
                worker_id,
                pid,
                status,
                timestamp,
                _utc(started_at) if started_at else None,
            ),
        )


def record_worker_stop(
    db_or_root: Path, worker_id: str, *, stopped_at: str, status: str = "stopped"
) -> None:
    db = operations_db_path(db_or_root)
    timestamp = _utc(stopped_at)
    with _connect(db) as connection:
        connection.execute(
            "UPDATE worker_state SET status=?, stopped_at=?, heartbeat_at=? "
            "WHERE worker_id=?",
            (status, timestamp, timestamp, worker_id),
        )


def worker_state(db: Path, worker_id: str | None = None) -> sqlite3.Row | None:
    apply_migrations(Path(db))
    with _connect(Path(db)) as connection:
        if worker_id:
            return cast(
                sqlite3.Row | None,
                connection.execute(
                    "SELECT * FROM worker_state WHERE worker_id=?", (worker_id,)
                ).fetchone(),
            )
        return cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT * FROM worker_state ORDER BY heartbeat_at DESC LIMIT 1"
            ).fetchone(),
        )


__all__ = [name for name in globals() if not name.startswith("_")]
