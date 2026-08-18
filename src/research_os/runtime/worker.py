"""Internal child-process entry point for the Web-hosted worker."""

from __future__ import annotations

import argparse
import os
import signal
from pathlib import Path
from threading import Event

from research_os.services.scheduler_worker import SchedulerWorker


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research OS internal scheduler worker"
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--parent-pid", required=True, type=int)
    args = parser.parse_args()
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    worker = SchedulerWorker(
        args.root, worker_id=f"worker-{os.getpid()}", parent_pid=args.parent_pid
    )
    worker.run_forever(stop)


if __name__ == "__main__":
    main()
