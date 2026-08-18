from __future__ import annotations

import os
import sys
from pathlib import Path
from threading import Event
from unittest.mock import patch

from research_os.runtime import worker as worker_runtime
from research_os.services import scheduler_worker
from research_os.services.jobs import JobExecutionResult
from research_os.services.operations_db import (
    ScheduleSpec,
    create_run,
    create_schedule,
    get_run,
    latest_run,
    operations_db_path,
    set_schedule_next_run,
    worker_state,
)
from research_os.services.scheduler_worker import SchedulerWorker

NOW = "2026-08-17T06:00:00Z"


def _schedule(
    root: Path,
    *,
    missed: str = "catch_up_once",
    retry: int = 0,
    timeout: int = 60,
) -> str:
    db = operations_db_path(root)
    schedule_id = f"SCH-{missed}"
    create_schedule(
        db,
        ScheduleSpec(
            schedule_id=schedule_id,
            name="Validate",
            job_name="validate",
            target=None,
            project_id=None,
            interval_seconds=21600,
            timezone="Asia/Shanghai",
            enabled=True,
            retry_limit=retry,
            retry_backoff_seconds=30,
            timeout_seconds=timeout,
            overlap_policy="skip",
            missed_run_policy=missed,  # type: ignore[arg-type]
        ),
        actor="test",
        now="2026-08-17T00:00:00Z",
    )
    set_schedule_next_run(db, schedule_id, NOW)
    return schedule_id


def test_tick_executes_due_schedule_and_updates_heartbeat(tmp_path: Path) -> None:
    schedule_id = _schedule(tmp_path)
    calls: list[str] = []

    def execute(_root: Path, job_name: str, **_: object) -> JobExecutionResult:
        calls.append(job_name)
        return JobExecutionResult("success", "done")

    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=os.getpid(),
        execute=execute,
        clock=lambda: NOW,
    )
    assert worker.tick(now=NOW) == 1
    run = latest_run(operations_db_path(tmp_path), schedule_id)
    assert run is not None and run.status == "success"
    assert run.request_kind == "scheduled"
    assert calls == ["validate"]
    state = worker_state(operations_db_path(tmp_path), "worker-test")
    assert state is not None and state["heartbeat_at"] == NOW


def test_skip_missed_advances_without_execution(tmp_path: Path) -> None:
    schedule_id = _schedule(tmp_path, missed="skip_missed")
    set_schedule_next_run(
        operations_db_path(tmp_path), schedule_id, "2026-08-16T00:00:00Z"
    )
    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=os.getpid(),
        execute=lambda *_args, **_kwargs: JobExecutionResult("success", "done"),
        clock=lambda: NOW,
    )
    assert worker.tick(now=NOW) == 0
    assert latest_run(operations_db_path(tmp_path), schedule_id) is None


def test_retry_backoff_is_bounded_and_failure_is_redacted(tmp_path: Path) -> None:
    schedule_id = _schedule(tmp_path, retry=2)
    results = [
        JobExecutionResult("failed", "token=first"),
        JobExecutionResult("failed", "token=second"),
        JobExecutionResult("success", "done"),
    ]
    sleeps: list[float] = []
    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=os.getpid(),
        execute=lambda *_args, **_kwargs: results.pop(0),
        clock=lambda: NOW,
        sleep=sleeps.append,
    )
    worker.tick(now=NOW)
    worker.tick(now=NOW)
    worker.tick(now=NOW)
    run = latest_run(operations_db_path(tmp_path), schedule_id)
    assert run is not None and run.status == "success" and run.attempt == 3
    assert sleeps == [30.0, 60.0]


def test_executor_exception_is_finalized_and_parent_loss_stops(tmp_path: Path) -> None:
    schedule_id = _schedule(tmp_path)

    def explode(*_args: object, **_kwargs: object) -> JobExecutionResult:
        raise RuntimeError("token=secret-value")

    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=999999,
        execute=explode,
        clock=lambda: NOW,
    )
    worker.tick(now=NOW)
    run = latest_run(operations_db_path(tmp_path), schedule_id)
    assert run is not None and run.status == "failed"
    assert "secret-value" not in (run.message or "")
    with patch(
        "research_os.services.scheduler_worker.parent_is_alive", return_value=False
    ):
        worker.run_forever(Event(), poll_seconds=0)
    state = worker_state(operations_db_path(tmp_path), "worker-test")
    assert state is not None and state["status"] == "stopped"


def test_schedule_timeout_sets_the_run_lease(tmp_path: Path) -> None:
    schedule_id = _schedule(tmp_path, timeout=90)
    lease_expiries: list[str | None] = []

    def execute(*_args: object, **_kwargs: object) -> JobExecutionResult:
        run = latest_run(operations_db_path(tmp_path), schedule_id)
        assert run is not None
        lease_expiries.append(run.lease_expires_at)
        return JobExecutionResult("success", "done")

    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=os.getpid(),
        execute=execute,
        clock=lambda: NOW,
    )
    worker.tick(now=NOW)
    assert lease_expiries == ["2026-08-17T06:01:30Z"]


def test_stop_signal_prevents_claiming_another_queued_run(tmp_path: Path) -> None:
    db = operations_db_path(tmp_path)
    for sequence in (1, 2):
        create_run(
            db,
            run_id=f"RUN-manual-{sequence}",
            schedule_id=None,
            job_name="validate",
            target=None,
            project_id=None,
            request_kind="manual",
            as_of=NOW,
            queued_at=f"2026-08-17T05:59:0{sequence}Z",
        )
    stop = Event()
    calls: list[str] = []

    def execute(*_args: object, **_kwargs: object) -> JobExecutionResult:
        calls.append("validate")
        stop.set()
        return JobExecutionResult("success", "done")

    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=os.getpid(),
        execute=execute,
        clock=lambda: NOW,
    )
    assert worker.tick(now=NOW, stop=stop) == 1
    assert calls == ["validate"]
    assert get_run(db, "RUN-manual-1").status == "queued"  # type: ignore[union-attr]
    assert get_run(db, "RUN-manual-2").status == "success"  # type: ignore[union-attr]


def test_internal_worker_entrypoint_installs_signals_and_runs(
    tmp_path: Path,
) -> None:
    installed: list[int] = []
    observed: dict[str, object] = {}

    class FakeWorker:
        def __init__(self, root: Path, *, worker_id: str, parent_pid: int) -> None:
            observed.update(root=root, worker_id=worker_id, parent_pid=parent_pid)

        def run_forever(self, stop: Event) -> None:
            observed["stop"] = stop

    def install_signal(number: int, _handler: object) -> None:
        installed.append(number)

    argv = [
        "research-os-worker",
        "--root",
        str(tmp_path),
        "--parent-pid",
        "1234",
    ]
    with (
        patch.object(sys, "argv", argv),
        patch.object(worker_runtime, "SchedulerWorker", FakeWorker),
        patch.object(worker_runtime.signal, "signal", side_effect=install_signal),
        patch.object(worker_runtime.os, "getpid", return_value=4321),
    ):
        worker_runtime.main()

    assert installed == [worker_runtime.signal.SIGTERM, worker_runtime.signal.SIGINT]
    assert observed["root"] == tmp_path
    assert observed["worker_id"] == "worker-4321"
    assert observed["parent_pid"] == 1234
    assert isinstance(observed["stop"], Event)


def test_parent_liveness_and_non_due_schedule_branches(tmp_path: Path) -> None:
    assert scheduler_worker.parent_is_alive(1)
    assert scheduler_worker.parent_is_alive(os.getpid())
    with patch.object(scheduler_worker.os, "kill", side_effect=OSError):
        assert not scheduler_worker.parent_is_alive(999999)

    schedule_id = _schedule(tmp_path)
    set_schedule_next_run(
        operations_db_path(tmp_path), schedule_id, "2026-08-18T00:00:00Z"
    )
    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=os.getpid(),
        execute=lambda *_args, **_kwargs: JobExecutionResult("success", "done"),
        clock=lambda: NOW,
    )
    assert worker.tick(now=NOW) == 0
    assert latest_run(operations_db_path(tmp_path), schedule_id) is None


def test_claim_race_is_ignored(tmp_path: Path) -> None:
    db = operations_db_path(tmp_path)
    create_run(
        db,
        run_id="RUN-race",
        schedule_id=None,
        job_name="validate",
        target=None,
        project_id=None,
        request_kind="manual",
        as_of=NOW,
        queued_at=NOW,
    )
    worker = SchedulerWorker(
        tmp_path,
        worker_id="worker-test",
        parent_pid=os.getpid(),
        execute=lambda *_args, **_kwargs: JobExecutionResult("success", "done"),
        clock=lambda: NOW,
    )
    with patch("research_os.services.scheduler_worker.claim_run", return_value=None):
        assert worker.tick(now=NOW) == 0
    assert get_run(db, "RUN-race").status == "queued"  # type: ignore[union-attr]
