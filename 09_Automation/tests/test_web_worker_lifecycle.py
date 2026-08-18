from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient

import test_research_os_core as fixtures
from research_os.services.operations_db import (
    ScheduleSpec,
    create_schedule,
    list_runs,
    operations_db_path,
    worker_state,
)
from research_os.ui.app import create_app


def _free_port() -> int:
    with socket.socket() as stream:
        try:
            stream.bind(("127.0.0.1", 0))
        except PermissionError:
            pytest.skip("execution sandbox forbids local socket binding")
        return int(stream.getsockname()[1])


def _wait_until(predicate, *, timeout: float = 12.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("condition did not become true before timeout")


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _start_server(root: Path, port: int) -> subprocess.Popen[str]:
    source_root = Path(__file__).resolve().parents[2] / "src"
    code = """
import sys
from pathlib import Path
from research_os.ui.app import run_ui
run_ui(Path(sys.argv[1]), host='127.0.0.1', port=int(sys.argv[2]))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    return subprocess.Popen(
        [sys.executable, "-c", code, str(root), str(port)],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        close_fds=True,
    )


def _wait_http(port: int) -> None:
    def ready() -> bool:
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
                return response.status == 200
        except OSError:
            return False

    _wait_until(ready)


def _stop_server(process: subprocess.Popen[str]) -> str:
    process.send_signal(signal.SIGTERM)
    try:
        output, _ = process.communicate(timeout=12)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        output, _ = process.communicate(timeout=3)
        raise AssertionError(f"Web server did not stop gracefully:\n{output}") from exc
    assert process.returncode == 0, output
    return output


def _schedule_runs(root: Path) -> list[str]:
    return [
        run.run_id
        for run in list_runs(operations_db_path(root), limit=100)
        if run.schedule_id == "SCH-lifecycle"
    ]


def _root_with_schedule(tmp_path: Path) -> Path:
    root = fixtures.RepositoryValidationTests().make_root(str(tmp_path))
    db = operations_db_path(root)
    create_schedule(
        db,
        ScheduleSpec(
            schedule_id="SCH-lifecycle",
            name="Lifecycle validation",
            job_name="validate",
            target=None,
            project_id=None,
            interval_seconds=1,
            timezone="UTC",
            enabled=True,
            retry_limit=0,
            retry_backoff_seconds=1,
            timeout_seconds=30,
            missed_run_policy="catch_up_once",
        ),
        actor="test",
        now=datetime.now(UTC).isoformat(),
    )
    return root


def test_web_lifespan_owns_worker_and_catches_up_once(tmp_path: Path) -> None:
    root = _root_with_schedule(tmp_path)
    db = operations_db_path(root)

    first_worker_pid = 0
    with TestClient(create_app(root)) as client:
        assert client.get("/health").status_code == 200

        def first_worker_ready() -> bool:
            nonlocal first_worker_pid
            state = worker_state(db)
            if state is None or state["status"] != "ready":
                return False
            first_worker_pid = int(state["pid"] or 0)
            return first_worker_pid > 0

        _wait_until(first_worker_ready)
        _wait_until(
            lambda: any(
                run.status == "success"
                for run in list_runs(db, limit=100)
                if run.schedule_id == "SCH-lifecycle"
            )
        )

    _wait_until(lambda: not _pid_exists(first_worker_pid))
    stopped_runs = _schedule_runs(root)
    time.sleep(2.0)
    assert _schedule_runs(root) == stopped_runs

    second_worker_pid = 0
    with TestClient(create_app(root)) as client:
        assert client.get("/health").status_code == 200

        def second_worker_ready() -> bool:
            nonlocal second_worker_pid
            state = worker_state(db)
            if state is None or state["status"] != "ready":
                return False
            second_worker_pid = int(state["pid"] or 0)
            return second_worker_pid > 0 and second_worker_pid != first_worker_pid

        _wait_until(second_worker_ready)
        _wait_until(lambda: len(_schedule_runs(root)) == len(stopped_runs) + 1)

    _wait_until(lambda: not _pid_exists(second_worker_pid))
    assert len(_schedule_runs(root)) == len(stopped_runs) + 1


def test_uvicorn_web_lifespan_owns_worker_and_catches_up_once(
    tmp_path: Path,
) -> None:
    root = _root_with_schedule(tmp_path)
    db = operations_db_path(root)

    first_server = _start_server(root, _free_port())
    first_worker_pid = 0
    try:
        first_port = int(first_server.args[-1])
        _wait_http(first_port)

        def first_worker_ready() -> bool:
            nonlocal first_worker_pid
            state = worker_state(db)
            if state is None or state["status"] != "ready":
                return False
            first_worker_pid = int(state["pid"] or 0)
            return first_worker_pid > 0

        _wait_until(first_worker_ready)
        _wait_until(
            lambda: any(
                run.status == "success"
                for run in list_runs(db, limit=100)
                if run.schedule_id == "SCH-lifecycle"
            )
        )
    finally:
        if first_server.poll() is None:
            _stop_server(first_server)

    _wait_until(lambda: not _pid_exists(first_worker_pid))
    stopped_runs = _schedule_runs(root)
    time.sleep(2.0)
    assert _schedule_runs(root) == stopped_runs

    second_server = _start_server(root, _free_port())
    second_worker_pid = 0
    try:
        second_port = int(second_server.args[-1])
        _wait_http(second_port)

        def second_worker_ready() -> bool:
            nonlocal second_worker_pid
            state = worker_state(db)
            if state is None or state["status"] != "ready":
                return False
            second_worker_pid = int(state["pid"] or 0)
            return second_worker_pid > 0 and second_worker_pid != first_worker_pid

        _wait_until(second_worker_ready)
        _wait_until(lambda: len(_schedule_runs(root)) == len(stopped_runs) + 1)
    finally:
        if second_server.poll() is None:
            _stop_server(second_server)

    _wait_until(lambda: not _pid_exists(second_worker_pid))
    assert len(_schedule_runs(root)) == len(stopped_runs) + 1
