from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import test_research_os_core as fixtures
from research_os.services.indexing import index_drift, render_project_indexes
from research_os.services.release import (
    completed_cadence_records,
    release_readiness,
    render_release_readiness,
)
from research_os.services.validation import validate_repository
from test_cli import run_cli


class ReleaseReadinessTests(unittest.TestCase):
    def test_v03_recovery_drill_records_rto_rpo_and_restored_chain(self) -> None:
        root = Path(__file__).resolve().parents[2]
        record = (root / "00_System/v0.3_Recovery_Drill.md").read_text(
            encoding="utf-8"
        )
        for text in (
            "Status: passed",
            "842636f22b4a068f674464c69e5e35b37dea33cd",
            "2026-08-10T00:18:04+08:00",
            "2026-08-10T00:39:30+08:00",
            "21 minutes 26 seconds",
            "2 minutes 51 seconds",
            "07c3e245cb92ab9ab3dadad60824a36272450386e9089390e7e8133c5a222171",
            "148/148",
            "CND-042b3f5ca3064ec5a72e",
            "SRC-20260806-077",
            "4ff48b41c7867608aab12ff7af81adf29969917c819fc39c8e4ae106b0f8480e",
            "discovery dry-run",
            "secrets",
            "launchd",
        ):
            self.assertIn(text, record)

    def test_v03_migration_rehearsal_records_forward_and_rollback_gates(
        self,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        record = (root / "00_System/v0.3_Migration_Rehearsal.md").read_text(
            encoding="utf-8"
        )
        for text in (
            "Status: passed",
            "v0.2 legacy Company",
            "v0.3 schema_version 2",
            "MIG-v0.3-F018-company-schema-v2",
            "8/8",
            "1027/1027",
            "1035/1035",
            "rollback precondition changed",
            "Candidate DB schema version: 2",
            "07c3e245cb92ab9ab3dadad60824a36272450386e9089390e7e8133c5a222171",
            "11 minutes 42 seconds",
            "Full pytest",
            "0 errors, 0 warnings",
        ):
            self.assertIn(text, record)

    def test_v03_user_runbook_covers_operating_and_failure_workflows(self) -> None:
        root = Path(__file__).resolve().parents[2]
        runbook = (root / "00_System/v0.3_User_Runbook.md").read_text(
            encoding="utf-8"
        )
        for text in (
            "Install and configure",
            "Dashboard",
            "Daily workflow",
            "Weekly workflow",
            "Monthly workflow",
            "Candidate triage",
            "Evidence review",
            "Impact review",
            "Analysis review",
            "Forecast review",
            "Decision review",
            "Backup",
            "Restore",
            "Failure response",
            "Secrets",
            "Escalation",
            "P0",
            "P1",
            "P2",
            "P3",
            "--dry-run",
            "--apply",
            "PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python",
        ):
            self.assertIn(text, runbook)

    def test_v03_known_limitations_separate_claim_types_and_real_time_gates(
        self,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        limitations = (root / "00_System/v0.3_Known_Limitations.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(limitations.split()).lower()
        for text in (
            "Facts",
            "Inferences",
            "Judgments",
            "coverage and freshness",
            "model uncertainty",
            "provider retention",
            "license",
            "SQLite",
            "single-user",
            "read-only Web UI",
            "calibration",
            "no automated investment action",
            "WP-530",
            "WP-620",
            "2026-10-31",
            "release check is v0.2-only",
            "not buy, sell, position-size, or execution instructions",
        ):
            self.assertIn(text.lower(), normalized)

        backlog = (
            root
            / "00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md"
        ).read_text(encoding="utf-8")
        wp530 = next(
            line for line in backlog.splitlines() if line.startswith("| WP-530")
        )
        wp620 = next(
            line for line in backlog.splitlines() if line.startswith("| WP-620")
        )
        self.assertIn("future-date dependent", wp530)
        self.assertIn("future-date dependent", wp620)

    def test_v03_license_audit_covers_every_enabled_channel(self) -> None:
        root = Path(__file__).resolve().parents[2]
        objects, _ = validate_repository(root)
        enabled_ids = {
            obj.object_id
            for obj in objects
            if obj.object_type == "source_channel" and obj.metadata.get("enabled")
        }
        audit = (root / "00_System/v0.3_Channel_License_Audit.md").read_text(
            encoding="utf-8"
        )
        audited_ids = set(re.findall(r"^\| (CHN-[^ |]+) \|", audit, re.MULTILINE))
        self.assertEqual(enabled_ids, audited_ids)
        self.assertIn("metadata governance audit", audit)
        self.assertIn("not fresh legal or robots verification", audit)

    def test_v03_performance_record_contains_profile_scale_and_slo_evidence(
        self,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        record = (root / "00_System/v0.3_Performance_Benchmark.md").read_text(
            encoding="utf-8"
        )
        for text in (
            "Status: passed",
            "1034",
            "1490",
            "1501",
            "Home",
            "Company",
            "cProfile",
            "authoritative writes: 0",
            "no persistent cache",
        ):
            self.assertIn(text, record)

    def test_approved_v03_governance_and_project_indexes_are_current(self) -> None:
        root = Path(__file__).resolve().parents[2]
        charter = (
            root
            / "00_System/v0.3_AI_Industry_Intelligence_OS/"
            "01_Product_Charter_and_Governance.md"
        ).read_text(encoding="utf-8")
        for decision in (
            "RCP-v03-004",
            "RCP-v03-005",
            "RCP-v03-006",
            "RCP-v03-010",
        ):
            row = next(line for line in charter.splitlines() if decision in line)
            self.assertIn("approved", row)
            self.assertNotIn("proposed", row)

        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("10-Source 真实人审 Gate 待完成", readme)

        objects, _ = validate_repository(root)
        self.assertEqual(
            [],
            index_drift(root, render_project_indexes(objects, "PRJ-001")),
        )

    def test_missing_pilot_is_reported_as_blockers_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            before = {
                path: path.read_bytes() for path in root.rglob("*") if path.is_file()
            }
            readiness = release_readiness(root)
            self.assertFalse(readiness.ready)
            keys = {check.key for check in readiness.blockers}
            self.assertIn("pilot.project", keys)
            self.assertIn("pilot.sources.count", keys)
            self.assertIn("release.human_decision", keys)
            self.assertIn("Ready: no", render_release_readiness(readiness))
            after = {
                path: path.read_bytes() for path in root.rglob("*") if path.is_file()
            }
            self.assertEqual(before, after)

    def test_completed_cadence_records_require_human_and_audit_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = (
                root / "05_Research" / "Projects" / "PRJ-002" / "Reviews" / "Weekly"
            )
            folder.mkdir(parents=True)
            (folder / "valid.md").write_text(
                "Review status: completed\n"
                "Reviewer: max\n"
                "Review date: 2026-08-05\n"
                "Metrics snapshot: METRICS-20260805.json\n",
                encoding="utf-8",
            )
            (folder / "automatic.md").write_text(
                "Review status: completed\n"
                "Reviewer: automation\n"
                "Review date: 2026-08-12\n"
                "Metrics snapshot: METRICS-20260812.json\n",
                encoding="utf-8",
            )
            (folder / "pending.md").write_text(
                "Review status: pending\n"
                "Reviewer: max\n"
                "Review date: 2026-08-19\n"
                "Metrics snapshot: METRICS-20260819.json\n",
                encoding="utf-8",
            )
            self.assertEqual(
                ["valid.md"],
                [
                    path.name
                    for path in completed_cadence_records(
                        root,
                        "PRJ-002",
                        "weekly",
                    )
                ],
            )

    def test_cli_returns_blocked_exit_code_and_gate_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            result = run_cli(root, "release", "check")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("pilot.project", result.stdout)
            self.assertIn("BLOCKED", result.stdout)

    def test_partial_recovery_is_not_promoted_by_nested_pass_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            recovery = root / "00_System" / "M6_Recovery_Drill.md"
            recovery.write_text(
                "Status: partial\n"
                "Commit: fa09283b40465c3e7b1de15c530369388db8daf8\n\n"
                "## Git recovery\n\n"
                "Status: passed\n",
                encoding="utf-8",
            )
            readiness = release_readiness(root)
            recovery_check = next(
                check
                for check in readiness.checks
                if check.key == "engineering.recovery"
            )
            self.assertFalse(recovery_check.passed)

    def test_release_gate_requires_rq07_and_rq08_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            readiness = release_readiness(root)
            quality = next(
                check
                for check in readiness.checks
                if check.key == "research_quality.actions"
            )
            self.assertFalse(quality.passed)
            self.assertEqual(
                "RQ-01–RQ-08 closed or formally cancelled",
                quality.requirement,
            )
            self.assertIn("ACT-20260730-001", quality.observed)
            self.assertIn("ACT-20260730-002", quality.observed)

    def test_recovery_requires_verification_rows_not_only_pass_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            recovery = root / "00_System" / "M6_Recovery_Drill.md"
            recovery.write_text(
                "Status: passed\nCommit: fa09283b40465c3e7b1de15c530369388db8daf8\n",
                encoding="utf-8",
            )
            readiness = release_readiness(root)
            recovery_check = next(
                check
                for check in readiness.checks
                if check.key == "engineering.recovery"
            )
            self.assertFalse(recovery_check.passed)

    def test_performance_requires_recorded_time_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            performance = root / "00_System" / "M6_Performance_Benchmark.md"
            performance.write_text(
                "Status: passed\n"
                "Sources: 1000\n"
                "Events: 500\n"
                "Decision: pass\n\n"
                "| Measure | Result |\n"
                "|---|---:|\n"
                "| Total query time | 10.1 s |\n"
                "| Maximum accepted | 10.0 s |\n",
                encoding="utf-8",
            )
            readiness = release_readiness(root)
            performance_check = next(
                check
                for check in readiness.checks
                if check.key == "engineering.performance"
            )
            self.assertFalse(performance_check.passed)
