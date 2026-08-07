from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import test_research_os_core as fixtures
from research_os.services import candidate_db
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

CHANNEL_MD = """---
id: CHN-test
type: source_channel
title: "Test Channel"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "Test"
channel_type: rss
locator: "https://example.com/feed"
allow_hosts: [example.com]
publisher: "Test"
source_grade_proposal: B
entity_ids: []
sector_ids: []
query: ""
schedule: "daily"
timezone: "Asia/Shanghai"
max_candidates_per_run: 5
rate_limit: ""
retention_days: 30
license_status: reviewed
robots_checked_at: "2026-08-06"
enabled: true
---

# Source Channel

## Channel

Test.
"""


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
            self.assertIn("本地 · 只读", home.text)

            queue = client.get("/reviews?project=PRJ-001&type=source&status=pending")
            self.assertEqual(200, queue.status_code)
            self.assertIn("SRC-20260729-001", queue.text)
            self.assertNotIn("EVT-20260729-001", queue.text)

            source = client.get("/sources/SRC-20260729-001")
            self.assertEqual(200, source.status_code)
            self.assertIn("来源溯源", source.text)
            self.assertIn("EVT-20260729-001", source.text)

            thesis = client.get("/theses/THS-001")
            self.assertEqual(200, thesis.status_code)
            self.assertIn("观点健康", thesis.text)
            self.assertIn("正常", thesis.text)

            company = client.get("/companies/COM-test")
            self.assertEqual(200, company.status_code)
            self.assertIn("查看关系网络", company.text)
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

    def _seed_channel_and_candidates(self, root: Path) -> None:
        channel_dir = root / "02_Knowledge" / "Channels"
        channel_dir.mkdir(parents=True, exist_ok=True)
        (channel_dir / "CHN-test.md").write_text(
            CHANNEL_MD,
            encoding="utf-8",
        )
        db_path = candidate_db.candidate_db_path(root)
        candidate_db.apply_migrations(db_path)
        candidate_db.insert_candidates(
            db_path,
            [
                {
                    "candidate_id": "CAND-new-001",
                    "published_at_proposal": "2026-08-06",
                    "title": "New candidate one",
                    "canonical_url": "https://example.com/1",
                    "publisher": "Example",
                },
                {
                    "candidate_id": "CAND-new-002",
                    "published_at_proposal": "2026-08-05",
                    "title": "New candidate two",
                    "canonical_url": "https://example.com/2",
                    "publisher": "Example",
                },
                {
                    "candidate_id": "CAND-pro-001",
                    "published_at_proposal": "2026-08-04",
                    "title": "Promoted candidate",
                    "canonical_url": "https://example.com/3",
                    "publisher": "Example",
                },
            ],
            "CHN-test",
            "2026-08-06T10:00:00Z",
        )
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                "UPDATE candidates SET status = 'promoted', "
                "promoted_source_id = ?, entity_proposals_json = ? "
                "WHERE candidate_id = 'CAND-pro-001'",
                (
                    "SRC-20260729-001",
                    json.dumps({"status": "matched", "entity_id": "COM-test"}),
                ),
            )
            connection.execute(
                "INSERT INTO candidate_actions (action_id, candidate_id, action, "
                "reason, actor, acted_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "ACT-test-1",
                    "CAND-pro-001",
                    "promote",
                    "from candidate triage",
                    "max",
                    "2026-08-06T12:00:00Z",
                    "{}",
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def test_pipeline_pages_render_and_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            self._seed_channel_and_candidates(root)
            client = TestClient(create_app(root))

            overview = client.get("/pipeline")
            self.assertEqual(200, overview.status_code)
            self.assertIn("机器运转中", overview.text)
            self.assertIn("/pipeline/queue", overview.text)

            sources = client.get("/pipeline/sources")
            self.assertEqual(200, sources.status_code)
            self.assertIn("已入库来源", sources.text)
            self.assertIn("SRC-20260729-001", sources.text)
            self.assertIn("CHN-test", sources.text)
            self.assertIn("COM-test", sources.text)

            queue = client.get("/pipeline/queue")
            self.assertEqual(200, queue.status_code)
            self.assertIn("候选队列", queue.text)
            self.assertIn("CAND-new-001", queue.text)

            detail = client.get("/pipeline/queue/CAND-new-001")
            self.assertEqual(200, detail.status_code)
            self.assertIn("操作历史", detail.text)
            promoted_detail = client.get("/pipeline/queue/CAND-pro-001")
            self.assertEqual(200, promoted_detail.status_code)
            self.assertIn("promote", promoted_detail.text)
            self.assertEqual(
                404, client.get("/pipeline/queue/CAND-nope").status_code
            )

            channels = client.get("/pipeline/channels")
            self.assertEqual(200, channels.status_code)
            self.assertIn("通道与指标", channels.text)
            self.assertIn("CHN-test", channels.text)
            self.assertIn("可调度", channels.text)

            pipeline_methods = {
                method
                for route in client.app.routes
                if route.path.startswith("/pipeline")
                for method in getattr(route, "methods", set())
            }
            self.assertNotIn("POST", pipeline_methods)
            self.assertNotIn("PUT", pipeline_methods)
            self.assertNotIn("DELETE", pipeline_methods)

    def test_impact_page_and_index_render(self) -> None:
        from research_os.domain.models import ResearchObject
        from research_os.services.indexing import render_impact_assertion_index

        imp = ResearchObject(
            path=Path("05_Research/Assertions/IMP-test-001.md"),
            metadata={
                "id": "IMP-test-001",
                "type": "impact_assertion",
                "subject_id": "EVT-20260729-001",
                "target_id": "COM-test",
                "impact_type": "supply",
                "direction": "positive",
                "horizon": "quarter",
                "confidence": 0.6,
                "review_status": "pending",
                "updated_at": "2026-08-08",
            },
            body="",
        )
        rendered = render_impact_assertion_index([imp])
        self.assertIn("Impact Assertion Index", rendered)
        self.assertIn("IMP-test-001", rendered)
        self.assertIn("COM-test", rendered)

        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            client = TestClient(create_app(root))
            page = client.get("/impact")
            self.assertEqual(200, page.status_code)
            self.assertIn("影响引擎", page.text)

    def test_intel_pages_render_and_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            client = TestClient(create_app(root))

            companies = client.get("/companies")
            self.assertEqual(200, companies.status_code)
            self.assertIn("企业名单", companies.text)
            self.assertIn("COM-test", companies.text)
            self.assertIn("/sectors", companies.text)
            self.assertIn("/reports", companies.text)

            sectors = client.get("/sectors")
            self.assertEqual(200, sectors.status_code)
            self.assertIn("板块分类", sectors.text)

            reports = client.get("/reports")
            self.assertEqual(200, reports.status_code)
            self.assertIn("研究报告", reports.text)

            intel_methods = {
                method
                for route in client.app.routes
                if route.path in {"/companies", "/sectors", "/reports"}
                for method in getattr(route, "methods", set())
            }
            self.assertEqual({"GET"}, intel_methods)

    def test_operations_points_at_pipeline_and_drops_embedded_panel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            client = TestClient(create_app(root))
            operations = client.get("/operations")
            self.assertEqual(200, operations.status_code)
            self.assertIn("打开管线看板", operations.text)
            self.assertNotIn("B-023", operations.text)

    def test_pipeline_pages_graceful_without_candidate_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            client = TestClient(create_app(root))
            for path in (
                "/pipeline",
                "/pipeline/sources",
                "/pipeline/queue",
                "/pipeline/channels",
            ):
                response = client.get(path)
                self.assertEqual(200, response.status_code, path)

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
            self.assertIn("失败任务", health.text)

    def test_discover_and_expire_scheduler_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            expired = run_job(
                root,
                "expire",
                started_at=datetime(2026, 8, 6, 10, 0, 0, tzinfo=UTC),
            )
            self.assertEqual("success", expired.status)
            self.assertIn("0 expired, 0 purged", expired.message)
            missing = run_job(
                root,
                "discover",
                started_at=datetime(2026, 8, 6, 10, 0, 1, tzinfo=UTC),
            )
            self.assertEqual("failed", missing.status)
            self.assertIn("requires --target", missing.message)

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
