from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import test_research_os_core as fixtures
from research_os.services.indexing import index_drift, render_project_indexes
from research_os.services.release import (
    ReleaseCheck,
    ReleaseEvaluationError,
    completed_cadence_records,
    release_readiness,
    release_readiness_for,
    release_readiness_v03,
    render_release_readiness,
)
from research_os.services.validation import validate_repository
from test_cli import run_cli


class ReleaseReadinessTests(unittest.TestCase):
    V03_KEYS = (
        "evidence_universe.pilot_universe",
        "evidence_universe.authoritative_references",
        "evidence_universe.repository_validation",
        "ingestion.pilot_completion",
        "ingestion.no_silent_missed_runs",
        "ingestion.channel_licenses",
        "impact_analysis.impact_field_gate",
        "impact_analysis.mode_field_gate",
        "impact_analysis.counterevidence_divergence",
        "decision.human_approved_forecasts",
        "decision.natural_resolutions",
        "decision.recommendation_pilot",
        "decision.no_automated_trading",
        "engineering.quality_suite",
        "engineering.performance_slo",
        "engineering.migration_recovery",
        "engineering.recovery_boundaries",
        "engineering.dashboard_security",
        "human.cadence_reviews",
        "human.known_limitations_read",
        "human.release_approval",
    )

    def test_default_v02_remains_18_gate_text_contract(self) -> None:
        root = Path(__file__).resolve().parents[2]
        legacy = release_readiness(root)
        dispatched = release_readiness_for(root)

        self.assertEqual(legacy, dispatched)
        self.assertEqual("0.2", dispatched.version)
        self.assertEqual(18, len(dispatched.checks))
        self.assertTrue(dispatched.ready)
        self.assertIn("- Passed: 18/18", render_release_readiness(dispatched))

        cli = run_cli(root, "release", "check")
        self.assertEqual(0, cli.returncode, cli.stdout)
        self.assertEqual(render_release_readiness(legacy), cli.stdout)

    def test_v03_maps_every_phase6_release_gate_key(self) -> None:
        root = Path(__file__).resolve().parents[2]
        readiness = release_readiness_v03(root, as_of="2026-08-10")

        self.assertEqual(self.V03_KEYS, tuple(check.key for check in readiness.checks))
        for check in readiness.checks:
            self.assertTrue(check.requirement)
            self.assertTrue(check.observed)
            self.assertTrue(check.evidence_paths)

    def test_current_v03_is_blocked_by_wp530_wp620_and_f024(self) -> None:
        root = Path(__file__).resolve().parents[2]
        readiness = release_readiness_v03(root, as_of="2026-08-10")
        blockers = {check.key: check for check in readiness.blockers}

        self.assertFalse(readiness.ready)
        self.assertEqual(7, len(blockers))
        self.assertIn("WP-620", blockers["ingestion.pilot_completion"].observed)
        self.assertIn("WP-530", blockers["decision.natural_resolutions"].observed)
        self.assertIn("2026-10-31", blockers["decision.natural_resolutions"].observed)
        self.assertIn("F-024", blockers["human.release_approval"].observed)
        by_key = {check.key: check for check in readiness.checks}
        self.assertTrue(by_key["decision.no_automated_trading"].passed)
        self.assertTrue(by_key["engineering.dashboard_security"].passed)

    def test_v03_rejects_automatic_placeholder_and_future_human_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            limitations = root / "00_System" / "v0.3_Known_Limitations.md"
            limitations.write_text("# Known limitations\n", encoding="utf-8")
            packet = root / "05_Research" / "Reviews" / "v0.3_Release_Packet.md"
            packet.parent.mkdir(parents=True, exist_ok=True)

            for reviewer in (
                "AI",
                "Research_OS automation",
                "CoDeX.Agent",
                "model/system",
                "A.I.",
                "A.I. Max",
                "m-o-d-e-l",
                "m-o-d-e-l max",
                "s-y-s-t-e-m",
                "placeholder reviewer",
                "synthetic-human",
                "unknown",
                "待定",
                "系统",
            ):
                packet.write_text(
                    "Status: approved\n"
                    f"Reviewer: {reviewer}\n"
                    "Decision date: 2026-08-10\n"
                    "Release decision: approve\n"
                    "Known limitations read: yes\n",
                    encoding="utf-8",
                )
                readiness = release_readiness_v03(root, as_of="2026-08-10")
                by_key = {check.key: check for check in readiness.checks}
                self.assertFalse(by_key["human.known_limitations_read"].passed)
                self.assertFalse(by_key["human.release_approval"].passed)

            packet.write_text(
                "Status: approved\n"
                "Reviewer: max\n"
                "Decision date: 2026-08-11\n"
                "Release decision: approve\n"
                "Known limitations read: yes\n",
                encoding="utf-8",
            )
            future = release_readiness_v03(root, as_of="2026-08-10")
            future_by_key = {check.key: check for check in future.checks}
            self.assertFalse(future_by_key["human.known_limitations_read"].passed)
            self.assertFalse(future_by_key["human.release_approval"].passed)

            packet.write_text(
                "Status: approved\n"
                "Reviewer: 张伟\n"
                "Decision date: 2026-08-10\n"
                "Release decision: approve\n"
                "Known limitations read: yes\n",
                encoding="utf-8",
            )
            valid = release_readiness_v03(root, as_of="2026-08-10")
            valid_by_key = {check.key: check for check in valid.checks}
            self.assertTrue(valid_by_key["human.known_limitations_read"].passed)
            self.assertTrue(valid_by_key["human.release_approval"].passed)

            packet.write_text(
                "Status: pending\n"
                "Reviewer: 张伟\n"
                "Decision date: 2026-08-10\n"
                "Release decision: approve\n"
                "Known limitations read: yes\n",
                encoding="utf-8",
            )
            contradictory = release_readiness_v03(root, as_of="2026-08-10")
            contradictory_by_key = {check.key: check for check in contradictory.checks}
            self.assertFalse(
                contradictory_by_key["human.known_limitations_read"].passed
            )
            self.assertFalse(contradictory_by_key["human.release_approval"].passed)

    def test_v03_missing_evidence_blocks_but_malformed_json_cannot_be_evaluated(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            missing = release_readiness_v03(root, as_of="2026-08-10")
            missing_check = next(
                check
                for check in missing.checks
                if check.key == "impact_analysis.impact_field_gate"
            )
            self.assertFalse(missing_check.passed)
            self.assertIn("missing", missing_check.observed.lower())

            judgments = (
                root / "05_Research" / "Reviews" / "Field_Gate_20_Impact_Judgments.json"
            )
            judgments.parent.mkdir(parents=True, exist_ok=True)
            judgments.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(ReleaseEvaluationError):
                release_readiness_v03(root, as_of="2026-08-10")

    def test_v03_semantically_invalid_structured_evidence_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            judgments = (
                root / "05_Research" / "Reviews" / "Field_Gate_20_Impact_Judgments.json"
            )
            judgments.parent.mkdir(parents=True, exist_ok=True)
            judgments.write_text(
                json.dumps(
                    {
                        "sample_size": 2,
                        "judgments": [],
                        "metrics": {"n": 2},
                        "approved": {
                            "by": "max",
                            "date": "2026-08-10",
                            "decision": "approve",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ReleaseEvaluationError):
                release_readiness_v03(root, as_of="2026-08-10")

    def test_v03_mode_dimensions_are_validated_before_set_operations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            judgments = (
                root / "05_Research" / "Reviews" / "Field_Gate_10_Case_Judgments.json"
            )
            judgments.parent.mkdir(parents=True, exist_ok=True)
            judgments.write_text(
                json.dumps(
                    {
                        "status": "confirmed",
                        "dimensions": [{}],
                        "runs": [],
                        "gate_verdict": {},
                        "reviewer": "max",
                        "confirmed_at": "2026-08-10",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ReleaseEvaluationError, "dimensions do not match"
            ):
                release_readiness_v03(root, as_of="2026-08-10")

    def test_v03_pilot_requires_b026_and_a_distinct_30_day_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            backlog = (
                root
                / "00_System"
                / "v0.3_AI_Industry_Intelligence_OS"
                / "09_Master_Backlog.md"
            )
            backlog.parent.mkdir(parents=True, exist_ok=True)
            backlog.write_text(
                "| ID | Scope | Status |\n"
                "|---|---|---|\n"
                "| WP-620 | F-021-F-022 | completed |\n",
                encoding="utf-8",
            )
            pilot_folder = root / "05_Research" / "Operations" / "Pilot"
            pilot_folder.mkdir(parents=True, exist_ok=True)
            (pilot_folder / "pilot.json").write_text(
                '{"started_at": "2026-08-06"}', encoding="utf-8"
            )
            candidate_acceptance = pilot_folder / "Phase_Acceptance_B026.md"
            candidate_acceptance.write_text(
                "Status: passed\nReviewer: 张伟\nDecision date: 2026-08-10\n",
                encoding="utf-8",
            )
            (pilot_folder / "v0.3_30_Day_Pilot_Acceptance.md").write_text(
                "Status: passed\n"
                "Pilot start date: 2026-08-10\n"
                "Reviewer: 张伟\n"
                "Decision date: 2026-09-08\n"
                "Release decision: approve\n",
                encoding="utf-8",
            )

            passed = release_readiness_v03(root, as_of="2026-09-08")
            passed_by_key = {check.key: check for check in passed.checks}
            self.assertTrue(passed_by_key["ingestion.pilot_completion"].passed)

            candidate_acceptance.write_text("Status: in_progress\n", encoding="utf-8")
            blocked = release_readiness_v03(root, as_of="2026-09-08")
            blocked_by_key = {check.key: check for check in blocked.checks}
            self.assertFalse(blocked_by_key["ingestion.pilot_completion"].passed)
            self.assertIn(
                "B-026", blocked_by_key["ingestion.pilot_completion"].observed
            )

    def test_v03_cadence_is_scoped_to_the_real_pilot_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            pilot = (
                root
                / "05_Research"
                / "Operations"
                / "Pilot"
                / "v0.3_30_Day_Pilot_Acceptance.md"
            )
            pilot.parent.mkdir(parents=True, exist_ok=True)
            pilot.write_text("Pilot start date: 2026-08-10\n", encoding="utf-8")
            review_root = root / "05_Research" / "Projects" / "PRJ-001" / "Reviews"

            def write_review(
                path: Path, review_date: str, scope: str = "v0.3 F-021"
            ) -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f"# {scope} review\n"
                    "Review status: completed\n"
                    "Reviewer: 张伟\n"
                    f"Review date: {review_date}\n"
                    "Metrics snapshot: METRICS.json\n",
                    encoding="utf-8",
                )

            first_weekly = review_root / "Weekly" / "WK-1.md"
            write_review(first_weekly, "2026-08-11")
            write_review(review_root / "Weekly" / "WK-2.md", "2026-08-18")
            write_review(review_root / "Monthly" / "MO-1.md", "2026-09-08")
            passed = release_readiness_v03(root, as_of="2026-09-08")
            passed_by_key = {check.key: check for check in passed.checks}
            self.assertTrue(passed_by_key["human.cadence_reviews"].passed)

            write_review(first_weekly, "2026-08-11", scope="v0.2 release")
            blocked = release_readiness_v03(root, as_of="2026-09-08")
            blocked_by_key = {check.key: check for check in blocked.checks}
            self.assertFalse(blocked_by_key["human.cadence_reviews"].passed)

    def test_v03_quality_and_passed_decision_provenance_are_exact(self) -> None:
        root = Path(__file__).resolve().parents[2]
        readiness = release_readiness_v03(root, as_of="2026-08-10")
        by_key = {check.key: check for check in readiness.checks}

        self.assertFalse(by_key["engineering.quality_suite"].passed)
        self.assertFalse(by_key["human.cadence_reviews"].passed)
        for key, object_folder in (
            ("decision.human_approved_forecasts", "/Forecasts/"),
            ("decision.recommendation_pilot", "/Recommendations/"),
        ):
            paths = by_key[key].evidence_paths
            self.assertTrue(any(object_folder in f"/{path}" for path in paths))
            self.assertTrue(any("/Reviews/Decisions/" in f"/{path}" for path in paths))
            self.assertTrue(all(path.endswith(".md") for path in paths))

        universe_paths = by_key["evidence_universe.pilot_universe"].evidence_paths
        self.assertLess(len(universe_paths), 40)

    def test_v03_as_of_and_version_inputs_fail_without_tracebacks(self) -> None:
        root = Path(__file__).resolve().parents[2]
        for value in ("", "2026-8-10", "2026-02-30", "not-a-date"):
            with self.assertRaises(ReleaseEvaluationError):
                release_readiness_v03(root, as_of=value)

        invalid_date = run_cli(
            root,
            "release",
            "check",
            "--version",
            "0.3",
            "--as-of",
            "2026-02-30",
        )
        self.assertEqual(2, invalid_date.returncode, invalid_date.stdout)
        self.assertNotIn("Traceback", invalid_date.stdout + invalid_date.stderr)

        invalid_version = run_cli(root, "release", "check", "--version", "0.4")
        self.assertEqual(2, invalid_version.returncode)
        self.assertNotIn("Traceback", invalid_version.stdout + invalid_version.stderr)

    def test_v03_checker_is_read_only_and_release_check_is_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            before = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            readiness = release_readiness_for(root, version="0.3", as_of="2026-08-10")
            self.assertFalse(readiness.ready)
            after = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)

        check = ReleaseCheck("key", False, "requirement", "observed")
        self.assertEqual((), check.evidence_paths)

    def test_cli_v03_text_names_every_gate_and_blocker(self) -> None:
        root = Path(__file__).resolve().parents[2]
        result = run_cli(
            root,
            "release",
            "check",
            "--version",
            "0.3",
            "--as-of",
            "2026-08-10",
        )
        self.assertEqual(1, result.returncode, result.stdout)
        for key in self.V03_KEYS:
            self.assertIn(key, result.stdout)
        for label in ("WP-530", "WP-620", "F-024", "BLOCKED"):
            self.assertIn(label, result.stdout)

    def test_cli_v03_json_blocked_returns_one_and_evaluation_error_returns_two(
        self,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        blocked = run_cli(
            root,
            "release",
            "check",
            "--version",
            "0.3",
            "--format",
            "json",
            "--as-of",
            "2026-08-10",
        )
        self.assertEqual(1, blocked.returncode, blocked.stdout)
        payload = json.loads(blocked.stdout)
        self.assertEqual("0.3", payload["version"])
        self.assertFalse(payload["ready"])
        self.assertEqual(
            list(self.V03_KEYS), [item["key"] for item in payload["checks"]]
        )

        with tempfile.TemporaryDirectory() as temp:
            invalid_root = fixtures.RepositoryValidationTests().make_root(temp)
            judgments = (
                invalid_root
                / "05_Research"
                / "Reviews"
                / "Field_Gate_10_Case_Judgments.json"
            )
            judgments.parent.mkdir(parents=True, exist_ok=True)
            judgments.write_text("[]", encoding="utf-8")
            failed = run_cli(
                invalid_root,
                "release",
                "check",
                "--version",
                "0.3",
                "--format",
                "json",
                "--as-of",
                "2026-08-10",
            )
            self.assertEqual(2, failed.returncode, failed.stdout)
            error_payload = json.loads(failed.stdout)
            self.assertEqual("release_evaluation_error", error_payload["error"]["code"])
            self.assertIn(
                "JSON root must be an object", error_payload["error"]["message"]
            )

    def test_v03_recovery_drill_records_rto_rpo_and_restored_chain(self) -> None:
        root = Path(__file__).resolve().parents[2]
        record = (root / "00_System/v0.3_Recovery_Drill.md").read_text(encoding="utf-8")
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
        runbook = (root / "00_System/v0.3_User_Runbook.md").read_text(encoding="utf-8")
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
            root / "00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md"
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
            root / "00_System/v0.3_AI_Industry_Intelligence_OS/"
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
