from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import test_research_os_core as fixtures
from research_os.adapters.file import FileCaptureAdapter
from research_os.repositories.markdown import MarkdownDocument
from research_os.services.drafts import apply_event_draft, write_new_file
from research_os.services.ingestion import (
    commit_new_source_capture,
    prepare_new_source_capture,
    process_source_asset,
)
from research_os.services.metrics import research_metrics
from research_os.services.reviews import apply_review
from research_os.services.validation import validate_repository
from research_os.services.workflow import (
    EventDraftSpec,
    ReportDraftSpec,
    incremental_reviewed_event_ids,
    prepare_company_update_proposal,
    prepare_reviewable_event_draft,
    prepare_synthesized_report,
)
from test_cli import run_cli


def add_thesis(root: Path) -> None:
    fixtures.write(
        root / "03_Theses" / "Active" / "THS-001-test.md",
        fixtures.thesis(),
    )


def add_company(root: Path) -> None:
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


def add_processed_source(root: Path) -> str:
    local = root / "input.html"
    local.write_text(
        "<html><p>Evidence line one</p><p>Evidence line two</p></html>",
        encoding="utf-8",
    )
    plan = prepare_new_source_capture(
        root,
        FileCaptureAdapter(
            local,
            captured_at="2026-07-30T10:00:00+00:00",
        ),
        title="Workflow Source",
        slug="workflow-source",
        created_at="2026-07-30",
        source_type="article",
        publisher="Publisher",
        published_at="2026-07-30",
        source_grade="A",
        companies=["COM-test"],
        technologies=["DEV-AGENT-FRAMEWORK"],
        products=[],
        tags=["EV-PRODUCT"],
        project_ids=["PRJ-001"],
    )
    commit_new_source_capture(root, plan)
    process_source_asset(root, "SRC-20260730-002")
    return "SRC-20260730-002"


def event_spec(source_id: str) -> EventDraftSpec:
    return EventDraftSpec.model_validate(
        {
            "title": "Anchored Event",
            "slug": "anchored-event",
            "created_at": "2026-07-30",
            "event_date": "2026-07-30",
            "source_ids": [source_id],
            "companies": ["COM-test"],
            "technologies": ["DEV-AGENT-FRAMEWORK"],
            "products": [],
            "facts": [
                {
                    "text": "The source directly states the first evidence line.",
                    "source_id": source_id,
                    "quote": "Evidence line one",
                }
            ],
            "inferences": ["This may indicate a workflow change."],
            "research_judgment": (
                "The signal is relevant but insufficient for an investment conclusion."
            ),
            "thesis_impacts": [
                {
                    "thesis_id": "THS-001",
                    "relationship": "contradicting",
                    "explanation": (
                        "The observed fact provides a direct counter-signal."
                    ),
                    "proposed_confidence_change": "-0.02, pending human review",
                }
            ],
            "alternative_explanations": [
                "The source may describe a limited pilot rather than broad adoption."
            ],
            "unknowns": ["Production usage and retention are unknown."],
            "follow_up_indicators": ["Track production accounts and retention."],
            "confidence": 0.6,
            "tags": ["EV-PRODUCT"],
            "project_ids": ["PRJ-001"],
        }
    )


class EventWorkflowTests(unittest.TestCase):
    def test_anchored_event_is_pending_valid_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            add_thesis(root)
            add_company(root)
            source_id = add_processed_source(root)
            spec = event_spec(source_id)

            relative, content = prepare_reviewable_event_draft(root, spec)
            self.assertIn("review_status: pending", content)
            self.assertIn("citation_anchors:", content)
            self.assertIn("Evidence line one", content)
            self.assertNotIn("TODO", content)
            apply_event_draft(
                root,
                relative,
                content,
                spec.source_ids,
                spec.created_at,
            )
            _, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )
            with self.assertRaisesRegex(ValueError, "duplicate generated Event"):
                prepare_reviewable_event_draft(root, spec)

    def test_anchor_validation_accepts_pdf_page_break_and_line_substring(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            add_thesis(root)
            add_company(root)
            source_id = add_processed_source(root)
            extracted = next(
                (root / "01_Inbox" / "_assets" / source_id).glob("*.extracted.txt")
            )
            extracted.write_text(
                "cover page\fPrefix Evidence line one suffix\nEvidence line two",
                encoding="utf-8",
            )
            spec = event_spec(source_id)
            relative, content = prepare_reviewable_event_draft(root, spec)
            self.assertIn("locator: L1", content)
            apply_event_draft(
                root,
                relative,
                content,
                spec.source_ids,
                spec.created_at,
            )
            _, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )

    def test_missing_quote_and_quality_sections_block_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            add_thesis(root)
            add_company(root)
            source_id = add_processed_source(root)
            payload = event_spec(source_id).model_dump()
            payload["facts"][0]["quote"] = "Not in the asset"
            with self.assertRaisesRegex(ValueError, "not present"):
                prepare_reviewable_event_draft(
                    root,
                    EventDraftSpec.model_validate(payload),
                )
            payload = event_spec(source_id).model_dump()
            payload["alternative_explanations"] = ["TODO"]
            with self.assertRaisesRegex(ValueError, "cannot contain TODO"):
                prepare_reviewable_event_draft(
                    root,
                    EventDraftSpec.model_validate(payload),
                )

    def test_tampered_anchor_is_a_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            add_thesis(root)
            add_company(root)
            source_id = add_processed_source(root)
            spec = event_spec(source_id)
            relative, content = prepare_reviewable_event_draft(root, spec)
            apply_event_draft(root, relative, content, [source_id], spec.created_at)
            event_path = root / relative
            document = MarkdownDocument.read(event_path)
            anchors = [dict(anchor) for anchor in document.metadata["citation_anchors"]]
            anchors[0]["quote"] = "tampered"
            document.set_metadata("citation_anchors", anchors)
            event_path.write_text(document.render(), encoding="utf-8")
            _, findings = validate_repository(root)
            self.assertTrue(
                {"EVT010", "EVT011"} <= {finding.code for finding in findings}
            )


class WorkflowCliTests(unittest.TestCase):
    def test_event_spec_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            add_thesis(root)
            add_company(root)
            source_id = add_processed_source(root)
            spec_path = root / "event-spec.json"
            spec_path.write_text(
                json.dumps(event_spec(source_id).model_dump(mode="json")),
                encoding="utf-8",
            )
            relative = (
                root / "04_Evidence" / "Events" / "EVT-20260730-002-anchored-event.md"
            )
            preview = run_cli(
                root,
                "workflow",
                "event",
                "--spec",
                str(spec_path),
            )
            self.assertEqual(0, preview.returncode, preview.stdout)
            self.assertIn("DRY-RUN", preview.stdout)
            self.assertFalse(relative.exists())
            applied = run_cli(
                root,
                "workflow",
                "event",
                "--spec",
                str(spec_path),
                "--apply",
            )
            self.assertEqual(0, applied.returncode, applied.stdout)
            self.assertTrue(relative.exists())


class ReportAndKnowledgeWorkflowTests(unittest.TestCase):
    def prepare_reviewed_event(self, root: Path) -> str:
        add_thesis(root)
        add_company(root)
        source_id = add_processed_source(root)
        spec = event_spec(source_id)
        relative, content = prepare_reviewable_event_draft(root, spec)
        apply_event_draft(root, relative, content, [source_id], spec.created_at)
        event_id = relative.name.split("-", 4)
        resolved_id = "-".join(event_id[:3])
        apply_review(
            root,
            target_ids=[resolved_id],
            decision="approve",
            reviewer="Researcher",
            reviewed_at="2026-07-30",
            notes="Facts and anchors checked.",
        )
        return resolved_id

    def test_report_preserves_contradiction_and_incremental_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            event_id = self.prepare_reviewed_event(root)
            baseline = {
                "as_of": "2026-07-29",
                "state": {"reviewed_event_ids": ["EVT-20260729-001"]},
            }
            objects, _ = validate_repository(root)
            self.assertEqual(
                [event_id],
                incremental_reviewed_event_ids(
                    [obj for obj in objects if obj.object_type == "event"],
                    baseline,
                ),
            )
            spec = ReportDraftSpec(
                title="Weekly Evidence Update v0.2",
                slug="weekly-evidence-update-v0-2",
                created_at="2026-07-30",
                period_start="2026-07-29",
                period_end="2026-07-30",
                evidence_ids=[],
                thesis_ids=["THS-001"],
                report_type="weekly",
                version="v0.2",
                tags=["EV-PRODUCT"],
                project_ids=["PRJ-001"],
            )
            relative, content = prepare_synthesized_report(
                root,
                spec,
                baseline=baseline,
            )
            self.assertIn(event_id, content)
            self.assertIn("## Contradicting Evidence", content)
            self.assertIn("| contradicting |", content)
            self.assertNotIn("TODO", content)
            write_new_file(root, relative, content)
            _, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )
            with self.assertRaisesRegex(ValueError, "duplicate generated Report"):
                prepare_synthesized_report(root, spec, baseline=baseline)

    def test_report_review_atomically_supersedes_prior_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            event_id = self.prepare_reviewed_event(root)
            prior_path = root / "06_Reports" / "Topics" / "RPT-20260729-prior-v0-1.md"
            fixtures.write(
                prior_path,
                fixtures.report()
                .replace("RPT-20260729-test", "RPT-20260729-prior-v0-1")
                .replace(
                    "evidence_ids: [EVT-20260729-001]",
                    f"evidence_ids: [{event_id}]",
                ),
            )
            spec = ReportDraftSpec(
                title="Versioned Report v0.2",
                slug="versioned-report-v0-2",
                created_at="2026-07-30",
                period_start="2026-07-29",
                period_end="2026-07-30",
                evidence_ids=[event_id],
                thesis_ids=["THS-001"],
                report_type="topic",
                version="v0.2",
                supersedes="RPT-20260729-prior-v0-1",
                tags=["EV-PRODUCT"],
                project_ids=["PRJ-001"],
            )
            relative, content = prepare_synthesized_report(root, spec)
            write_new_file(root, relative, content)
            new_id = "RPT-20260730-versioned-report-v0-2"
            apply_review(
                root,
                target_ids=[new_id],
                decision="approve",
                reviewer="Researcher",
                reviewed_at="2026-07-30",
                notes="Synthesis checked.",
            )
            prior = MarkdownDocument.read(prior_path)
            current = MarkdownDocument.read(root / relative)
            self.assertEqual("superseded", prior.metadata["status"])
            self.assertEqual(new_id, prior.metadata["superseded_by"])
            self.assertEqual("final", current.metadata["status"])
            _, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )

    def test_company_update_proposal_uses_only_reviewed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            event_id = self.prepare_reviewed_event(root)
            relative, content = prepare_company_update_proposal(
                root,
                company_id="COM-test",
                event_ids=[event_id],
                created_at="2026-07-30",
            )
            self.assertIn("status: pending", content)
            self.assertIn(event_id, content)
            self.assertFalse((root / relative).exists())
            metrics = research_metrics(root, "2026-07-30")
            self.assertIn(event_id, metrics["state"]["reviewed_event_ids"])
