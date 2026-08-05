from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

try:
    from research_os.domain.lifecycle import (
        InvalidTransition,
        ReportLifecycle,
        transition_review,
    )
    from research_os.repositories.transaction import (
        FileTransaction,
        TransactionError,
    )
    from research_os.schemas.common import ReviewStatus
    from research_os.services.drafts import apply_event_draft
    from research_os.services.indexing import (
        render_indexes as render_product_indexes,
    )
    from research_os.services.migration import (
        AddFieldMigration,
        MigrationEngine,
        SourceProvenanceMigration,
    )
    from research_os.services.status import render_status as render_product_status
    from research_os.services.validation import (
        validate_repository as validate_product_repository,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest(
        "install product dependencies to run product core tests"
    ) from exc


class LifecycleTests(unittest.TestCase):
    def test_review_lifecycle_accepts_explicit_transitions(self) -> None:
        self.assertEqual(
            ReviewStatus.REVIEWED,
            transition_review("pending", "reviewed"),
        )
        self.assertEqual(
            ReviewStatus.PENDING,
            transition_review("rejected", "pending"),
        )

    def test_review_lifecycle_rejects_skipped_or_reversed_transitions(self) -> None:
        with self.assertRaises(InvalidTransition):
            transition_review("pending", "superseded")
        with self.assertRaises(InvalidTransition):
            transition_review("reviewed", "pending")

    def test_report_publish_and_supersede_are_coupled(self) -> None:
        draft = ReportLifecycle("draft", ReviewStatus.PENDING)
        final = draft.publish()
        self.assertEqual(
            ReportLifecycle("final", ReviewStatus.REVIEWED),
            final,
        )
        self.assertEqual(
            ReportLifecycle("superseded", ReviewStatus.SUPERSEDED),
            final.supersede(),
        )


class ProductValidationTests(unittest.TestCase):
    def test_real_repository_matches_legacy_validation_result(self) -> None:
        from research_os.legacy_core import (
            validate_repository as validate_legacy_repository,
        )

        root = Path(__file__).resolve().parents[2]
        legacy_objects, legacy_findings = validate_legacy_repository(root)
        product_objects, product_findings = validate_product_repository(root)
        self.assertEqual(
            [obj.object_id for obj in legacy_objects],
            [obj.object_id for obj in product_objects],
        )
        self.assertEqual(
            [
                (item.level, item.code, item.path, item.message)
                for item in legacy_findings
            ],
            [
                (item.level, item.code, item.path, item.message)
                for item in product_findings
            ],
        )
        from research_os.legacy_core import render_indexes as render_legacy_indexes
        from research_os.legacy_core import render_status as render_legacy_status

        self.assertEqual(
            render_legacy_indexes(legacy_objects),
            render_product_indexes(product_objects),
        )
        self.assertEqual(
            render_legacy_status(root),
            render_product_status(root),
        )

    def test_draft_generators_match_legacy_golden_output(self) -> None:
        from research_os.legacy_core import (
            prepare_event_draft as legacy_event,
        )
        from research_os.legacy_core import (
            prepare_report_draft as legacy_report,
        )
        from research_os.legacy_core import (
            prepare_source_draft as legacy_source,
        )
        from research_os.services.drafts import (
            prepare_event_draft as product_event,
        )
        from research_os.services.drafts import (
            prepare_report_draft as product_report,
        )
        from research_os.services.drafts import (
            prepare_source_draft as product_source,
        )

        root = Path(__file__).resolve().parents[2]
        source_arguments = {
            "title": "Golden Source",
            "slug": "golden-source",
            "created_at": "2026-07-30",
            "source_type": "article",
            "publisher": "Publisher",
            "published_at": "2026-07-30",
            "url": "https://example.com/golden",
            "local_path": "",
            "source_grade": "A",
            "companies": [],
            "technologies": ["DEV-AGENT-FRAMEWORK"],
            "products": [],
            "tags": ["EV-PRODUCT"],
        }
        self.assertEqual(
            legacy_source(root, **source_arguments),
            product_source(root, **source_arguments),
        )
        event_arguments = {
            "title": "Golden Event",
            "slug": "golden-event",
            "created_at": "2026-07-30",
            "event_date": "2026-07-30",
            "source_ids": ["SRC-20260729-013"],
            "companies": [],
            "technologies": ["DEV-AGENT-FRAMEWORK"],
            "products": [],
            "thesis_links": ["THS-005"],
            "confidence": 0.5,
            "tags": ["EV-PRODUCT"],
        }
        self.assertEqual(
            legacy_event(root, **event_arguments),
            product_event(root, **event_arguments),
        )
        report_arguments = {
            "title": "Golden Report",
            "slug": "golden-report",
            "created_at": "2026-07-30",
            "period_start": "2026-07-01",
            "period_end": "2026-07-30",
            "thesis_ids": ["THS-005"],
            "evidence_ids": ["EVT-20260729-015"],
            "tags": ["EV-PRODUCT"],
        }
        self.assertEqual(
            legacy_report(root, **report_arguments),
            product_report(root, **report_arguments),
        )

    def test_metrics_match_legacy_golden_output(self) -> None:
        from research_os.legacy_core import (
            load_metrics_snapshot as legacy_load_snapshot,
        )
        from research_os.legacy_core import metrics_json as legacy_metrics_json
        from research_os.legacy_core import (
            render_metrics_comparison as legacy_comparison,
        )
        from research_os.legacy_core import (
            render_metrics_markdown as legacy_markdown,
        )
        from research_os.legacy_core import research_metrics as legacy_metrics
        from research_os.services.metrics import (
            load_metrics_snapshot as product_load_snapshot,
        )
        from research_os.services.metrics import (
            metrics_json as product_metrics_json,
        )
        from research_os.services.metrics import (
            render_metrics_comparison as product_comparison,
        )
        from research_os.services.metrics import (
            render_metrics_markdown as product_markdown,
        )
        from research_os.services.metrics import (
            research_metrics as product_metrics,
        )

        root = Path(__file__).resolve().parents[2]
        legacy = legacy_metrics(root, "2026-07-29")
        product = product_metrics(root, "2026-07-29")
        self.assertEqual(legacy, product)
        self.assertEqual(legacy_markdown(legacy), product_markdown(product))
        self.assertEqual(
            legacy_metrics_json(legacy),
            product_metrics_json(product),
        )

        snapshot = (
            root / "05_Research" / "Reviews" / "Snapshots" / "METRICS-20260729.json"
        )
        legacy_baseline = legacy_load_snapshot(snapshot)
        product_baseline = product_load_snapshot(snapshot)
        self.assertEqual(legacy_baseline, product_baseline)
        self.assertEqual(
            legacy_comparison(legacy_baseline, legacy),
            product_comparison(product_baseline, product),
        )

    def test_ontology_views_and_exports_match_legacy(self) -> None:
        import sqlite3

        from research_os.legacy_core import ontology_jsonl as legacy_jsonl
        from research_os.legacy_core import render_impact as legacy_impact
        from research_os.legacy_core import (
            render_scale_assessment as legacy_scale,
        )
        from research_os.legacy_core import (
            write_sqlite_export as legacy_sqlite,
        )
        from research_os.services.ontology import ontology_jsonl as product_jsonl
        from research_os.services.ontology import render_impact as product_impact
        from research_os.services.ontology import (
            render_scale_assessment as product_scale,
        )
        from research_os.services.ontology import (
            write_sqlite_export as product_sqlite,
        )

        root = Path(__file__).resolve().parents[2]
        self.assertEqual(legacy_jsonl(root), product_jsonl(root))
        self.assertEqual(
            legacy_impact(root, "THS-005", 2),
            product_impact(root, "THS-005", 2),
        )
        self.assertEqual(legacy_scale(root), product_scale(root))

        with tempfile.TemporaryDirectory() as temp:
            legacy_path = Path(temp) / "legacy.sqlite"
            product_path = Path(temp) / "product.sqlite"
            legacy_sqlite(root, legacy_path)
            product_sqlite(root, product_path)

            def rows(path: Path, table: str) -> list[tuple[object, ...]]:
                connection = sqlite3.connect(path)
                try:
                    return connection.execute(
                        f"SELECT * FROM {table} ORDER BY 1, 2"
                    ).fetchall()
                finally:
                    connection.close()

            for table in ("metadata", "nodes", "edges"):
                self.assertEqual(
                    rows(legacy_path, table),
                    rows(product_path, table),
                )


class TransactionTests(unittest.TestCase):
    def test_preflight_conflict_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = root / "existing.md"
            existing.write_text("original", encoding="utf-8")
            transaction = FileTransaction(root)
            transaction.stage_create(Path("new.md"), "new")
            transaction.stage_create(Path("existing.md"), "replacement")
            with self.assertRaises(TransactionError):
                transaction.commit()
            self.assertFalse((root / "new.md").exists())
            self.assertEqual("original", existing.read_text(encoding="utf-8"))

    def test_mid_commit_failure_rolls_back_all_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = root / "existing.md"
            existing.write_text("original", encoding="utf-8")
            calls = 0

            def fail_second(source: Path, target: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated write failure")
                os.replace(source, target)

            transaction = FileTransaction(root, replacer=fail_second)
            transaction.stage_replace(Path("existing.md"), "changed")
            transaction.stage_create(Path("new.md"), "new")
            with self.assertRaises(TransactionError):
                transaction.commit()
            self.assertEqual("original", existing.read_text(encoding="utf-8"))
            self.assertFalse((root / "new.md").exists())


class DraftServiceTests(unittest.TestCase):
    def test_event_and_source_processing_commit_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "01_Inbox" / "Articles" / "SRC-20260729-001-test.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                """---
id: SRC-20260729-001
type: source
title: Test
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: pending
source_type: article
publisher: Publisher
published_at: 2026-07-29
accessed_at: 2026-07-29
url: https://example.com
local_path:
source_grade: A
companies: []
technologies: []
products: []
canonical_url: https://example.com
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered
processing_error:
published_date_proposal:
tags: []
---
# Source

## Processing status

- [ ] Event extraction completed
- [ ] Entity links reviewed
- [ ] Thesis links reviewed
""",
                encoding="utf-8",
            )
            event = Path("04_Evidence/Events/EVT-20260730-001-test.md")
            apply_event_draft(
                root,
                event,
                "event content",
                ["SRC-20260729-001"],
                "2026-07-30",
            )
            self.assertEqual("event content", (root / event).read_text())
            self.assertIn(
                "- [x] Event extraction completed",
                source.read_text(encoding="utf-8"),
            )


class MigrationTests(unittest.TestCase):
    def test_plan_apply_idempotency_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "01_Inbox" / "Articles" / "SRC-20260729-001-test.md"
            source.parent.mkdir(parents=True)
            original = """---
id: SRC-20260729-001
type: source
title: Test
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: pending
tags: []
source_type: article
publisher: Publisher
authors: []
published_at: 2026-07-29
accessed_at: 2026-07-29
url: https://example.com
local_path:
source_grade: A
companies: []
technologies: []
products: []
---
# Body
"""
            source.write_text(original, encoding="utf-8")
            migration = AddFieldMigration(
                migration_id="MIG-TEST-001",
                field_name="schema_version",
                value=1,
            )
            engine = MigrationEngine(root)
            plan = engine.plan(migration)
            self.assertEqual(1, len(plan.changes))

            engine.apply(plan)
            self.assertIn(
                "schema_version: 1",
                source.read_text(encoding="utf-8"),
            )
            self.assertEqual(0, len(engine.plan(migration).changes))

            engine.rollback("MIG-TEST-001")
            self.assertEqual(original, source.read_text(encoding="utf-8"))

    def test_source_migration_writes_explicit_null_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "01_Inbox" / "Articles" / "SRC-20260729-001-test.md"
            source.parent.mkdir(parents=True)
            original = """---
id: SRC-20260729-001
type: source
url: https://example.com/article
---
# Human body
"""
            source.write_text(original, encoding="utf-8")
            engine = MigrationEngine(root)
            plan = engine.plan(SourceProvenanceMigration("MIG-TEST-SOURCE"))
            self.assertEqual(1, len(plan.changes))
            engine.apply(plan)
            migrated = source.read_text(encoding="utf-8")
            self.assertIn("content_sha256:", migrated)
            self.assertIn("fetched_at:", migrated)
            self.assertIn("published_date_proposal:", migrated)
            self.assertTrue(migrated.endswith("# Human body\n"))


if __name__ == "__main__":
    unittest.main()
