"""Single-process scheduler worker owned by the Web application."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

from research_os.services.jobs import JobExecutionResult, execute_job
from research_os.services.operations_db import (
    ScheduleRunRecord,
    apply_migrations,
    claim_run,
    create_run,
    finalize_run,
    list_runs,
    list_schedules,
    mark_run_running,
    operations_db_path,
    reclaim_stale_leases,
    record_worker_stop,
    refresh_worker_heartbeat,
    requeue_run,
    set_schedule_next_run,
)
from research_os.services.redaction import redact_secrets
from research_os.services.schedule_control import SchedulePolicy, due_decision

JobExecutor = Callable[..., JobExecutionResult]


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parent_is_alive(parent_pid: int) -> bool:
    if parent_pid <= 1:
        return True
    try:
        os.kill(parent_pid, 0)
    except OSError:
        return False
    return True


def _run_id(now: str, sequence: int) -> str:
    compact = now.replace("-", "").replace(":", "").replace("T", "").replace("Z", "")
    return f"RUN-{compact}-{sequence:04d}"


@dataclass
class SchedulerWorker:
    root: Path
    worker_id: str
    parent_pid: int
    execute: JobExecutor = execute_job
    clock: Callable[[], str] = utc_now
    sleep: Callable[[float], None] = time.sleep
    lease_seconds: int = 300

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()
        apply_migrations(operations_db_path(self.root))
        self._sequence = 0

    def _queue_due_schedules(self, observed: str) -> None:
        db = operations_db_path(self.root)
        for schedule in list_schedules(db, enabled=True):
            next_run = schedule.next_run_at or observed
            decision = due_decision(
                next_run_at=next_run,
                now=observed,
                policy=schedule.missed_run_policy,
                schedule=SchedulePolicy(schedule.interval_seconds, schedule.timezone),
            )
            if decision.action == "not_due":
                if schedule.next_run_at is None:
                    set_schedule_next_run(
                        db, schedule.schedule_id, decision.next_run_at
                    )
                continue
            set_schedule_next_run(db, schedule.schedule_id, decision.next_run_at)
            if decision.action != "run_once":
                continue
            self._sequence += 1
            try:
                create_run(
                    db,
                    run_id=_run_id(observed, self._sequence),
                    schedule_id=schedule.schedule_id,
                    job_name=schedule.job_name,
                    target=schedule.target,
                    project_id=schedule.project_id,
                    request_kind="scheduled",
                    as_of=observed,
                    queued_at=observed,
                    max_attempts=schedule.retry_limit + 1,
                )
            except Exception:
                # The partial unique active-run index makes overlap a harmless
                # race between a restarted worker and the current worker.
                continue

    def _claimable(self, observed: str) -> list[ScheduleRunRecord]:
        return [
            run
            for run in list_runs(operations_db_path(self.root), limit=200)
            if run.status == "queued"
            and (run.request_kind == "manual" or run.queued_at <= observed)
        ]

    def tick(self, *, now: str | None = None, stop: Event | None = None) -> int:
        observed = now or self.clock()
        db = operations_db_path(self.root)
        refresh_worker_heartbeat(
            db, self.worker_id, observed, pid=os.getpid(), status="ready"
        )
        reclaim_stale_leases(db, now=observed)
        self._queue_due_schedules(observed)
        claimed_count = 0
        schedules = {item.schedule_id: item for item in list_schedules(db)}
        for queued in self._claimable(observed):
            if stop is not None and stop.is_set():
                break
            schedule = schedules.get(queued.schedule_id or "")
            claimed = claim_run(
                db,
                queued.run_id,
                worker_id=self.worker_id,
                now=observed,
                lease_seconds=(
                    schedule.timeout_seconds if schedule else self.lease_seconds
                ),
            )
            if claimed is None:
                continue
            claimed_count += 1
            mark_run_running(db, claimed.run_id, worker_id=self.worker_id)
            config = self.root / "09_Automation" / "operational" / "durable_backup.json"
            try:
                result = self.execute(
                    self.root,
                    claimed.job_name,
                    project_id=claimed.project_id,
                    target=claimed.target,
                    as_of=claimed.as_of,
                    durable_config=config if config.exists() else None,
                )
            except Exception as exc:
                result = JobExecutionResult(
                    "failed",
                    redact_secrets(f"{type(exc).__name__}: {exc}"),
                )
            result = JobExecutionResult(
                result.status,
                redact_secrets(result.message),
            )
            if (
                result.status == "failed"
                and schedule
                and claimed.attempt < claimed.max_attempts
            ):
                requeue_run(db, claimed.run_id, queued_at=self.clock())
                self.sleep(float(schedule.retry_backoff_seconds * claimed.attempt))
                continue
            finalize_run(
                db,
                claimed.run_id,
                status=result.status,
                message=result.message,
                finished_at=self.clock(),
            )
        refresh_worker_heartbeat(
            db, self.worker_id, self.clock(), pid=os.getpid(), status="ready"
        )
        return claimed_count

    def run_forever(self, stop: Event, *, poll_seconds: float = 5.0) -> None:
        while not stop.is_set() and parent_is_alive(self.parent_pid):
            self.tick(stop=stop)
            stop.wait(poll_seconds)
        record_worker_stop(
            operations_db_path(self.root), self.worker_id, stopped_at=self.clock()
        )


__all__ = ["SchedulerWorker", "parent_is_alive", "utc_now"]
