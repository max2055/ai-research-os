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


def mode_file(
    mode_id: str = "MOD-ANL-value-chain-v1",
    *,
    status: str = "active",
    review_status: str = "reviewed",
) -> str:
    return f"""---
id: {mode_id}
type: analysis_mode
title: Value Chain Mode
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: {status}
review_status: {review_status}
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


def run_file(
    run_id: str = "ANL-20260808-001",
    *,
    mode_id: str = "MOD-ANL-value-chain-v1",
    status: str = "completed",
    review_status: str = "rejected",
    event_ids: tuple[str, ...] = ("EVT-20260729-001",),
) -> str:
    return f"""---
id: {run_id}
type: analysis_run
title: Analysis Run {run_id}
created_at: 2026-08-08
updated_at: 2026-08-08
schema_version: 2
project_ids: []
status: {status}
review_status: {review_status}
tags: []
mode_id: {mode_id}
scope_ids: []
as_of: 2026-08-08
input_source_ids: []
input_event_ids: [{', '.join(event_ids)}]
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
产能爬坡速度与二供进展。

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


def analysis_fixture_root(temp: str, *, review_status: str = "rejected") -> Path:
    root = Path(temp)
    fixtures.write(root / "00_System" / "Taxonomy.md", fixtures.TAXONOMY)
    fixtures.write(root / "05_Research" / "Projects" / "PRJ-001.md", fixtures.project())
    fixtures.write(
        root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md",
        fixtures.source(),
    )
    fixtures.write(
        root / "04_Evidence" / "Events" / "EVT-20260729-001-event.md",
        fixtures.event(status="reviewed"),
    )
    fixtures.write(
        root / "02_Knowledge" / "Modes" / "MOD-ANL-value-chain-v1.md",
        mode_file(),
    )
    fixtures.write(
        root / "05_Research" / "Analysis" / "ANL-20260808-001.md",
        run_file(review_status=review_status),
    )
    return root


class AnalysisCliTests(unittest.TestCase):
    """WP-412 (D-014/D-016): modes + analyze CLI command groups."""

    def test_modes_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(root, "modes", "list")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("MOD-ANL-value-chain-v1", result.stdout)
            self.assertIn("价值链分析", result.stdout)

    def test_modes_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(root, "modes", "check")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("OK       MOD-ANL-value-chain-v1", result.stdout)
            self.assertIn("1 runnable / 1 modes", result.stdout)

    def test_modes_show(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(root, "modes", "show", "MOD-ANL-value-chain-v1")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("定位价值链各环节的控制力", result.stdout)
            self.assertIn("## Required questions", result.stdout)

    def test_modes_show_unknown_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(root, "modes", "show", "MOD-ANL-missing-v1")
            self.assertEqual(2, result.returncode)
            self.assertIn("ERROR:", result.stdout)

    def test_analyze_show(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(root, "analyze", "show", "ANL-20260808-001")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("mode: MOD-ANL-value-chain-v1", result.stdout)
            self.assertIn("## Current chain", result.stdout)

    def test_analyze_show_unknown_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(root, "analyze", "show", "ANL-missing")
            self.assertEqual(2, result.returncode)
            self.assertIn("ERROR:", result.stdout)

    def test_analyze_compare(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(root, "analyze", "compare", "--runs", "ANL-20260808-001")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("# Mode comparison", result.stdout)
            self.assertIn("ANL-20260808-001", result.stdout)

    def test_analyze_run_echo_surfaces_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp)
            result = run_cli(
                root,
                "analyze",
                "run",
                "--mode",
                "MOD-ANL-value-chain-v1",
                "--event",
                "EVT-20260729-001",
                "--as-of",
                "2026-08-08",
                "--model-provider",
                "echo",
                "--model-id",
                "echo",
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("ERROR:", result.stdout)

    def test_analyze_propose_thesis_rejected_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp, review_status="rejected")
            result = run_cli(
                root, "analyze", "propose-thesis", "--run", "ANL-20260808-001"
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("only reviewed runs", result.stdout)

    def test_analyze_propose_thesis_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp, review_status="reviewed")
            result = run_cli(
                root, "analyze", "propose-thesis", "--run", "ANL-20260808-001"
            )
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("DRY-RUN: no files changed", result.stdout)
            self.assertIn("## Proposed Thesis", result.stdout)
            self.assertFalse((root / "05_Research" / "Analysis_Proposals").exists())

    def test_analyze_propose_thesis_apply_writes_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = analysis_fixture_root(temp, review_status="reviewed")
            result = run_cli(
                root,
                "analyze",
                "propose-thesis",
                "--run",
                "ANL-20260808-001",
                "--apply",
            )
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("CREATED: 05_Research/Analysis_Proposals/", result.stdout)
            proposal = (
                root / "05_Research" / "Analysis_Proposals"
                / "Thesis_Proposal_ANL-20260808-001.md"
            )
            self.assertTrue(proposal.exists())
            text = proposal.read_text(encoding="utf-8")
            self.assertIn("这是 Proposal，不是权威 Thesis", text)


if __name__ == "__main__":
    unittest.main()
