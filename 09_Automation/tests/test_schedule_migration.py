from __future__ import annotations

import hashlib
from pathlib import Path

from research_os.services.operations_db import (
    get_schedule,
    list_runs,
    operations_db_path,
)
from research_os.services.schedule_migration import migrate_operational_history

NOW = "2026-08-17T01:00:00Z"


def _write_channel(
    root: Path,
    channel_id: str,
    schedule: str,
    *,
    enabled: bool = True,
    review: str = "reviewed",
    license_status: str = "reviewed",
) -> None:
    path = root / "02_Knowledge" / "Channels" / f"{channel_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {channel_id}
type: source_channel
title: {channel_id}
name: {channel_id}
project_ids: []
review_status: {review}
license_status: {license_status}
schedule: {schedule!r}
timezone: Asia/Shanghai
enabled: {str(enabled).lower()}
---
# Channel
""",
        encoding="utf-8",
    )


def _write_job(root: Path, job_id: str, status: str = "success") -> None:
    path = root / "05_Research" / "Operations" / "Jobs" / f"{job_id}-validate.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {job_id}
type: job
status: {status}
job_name: validate
started_at: 2026-08-16T00:00:00Z
finished_at: 2026-08-16T00:00:01Z
message: done
---
# Job
""",
        encoding="utf-8",
    )


def _digest(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_migration_is_idempotent_and_preserves_markdown(tmp_path: Path) -> None:
    _write_channel(tmp_path, "CHN-daily", "daily 1x")
    _write_channel(tmp_path, "CHN-six", "every 6 hours")
    _write_channel(tmp_path, "CHN-invalid", "whenever")
    _write_channel(tmp_path, "CHN-restricted", "daily 2x", license_status="restricted")
    for number in range(3):
        _write_job(tmp_path, f"JOB-2026081600000{number}-001")
    channel_hash = _digest(tmp_path / "02_Knowledge" / "Channels")
    job_hash = _digest(tmp_path / "05_Research" / "Operations" / "Jobs")

    first = migrate_operational_history(tmp_path, actor="system:migration", now=NOW)
    second = migrate_operational_history(tmp_path, actor="system:migration", now=NOW)

    assert first.channels_imported == 4
    assert first.jobs_imported == 3
    assert first.files_changed == ()
    assert second.channels_imported == 0
    assert second.jobs_imported == 0
    assert _digest(tmp_path / "02_Knowledge" / "Channels") == channel_hash
    assert _digest(tmp_path / "05_Research" / "Operations" / "Jobs") == job_hash
    db = operations_db_path(tmp_path)
    assert get_schedule(db, "SCH-channel-daily").interval_seconds == 86400  # type: ignore[union-attr]
    assert get_schedule(db, "SCH-channel-six").interval_seconds == 21600  # type: ignore[union-attr]
    assert get_schedule(db, "SCH-channel-invalid").enabled is False  # type: ignore[union-attr]
    assert get_schedule(db, "SCH-channel-restricted").enabled is False  # type: ignore[union-attr]
    assert len(list_runs(db)) == 3
    assert first.warnings == ("CHN-invalid: unparseable schedule 'whenever'",)
