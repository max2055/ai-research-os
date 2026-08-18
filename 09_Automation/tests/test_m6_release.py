from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import pytest

import test_research_os_core as fixtures
from research_os.services.indexing import index_drift, render_project_indexes
from research_os.services.release import (
    SECURITY_PATHS,
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

    def test_dashboard_security_provenance_covers_web_mutation_boundary(self) -> None:
        self.assertEqual(
            {
                "src/research_os/repositories/transaction.py",
                "src/research_os/services/actions.py",
                "src/research_os/services/candidate_db.py",
                "src/research_os/services/mutation_audit.py",
                "src/research_os/services/mutation_gateway.py",
                "src/research_os/services/operations_db.py",
                "src/research_os/services/product_capabilities.py",
                "src/research_os/services/scheduler_worker.py",
                "src/research_os/services/triage.py",
                "src/research_os/services/web_candidate_mutations.py",
                "src/research_os/services/web_identity.py",
                "src/research_os/services/web_repository_mutations.py",
                "src/research_os/services/web_registry_mutations.py",
                "src/research_os/services/web_analysis_mutations.py",
                "src/research_os/services/web_decision_mutations.py",
                "src/research_os/services/web_operations_mutations.py",
                "src/research_os/services/web_research_drafts.py",
                "src/research_os/services/web_review_mutations.py",
                "src/research_os/services/web_schedule_mutations.py",
                "src/research_os/services/web_source_workflows.py",
                "src/research_os/services/worker_supervisor.py",
                "src/research_os/ui/app.py",
                "src/research_os/ui/scheduler_views.py",
                "09_Automation/tests/test_m6_security.py",
                "09_Automation/tests/test_operations_db.py",
                "09_Automation/tests/test_product_capabilities.py",
                "09_Automation/tests/test_web_candidate_parity.py",
                "09_Automation/tests/test_web_mutation.py",
                "09_Automation/tests/test_web_repository_mutations.py",
                "09_Automation/tests/test_web_registry_parity.py",
                "09_Automation/tests/test_web_analysis_parity.py",
                "09_Automation/tests/test_web_decision_parity.py",
                "09_Automation/tests/test_web_operations_parity.py",
                "09_Automation/tests/test_web_research_drafts.py",
                "09_Automation/tests/test_web_review_parity.py",
                "09_Automation/tests/test_web_scheduler.py",
                "09_Automation/tests/test_web_source_parity.py",
                "09_Automation/tests/test_worker_supervisor.py",
            },
            set(SECURITY_PATHS),
        )

    def seed_v03_field_gate_evidence(self, root: Path) -> None:
        source_root = Path(__file__).resolve().parents[2]
        for relative in (
            "00_System/C020_Phase_3_Acceptance.md",
            "00_System/D020_Phase_4_Acceptance.md",
            "05_Research/Reviews/Field_Gate_20_Impact_Judgments.json",
            "05_Research/Reviews/Field_Gate_10_Case_Judgments.json",
        ):
            fixtures.write(
                root / relative,
                (source_root / relative).read_text(encoding="utf-8"),
            )
        for relative_folder in (
            "04_Evidence/Events",
            "05_Research/Analysis",
            "02_Knowledge/Modes",
        ):
            for source in (source_root / relative_folder).glob("*.md"):
                fixtures.write(
                    root / source.relative_to(source_root),
                    source.read_text(encoding="utf-8"),
                )

    def seed_v03_recovery_chain_evidence(self, root: Path) -> Path:
        source_root = Path(__file__).resolve().parents[2]
        for relative in (
            "00_System/v0.3_Recovery_Drill.md",
            "01_Inbox/Articles/SRC-20260806-077-10-q-filing-2025-04-30.md",
            "02_Knowledge/Channels/CHN-sec-microsoft.md",
        ):
            fixtures.write(
                root / relative,
                (source_root / relative).read_text(encoding="utf-8"),
            )
        for relative in (
            "09_Automation/operational/candidates.db",
            ("01_Inbox/_assets/SRC-20260806-077/20260806142517-4ff48b41c786.html"),
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, target)
        return root / "00_System/v0.3_Recovery_Drill.md"

    @staticmethod
    def checks_by_key(root: Path) -> dict[str, ReleaseCheck]:
        return {
            check.key: check
            for check in release_readiness_v03(root, as_of="2026-08-10").checks
        }

    @staticmethod
    def replace_recovery_chain_value(text: str, label: str, value: str) -> str:
        pattern = rf"(?m)^(\|\s*{re.escape(label)}\s*\|)\s*[^|]*(\|\s*)$"
        updated, count = re.subn(
            pattern,
            lambda match: f"{match.group(1)} {value} {match.group(2)}",
            text,
        )
        if count != 1:
            raise AssertionError(f"expected one recovery row for {label}, got {count}")
        return updated

    @pytest.mark.local_integration
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
        readiness = release_readiness_v03(root, as_of="2026-08-13")

        self.assertEqual(self.V03_KEYS, tuple(check.key for check in readiness.checks))
        for check in readiness.checks:
            self.assertTrue(check.requirement)
            self.assertTrue(check.observed)
            self.assertTrue(check.evidence_paths)

    @pytest.mark.local_integration
    def test_current_v03_has_only_the_five_time_and_human_blockers(self) -> None:
        root = Path(__file__).resolve().parents[2]
        readiness = release_readiness_v03(root, as_of="2026-08-13")
        blockers = {check.key: check for check in readiness.blockers}

        self.assertFalse(readiness.ready)
        self.assertEqual(5, len(blockers))
        self.assertIn("WP-620", blockers["ingestion.pilot_completion"].observed)
        self.assertIn("WP-530", blockers["decision.natural_resolutions"].observed)
        self.assertIn("2026-10-31", blockers["decision.natural_resolutions"].observed)
        self.assertIn("F-024", blockers["human.release_approval"].observed)
        by_key = {check.key: check for check in readiness.checks}
        self.assertTrue(by_key["ingestion.no_silent_missed_runs"].passed)
        self.assertTrue(by_key["impact_analysis.impact_field_gate"].passed)
        self.assertIn("20/20", by_key["impact_analysis.impact_field_gate"].observed)
        self.assertTrue(by_key["decision.no_automated_trading"].passed)
        self.assertTrue(by_key["engineering.quality_suite"].passed)
        self.assertTrue(by_key["engineering.performance_slo"].passed)
        self.assertTrue(by_key["engineering.migration_recovery"].passed)
        self.assertTrue(by_key["engineering.recovery_boundaries"].passed)
        self.assertTrue(by_key["engineering.dashboard_security"].passed)
        verification_path = "00_System/v0.3_Release_Gate_Verification_2026-08-13.md"
        self.assertIn(
            verification_path,
            by_key["engineering.quality_suite"].evidence_paths,
        )
        self.assertIn(
            verification_path,
            by_key["engineering.dashboard_security"].evidence_paths,
        )

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
                "ＡＩ",
                "ＳＹＳＴＥＭ",
                "ⒶⒾ",
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

    def test_v03_structured_gates_cross_check_real_objects_and_terminal_values(
        self,
    ) -> None:
        source_root = Path(__file__).resolve().parents[2]
        real = self.checks_by_key(source_root)
        self.assertFalse(real["impact_analysis.impact_field_gate"].passed)
        self.assertTrue(real["impact_analysis.mode_field_gate"].passed)

        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            self.seed_v03_field_gate_evidence(root)
            impact_path = (
                root / "05_Research/Reviews/Field_Gate_20_Impact_Judgments.json"
            )
            mode_path = root / "05_Research/Reviews/Field_Gate_10_Case_Judgments.json"
            impact_original = json.loads(impact_path.read_text(encoding="utf-8"))
            mode_original = json.loads(mode_path.read_text(encoding="utf-8"))

            def reject_impact(label: str) -> None:
                payload = json.loads(json.dumps(impact_original))
                if label == "fake-event":
                    payload["judgments"][0]["event_id"] = "EVT-20260810-999"
                elif label == "duplicate-event":
                    payload["judgments"][-1]["event_id"] = payload["judgments"][0][
                        "event_id"
                    ]
                elif label == "wrong-count":
                    payload["metrics"]["n"] = 13
                elif label == "float-count":
                    payload["metrics"]["n"] = 14.0
                elif label == "invalid-decision":
                    payload["approved"]["decision"] = "approve-but-not-terminal"
                impact_path.write_text(json.dumps(payload), encoding="utf-8")
                with (
                    self.subTest(gate="impact", mutation=label),
                    self.assertRaises(ReleaseEvaluationError),
                ):
                    release_readiness_v03(root, as_of="2026-08-10")

            for label in (
                "fake-event",
                "duplicate-event",
                "wrong-count",
                "float-count",
                "invalid-decision",
            ):
                reject_impact(label)
            impact_path.write_text(json.dumps(impact_original), encoding="utf-8")

            def reject_mode(label: str) -> None:
                payload = json.loads(json.dumps(mode_original))
                if label == "fake-run":
                    payload["runs"][0]["run_id"] = "ANL-20260810-999"
                elif label == "missing-mode":
                    payload["runs"][0].pop("mode")
                elif label == "mismatched-mode":
                    payload["runs"][0]["mode"] = "supply-demand"
                elif label == "unregistered-mode":
                    payload["runs"][0]["mode"] = "market-timing"
                elif label == "duplicate-run":
                    payload["runs"][-1]["run_id"] = payload["runs"][0]["run_id"]
                elif label == "wrong-count":
                    payload["gate_verdict"]["runs"] = 33
                elif label == "invalid-status":
                    payload["status"] = "confirmed-but-not-terminal"
                mode_path.write_text(json.dumps(payload), encoding="utf-8")
                with (
                    self.subTest(gate="mode", mutation=label),
                    self.assertRaises(ReleaseEvaluationError),
                ):
                    release_readiness_v03(root, as_of="2026-08-10")

            for label in (
                "fake-run",
                "missing-mode",
                "mismatched-mode",
                "unregistered-mode",
                "duplicate-run",
                "wrong-count",
                "invalid-status",
            ):
                reject_mode(label)

    def test_v03_impact_gate_requires_twenty_reviewed_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            self.seed_v03_field_gate_evidence(root)
            impact_path = (
                root / "05_Research/Reviews/Field_Gate_20_Impact_Judgments.json"
            )
            payload = json.loads(impact_path.read_text(encoding="utf-8"))
            payload["judgments"] = payload["judgments"][:14]
            payload["sample_size"] = 14
            payload["metrics"]["n"] = 14
            payload["approved"]["date"] = "2026-08-10"
            payload["approved"]["decision"] = (
                "approve all 14 in-scope events; EVT-046 excluded"
            )
            sampled_ids = {str(row["event_id"]) for row in payload["judgments"]}
            objects, _ = validate_repository(root)
            extra_events = [
                obj
                for obj in objects
                if obj.object_type == "event"
                and obj.metadata.get("review_status") == "reviewed"
                and obj.object_id not in sampled_ids
            ][:6]
            self.assertEqual(6, len(extra_events))
            for event in extra_events:
                row = json.loads(json.dumps(payload["judgments"][0]))
                row["event_id"] = event.object_id
                payload["judgments"].append(row)
            payload["sample_size"] = 20
            payload["metrics"]["n"] = 20
            impact_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseEvaluationError, "approved.decision"):
                release_readiness_v03(root, as_of="2026-08-10")

            payload["approved"]["decision"] = "approve"
            impact_path.write_text(json.dumps(payload), encoding="utf-8")

            complete = self.checks_by_key(root)
            self.assertTrue(complete["impact_analysis.impact_field_gate"].passed)

            pending_path = extra_events[0].path
            pending_text = pending_path.read_text(encoding="utf-8")
            self.assertIn("review_status: reviewed", pending_text)
            pending_path.write_text(
                pending_text.replace(
                    "review_status: reviewed", "review_status: pending", 1
                ),
                encoding="utf-8",
            )
            pending = self.checks_by_key(root)
            self.assertFalse(pending["impact_analysis.impact_field_gate"].passed)

    def test_v03_engineering_gates_reject_duplicate_and_label_only_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            performance_rows = "\n".join(
                "| Home | 0.1 | 0.1 | <2 | pass |" for _ in range(7)
            )
            fixtures.write(
                root / "00_System/v0.3_Performance_Benchmark.md",
                "# Benchmark\n\n"
                "Status: passed\nDate: 2026-08-10\n"
                "authoritative writes: 0\n\n"
                "| Operation | Samples (s) | p95 (s) | SLO (s) | Result |\n"
                "|---|---|---:|---:|---|\n"
                f"{performance_rows}\n"
                "| Nearest-rank p95 | 0.1 s |\n",
            )
            recovery = (
                "# Recovery labels only\n\n"
                "Status: passed\nDate: 2026-08-10\n"
                "Git recovery\nSource assets\nCandidate store\nsecrets\nlaunchd\n"
                "| Full pytest | complete suite | pass |\n"
                "| Ruff | source and tests | pass |\n"
                "| mypy | source | pass |\n"
                "| Coverage | 99% | pass |\n"
                "| Dashboard | loopback GET smoke | pass |\n"
            )
            fixtures.write(root / "00_System/v0.3_Recovery_Drill.md", recovery)
            fixtures.write(
                root / "00_System/v0.3_Migration_Rehearsal.md",
                "# Migration labels only\n\n"
                "Status: passed\nDate: 2026-08-10\n"
                "rollback precondition changed\n"
                "Candidate DB schema version: 2\n"
                "0 errors, 0 warnings\n",
            )
            fixtures.write(
                root / "09_Automation/tests/test_m6_security.py",
                "def test_dashboard_mutation_routes_remain_allowlisted(): pass\n"
                "def test_traversal_payloads_never_escape_repository(): pass\n"
                "def test_secrets_never_appear_in_health_html(): pass\n",
            )

            by_key = self.checks_by_key(root)
            for key in (
                "engineering.performance_slo",
                "engineering.migration_recovery",
                "engineering.recovery_boundaries",
                "engineering.dashboard_security",
            ):
                with self.subTest(key=key):
                    self.assertFalse(by_key[key].passed)

    def test_v03_no_trading_rejects_recommendation_order_directives(self) -> None:
        source_root = Path(__file__).resolve().parents[2]
        recommendation = (
            source_root / "05_Research/Recommendations/REC-20260809-001.md"
        ).read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            fixtures.write(
                root / "05_Research/Recommendations/REC-20260809-001.md",
                recommendation
                + "\nPlace a market order through the broker execution API.\n",
            )
            fixtures.write(
                root / "00_System/v0.3_Known_Limitations.md",
                "No automated investment action.\n"
                "No broker, order, or portfolio execution integration.\n",
            )

            by_key = self.checks_by_key(root)
            self.assertFalse(by_key["decision.no_automated_trading"].passed)

    def test_v03_no_trading_rejects_public_action_surfaces_without_text_noise(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            fixtures.write(
                root / "00_System/v0.3_Known_Limitations.md",
                "No automated investment action.\n"
                "No broker, order, or portfolio execution integration.\n",
            )
            runtime_path = root / "src/research_os/runtime/product.py"
            fixtures.write(
                runtime_path,
                "def place_market_order() -> None:\n    pass\n\n"
                '__all__ = ["place_market_order"]\n',
            )

            by_key = self.checks_by_key(root)
            self.assertFalse(by_key["decision.no_automated_trading"].passed)

            runtime_path.write_text(
                "# Enforcement note: no broker execution is allowed.\n"
                'QUERY = "SELECT * FROM candidates ORDER BY created_at"\n'
                "__all__: list[str] = []\n",
                encoding="utf-8",
            )
            without_surface = self.checks_by_key(root)
            self.assertTrue(without_surface["decision.no_automated_trading"].passed)

    def test_v03_no_trading_resolves_static_names_and_registry_mutations(
        self,
    ) -> None:
        cases = (
            (
                "src/research_os/cli.py",
                'COMMAND = "trade"\nparser.add_parser(COMMAND)\n',
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/broker/order"\n'
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/cli.py",
                'COMMAND = "trade"\nparser.add_parser(name=COMMAND)\n',
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/broker/order"\n'
                "@app.post(path=ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/broker/order"\n'
                "def submit() -> None:\n    pass\n"
                "app.add_api_route(path=ROUTE, endpoint=submit)\n",
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/" + "broker/order"\n'
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/safe"\n'
                "if ENABLED:\n"
                '    ROUTE = "/broker/order"\n'
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/safe"\n'
                "try:\n"
                '    ROUTE = "/broker/order"\n'
                "except RuntimeError:\n"
                "    pass\n"
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/safe"\n'
                "for item in ITEMS:\n"
                '    ROUTE = "/broker/order"\n'
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/safe"\n'
                "while ENABLED:\n"
                '    ROUTE = "/broker/order"\n'
                "    break\n"
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/ui/app.py",
                'ROUTE = "/safe"\n'
                "match MODE:\n"
                '    case "trade":\n'
                '        ROUTE = "/broker/order"\n'
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
            ),
            (
                "src/research_os/services/jobs.py",
                'JOB_NAMES = {"daily"}\nJOB_NAMES |= {"trade"}\n',
            ),
            (
                "src/research_os/services/jobs.py",
                'JOB_NAMES = ("daily",)\nJOB_NAMES += ("trade",)\n',
            ),
            (
                "src/research_os/services/jobs.py",
                'JOB_NAMES = {"daily"}\nJOB_NAMES.add("trade")\n',
            ),
            (
                "src/research_os/runtime/product.py",
                '__all__ = []\n__all__.append("place_market_order")\n',
            ),
        )
        for relative, source in cases:
            with (
                self.subTest(relative=relative, source=source),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = fixtures.RepositoryValidationTests().make_root(temp)
                fixtures.write(
                    root / "00_System/v0.3_Known_Limitations.md",
                    "No automated investment action.\n"
                    "No broker, order, or portfolio execution integration.\n",
                )
                fixtures.write(root / relative, source)
                by_key = self.checks_by_key(root)
                self.assertFalse(by_key["decision.no_automated_trading"].passed)

    def test_v03_no_trading_static_names_use_latest_unconditional_value(
        self,
    ) -> None:
        cases = (
            (
                'ROUTE = "/broker/order"\n'
                'ROUTE = "/safe"\n'
                "@app.post(ROUTE)\n"
                "def status() -> None:\n    pass\n",
                True,
            ),
            (
                'ROUTE = "/broker/order"\n'
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n"
                'ROUTE = "/safe"\n',
                False,
            ),
            (
                'ROUTE = "/broker/order"\n'
                "ROUTE: str\n"
                "@app.post(ROUTE)\n"
                "def submit() -> None:\n    pass\n",
                False,
            ),
            (
                'ROUTE = "/broker/order"\n'
                "ROUTE = configured_route()\n"
                "@app.post(ROUTE)\n"
                "def status() -> None:\n    pass\n",
                True,
            ),
            (
                'ROUTE = "/safe"\n'
                "def configure() -> None:\n"
                '    ROUTE = "/broker/order"\n'
                "@app.post(ROUTE)\n"
                "def status() -> None:\n    pass\n",
                True,
            ),
        )
        for source, expected in cases:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as temp:
                root = fixtures.RepositoryValidationTests().make_root(temp)
                fixtures.write(
                    root / "00_System/v0.3_Known_Limitations.md",
                    "No automated investment action.\n"
                    "No broker, order, or portfolio execution integration.\n",
                )
                fixtures.write(root / "src/research_os/ui/app.py", source)

                by_key = self.checks_by_key(root)
                self.assertEqual(
                    expected,
                    by_key["decision.no_automated_trading"].passed,
                )

    def test_v03_no_trading_rejects_position_surfaces(self) -> None:
        cases = (
            ("src/research_os/cli.py", 'parser.add_parser("position")\n'),
            (
                "src/research_os/ui/app.py",
                '@app.get("/positions")\ndef positions() -> None:\n    pass\n',
            ),
            (
                "src/research_os/services/jobs.py",
                'JOB_NAMES = {"position-size"}\n',
            ),
            (
                "src/research_os/runtime/product.py",
                '__all__ = ["position_sizes"]\n',
            ),
        )
        for relative, source in cases:
            with (
                self.subTest(relative=relative, source=source),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = fixtures.RepositoryValidationTests().make_root(temp)
                fixtures.write(
                    root / "00_System/v0.3_Known_Limitations.md",
                    "No automated investment action.\n"
                    "No broker, order, or portfolio execution integration.\n",
                )
                fixtures.write(root / relative, source)
                by_key = self.checks_by_key(root)
                self.assertFalse(by_key["decision.no_automated_trading"].passed)

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

    @pytest.mark.local_integration
    def test_v03_quality_and_passed_decision_provenance_are_exact(self) -> None:
        root = Path(__file__).resolve().parents[2]
        readiness = release_readiness_v03(root, as_of="2026-08-13")
        by_key = {check.key: check for check in readiness.checks}

        self.assertTrue(by_key["engineering.quality_suite"].passed)
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

        for arguments in (
            ("--version", "0.4", "--format", "json"),
            ("--format", "json", "--version", "0.4"),
        ):
            invalid_version = run_cli(root, "release", "check", *arguments)
            self.assertEqual(2, invalid_version.returncode)
            self.assertEqual("", invalid_version.stderr)
            payload = json.loads(invalid_version.stdout)
            self.assertEqual("release_evaluation_error", payload["error"]["code"])
            self.assertIn("version must be 0.2 or 0.3", payload["error"]["message"])

        invalid_version_text = run_cli(root, "release", "check", "--version", "0.4")
        self.assertEqual(2, invalid_version_text.returncode)
        self.assertEqual("", invalid_version_text.stderr)
        self.assertIn("ERROR: version must be 0.2 or 0.3", invalid_version_text.stdout)

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

    @pytest.mark.local_integration
    def test_v03_recovery_chain_rejects_empty_structured_fields(self) -> None:
        labels = (
            "Candidate",
            "Channel",
            "Candidate URL",
            "Promoted Source",
            "Source record",
            "Raw asset",
            "Raw bytes",
            "Expected and actual SHA-256",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            recovery_path = self.seed_v03_recovery_chain_evidence(root)
            original = recovery_path.read_text(encoding="utf-8")
            baseline = self.checks_by_key(root)
            self.assertTrue(baseline["engineering.recovery_boundaries"].passed)

            for label in labels:
                with self.subTest(label=label):
                    recovery_path.write_text(
                        self.replace_recovery_chain_value(original, label, ""),
                        encoding="utf-8",
                    )
                    with self.assertRaises(ReleaseEvaluationError):
                        release_readiness_v03(root, as_of="2026-08-10")

    @pytest.mark.local_integration
    def test_v03_recovery_chain_blocks_completely_forged_links(self) -> None:
        replacements = {
            "Candidate": "`CND-aaaaaaaaaaaaaaaaaaaa`, status `promoted`",
            "Channel": "`CHN-forged`",
            "Candidate URL": "`https://example.invalid/forged`",
            "Promoted Source": "`SRC-20990101-999`",
            "Source record": "`01_Inbox/Articles/SRC-20990101-999-forged.md`",
            "Raw asset": "`01_Inbox/_assets/SRC-20990101-999/forged.bin`",
            "Raw bytes": "123",
            "Expected and actual SHA-256": f"`{'a' * 64}`",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            recovery_path = self.seed_v03_recovery_chain_evidence(root)
            forged = recovery_path.read_text(encoding="utf-8")
            for label, value in replacements.items():
                forged = self.replace_recovery_chain_value(forged, label, value)
            recovery_path.write_text(forged, encoding="utf-8")

            by_key = self.checks_by_key(root)
            self.assertFalse(by_key["engineering.recovery_boundaries"].passed)

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
            "Candidate dismiss through preview",
            "Web parity remains incomplete",
            "No Review approval or Thesis mutation adapter exists",
            "calibration",
            "no automated investment action",
            "WP-530",
            "WP-620",
            "F-024",
            "2026-10-31",
            "default release check remains v0.2",
            "explicit --version 0.3",
            "metadata-only",
            "strict local",
            "blocked",
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

    def test_v03_docs_pin_ci_cost_and_blocked_release_contract(self) -> None:
        root = Path(__file__).resolve().parents[2]
        readme = (root / "README.md").read_text(encoding="utf-8")
        runbook = (root / "00_System/v0.3_User_Runbook.md").read_text(encoding="utf-8")
        limitations = (root / "00_System/v0.3_Known_Limitations.md").read_text(
            encoding="utf-8"
        )
        backlog = (
            root / "00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md"
        ).read_text(encoding="utf-8")

        for text in (
            "research-os validate --strict",
            "research-os validate --metadata-only",
            "research-os release check --version 0.3 --format json",
            "metadata-only",
            "strict local",
        ):
            with self.subTest(document="readme", text=text):
                self.assertIn(text, readme)

        combined = f"{runbook}\n{limitations}"
        for state in (
            "unconfigured",
            "no_data",
            "ok",
            "warning",
            "exceeded",
            "invalid",
        ):
            with self.subTest(cost_state=state):
                self.assertIn(f"`{state}`", combined)
        for text in (
            "RESEARCH_OS_MODEL_COST_BUDGET",
            "natural month",
            "missing cost is not zero",
            "metadata-only",
            "strict local",
            "WP-530",
            "WP-620",
            "F-024",
            "2026-10-31",
            "BLOCKED",
        ):
            with self.subTest(operational_contract=text):
                self.assertIn(text, combined)

        wp530 = next(
            line for line in backlog.splitlines() if line.startswith("| WP-530")
        )
        wp620 = next(
            line for line in backlog.splitlines() if line.startswith("| WP-620")
        )
        wp630 = next(
            line for line in backlog.splitlines() if line.startswith("| WP-630")
        )
        self.assertIn("BLOCKED", wp530)
        self.assertIn("future-date dependent", wp530)
        self.assertIn("2026-10-31", wp530)
        self.assertIn("BLOCKED", wp620)
        self.assertIn("future-date dependent", wp620)
        self.assertIn("30-day Pilot", wp620)
        self.assertIn("F-023 completed", wp630)
        self.assertIn("F-024 BLOCKED", wp630)

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
