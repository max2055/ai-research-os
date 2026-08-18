from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

import test_research_os_core as fixtures
from research_os.services import candidate_db
from research_os.services.operations_db import (
    ScheduleSpec,
    create_run,
    create_schedule,
    get_run,
    get_schedule,
    operations_db_path,
    set_schedule_enabled,
)
from research_os.ui.app import create_app


class _NoWorker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def _hidden(page: str, name: str) -> str:
    match = re.search(rf'name="{re.escape(name)}" value="([^"]+)"', page)
    assert match is not None, page
    return match.group(1)


def _client(tmp_path: Path) -> tuple[Path, TestClient]:
    root = fixtures.RepositoryValidationTests().make_root(str(tmp_path))
    config = root / "00_System" / "web.local.json"
    config.write_text(
        json.dumps({"researcher_id": "max", "mutation_signing_secret": "s" * 64}),
        encoding="utf-8",
    )
    config.chmod(0o600)
    return root, TestClient(
        create_app(root, worker_factory=lambda _root: _NoWorker()),
        base_url="http://127.0.0.1",
    )


def _post(client: TestClient, path: str, data: dict[str, str]):
    return client.post(
        path,
        content=urlencode(data),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://127.0.0.1",
        },
        follow_redirects=False,
    )


def _preview_action(
    client: TestClient, schedule_id: str, action: str
) -> dict[str, str]:
    form = client.get(f"/operations/schedules/{schedule_id}/{action}")
    assert form.status_code == 200
    preview = _post(
        client,
        f"/operations/schedules/{schedule_id}/{action}/preview",
        {"csrf_token": _hidden(form.text, "csrf_token")},
    )
    assert preview.status_code == 200, preview.text
    return {
        "preview_token": _hidden(preview.text, "preview_token"),
        "csrf_token": _hidden(preview.text, "csrf_token"),
    }


def test_schedule_create_preview_commit_replay_and_run_now(tmp_path: Path) -> None:
    root, client = _client(tmp_path)
    with client:
        form = client.get("/operations/schedules/new")
        assert form.status_code == 200
        assert "textarea" not in form.text
        assert 'name="interval_value"' in form.text
        assert '<select name="target">' in form.text
        assert '<select name="project_id">' in form.text
        assert '<select name="timezone">' in form.text
        assert '<select name="overlap_policy">' in form.text
        assert '<option value="source-process">' in form.text
        assert '<option value="forecast-alerts">' in form.text
        csrf = _hidden(form.text, "csrf_token")
        invalid_timezone = _post(
            client,
            "/operations/schedules/new/preview",
            {
                "csrf_token": csrf,
                "name": "Invalid timezone",
                "job_name": "validate",
                "target": "",
                "project_id": "",
                "interval_value": "1",
                "interval_unit": "hours",
                "timezone": "Mars/Olympus",
                "retry_limit": "0",
                "retry_backoff_seconds": "30",
                "timeout_seconds": "1800",
                "overlap_policy": "skip",
                "missed_run_policy": "catch_up_once",
            },
        )
        assert invalid_timezone.status_code == 422
        invalid_target = _post(
            client,
            "/operations/schedules/new/preview",
            {
                "csrf_token": csrf,
                "name": "Invalid target",
                "job_name": "validate",
                "target": "https://example.test/?token=secret",
                "project_id": "",
                "interval_value": "1",
                "interval_unit": "hours",
                "timezone": "UTC",
                "retry_limit": "0",
                "retry_backoff_seconds": "30",
                "timeout_seconds": "1800",
                "overlap_policy": "skip",
                "missed_run_policy": "catch_up_once",
            },
        )
        assert invalid_target.status_code == 422
        valid_fields = {
            "csrf_token": csrf,
            "name": "Daily validation",
            "job_name": "validate",
            "target": "",
            "project_id": "",
            "interval_value": "6",
            "interval_unit": "hours",
            "timezone": "Asia/Shanghai",
            "retry_limit": "2",
            "retry_backoff_seconds": "30",
            "timeout_seconds": "1800",
            "overlap_policy": "skip",
            "missed_run_policy": "catch_up_once",
            "enabled": "true",
        }
        preview = _post(
            client,
            "/operations/schedules/new/preview",
            valid_fields,
        )
        assert preview.status_code == 200, preview.text
        token = _hidden(preview.text, "preview_token")
        body = {
            "preview_token": token,
            "csrf_token": _hidden(preview.text, "csrf_token"),
        }
        committed = _post(client, "/operations/schedules/new/commit", body)
        assert committed.status_code == 303
        schedule_id = committed.headers["location"].rsplit("/", 1)[-1]
        record = get_schedule(operations_db_path(root), schedule_id)
        assert record is not None and record.interval_seconds == 21600
        assert (
            _post(client, "/operations/schedules/new/commit", body).status_code == 409
        )

        tamper_preview = _post(
            client,
            "/operations/schedules/new/preview",
            {**valid_fields, "name": "Tampered token"},
        )
        tamper_token = _hidden(tamper_preview.text, "preview_token")
        tampered = _post(
            client,
            "/operations/schedules/new/commit",
            {
                "preview_token": tamper_token[:-1]
                + ("0" if tamper_token[-1] != "0" else "1"),
                "csrf_token": _hidden(tamper_preview.text, "csrf_token"),
            },
        )
        assert tampered.status_code == 403
        with sqlite3.connect(candidate_db.candidate_db_path(root)) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM mutation_audit "
                    "WHERE operation='schedule.create' AND event_status='rejected' "
                    "AND reason_code='invalid_token'"
                ).fetchone()[0]
                == 1
            )

        run_body = _preview_action(client, schedule_id, "run-now")
        queued = _post(
            client,
            "/operations/schedules/action/commit",
            run_body,
        )
        assert queued.status_code == 303
        run_id = queued.headers["location"].rsplit("/", 1)[-1]
        run = get_run(operations_db_path(root), run_id)
        assert run is not None and run.status == "queued"
        assert (
            _post(client, "/operations/schedules/action/commit", run_body).status_code
            == 409
        )

        pause_body = _preview_action(client, schedule_id, "pause")
        paused = _post(client, "/operations/schedules/action/commit", pause_body)
        assert paused.status_code == 303
        record = get_schedule(operations_db_path(root), schedule_id)
        assert record is not None and record.enabled is False

        resume_body = _preview_action(client, schedule_id, "resume")
        resumed = _post(client, "/operations/schedules/action/commit", resume_body)
        assert resumed.status_code == 303
        record = get_schedule(operations_db_path(root), schedule_id)
        assert record is not None and record.enabled is True


def test_schedule_action_rejects_stale_version_and_restricted_resume(
    tmp_path: Path,
) -> None:
    root, client = _client(tmp_path)
    db = operations_db_path(root)
    created = create_schedule(
        db,
        ScheduleSpec(
            schedule_id="SCH-stale",
            name="Stale",
            job_name="validate",
            target=None,
            project_id=None,
            interval_seconds=3600,
            timezone="Asia/Shanghai",
            enabled=True,
            retry_limit=0,
            retry_backoff_seconds=30,
            timeout_seconds=1800,
            missed_run_policy="catch_up_once",
        ),
        actor="test",
        now="2026-08-17T00:00:00Z",
    )
    channel_path = root / "02_Knowledge/Channels/CHN-restricted.md"
    channel_path.parent.mkdir(parents=True, exist_ok=True)
    channel_path.write_text(
        """---
id: CHN-restricted
type: source_channel
title: Restricted
created_at: 2026-08-17
updated_at: '2026-08-17'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: Restricted
channel_type: web_page
locator: https://example.com
allow_hosts: [example.com]
publisher: Test
source_grade_proposal: B
entity_ids: []
sector_ids: []
query: ''
schedule: daily
timezone: Asia/Shanghai
max_candidates_per_run: 1
rate_limit: ''
retention_days: 30
license_status: restricted
license_notes: restricted
robots_checked_at: '2026-08-17'
enabled: false
---

# Restricted
""",
        encoding="utf-8",
    )
    restricted = create_schedule(
        db,
        ScheduleSpec(
            schedule_id="SCH-restricted",
            name="Restricted",
            job_name="discover",
            target="CHN-restricted",
            project_id=None,
            interval_seconds=3600,
            timezone="Asia/Shanghai",
            enabled=False,
            retry_limit=0,
            retry_backoff_seconds=30,
            timeout_seconds=1800,
            missed_run_policy="catch_up_once",
        ),
        actor="test",
        now="2026-08-17T00:00:00Z",
    )

    with client:
        stale_body = _preview_action(client, created.schedule_id, "pause")
        set_schedule_enabled(
            db,
            created.schedule_id,
            enabled=False,
            expected_version=created.version,
            actor="test",
            now="2026-08-17T00:01:00Z",
        )
        assert (
            _post(client, "/operations/schedules/action/commit", stale_body).status_code
            == 409
        )

        form = client.get(f"/operations/schedules/{restricted.schedule_id}/resume")
        rejected = _post(
            client,
            f"/operations/schedules/{restricted.schedule_id}/resume/preview",
            {"csrf_token": _hidden(form.text, "csrf_token")},
        )
        assert rejected.status_code == 422
        assert get_schedule(db, restricted.schedule_id).enabled is False  # type: ignore[union-attr]


def test_typed_job_form_enqueues_without_markdown_request(tmp_path: Path) -> None:
    root, client = _client(tmp_path)
    with client:
        form = client.get("/operations/jobs/run")
        assert form.status_code == 200
        assert "textarea" not in form.text
        assert 'select name="job_name"' in form.text
        assert 'select name="target"' in form.text
        assert 'select name="project_id"' in form.text
        assert "source-process" in form.text
        rejected_path = _post(
            client,
            "/operations/jobs/run/preview",
            {
                "csrf_token": _hidden(form.text, "csrf_token"),
                "job_name": "backup-candidate",
                "target": "/tmp/attacker-selected.db",
                "project_id": "",
                "as_of": "2026-08-17",
            },
        )
        assert rejected_path.status_code == 422
        preview = _post(
            client,
            "/operations/jobs/run/preview",
            {
                "csrf_token": _hidden(form.text, "csrf_token"),
                "job_name": "validate",
                "target": "",
                "project_id": "",
                "as_of": "2026-08-17",
            },
        )
        assert preview.status_code == 200, preview.text
        body = {
            "preview_token": _hidden(preview.text, "preview_token"),
            "csrf_token": _hidden(preview.text, "csrf_token"),
        }
        committed = _post(client, "/operations/jobs/run/commit", body)
        assert committed.status_code == 303
        run_id = committed.headers["location"].rsplit("/", 1)[-1]
        assert get_run(operations_db_path(root), run_id).status == "queued"  # type: ignore[union-attr]
        requests = root / "05_Research" / "Operations" / "Requests"
        assert not requests.exists() or not list(requests.glob("REQ-*.md"))
        assert _post(client, "/operations/jobs/run/commit", body).status_code == 409

        tamper_preview = _post(
            client,
            "/operations/jobs/run/preview",
            {
                "csrf_token": _hidden(form.text, "csrf_token"),
                "job_name": "validate",
                "target": "",
                "project_id": "",
                "as_of": "2026-08-17",
            },
        )
        tamper_token = _hidden(tamper_preview.text, "preview_token")
        tampered = _post(
            client,
            "/operations/jobs/run/commit",
            {
                "preview_token": tamper_token[:-1]
                + ("0" if tamper_token[-1] != "0" else "1"),
                "csrf_token": _hidden(tamper_preview.text, "csrf_token"),
            },
        )
        assert tampered.status_code == 403


def test_backup_flow_uses_only_server_owned_configuration(tmp_path: Path) -> None:
    root, client = _client(tmp_path)
    with client:
        operations = client.get("/operations")
        assert 'href="/operations/schedules"' in operations.text
        assert 'href="/operations/jobs"' in operations.text
        assert 'href="/operations/backups"' in operations.text

        form = client.get("/operations/backups")
        assert form.status_code == 200
        assert "durable_backup.json" not in form.text
        assert 'name="config_path"' not in form.text
        assert 'name="recipient"' not in form.text
        assert 'name="token"' not in form.text
        csrf = _hidden(form.text, "csrf_token")
        rejected = _post(
            client,
            "/operations/backups/durable/preview",
            {"csrf_token": csrf, "config_path": "/tmp/attacker.json"},
        )
        assert rejected.status_code == 422

        preview = _post(
            client,
            "/operations/backups/durable/preview",
            {"csrf_token": csrf},
        )
        assert preview.status_code == 200, preview.text
        committed = _post(
            client,
            "/operations/jobs/run/commit",
            {
                "preview_token": _hidden(preview.text, "preview_token"),
                "csrf_token": _hidden(preview.text, "csrf_token"),
            },
        )
        assert committed.status_code == 303
        run_id = committed.headers["location"].rsplit("/", 1)[-1]
        run = get_run(operations_db_path(root), run_id)
        assert run is not None
        assert run.job_name == "backup-durable"
        assert run.status == "queued"
        assert run.target is None

        health = client.get("/health")
        assert 'href="/operations/jobs"' in health.text


def test_job_history_is_paginated_at_fifty_rows(tmp_path: Path) -> None:
    root, client = _client(tmp_path)
    db = operations_db_path(root)
    for index in range(51):
        create_run(
            db,
            run_id=f"RUN-page-{index:02d}",
            schedule_id=None,
            job_name="validate",
            target=None,
            project_id=None,
            request_kind="manual",
            as_of="2026-08-17",
            queued_at=f"2026-08-17T00:{index:02d}:00Z",
        )

    with client:
        first = client.get("/operations/jobs?page=1")
        second = client.get("/operations/jobs?page=2")

    assert first.status_code == 200
    assert first.text.count('href="/operations/runs/RUN-page-') == 50
    assert 'href="/operations/jobs?page=2"' in first.text
    assert second.status_code == 200
    assert second.text.count('href="/operations/runs/RUN-page-') == 1
    assert 'href="/operations/jobs?page=1"' in second.text
