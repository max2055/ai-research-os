from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from research_os.services.worker_supervisor import WorkerSupervisor, _child_environment
from research_os.ui.app import create_app


def _wait_until(predicate, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition did not become true before timeout")


def _fixture_command(code: str):
    def command(root: Path, parent_pid: int) -> list[str]:
        del parent_pid
        return [sys.executable, "-c", code, str(root)]

    return command


def test_child_environment_is_platform_safe_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SYSTEMROOT", "C:\\Windows")
    monkeypatch.setenv("GH_TOKEN", "do-not-inherit")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-inherit")

    environment = _child_environment(tmp_path / "src")

    assert environment["HOME"] == str(tmp_path)
    assert environment["SYSTEMROOT"] == "C:\\Windows"
    assert environment["PYTHONPATH"] == str(tmp_path / "src")
    assert environment["PYTHONUNBUFFERED"] == "1"
    assert "GH_TOKEN" not in environment
    assert "OPENAI_API_KEY" not in environment


def test_real_supervisor_starts_one_child_and_stops_it(tmp_path: Path) -> None:
    supervisor = WorkerSupervisor(tmp_path, readiness_timeout=3, stop_timeout=2)
    supervisor.start()
    first_pid = supervisor.snapshot()["pid"]
    assert first_pid
    supervisor.start()
    assert supervisor.snapshot()["pid"] == first_pid
    supervisor.stop()
    assert supervisor.snapshot()["running"] is False


def test_readiness_timeout_cleans_up_child(tmp_path: Path) -> None:
    supervisor = WorkerSupervisor(
        tmp_path,
        readiness_timeout=0.1,
        stop_timeout=0.1,
        command_factory=_fixture_command("import time; time.sleep(30)"),
    )

    with pytest.raises(RuntimeError, match="did not become ready"):
        supervisor.start()

    assert supervisor.snapshot()["running"] is False


def test_stop_forces_kill_when_child_ignores_sigterm(tmp_path: Path) -> None:
    code = """
import os, signal, sys, time
from datetime import UTC, datetime
from pathlib import Path
from research_os.services.operations_db import (
    operations_db_path,
    refresh_worker_heartbeat,
)
root = Path(sys.argv[1])
refresh_worker_heartbeat(
    operations_db_path(root),
    'fixture-worker',
    datetime.now(UTC).isoformat(),
    pid=os.getpid(),
    status='ready',
)
signal.signal(signal.SIGTERM, signal.SIG_IGN)
time.sleep(30)
"""
    supervisor = WorkerSupervisor(
        tmp_path,
        readiness_timeout=2,
        stop_timeout=0.05,
        command_factory=_fixture_command(code),
    )
    supervisor.start()
    pid = supervisor.snapshot()["pid"]

    supervisor.stop()

    assert pid
    assert supervisor.snapshot()["running"] is False


def test_crashes_restart_at_most_three_times_in_five_minutes(tmp_path: Path) -> None:
    supervisor = WorkerSupervisor(
        tmp_path,
        readiness_timeout=3,
        stop_timeout=1,
        monitor_interval=0.02,
    )
    supervisor.start()
    try:
        previous_pid = supervisor.snapshot()["pid"]
        for expected_restarts in range(1, 4):
            assert previous_pid
            os.kill(previous_pid, signal.SIGKILL)
            _wait_until(
                lambda expected_restarts=expected_restarts,
                previous_pid=previous_pid: supervisor.snapshot()["restart_count"]
                == expected_restarts
                and supervisor.snapshot()["ready"]
                and supervisor.snapshot()["pid"] != previous_pid
            )
            previous_pid = supervisor.snapshot()["pid"]

        assert previous_pid
        os.kill(previous_pid, signal.SIGKILL)
        _wait_until(lambda: supervisor.snapshot()["restart_exhausted"])
        assert supervisor.snapshot()["running"] is False
        assert supervisor.snapshot()["restart_count"] == 3
    finally:
        supervisor.stop()


def test_graceful_stop_never_restarts_worker(tmp_path: Path) -> None:
    supervisor = WorkerSupervisor(
        tmp_path,
        readiness_timeout=3,
        stop_timeout=1,
        monitor_interval=0.02,
    )
    supervisor.start()
    pid = supervisor.snapshot()["pid"]
    supervisor.stop()
    restart_count = supervisor.snapshot()["restart_count"]
    time.sleep(0.1)

    assert pid
    assert supervisor.snapshot()["pid"] is None
    assert supervisor.snapshot()["restart_count"] == restart_count


def test_worker_log_is_redacted_and_bounded(tmp_path: Path) -> None:
    secret = "supervisor-log-secret"
    code = f"""
import os, sys, time
from datetime import UTC, datetime
from pathlib import Path
from research_os.services.operations_db import (
    operations_db_path,
    refresh_worker_heartbeat,
)
root = Path(sys.argv[1])
refresh_worker_heartbeat(
    operations_db_path(root),
    'fixture-worker',
    datetime.now(UTC).isoformat(),
    pid=os.getpid(),
    status='ready',
)
print('token={secret} ' + 'x' * 400, flush=True)
time.sleep(30)
"""
    supervisor = WorkerSupervisor(
        tmp_path,
        readiness_timeout=2,
        stop_timeout=0.1,
        log_max_bytes=128,
        log_backup_count=2,
        command_factory=_fixture_command(code),
    )
    supervisor.start()
    log = tmp_path / "09_Automation/operational/logs/worker.current.log"
    try:
        _wait_until(lambda: log.exists() and log.stat().st_size > 0)
    finally:
        supervisor.stop()

    payload = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(log.parent.glob("worker.*.log"))
    )
    assert secret not in payload
    assert "<REDACTED>" in payload
    assert all(path.stat().st_size <= 128 for path in log.parent.glob("worker.*.log"))
    assert len(list(log.parent.glob("worker.*.log"))) <= 3


def test_fastapi_lifespan_owns_supervisor(tmp_path: Path) -> None:
    class FakeSupervisor:
        started = 0
        stopped = 0

        def start(self) -> None:
            self.started += 1

        def stop(self) -> None:
            self.stopped += 1

    supervisor = FakeSupervisor()
    with TestClient(
        create_app(tmp_path, worker_factory=lambda _root: supervisor)
    ) as client:
        assert supervisor.started == 1
        assert client.get("/operations/schedules").status_code == 200
    assert supervisor.stopped == 1
