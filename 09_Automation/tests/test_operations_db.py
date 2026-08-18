from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from research_os.services import operations_db
from research_os.services.operations_db import (
    ScheduleConflictError,
    ScheduleSpec,
    apply_migrations,
    claim_run,
    create_run,
    create_schedule,
    get_run,
    get_schedule,
    reclaim_stale_leases,
    refresh_worker_heartbeat,
    update_schedule,
)
from research_os.services.operations_health import (
    operations_db_health,
    schedule_health,
    worker_health,
)

NOW = "2026-08-17T01:00:00Z"


def _spec(**changes: object) -> ScheduleSpec:
    values = {
        "schedule_id": "SCH-channel-sec-micron",
        "name": "Micron SEC",
        "job_name": "discover",
        "target": "CHN-sec-micron",
        "project_id": None,
        "interval_seconds": 21600,
        "timezone": "Asia/Shanghai",
        "enabled": True,
        "retry_limit": 2,
        "retry_backoff_seconds": 30,
        "timeout_seconds": 1800,
        "overlap_policy": "skip",
        "missed_run_policy": "catch_up_once",
    }
    values.update(changes)
    return ScheduleSpec(**values)  # type: ignore[arg-type]


def test_schema_crud_and_optimistic_version(tmp_path: Path) -> None:
    db = tmp_path / "operations.db"
    apply_migrations(db)
    created = create_schedule(db, _spec(), actor="max", now=NOW)
    assert created.version == 1
    assert get_schedule(db, created.schedule_id) == created
    updated = update_schedule(
        db,
        created.schedule_id,
        expected_version=1,
        changes={"enabled": False},
        actor="max",
        now="2026-08-17T01:01:00Z",
    )
    assert updated.version == 2
    with pytest.raises(ScheduleConflictError):
        update_schedule(
            db,
            created.schedule_id,
            expected_version=1,
            changes={"enabled": True},
            actor="max",
            now="2026-08-17T01:02:00Z",
        )


def test_wal_constraints_lease_reclaim_and_audit(tmp_path: Path) -> None:
    db = tmp_path / "operations.db"
    apply_migrations(db)
    create_schedule(db, _spec(), actor="max", now=NOW)
    with sqlite3.connect(db) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        events = connection.execute(
            "SELECT action, details_json FROM service_events"
        ).fetchall()
    assert events == [("schedule.create", '{"version": 1}')]

    for run_id in ("RUN-1", "RUN-2"):
        create_run(
            db,
            run_id=run_id,
            schedule_id="SCH-channel-sec-micron",
            job_name="discover",
            target="CHN-sec-micron",
            project_id=None,
            request_kind="scheduled",
            as_of=NOW,
            queued_at=NOW,
        )
    assert claim_run(db, "RUN-1", worker_id="worker-1", now=NOW, lease_seconds=5)
    assert claim_run(db, "RUN-2", worker_id="worker-2", now=NOW) is None
    assert reclaim_stale_leases(db, now="2026-08-17T01:00:06Z") == 1
    assert claim_run(db, "RUN-2", worker_id="worker-2", now="2026-08-17T01:00:06Z")


def test_run_enqueue_and_service_audit_are_atomic(tmp_path: Path) -> None:
    db = tmp_path / "operations.db"
    apply_migrations(db)
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            operations_db,
            "_event",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                sqlite3.OperationalError("audit unavailable")
            ),
        )
        with pytest.raises(sqlite3.OperationalError, match="audit unavailable"):
            create_run(
                db,
                run_id="RUN-atomic",
                schedule_id=None,
                job_name="validate",
                target=None,
                project_id=None,
                request_kind="manual",
                as_of=NOW,
                queued_at=NOW,
                actor="max",
            )
    assert get_run(db, "RUN-atomic") is None


@pytest.mark.parametrize(
    "changes",
    [
        {"interval_seconds": 0},
        {"retry_limit": 6},
        {"timeout_seconds": 1},
        {"timezone": "Mars/Olympus"},
        {"overlap_policy": "allow"},
        {"missed_run_policy": "all"},
    ],
)
def test_invalid_schedule_values_fail_before_sql(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    db = tmp_path / "operations.db"
    with pytest.raises(ValueError):
        create_schedule(db, _spec(**changes), actor="max", now=NOW)
    assert not db.exists()


def test_operations_worker_and_schedule_health(tmp_path: Path) -> None:
    db = tmp_path / "operations.db"
    create_schedule(db, _spec(enabled=False), actor="max", now=NOW)
    refresh_worker_heartbeat(
        db,
        "worker-1",
        "2026-08-17T01:00:00Z",
        pid=123,
    )
    observed = datetime(2026, 8, 17, 1, 0, 10, tzinfo=UTC)
    assert operations_db_health(db) == {
        "status": "ok",
        "schema_version": 1,
        "integrity": "ok",
    }
    worker = worker_health(db, now=observed)
    assert worker["status"] == "ready"
    assert worker["heartbeat_age_seconds"] == 10.0
    schedules = schedule_health(db, now=observed)
    assert schedules["active"] == 0
    assert schedules["paused"] == 1
