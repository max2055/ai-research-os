from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_research_os_core as fixtures

SCRIPT = Path(__file__).resolve().parents[1] / "research_os.py"


def run_cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--root",
            str(root),
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


class CliPathTests(unittest.TestCase):
    def test_validate_output_matches_golden_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            result = run_cli(root, "validate")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(
                "Objects: event=1, project=1, source=1\n"
                "Findings: errors=0, warnings=0\n"
                "PASS: repository validation succeeded\n",
                result.stdout,
            )

    def test_source_event_report_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)

            source_args = (
                "new-source",
                "--title",
                "CLI Source",
                "--slug",
                "cli-source",
                "--date",
                "2026-07-30",
                "--source-type",
                "article",
                "--publisher",
                "Publisher",
                "--published-at",
                "2026-07-30",
                "--url",
                "https://example.com/cli",
                "--source-grade",
                "A",
            )
            source_path = (
                root / "01_Inbox" / "Articles" / "SRC-20260730-002-cli-source.md"
            )
            dry_run = run_cli(root, *source_args)
            self.assertEqual(0, dry_run.returncode, dry_run.stderr)
            self.assertIn("DRY-RUN", dry_run.stdout)
            self.assertFalse(source_path.exists())

            applied = run_cli(root, *source_args, "--apply")
            self.assertEqual(0, applied.returncode, applied.stdout)
            self.assertTrue(source_path.exists())

            event_args = (
                "new-event",
                "--title",
                "CLI Event",
                "--slug",
                "cli-event",
                "--date",
                "2026-07-30",
                "--event-date",
                "2026-07-30",
                "--source-ids",
                "SRC-20260730-002",
                "--confidence",
                "0.50",
            )
            event_path = (
                root / "04_Evidence" / "Events" / "EVT-20260730-002-cli-event.md"
            )
            dry_run = run_cli(root, *event_args)
            self.assertEqual(0, dry_run.returncode, dry_run.stdout)
            self.assertFalse(event_path.exists())

            applied = run_cli(root, *event_args, "--apply")
            self.assertEqual(0, applied.returncode, applied.stdout)
            self.assertTrue(event_path.exists())
            self.assertIn(
                "- [x] Event extraction completed",
                source_path.read_text(encoding="utf-8"),
            )
            self.assertIn("UPDATED:", applied.stdout)

            report_args = (
                "new-report",
                "--title",
                "CLI Report",
                "--slug",
                "cli-report",
                "--date",
                "2026-07-30",
                "--period-start",
                "2026-07-01",
                "--period-end",
                "2026-07-30",
                "--evidence-ids",
                "EVT-20260730-002",
            )
            report_path = root / "06_Reports" / "Topics" / "RPT-20260730-cli-report.md"
            dry_run = run_cli(root, *report_args)
            self.assertEqual(0, dry_run.returncode, dry_run.stdout)
            self.assertFalse(report_path.exists())

            applied = run_cli(root, *report_args, "--apply")
            self.assertEqual(0, applied.returncode, applied.stdout)
            self.assertTrue(report_path.exists())

            validated = run_cli(root, "validate")
            self.assertEqual(0, validated.returncode, validated.stdout)
            self.assertIn("Findings: errors=0", validated.stdout)

    def test_project_review_and_action_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)

            projects = run_cli(root, "project", "list")
            self.assertEqual(0, projects.returncode, projects.stdout)
            self.assertIn("PRJ-001", projects.stdout)

            create_project = (
                "project",
                "create",
                "--title",
                "Second Project",
                "--slug",
                "second-project",
                "--date",
                "2026-07-30",
                "--owner",
                "max",
                "--question",
                "What is the second question?",
                "--charter-path",
                "charter.md",
                "--queue-path",
                "queue.md",
                "--review-cadence",
                "Weekly",
                "--next-review-date",
                "2026-08-06",
            )
            preview = run_cli(root, *create_project)
            self.assertEqual(0, preview.returncode, preview.stdout)
            self.assertIn("PRJ-002", preview.stdout)
            created = run_cli(root, *create_project, "--apply")
            self.assertEqual(0, created.returncode, created.stdout)

            queue = run_cli(
                root,
                "review",
                "queue",
                "--project",
                "PRJ-001",
                "--type",
                "source",
            )
            self.assertEqual(0, queue.returncode, queue.stdout)
            self.assertIn("SRC-20260729-001", queue.stdout)

            reviewed = run_cli(
                root,
                "review",
                "apply",
                "--targets",
                "SRC-20260729-001",
                "--decision",
                "approve",
                "--reviewer",
                "Researcher",
                "--date",
                "2026-07-30",
                "--notes",
                "Checked.",
                "--apply",
            )
            self.assertEqual(0, reviewed.returncode, reviewed.stdout)
            self.assertIn("REV-20260730-001", reviewed.stdout)

            action = run_cli(
                root,
                "actions",
                "create",
                "--title",
                "Second project action",
                "--owner",
                "max",
                "--date",
                "2026-07-30",
                "--due-date",
                "2026-08-06",
                "--success-evidence",
                "A linked Source",
                "--projects",
                "PRJ-002",
                "--apply",
            )
            self.assertEqual(0, action.returncode, action.stdout)
            listed = run_cli(
                root,
                "actions",
                "list",
                "--project",
                "PRJ-002",
            )
            self.assertEqual(0, listed.returncode, listed.stdout)
            self.assertIn("Second project action", listed.stdout)

            source = run_cli(
                root,
                "new-source",
                "--title",
                "Second Project Source",
                "--slug",
                "second-project-source",
                "--date",
                "2026-07-30",
                "--source-type",
                "article",
                "--publisher",
                "Publisher",
                "--published-at",
                "2026-07-30",
                "--url",
                "https://example.com/prj-002",
                "--source-grade",
                "A",
                "--project",
                "PRJ-002",
                "--apply",
            )
            self.assertEqual(0, source.returncode, source.stdout)

            event = run_cli(
                root,
                "new-event",
                "--title",
                "Second Project Event",
                "--slug",
                "second-project-event",
                "--date",
                "2026-07-30",
                "--event-date",
                "2026-07-30",
                "--source-ids",
                "SRC-20260730-002",
                "--confidence",
                "0.5",
                "--project",
                "PRJ-002",
                "--apply",
            )
            self.assertEqual(0, event.returncode, event.stdout)
            event_review = run_cli(
                root,
                "review",
                "apply",
                "--targets",
                "EVT-20260730-002",
                "--decision",
                "approve",
                "--reviewer",
                "Researcher",
                "--date",
                "2026-07-30",
                "--notes",
                "Claims checked.",
                "--apply",
            )
            self.assertEqual(
                0,
                event_review.returncode,
                event_review.stdout,
            )

            report = run_cli(
                root,
                "new-report",
                "--title",
                "Second Project Report",
                "--slug",
                "second-project-report",
                "--date",
                "2026-07-30",
                "--period-start",
                "2026-07-30",
                "--period-end",
                "2026-07-30",
                "--evidence-ids",
                "EVT-20260730-002",
                "--project",
                "PRJ-002",
                "--apply",
            )
            self.assertEqual(0, report.returncode, report.stdout)
            metrics = run_cli(
                root,
                "metrics",
                "--project",
                "PRJ-002",
                "--as-of",
                "2026-07-30",
                "--format",
                "json",
            )
            self.assertEqual(0, metrics.returncode, metrics.stdout)
            self.assertIn('"project_id": "PRJ-002"', metrics.stdout)
            self.assertIn('"report"', metrics.stdout)

    def test_source_capture_process_and_verify_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            local_file = root / "captured.html"
            local_file.write_text(
                "<html><p>Captured evidence.</p></html>",
                encoding="utf-8",
            )
            added = run_cli(
                root,
                "source",
                "add",
                "--title",
                "Captured Source",
                "--slug",
                "captured-source",
                "--date",
                "2026-07-30",
                "--source-type",
                "article",
                "--publisher",
                "Publisher",
                "--published-at",
                "unknown",
                "--file",
                str(local_file),
                "--source-grade",
                "A",
                "--apply",
            )
            self.assertEqual(0, added.returncode, added.stdout)
            self.assertIn("SRC-20260730-002", added.stdout)

            processed = run_cli(
                root,
                "source",
                "process",
                "--id",
                "SRC-20260730-002",
                "--apply",
            )
            self.assertEqual(0, processed.returncode, processed.stdout)
            verified = run_cli(root, "source", "verify-assets")
            self.assertEqual(0, verified.returncode, verified.stdout)
            self.assertIn("OK SRC-20260730-002", verified.stdout)

            local_file.write_text(
                "<html><p>Changed evidence.</p></html>",
                encoding="utf-8",
            )
            fetched = run_cli(
                root,
                "source",
                "fetch",
                "--id",
                "SRC-20260730-002",
                "--file",
                str(local_file),
                "--apply",
            )
            self.assertEqual(0, fetched.returncode, fetched.stdout)
            confirmed = run_cli(
                root,
                "source",
                "confirm-date",
                "--id",
                "SRC-20260730-002",
                "--date",
                "2026-07-29",
                "--apply",
            )
            self.assertEqual(0, confirmed.returncode, confirmed.stdout)


if __name__ == "__main__":
    unittest.main()
