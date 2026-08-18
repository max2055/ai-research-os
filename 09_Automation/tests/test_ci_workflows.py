from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from ruamel.yaml import YAML

import test_research_os_core as fixtures
from research_os.ui.app import create_app

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
CONSTRAINTS = ROOT / "requirements" / "ci.txt"


class HostedCiWorkflowTests(unittest.TestCase):
    def workflow_text(self) -> str:
        return WORKFLOW.read_text(encoding="utf-8")

    def workflow(self) -> dict[str, object]:
        payload = YAML(typ="safe").load(self.workflow_text())
        self.assertIsInstance(payload, dict)
        return payload

    def test_hosted_ci_is_read_only_metadata_only_and_has_no_secret_jobs(
        self,
    ) -> None:
        workflow = self.workflow()
        self.assertEqual({"contents": "read"}, workflow["permissions"])
        self.assertEqual(
            {"pull_request", "push", "workflow_dispatch"},
            set(workflow["on"]),
        )
        self.assertEqual(["main"], workflow["on"]["push"]["branches"])

        text = self.workflow_text()
        for command in (
            "validate --metadata-only",
            "index --check --metadata-only",
            "index --check --project PRJ-001 --metadata-only",
            "index --check --project PRJ-002 --metadata-only",
            'pytest -m "not local_integration"',
            "ruff check .",
            "ruff format --check .",
            "mypy src/research_os",
        ):
            self.assertIn(command, text)
        for forbidden in (
            "secrets.",
            "01_Inbox/_assets",
            "09_Automation/operational",
            "candidates.db",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        ):
            self.assertNotIn(forbidden, text)

        checkout = next(
            step
            for step in workflow["jobs"]["quality"]["steps"]
            if str(step.get("uses", "")).startswith("actions/checkout@")
        )
        self.assertIs(checkout["with"]["persist-credentials"], False)

    def test_hosted_ci_asserts_expected_v03_blockers(self) -> None:
        text = self.workflow_text()
        self.assertIn("release check --version 0.3 --format json", text)
        self.assertIn('test "$release_status" -eq 1', text)
        for key, label in (
            ("decision.natural_resolutions", "WP-530"),
            ("ingestion.pilot_completion", "WP-620"),
            ("human.release_approval", "F-024"),
        ):
            self.assertIn(key, text)
            self.assertIn(label, text)

    def test_workflow_never_uses_pull_request_target_cache_or_artifact_upload(
        self,
    ) -> None:
        text = self.workflow_text().lower()
        for forbidden in (
            "pull_request_target",
            "actions/cache",
            "upload-artifact",
            "download-artifact",
            "cache:",
        ):
            self.assertNotIn(forbidden, text)

    def test_action_references_are_full_sha_pins(self) -> None:
        workflow = self.workflow()
        uses = [
            step["uses"]
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if "uses" in step
        ]
        self.assertTrue(uses)
        for reference in uses:
            with self.subTest(reference=reference):
                self.assertRegex(
                    reference,
                    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$",
                )

    def test_ci_constraints_are_exact_and_used_by_workflow(self) -> None:
        requirement_lines = [
            line.strip()
            for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertGreater(len(requirement_lines), 10)
        for line in requirement_lines:
            with self.subTest(requirement=line):
                self.assertRegex(
                    line,
                    r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[^\s;]+$",
                )
        normalized = {
            re.split(r"==", line, maxsplit=1)[0].lower() for line in requirement_lines
        }
        for package in (
            "pydantic",
            "pypdf",
            "ruamel.yaml",
            "typer",
            "fastapi",
            "uvicorn",
            "pytest",
            "ruff",
            "mypy",
        ):
            self.assertIn(package, normalized)
        self.assertIn(
            'pip install --constraint requirements/ci.txt --editable ".[ui,dev]"',
            self.workflow_text(),
        )

    def test_production_docs_and_entrypoints_use_only_web_hosted_scheduler(
        self,
    ) -> None:
        production_docs = (ROOT / "README.md", ROOT / "09_Automation" / "README.md")
        forbidden = (
            "launchctl",
            "LaunchAgent",
            "run_daily.sh",
            "research-os jobs run",
            "research-os discover due",
            "05_Research/Operations/Jobs/JOB-",
            "Markdown success/failure records",
        )
        for path in production_docs:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                for value in forbidden:
                    self.assertNotIn(value, text)
                self.assertIn("python -m research_os.ui", text)
                self.assertIn("/operations/schedules", text)
                self.assertIn("operations.db", text)

        entrypoints = (
            ROOT / "src/research_os/ui/__main__.py",
            ROOT / "src/research_os/services/worker_supervisor.py",
            ROOT / "src/research_os/runtime/worker.py",
        )
        for path in entrypoints:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                for value in ("launchctl", ".plist", "run_daily.sh"):
                    self.assertNotIn(value, text)

    def test_user_runbook_has_no_retired_product_cli(self) -> None:
        text = (ROOT / "00_System" / "v0.3_User_Runbook.md").read_text(encoding="utf-8")
        self.assertNotIn("python -m research_os --", text)
        self.assertNotIn("research-os ", text)
        self.assertNotIn("09_Automation/research_os.py", text)
        self.assertIn("python -m research_os.ui", text)
        self.assertIn("/health", text)
        self.assertIn("/operations/schedules", text)


class CiDashboardSmokeTests(unittest.TestCase):
    def test_fixture_dashboard_routes_return_200(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            client = TestClient(create_app(root))
            routes = (
                "/",
                "/home",
                "/reviews",
                "/metrics",
                "/operations",
                "/pipeline",
                "/pipeline/sources",
                "/pipeline/queue",
                "/pipeline/channels",
                "/companies",
            )
            self.assertEqual(10, len(routes))
            for route in routes:
                with self.subTest(route=route):
                    response = client.get(route)
                    self.assertEqual(200, response.status_code, response.text)


if __name__ == "__main__":
    unittest.main()
