from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

import test_research_os_core as fixtures
from research_os.services.indexing import (
    apply_indexes,
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.jobs import job_rows, run_job
from research_os.services.validation import validate_repository
from research_os.ui.app import create_app, run_ui
from test_cli import run_cli


def prepared_root(temp: str):
    root = fixtures.RepositoryValidationTests().make_root(temp)
    fixtures.write(
        root / "03_Theses" / "Active" / "THS-001-test.md",
        fixtures.thesis(),
    )
    fixtures.write(
        root / "02_Knowledge" / "Companies" / "COM-test.md",
        """---
id: COM-test
type: company
title: Test Company
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: pending
aliases: []
related_entities: []
evidence_ids: []
source_ids: []
tags: []
---

# Company

## Company role in the value chain
## Business model
## Competitive advantages
## Risks
## Related Thesis
""",
    )
    objects, _ = validate_repository(root)
    apply_indexes(root, render_indexes(objects))
    apply_indexes(root, render_project_indexes(objects, "PRJ-001"))
    return root


class DashboardTests(unittest.TestCase):
    def test_read_only_routes_are_markdown_backed_and_navigable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            app = create_app(root)
            client = TestClient(app)

            home = client.get("/")
            self.assertEqual(200, home.status_code)
            self.assertIn("AI Research OS", home.text)
            self.assertIn("THS-001", home.text)
            self.assertIn("Local · Read-only", home.text)

            queue = client.get("/reviews?project=PRJ-001&type=source&status=pending")
            self.assertEqual(200, queue.status_code)
            self.assertIn("SRC-20260729-001", queue.text)
            self.assertNotIn("EVT-20260729-001", queue.text)

            source = client.get("/sources/SRC-20260729-001")
            self.assertEqual(200, source.status_code)
            self.assertIn("Source provenance", source.text)
            self.assertIn("EVT-20260729-001", source.text)

            thesis = client.get("/theses/THS-001")
            self.assertEqual(200, thesis.status_code)
            self.assertIn("Thesis health", thesis.text)
            self.assertIn("current", thesis.text)

            company = client.get("/companies/COM-test")
            self.assertEqual(200, company.status_code)
            self.assertIn("Explore relationships", company.text)
            self.assertEqual(200, client.get("/impact/COM-test").status_code)

            state = client.get("/api/state?project=PRJ-001")
            self.assertEqual("PRJ-001", state.json()["project_id"])
            self.assertGreaterEqual(len(state.json()["objects"]), 4)

            route_methods = {
                method
                for route in app.routes
                for method in getattr(route, "methods", set())
            }
            self.assertNotIn("POST", route_methods)
            self.assertNotIn("PUT", route_methods)
            self.assertNotIn("DELETE", route_methods)

    def test_health_metrics_operations_and_missing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            client = TestClient(create_app(root))
            for path in ("/health", "/metrics", "/operations"):
                response = client.get(path)
                self.assertEqual(200, response.status_code, path)
            self.assertEqual(
                404,
                client.get("/source-assets/SRC-20260729-001/0").status_code,
            )
            self.assertEqual(404, client.get("/sources/SRC-99999999-999").status_code)

    def test_obsidian_home_is_rebuildable_after_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            home = root / "08_Indexes" / "Home_Dashboard.md"
            self.assertTrue(home.is_file())
            self.assertIn("[[THS-001]]", home.read_text(encoding="utf-8"))
            home.unlink()
            objects, _ = validate_repository(root)
            rendered = render_indexes(objects)
            self.assertIn(
                "08_Indexes/Home_Dashboard.md",
                {str(path) for path in index_drift(root, rendered)},
            )
            apply_indexes(root, rendered)
            self.assertTrue(home.is_file())
            self.assertEqual([], index_drift(root, rendered))

    def test_ui_rejects_non_loopback_bind_and_starts_on_loopback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            with self.assertRaisesRegex(ValueError, "loopback"):
                run_ui(root, host="0.0.0.0")
            with patch("uvicorn.run") as mocked:
                run_ui(root, host="127.0.0.1", port=8876)
            _, kwargs = mocked.call_args
            self.assertEqual("127.0.0.1", kwargs["host"])
            self.assertEqual(8876, kwargs["port"])


class SchedulerJobTests(unittest.TestCase):
    def test_success_failure_audit_and_idempotent_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            first = run_job(
                root,
                "validate",
                started_at=datetime(2026, 7, 30, 10, 0, 0, tzinfo=UTC),
            )
            self.assertEqual("success", first.status)

            metrics_first = run_job(
                root,
                "metrics",
                project_id="PRJ-001",
                as_of="2026-07-30",
                started_at=datetime(2026, 7, 30, 10, 0, 1, tzinfo=UTC),
            )
            metrics_second = run_job(
                root,
                "metrics",
                project_id="PRJ-001",
                as_of="2026-07-30",
                started_at=datetime(2026, 7, 30, 10, 0, 2, tzinfo=UTC),
            )
            self.assertIn("created", metrics_first.message)
            self.assertIn("unchanged", metrics_second.message)

            failed = run_job(
                root,
                "source-process",
                target="SRC-20990101-999",
                started_at=datetime(2026, 7, 30, 10, 0, 3, tzinfo=UTC),
            )
            self.assertEqual("failed", failed.status)
            self.assertIn("unknown Source", failed.message)

            objects, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )
            jobs = [obj for obj in objects if obj.object_type == "job"]
            self.assertEqual(4, len(jobs))
            self.assertEqual(
                [failed.job_id],
                [row.object_id for row in job_rows(root, status="failed")],
            )
            health = TestClient(create_app(root)).get("/health")
            self.assertIn(failed.job_id, health.text)
            self.assertIn("failed jobs", health.text)

    def test_refresh_job_and_cli_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            result = run_job(
                root,
                "refresh",
                project_id="PRJ-001",
                as_of="2026-07-31",
                started_at=datetime(2026, 7, 31, 10, 0, 0, tzinfo=UTC),
            )
            self.assertEqual("success", result.status)
            objects, _ = validate_repository(root)
            self.assertEqual([], index_drift(root, render_indexes(objects)))
            self.assertEqual(
                [],
                index_drift(
                    root,
                    render_project_indexes(objects, "PRJ-001"),
                ),
            )

            cli = run_cli(root, "jobs", "run", "validate")
            self.assertEqual(0, cli.returncode, cli.stdout)
            self.assertIn("SUCCESS JOB-", cli.stdout)
