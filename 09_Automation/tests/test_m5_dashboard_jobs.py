from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import UTC, date, datetime, timedelta
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

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
from research_os.services.operations_health import health_snapshot, operations_snapshot
from research_os.services.read_model import (
    analysis_workspace_snapshot,
    decision_desk_snapshot,
    impact_explorer_snapshot,
    industry_home_snapshot,
)
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

JOB_RSS_PAYLOAD = b"""<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>job-item-1</id>
    <title>Job retry item</title>
    <link href="https://example.com/items/job-1" />
    <published>2026-08-10T00:00:00Z</published>
  </entry>
</feed>"""


class _JobBytesResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> _JobBytesResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self.content[:size]


class _JobOutcomeOpener:
    def __init__(self, outcome: _JobBytesResponse | Exception) -> None:
        self.outcome = outcome

    def open(self, request: object, timeout: float) -> _JobBytesResponse:
        del request, timeout
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _job_http_error(status: int, secret: str) -> HTTPError:
    headers = Message()
    headers["Retry-After"] = "0"
    return HTTPError(
        f"https://example.com/feed?token={secret}",
        status,
        f"response body {secret}",
        headers,
        None,
    )


def _job_opener_builder(
    outcomes: list[_JobBytesResponse | Exception],
):
    openers = iter(_JobOutcomeOpener(outcome) for outcome in outcomes)

    def build_opener(
        allowed_hosts: frozenset[str], *, max_bytes: int
    ) -> _JobOutcomeOpener:
        del allowed_hosts, max_bytes
        return next(openers)

    return build_opener


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

            # The research dashboard is read-only EXCEPT the /llm config
            # endpoints (deliberate server-side provider/key/model config UI —
            # the API key never leaves the server). No other write routes.
            write_routes = sorted(
                {
                    route.path
                    for route in app.routes
                    if (set(getattr(route, "methods", set())) - {"HEAD", "OPTIONS"})
                    - {"GET"}
                }
            )
            self.assertEqual(["/llm/config", "/llm/models", "/llm/test"], write_routes)
            for route in app.routes:
                methods = set(getattr(route, "methods", set())) - {"HEAD", "OPTIONS"}
                if route.path.startswith("/llm") or route.path in {
                    "/llm/config",
                    "/llm/models",
                    "/llm/test",
                }:
                    continue
                self.assertEqual({"GET"}, methods, route.path)

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
            self.assertEqual(404, client.get("/pipeline/queue/CAND-nope").status_code)

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

    def test_candidate_queue_uses_discovery_time_label(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            self._seed_channel_and_candidates(root)
            response = TestClient(create_app(root)).get("/pipeline/queue")

        self.assertEqual(200, response.status_code)
        self.assertIn("发现时间", response.text)
        self.assertNotIn(">发布时间<", response.text)

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
            self.assertIn("1–3 跳", page.text)
            self.assertNotIn("多跳待 C-018", page.text)

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


class ResearchWorkspaceSnapshotTests(unittest.TestCase):
    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def test_impact_explorer_contract_and_depth_bounds(self) -> None:
        snapshot = impact_explorer_snapshot(self.root, max_depth=3)
        self.assertEqual(3, snapshot["max_depth"])
        self.assertIn("direct_assertions", snapshot)
        self.assertTrue(
            all(
                row["review_status"] == "reviewed"
                for row in snapshot["direct_assertions"]
            )
        )
        for key in (
            "paths",
            "pruning_reasons",
            "conflicts",
            "countervailing_factors",
            "alternative_explanations",
        ):
            self.assertIn(key, snapshot)
        for depth in (0, 4):
            with self.assertRaisesRegex(ValueError, "between 1 and 3"):
                impact_explorer_snapshot(self.root, max_depth=depth)

    def test_analysis_workspace_contract_and_compare(self) -> None:
        all_runs = analysis_workspace_snapshot(self.root)
        self.assertTrue(all_runs["runs"])
        run_ids = [row["run_id"] for row in all_runs["runs"][:2]]
        snapshot = analysis_workspace_snapshot(self.root, run_ids=run_ids)
        self.assertEqual(run_ids, [row["run_id"] for row in snapshot["runs"]])
        for key in (
            "input_ids",
            "mode_version",
            "model_version",
            "template_version",
            "input_snapshot_hash",
            "prompt_hash",
            "output_hash",
            "evaluator_scores",
        ):
            self.assertIn(key, snapshot["runs"][0])
        for key in ("shared_facts", "evidence_omitted", "conflicting_signals"):
            self.assertIn(key, snapshot["comparison"])
        self.assertIn("mode_metrics", snapshot)
        with self.assertRaises(KeyError):
            analysis_workspace_snapshot(self.root, run_ids=["ANL-unknown"])

    def test_decision_desk_contract_is_honest_before_resolutions(self) -> None:
        snapshot = decision_desk_snapshot(self.root, as_of="2026-08-09")
        for key in (
            "open_forecasts",
            "due_forecasts",
            "overdue_forecasts",
            "calibration",
            "valuations",
            "recommendations",
            "resolution_history",
        ):
            self.assertIn(key, snapshot)
        self.assertEqual("insufficient_sample", snapshot["calibration"]["status"])
        self.assertTrue(snapshot["valuations"])
        for key in ("age_days", "threshold_days", "freshness"):
            self.assertIn(key, snapshot["valuations"][0])
        self.assertTrue(snapshot["recommendations"])
        for key in (
            "catalysts",
            "falsification_conditions",
            "risks",
            "unknowns",
            "scenario_references",
        ):
            self.assertIn(key, snapshot["recommendations"][0])
        self.assertEqual([], snapshot["resolution_history"])

    def test_workspace_pages_render_complete_read_only_sections(self) -> None:
        client = TestClient(create_app(self.root))
        expectations = {
            "/impact": (
                "直接断言",
                "1–3 跳路径",
                "最弱环节置信度",
                "剪枝原因",
                "冲突信号",
                "反向因素",
                "替代解释",
            ),
            "/analysis": (
                "冻结输入",
                "版本与哈希",
                "Evaluator",
                "共享事实",
                "遗漏 Evidence",
                "冲突信号",
            ),
            "/decision": (
                "Open Forecast",
                "Due / Overdue",
                "校准样本",
                "估值新鲜度",
                "催化剂与证伪条件",
                "风险与未知",
                "Scenario 引用",
                "Resolution 历史",
            ),
        }
        for path, labels in expectations.items():
            response = client.get(path)
            self.assertEqual(200, response.status_code, path)
            for label in labels:
                self.assertIn(label, response.text, (path, label))
        for route in client.app.routes:
            if route.path in expectations:
                methods = set(getattr(route, "methods", set())) - {"HEAD", "OPTIONS"}
                self.assertEqual({"GET"}, methods, route.path)


class OperationsHealthSnapshotTests(unittest.TestCase):
    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def test_operations_unifies_all_due_work(self) -> None:
        snapshot = operations_snapshot(self.root, as_of="2026-08-09")
        for key in (
            "schedules",
            "jobs",
            "actions",
            "reviews",
            "forecasts",
            "recommendations",
        ):
            self.assertIn(key, snapshot)
        self.assertTrue(snapshot["jobs"])
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            operations_snapshot(self.root, as_of="09-08-2026")

    def test_health_covers_every_required_category_without_secret_values(self) -> None:
        sentinel = "do-not-render-this-secret"
        with patch.dict(os.environ, {"OPENAI_API_KEY": sentinel}):
            snapshot = health_snapshot(self.root)
        for key in (
            "validation",
            "indexes",
            "assets",
            "candidate_db",
            "channels",
            "failed_runs",
            "backup",
            "host",
            "config",
            "model_cost",
        ):
            self.assertIn(key, snapshot)
        self.assertNotIn(sentinel, repr(snapshot))
        self.assertEqual("present", snapshot["config"]["OPENAI_API_KEY"])
        self.assertIn("free_bytes", snapshot["host"]["disk"])
        self.assertTrue(snapshot["host"]["timezone"])

    def test_operations_and_health_pages_render_all_sections(self) -> None:
        client = TestClient(create_app(self.root))
        operations = client.get("/operations")
        self.assertEqual(200, operations.status_code)
        for label in (
            "调度",
            "Jobs",
            "Actions",
            "研究评审",
            "到期 Forecast",
            "过期 Recommendation",
        ):
            self.assertIn(label, operations.text)

        health = client.get("/health")
        self.assertEqual(200, health.status_code)
        for label in (
            "仓库校验",
            "索引",
            "Source assets",
            "Candidate DB",
            "Channels / License",
            "失败运行",
            "备份",
            "磁盘与时区",
            "配置存在性",
            "模型与成本",
        ):
            self.assertIn(label, health.text)

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

    def test_failed_run_message_includes_run_id_safe_class_and_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            fixtures.write(
                root / "02_Knowledge" / "Channels" / "CHN-test.md",
                CHANNEL_MD,
            )
            secret = "job-transport-secret"
            before_jobs = len(
                list((root / "05_Research" / "Operations" / "Jobs").glob("*.md"))
            )
            outcomes = [_job_http_error(503, secret) for _ in range(3)]
            with patch(
                "research_os.adapters.discovery._build_discovery_opener",
                side_effect=_job_opener_builder(outcomes),
            ):
                result = run_job(
                    root,
                    "discover",
                    target="CHN-test",
                    started_at=datetime(2026, 8, 10, 10, 0, 0, tzinfo=UTC),
                )

            self.assertEqual("failed", result.status)
            self.assertRegex(result.message, r"RUN-[0-9a-f]{16}")
            self.assertIn("http_503", result.message)
            self.assertIn("3 attempts", result.message)
            self.assertNotIn(secret, result.message)
            self.assertNotIn("token=", result.message)
            self.assertEqual(
                before_jobs + 1,
                len(list((root / "05_Research" / "Operations" / "Jobs").glob("*.md"))),
            )
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                row = connection.execute(
                    "SELECT status, retries, http_errors FROM discovery_runs"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(("failed", 2, 3), row)

    def test_discover_job_with_internal_retry_writes_one_success_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            fixtures.write(
                root / "02_Knowledge" / "Channels" / "CHN-test.md",
                CHANNEL_MD,
            )
            jobs_dir = root / "05_Research" / "Operations" / "Jobs"
            before_jobs = len(list(jobs_dir.glob("*.md")))
            outcomes = [
                _job_http_error(429, "retry-success-secret"),
                _JobBytesResponse(JOB_RSS_PAYLOAD),
            ]
            with patch(
                "research_os.adapters.discovery._build_discovery_opener",
                side_effect=_job_opener_builder(outcomes),
            ):
                result = run_job(
                    root,
                    "discover",
                    target="CHN-test",
                    started_at=datetime(2026, 8, 10, 10, 0, 1, tzinfo=UTC),
                )

            self.assertEqual("success", result.status)
            self.assertEqual(before_jobs + 1, len(list(jobs_dir.glob("*.md"))))
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                run_rows = connection.execute(
                    "SELECT status, retries, http_errors FROM discovery_runs"
                ).fetchall()
                candidate_count = connection.execute(
                    "SELECT COUNT(*) FROM candidates"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual([("succeeded", 1, 1)], run_rows)
            self.assertEqual(1, candidate_count)

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


def _mode_fixture(mode_id: str = "MOD-ANL-value-chain-v1") -> str:
    return f"""---
id: {mode_id}
type: analysis_mode
title: Value Chain Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: active
review_status: reviewed
valid_from: 2026-08-08
tags: []
name: 价值链分析
purpose: 定位价值链各环节的控制力、瓶颈与利润池迁移。
applicable_scopes: [sector, company, technology, event, thesis]
required_input_types: [event]
optional_input_types: []
required_questions:
- 哪个环节控制稀缺资源？
required_output_sections: [Current chain]
assumption_policy: 显式列出假设。
evidence_policy: 只引用冻结输入。
counterevidence_policy: 列出反向证据。
time_horizons: [quarter, year]
prohibited_conclusions:
- 不得输出投资建议。
---

# Value Chain Mode
"""


def _run_fixture(run_id: str = "ANL-20260808-001") -> str:
    return f"""---
id: {run_id}
type: analysis_run
title: Analysis Run {run_id}
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: completed
review_status: rejected
tags: []
mode_id: MOD-ANL-value-chain-v1
scope_ids: []
as_of: 2026-08-08
input_source_ids: []
input_event_ids: [EVT-20260729-001]
input_impact_ids: []
input_thesis_ids: []
input_snapshot_hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
model_provider: deterministic
model_id: valid-body-v1
model_parameters: {{}}
prompt_hash: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
output_hash: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
generation_method: mode-runner
---

## Facts used
- EVT-20260729-001

## Inferences
议价权向稀缺产能方转移。

## Judgments
先进制程与 HBM 存储环节的产能瓶颈维持。

## Contradicting evidence
输入事件未提供明显反证。

## Alternative explanations
需求端增速可能弱于供给约束假设。

## Unknowns
产能爬坡速度。

## Indicators
资本开支指引。

## Mode-specific output
算力价值链全景图。

## Current chain
当前链：设备→代工→存储→设计→云。

## Changed chain
变化后链：HBM 与先进制程地位上升。

## Beneficiaries and losers
受益：先进制程代工与 HBM 存储。

## Mechanism
稀缺产能→议价权→利润池迁移。

## Falsification indicators
新增产能投产快于预期。

## Limitations
推断性分析。
"""


def analysis_root(temp: str):
    root = prepared_root(temp)
    fixtures.write(
        root / "02_Knowledge" / "Modes" / "MOD-ANL-value-chain-v1.md",
        _mode_fixture(),
    )
    fixtures.write(
        root / "05_Research" / "Analysis" / "ANL-20260808-001.md",
        _run_fixture(),
    )
    return root


class AnalysisDashboardTests(unittest.TestCase):
    """WP-412 (D-015): analysis workspace pages render read-only."""

    def test_analysis_workspace_pages_render(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))

            overview = client.get("/analysis")
            self.assertEqual(200, overview.status_code)
            self.assertIn("分析工作区", overview.text)
            self.assertIn("ANL-20260808-001", overview.text)
            self.assertIn("/analysis/modes", overview.text)
            self.assertIn("/analysis/runs", overview.text)
            self.assertIn("/analysis/compare", overview.text)

            modes = client.get("/analysis/modes")
            self.assertEqual(200, modes.status_code)
            self.assertIn("MOD-ANL-value-chain-v1", modes.text)
            self.assertIn("可运行", modes.text)

            runs = client.get("/analysis/runs")
            self.assertEqual(200, runs.status_code)
            self.assertIn("ANL-20260808-001", runs.text)

    def test_analysis_mode_detail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))
            page = client.get("/analysis/modes/MOD-ANL-value-chain-v1")
            self.assertEqual(200, page.status_code)
            self.assertIn("定位价值链各环节的控制力", page.text)
            self.assertIn("必答问题", page.text)
            self.assertIn("禁止结论", page.text)
            missing = client.get("/analysis/modes/MOD-ANL-missing-v1")
            self.assertEqual(404, missing.status_code)

    def test_analysis_run_detail_with_input_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))
            page = client.get("/analysis/runs/ANL-20260808-001")
            self.assertEqual(200, page.status_code)
            self.assertIn("冻结元数据", page.text)
            self.assertIn("input_event_ids", page.text)
            self.assertIn("/events/EVT-20260729-001", page.text)
            self.assertIn("## Current chain", page.text)
            missing = client.get("/analysis/runs/ANL-missing")
            self.assertEqual(404, missing.status_code)

    def test_analysis_compare_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))
            page = client.get("/analysis/compare?runs=ANL-20260808-001")
            self.assertEqual(200, page.status_code)
            self.assertIn("模式比较", page.text)
            self.assertIn("ANL-20260808-001", page.text)
            self.assertIn("共享事实", page.text)

    def test_analysis_routes_are_read_only_get(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))
            for route in client.app.routes:
                if getattr(route, "path", "").startswith("/analysis"):
                    self.assertEqual(
                        {"GET"},
                        set(route.methods) or {"GET"},
                        route.path,
                    )


class AnalysisEvalMetricsDashboardTests(unittest.TestCase):
    """WP-420 (D-017/D-018): evaluator scorecard + mode metrics dashboard pages."""

    def test_run_detail_shows_scorecard(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))
            page = client.get("/analysis/runs/ANL-20260808-001")
            self.assertEqual(200, page.status_code)
            self.assertIn("确定性评分（D-017）", page.text)
            self.assertIn("引用可解析", page.text)

    def test_eval_packet_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))
            page = client.get("/analysis/eval?run=ANL-20260808-001")
            self.assertEqual(200, page.status_code)
            self.assertIn("D-017 Evaluation Packet", page.text)
            self.assertIn("人工评分", page.text)
            missing = client.get("/analysis/eval?run=ANL-missing")
            self.assertEqual(200, missing.status_code)
            self.assertIn("unknown analysis run", missing.text)

    def test_overview_and_metrics_pages_show_mode_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_root(temp)
            client = TestClient(create_app(root))
            overview = client.get("/analysis")
            self.assertEqual(200, overview.status_code)
            self.assertIn("模式指标（D-018）", overview.text)
            self.assertIn("输出多样性", overview.text)
            metrics = client.get("/analysis/metrics")
            self.assertEqual(200, metrics.status_code)
            self.assertIn("模式指标", metrics.text)
            self.assertIn("证据遗漏", metrics.text)


def _seed_home_candidates(root: Path) -> None:
    today = date.today().isoformat()
    channel_dir = root / "02_Knowledge" / "Channels"
    channel_dir.mkdir(parents=True, exist_ok=True)
    (channel_dir / "CHN-test.md").write_text(CHANNEL_MD, encoding="utf-8")
    db_path = candidate_db.candidate_db_path(root)
    candidate_db.apply_migrations(db_path)
    candidate_db.insert_candidates(
        db_path,
        [
            {
                "candidate_id": "CAND-new-001",
                "published_at_proposal": today,
                "title": "HBM supply shortage risk",
                "canonical_url": "https://example.com/1",
                "publisher": "Example",
            },
            {
                "candidate_id": "CAND-new-002",
                "published_at_proposal": today,
                "title": "New capacity ramp",
                "canonical_url": "https://example.com/2",
                "publisher": "Example",
            },
            {
                "candidate_id": "CAND-low-001",
                "published_at_proposal": today,
                "title": "Low priority note",
                "canonical_url": "https://example.com/3",
                "publisher": "Example",
            },
        ],
        "CHN-test",
        f"{today}T10:00:00Z",
    )
    connection = sqlite3.connect(db_path)
    try:
        for candidate_id, score in (
            ("CAND-new-001", 0.8),
            ("CAND-new-002", 0.6),
            ("CAND-low-001", 0.2),
        ):
            connection.execute(
                "UPDATE candidates SET priority_score = ?, model_version = ? "
                "WHERE candidate_id = ?",
                (score, "1", candidate_id),
            )
        connection.commit()
    finally:
        connection.close()


def _write_home_sector(root: Path) -> None:
    path = root / "02_Knowledge" / "Sectors" / "SEG-test.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
id: SEG-test
type: sector
title: "Test Sector"
schema_version: 2
created_at: 2026-08-06
updated_at: 2026-08-06
project_ids: []
status: active
review_status: reviewed
tags: []
core_company_ids: [COM-test]
tracked_company_ids: []
---
# Sector

## Definition

Test.
""",
        encoding="utf-8",
    )


def _write_home_core_company(root: Path) -> None:
    channel_dir = root / "02_Knowledge" / "Channels"
    channel_dir.mkdir(parents=True, exist_ok=True)
    (channel_dir / "CHN-test.md").write_text(CHANNEL_MD, encoding="utf-8")
    path = root / "02_Knowledge" / "Companies" / "COM-core-test.md"
    path.write_text(
        """---
id: COM-core-test
type: company
title: Core Test Company
schema_version: 1
created_at: 2026-08-06
updated_at: 2026-08-06
project_ids: [PRJ-001]
status: active
review_status: reviewed
coverage_tier: core
source_channel_ids: [CHN-test]
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
        encoding="utf-8",
    )


def _write_home_forecast(root: Path) -> str:
    today = date.today()
    forecast_id = f"FCT-{today:%Y%m%d}-001"
    resolution_date = (today - timedelta(days=1)).isoformat()
    forecast_as_of = (today - timedelta(days=30)).isoformat()
    path = root / "05_Research" / "Forecasts" / f"{forecast_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {forecast_id}
type: forecast
title: "Will X ramp?"
schema_version: 2
created_at: {today.isoformat()}
updated_at: {today.isoformat()}
project_ids: [PRJ-001]
status: open
review_status: reviewed
tags: []
scope_ids: []
question: "Will X ramp by end of year?"
outcome_type: binary
outcome_definition: "X disclosed in the quarterly report."
base_rate: unknown
forecast_as_of: "{forecast_as_of}"
horizon: quarter
resolution_date: {resolution_date}
resolution_source_requirements: []
evidence_ids: []
analysis_run_ids: []
assumptions: []
alternative_outcomes: []
falsification_conditions: []
---
# Forecast

## Question

Will X ramp?
""",
        encoding="utf-8",
    )
    return forecast_id


def _write_home_action(root: Path) -> str:
    today = date.today()
    action_id = f"ACT-{today:%Y%m%d}-001"
    due_date = (today - timedelta(days=1)).isoformat()
    path = root / "05_Research" / "Reviews" / "Actions" / f"{action_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {action_id}
type: action
title: "Follow up on X"
created_at: {today.isoformat()}
updated_at: {today.isoformat()}
schema_version: 1
project_ids: [PRJ-001]
status: open
owner: max
due_date: {due_date}
success_evidence: "evidence"
tags: []
---
# {action_id}

## Action

Follow up on X.

## Success evidence

Evidence.

## History

- {today.isoformat()}：test.
""",
        encoding="utf-8",
    )
    return action_id


class TestIndustryHomeSnapshot(unittest.TestCase):
    """F-002: industry_home_snapshot composer (WP-600)."""

    def test_snapshot_covers_all_section_3_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            snapshot = industry_home_snapshot(root)
            for key in (
                "as_of",
                "generated_at",
                "top_candidates",
                "high_priority_candidates",
                "events_today",
                "sources_today",
                "impacts_today",
                "conflicts",
                "stale_core_companies",
                "stale_channels",
                "never_run_channels",
                "due_forecasts",
                "overdue_forecasts",
                "due_actions",
                "sector_heatmap",
                "freshness",
                "failed_runs",
            ):
                self.assertIn(key, snapshot)
            self.assertEqual(2, len(snapshot["high_priority_candidates"]))
            self.assertEqual(
                "CAND-new-001", snapshot["top_candidates"][0]["candidate_id"]
            )
            self.assertEqual(1, len(snapshot["conflicts"]))
            self.assertIn("failure_rate", snapshot["freshness"])

    def test_snapshot_without_candidate_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            snapshot = industry_home_snapshot(root)
            self.assertEqual([], snapshot["high_priority_candidates"])
            self.assertEqual([], snapshot["conflicts"])
            self.assertEqual([], snapshot["due_actions"])
            self.assertEqual([], snapshot["sector_heatmap"])

    def test_snapshot_raises_on_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            broken = root / "02_Knowledge" / "Companies" / "COM-broken.md"
            broken.parent.mkdir(parents=True, exist_ok=True)
            broken.write_text(
                "---\nid: COM-broken\ntype: company\n---\n# Company\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                industry_home_snapshot(root)

    def test_sector_heatmap_is_raw_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _write_home_sector(root)
            snapshot = industry_home_snapshot(root)
            self.assertEqual(1, len(snapshot["sector_heatmap"]))
            sector = snapshot["sector_heatmap"][0]
            self.assertEqual("SEG-test", sector["sector_id"])
            for key in (
                "entity_count",
                "event_count_recent",
                "impact_count_reviewed",
                "fresh_channels",
                "stale_channels",
            ):
                self.assertIsInstance(sector[key], int)
            self.assertNotIn("sentiment", sector)
            self.assertNotIn("score", sector)

    def test_stale_core_company_rollup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            _write_home_core_company(root)
            snapshot = industry_home_snapshot(root)
            ids = [row["object_id"] for row in snapshot["stale_core_companies"]]
            self.assertIn("COM-core-test", ids)

    def test_due_forecasts_and_actions_wired(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            forecast_id = _write_home_forecast(root)
            action_id = _write_home_action(root)
            snapshot = industry_home_snapshot(root)
            self.assertEqual(1, len(snapshot["due_forecasts"]))
            self.assertEqual(1, len(snapshot["overdue_forecasts"]))
            self.assertEqual(forecast_id, snapshot["due_forecasts"][0]["id"])
            self.assertEqual(1, len(snapshot["due_actions"]))
            self.assertEqual(action_id, snapshot["due_actions"][0]["id"])


class IndustryHomeTests(unittest.TestCase):
    """F-003: /home Industry Home UI (WP-600)."""

    def test_industry_home_renders(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            client = TestClient(create_app(root))
            page = client.get("/home")
            self.assertEqual(200, page.status_code)
            self.assertIn("产业首页", page.text)
            self.assertIn("今日高优先级候选", page.text)
            self.assertIn("板块热度", page.text)
            self.assertIn("数据新鲜度", page.text)
            self.assertIn("运行失败", page.text)
            self.assertIn("CAND-new-001", page.text)

    def test_industry_home_links_to_detail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            _write_home_sector(root)
            forecast_id = _write_home_forecast(root)
            action_id = _write_home_action(root)
            client = TestClient(create_app(root))
            page = client.get("/home")
            self.assertEqual(200, page.status_code)
            self.assertIn("/pipeline/queue/CAND-new-001", page.text)
            self.assertIn(f"/decision/forecast/{forecast_id}", page.text)
            self.assertIn(f"/actions/{action_id}", page.text)
            self.assertIn("/sectors/SEG-test", page.text)

    def test_industry_home_is_get_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            client = TestClient(create_app(root))
            paths = {route.path for route in client.app.routes}
            self.assertIn("/home", paths)
            for route in client.app.routes:
                if route.path == "/home":
                    methods = set(route.methods) - {"HEAD", "OPTIONS"}
                    self.assertEqual({"GET"}, methods)
            write_routes = sorted(
                {
                    route.path
                    for route in client.app.routes
                    if (set(getattr(route, "methods", set())) - {"HEAD", "OPTIONS"})
                    - {"GET"}
                }
            )
            self.assertEqual(["/llm/config", "/llm/models", "/llm/test"], write_routes)


def _write_home_security(root: Path) -> str:
    today = date.today()
    security_id = "INS-TST-NASDAQ"
    path = root / "02_Knowledge" / "Securities" / f"{security_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {security_id}
type: security
title: "Test Security"
schema_version: 2
created_at: {today.isoformat()}
updated_at: {today.isoformat()}
project_ids: []
status: active
review_status: reviewed
issuer_company_id: COM-core-test
instrument_type: common_stock
ticker: TST
exchange: NASDAQ
currency: USD
country: US
share_class: ""
active_from: {today.isoformat()}
tags: []
---
# Security

## Description

Test.
""",
        encoding="utf-8",
    )
    return security_id


def _write_home_rel(root: Path) -> str:
    today = date.today()
    rel_id = f"REL-{today:%Y%m%d}-001"
    path = root / "05_Research" / "Assertions" / f"{rel_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {rel_id}
type: ontology_assertion
title: "COM-core-test SUPPLIES COM-test"
schema_version: 2
created_at: {today.isoformat()}
updated_at: {today.isoformat()}
project_ids: []
status: active
review_status: pending
subject_id: COM-core-test
predicate: SUPPLIES
object_id: COM-test
valid_from: {today.isoformat()}
as_of: {today.isoformat()}
evidence_ids: []
source_ids: []
confidence: 0.5
scope: ""
qualifiers: {{}}
tags: []
---
# Ontology Assertion

## Relation

Test.
""",
        encoding="utf-8",
    )
    return rel_id


class SectorCompanyDetailTests(unittest.TestCase):
    """F-004 / F-005: bespoke sector + company detail pages (WP-601)."""

    def test_sector_detail_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _write_home_sector(root)
            _write_home_core_company(root)
            client = TestClient(create_app(root))
            page = client.get("/sectors/SEG-test")
            self.assertEqual(200, page.status_code)
            self.assertIn("查看关系网络", page.text)
            self.assertIn("核心与追踪企业", page.text)
            self.assertIn("事件时间线", page.text)
            self.assertIn("覆盖完整度", page.text)
            self.assertIn("COM-test", page.text)

    def test_company_detail_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _write_home_core_company(root)
            _write_home_security(root)
            _write_home_rel(root)
            client = TestClient(create_app(root))
            page = client.get("/companies/COM-core-test")
            self.assertEqual(200, page.status_code)
            self.assertIn("查看关系网络", page.text)
            self.assertIn("主体与证券分离", page.text)
            self.assertIn("SUPPLIES", page.text)
            self.assertIn("证据时间线", page.text)
            self.assertIn("分析运行", page.text)
            self.assertIn("INS-TST-NASDAQ", page.text)


class CandidateDetailTests(unittest.TestCase):
    """F-006: candidate queue list + detail enhancements (WP-601)."""

    def test_candidate_detail_subscores(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            client = TestClient(create_app(root))
            page = client.get("/pipeline/queue/CAND-new-001")
            self.assertEqual(200, page.status_code)
            self.assertIn("评分分项", page.text)
            self.assertIn("scope_relevance", page.text)
            self.assertIn("novelty", page.text)

    def test_candidate_reviewed_evidence_separation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            client = TestClient(create_app(root))
            page = client.get("/pipeline/queue/CAND-new-001")
            self.assertEqual(200, page.status_code)
            self.assertIn("候选区", page.text)
            self.assertIn("已评审证据区", page.text)
            self.assertIn("处理建议", page.text)

    def test_candidate_queue_list_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            client = TestClient(create_app(root))
            page = client.get("/pipeline/queue")
            self.assertEqual(200, page.status_code)
            self.assertIn("发现时间", page.text)
            self.assertIn("CAND-new-001", page.text)

    def test_candidate_queue_navigation_preserves_encoded_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = prepared_root(temp)
            _seed_home_candidates(root)
            client = TestClient(create_app(root))
            page = client.get(
                "/pipeline/queue",
                params={
                    "status": "new",
                    "channel": "CHN-test & special",
                    "entity": "COM-test/value",
                    "tier": "core",
                    "min_priority": "0.25",
                    "limit": "1",
                    "offset": "1",
                    "show_dups": "true",
                },
            )

            self.assertEqual(200, page.status_code)
            self.assertIn(
                "status=new&amp;channel=CHN-test+%26+special"
                "&amp;entity=COM-test%2Fvalue&amp;tier=core"
                "&amp;min_priority=0.25&amp;limit=1&amp;offset=0"
                "&amp;show_dups=true",
                page.text,
            )
