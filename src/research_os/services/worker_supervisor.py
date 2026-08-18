"""Subprocess supervisor owned by the Web application's lifespan."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, RLock, Thread, current_thread
from typing import IO, Any

from research_os.services.operations_db import (
    operations_db_path,
    record_worker_stop,
    worker_state,
)
from research_os.services.redaction import redact_secrets

CommandFactory = Callable[[Path, int], list[str]]
_CHILD_ENV_KEYS = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TMPDIR",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "XDG_CONFIG_HOME",
    "GH_CONFIG_DIR",
    "SSL_CERT_FILE",
)


def _default_command(root: Path, parent_pid: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "research_os.runtime.worker",
        "--root",
        str(root),
        "--parent-pid",
        str(parent_pid),
    ]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _child_environment(source_root: Path) -> dict[str, str]:
    environment = {key: os.environ[key] for key in _CHILD_ENV_KEYS if key in os.environ}
    environment.update(
        {
            "PYTHONPATH": str(source_root),
            "PYTHONUNBUFFERED": "1",
        }
    )
    return environment


class _RotatingLogSink:
    def __init__(self, path: Path, *, max_bytes: int, backup_count: int) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._lock = RLock()

    def write(self, value: str) -> None:
        payload = redact_secrets(value).encode("utf-8")
        if len(payload) > self.max_bytes:
            payload = (
                payload[: self.max_bytes].decode("utf-8", "ignore").encode("utf-8")
            )
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            current_size = self.path.stat().st_size if self.path.exists() else 0
            if current_size and current_size + len(payload) > self.max_bytes:
                self._rotate()
            with self.path.open("ab") as stream:
                stream.write(payload)

    def _rotate(self) -> None:
        oldest = self.path.with_name(f"worker.{self.backup_count}.log")
        oldest.unlink(missing_ok=True)
        for number in range(self.backup_count - 1, 0, -1):
            source = self.path.with_name(f"worker.{number}.log")
            if source.exists():
                source.replace(self.path.with_name(f"worker.{number + 1}.log"))
        if self.backup_count and self.path.exists():
            self.path.replace(self.path.with_name("worker.1.log"))
        elif self.path.exists():
            self.path.unlink()


class WorkerSupervisor:
    def __init__(
        self,
        root: Path,
        *,
        readiness_timeout: float = 5.0,
        stop_timeout: float = 3.0,
        monitor_interval: float = 0.25,
        max_restarts: int = 3,
        restart_window_seconds: float = 300.0,
        log_max_bytes: int = 1_000_000,
        log_backup_count: int = 3,
        command_factory: CommandFactory = _default_command,
    ) -> None:
        if min(readiness_timeout, stop_timeout, monitor_interval) <= 0:
            raise ValueError("supervisor timeouts must be positive")
        if max_restarts < 0 or restart_window_seconds <= 0:
            raise ValueError("invalid restart policy")
        if log_max_bytes < 1 or log_backup_count < 0:
            raise ValueError("invalid log rotation policy")
        self.root = Path(root).resolve()
        self.readiness_timeout = readiness_timeout
        self.stop_timeout = stop_timeout
        self.monitor_interval = monitor_interval
        self.max_restarts = max_restarts
        self.restart_window_seconds = restart_window_seconds
        self.command_factory = command_factory
        self.process: subprocess.Popen[str] | None = None
        self.shutting_down = False
        self.ready = False
        self.restart_times: list[float] = []
        self.restart_exhausted = False
        self.last_exit_code: int | None = None
        self._lock = RLock()
        self._stop_event = Event()
        self._monitor_thread: Thread | None = None
        self._log_threads: list[Thread] = []
        self._log_sink = _RotatingLogSink(
            self.root / "09_Automation" / "operational" / "logs" / "worker.current.log",
            max_bytes=log_max_bytes,
            backup_count=log_backup_count,
        )

    def start(self) -> None:
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return
            self.shutting_down = False
            self.ready = False
            self.restart_exhausted = False
            self.restart_times.clear()
            self._stop_event.clear()
        self._spawn_and_wait_ready()
        monitor = Thread(
            target=self._monitor,
            name="research-os-worker-supervisor",
            daemon=True,
        )
        with self._lock:
            self._monitor_thread = monitor
        monitor.start()

    def _spawn_and_wait_ready(self) -> None:
        source_root = Path(__file__).resolve().parents[2]
        process = subprocess.Popen(
            self.command_factory(self.root, os.getpid()),
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            close_fds=True,
            env=_child_environment(source_root),
        )
        with self._lock:
            self.process = process
        assert process.stdout is not None
        self._start_log_drain(process.stdout)
        deadline = time.monotonic() + self.readiness_timeout
        while time.monotonic() < deadline and not self._stop_event.is_set():
            state = worker_state(operations_db_path(self.root))
            if (
                state is not None
                and int(state["pid"] or 0) == process.pid
                and state["status"] == "ready"
            ):
                with self._lock:
                    self.ready = True
                return
            if process.poll() is not None:
                break
            self._stop_event.wait(0.05)
        self._terminate(process)
        with self._lock:
            self.ready = False
            if self.process is process:
                self.process = None
        raise RuntimeError("scheduler worker did not become ready")

    def _start_log_drain(self, stream: IO[str]) -> None:
        def drain() -> None:
            try:
                for line in stream:
                    self._log_sink.write(line)
            finally:
                stream.close()

        thread = Thread(target=drain, name="research-os-worker-log", daemon=True)
        with self._lock:
            self._log_threads.append(thread)
        thread.start()

    def _monitor(self) -> None:
        while not self._stop_event.wait(self.monitor_interval):
            with self._lock:
                process = self.process
                shutting_down = self.shutting_down
            if shutting_down:
                return
            if process is not None and process.poll() is None:
                continue
            if process is not None:
                self.last_exit_code = process.returncode
            with self._lock:
                self.ready = False
            now = time.monotonic()
            with self._lock:
                self.restart_times = [
                    value
                    for value in self.restart_times
                    if now - value <= self.restart_window_seconds
                ]
                if len(self.restart_times) >= self.max_restarts:
                    self.restart_exhausted = True
                    if process is not None:
                        self._mark_worker_state(process, status="failed")
                    return
                self.restart_times.append(now)
            try:
                self._spawn_and_wait_ready()
            except RuntimeError:
                if self._stop_event.is_set():
                    return

    def _mark_worker_state(
        self, process: subprocess.Popen[str], *, status: str
    ) -> None:
        state = worker_state(operations_db_path(self.root))
        if state is None or int(state["pid"] or 0) != process.pid:
            return
        record_worker_stop(
            operations_db_path(self.root),
            str(state["worker_id"]),
            stopped_at=_utc_now(),
            status=status,
        )

    def _terminate(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=self.stop_timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=max(1.0, self.stop_timeout))

    def stop(self) -> None:
        with self._lock:
            self.shutting_down = True
            self.ready = False
            self._stop_event.set()
            process = self.process
            monitor = self._monitor_thread
        if process is not None:
            self._terminate(process)
            self._mark_worker_state(process, status="stopped")
        if monitor is not None and monitor is not current_thread():
            monitor.join(timeout=self.stop_timeout + self.readiness_timeout + 1)
        with self._lock:
            if self.process is process or (
                (current_process := self.process) is not None
                and current_process.poll() is not None
            ):
                self.process = None
            log_threads = tuple(self._log_threads)
        for thread in log_threads:
            thread.join(timeout=1)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            process = self.process
            running = process is not None and process.poll() is None
            return {
                "pid": process.pid if process is not None and running else None,
                "running": running,
                "ready": running and self.ready,
                "shutting_down": self.shutting_down,
                "restart_count": len(self.restart_times),
                "restart_exhausted": self.restart_exhausted,
                "last_exit_code": self.last_exit_code,
            }


__all__ = ["WorkerSupervisor"]
