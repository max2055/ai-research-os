from __future__ import annotations

import tempfile
import unittest

import test_research_os_core as fixtures
from research_os.repositories.markdown import MarkdownDocument
from research_os.services.actions import (
    action_rows,
    close_action,
    prepare_action_draft,
)
from research_os.services.drafts import write_new_file
from research_os.services.indexing import (
    apply_indexes,
    index_drift,
    render_project_indexes,
)
from research_os.services.projects import (
    objects_for_project,
    prepare_project_draft,
)
from research_os.services.reviews import apply_review, review_queue
from research_os.services.validation import validate_repository


class ProjectServicesTests(unittest.TestCase):
    def test_create_second_project_and_scope_objects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            relative, content = prepare_project_draft(
                root,
                title="Second Project",
                slug="second-project",
                created_at="2026-07-30",
                owner="max",
                research_question="What should the second project study?",
                charter_path="05_Research/Projects/PRJ-002-charter.md",
                queue_path="05_Research/Projects/PRJ-002-queue.md",
                review_cadence="Weekly",
                next_review_date="2026-08-06",
                tags=[],
            )
            self.assertTrue(relative.name.startswith("PRJ-002-"))
            write_new_file(root, relative, content)
            objects, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )
            scoped = objects_for_project(objects, "PRJ-002")
            self.assertEqual(["PRJ-002"], [obj.object_id for obj in scoped])

            source_path = root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
            source = MarkdownDocument.read(source_path)
            source.set_metadata("project_ids", ["PRJ-001", "PRJ-002"])
            source_path.write_text(source.render(), encoding="utf-8")
            objects, _ = validate_repository(root)
            self.assertIn(
                "SRC-20260729-001",
                {obj.object_id for obj in objects_for_project(objects, "PRJ-002")},
            )
            self.assertEqual(
                1,
                sum(obj.object_id == "SRC-20260729-001" for obj in objects),
            )

    def test_project_indexes_are_independent_and_rebuildable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            objects, _ = validate_repository(root)
            rendered = render_project_indexes(objects, "PRJ-001")
            self.assertEqual(9, len(rendered))
            self.assertEqual(9, len(index_drift(root, rendered)))
            apply_indexes(root, rendered)
            self.assertEqual([], index_drift(root, rendered))


class ReviewServicesTests(unittest.TestCase):
    def test_queue_filters_and_review_apply_are_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            pending_sources = review_queue(
                root,
                project_id="PRJ-001",
                object_type="source",
            )
            self.assertEqual(
                ["SRC-20260729-001"],
                [obj.object_id for obj in pending_sources],
            )
            changed = apply_review(
                root,
                target_ids=["SRC-20260729-001"],
                decision="approve",
                reviewer="Researcher",
                reviewed_at="2026-07-30",
                notes="Provenance and summary checked.",
            )
            self.assertEqual(2, len(changed))
            review_path = next(path for path in changed if path.name.startswith("REV-"))
            source_path = next(path for path in changed if path.name.startswith("SRC-"))
            self.assertEqual(
                "reviewed",
                MarkdownDocument.read(source_path).metadata["review_status"],
            )
            review = MarkdownDocument.read(review_path)
            self.assertEqual("review", review.metadata["type"])
            self.assertEqual(
                ["SRC-20260729-001"],
                review.metadata["target_ids"],
            )
            _, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )

    def test_reject_requires_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            with self.assertRaises(ValueError):
                apply_review(
                    root,
                    target_ids=["SRC-20260729-001"],
                    decision="reject",
                    reviewer="Researcher",
                    reviewed_at="2026-07-30",
                    notes="",
                )
            self.assertFalse(
                list((root / "05_Research" / "Reviews" / "Decisions").glob("REV-*.md"))
            )

    def test_one_review_service_supports_all_core_object_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
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
            fixtures.write(
                root / "06_Reports" / "Topics" / "RPT-20260729-test.md",
                fixtures.report()
                .replace("status: final", "status: draft")
                .replace(
                    "review_status: reviewed",
                    "review_status: pending",
                ),
            )
            targets = [
                "SRC-20260729-001",
                "EVT-20260729-001",
                "THS-001",
                "COM-test",
                "RPT-20260729-test",
            ]
            changed = apply_review(
                root,
                target_ids=targets,
                decision="reject",
                reviewer="Researcher",
                reviewed_at="2026-07-30",
                notes="Insufficient support.",
            )
            self.assertEqual(6, len(changed))
            objects, findings = validate_repository(root)
            by_id = {obj.object_id: obj for obj in objects}
            self.assertTrue(
                all(
                    by_id[target].metadata["review_status"] == "rejected"
                    for target in targets
                )
            )
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )


class ActionServicesTests(unittest.TestCase):
    def test_create_query_overdue_and_close_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            relative, content = prepare_action_draft(
                root,
                title="Verify a claim",
                owner="max",
                created_at="2026-07-30",
                due_date="2026-08-01",
                success_evidence="A reviewed Source ID",
                project_ids=["PRJ-001"],
            )
            write_new_file(root, relative, content)
            overdue = action_rows(
                root,
                project_id="PRJ-001",
                overdue_as_of="2026-08-02",
            )
            self.assertEqual(1, len(overdue))
            close_action(
                root,
                overdue[0].object_id,
                closed_at="2026-08-02",
                success_evidence="SRC-20260729-001 reviewed",
            )
            self.assertEqual(
                [],
                action_rows(
                    root,
                    project_id="PRJ-001",
                    overdue_as_of="2026-08-03",
                ),
            )
