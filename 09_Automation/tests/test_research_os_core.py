from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

AUTOMATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMATION))

from research_os_core import (
    FrontMatterError,
    apply_indexes,
    index_drift,
    load_metrics_snapshot,
    mark_sources_extracted,
    metrics_snapshot_path,
    next_object_id,
    ontology_graph,
    ontology_jsonl,
    parse_front_matter,
    prepare_event_draft,
    prepare_report_draft,
    prepare_source_draft,
    render_impact,
    render_indexes,
    render_metrics_comparison,
    render_metrics_markdown,
    render_scale_assessment,
    render_status,
    render_universe_coverage,
    research_metrics,
    source_processing_state,
    universe_coverage,
    validate_repository,
    write_metrics_snapshot,
    write_new_file,
    write_sqlite_export,
)

TAXONOMY = """# Taxonomy

- `DEV-AGENT-FRAMEWORK`
- `EV-PRODUCT`
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def source(source_id: str = "SRC-20260729-001") -> str:
    return f"""---
id: {source_id}
type: source
title: Source
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
technologies: [DEV-AGENT-FRAMEWORK]
products: []
canonical_url: https://example.com
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered
processing_error:
published_date_proposal:
tags: [EV-PRODUCT]
---

# Source

## Processing status

- [x] Event extraction completed
- [ ] Entity links reviewed
- [ ] Thesis links reviewed
"""


def event(
    source_id: str = "SRC-20260729-001",
    status: str = "pending",
) -> str:
    return f"""---
id: EVT-20260729-001
type: event
title: Event
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: {status}
event_date: 2026-07-29
source_ids: [{source_id}]
companies: []
technologies: [DEV-AGENT-FRAMEWORK]
products: []
thesis_links: []
confidence: 0.5
tags: [EV-PRODUCT]
---

# Event

## Facts
## Inferences
## Research judgment
## Thesis impact
## Alternative explanations
## Unknowns
## Follow-up indicators
"""


def add_generated_event_with_asset(
    root: Path,
    *,
    asset_path: str = (
        "01_Inbox/_assets/SRC-20260729-001/source.html.extracted.txt"
    ),
    source_asset_path: str | None = None,
    quote: str = "Evidence line one",
    quote_sha256: str | None = None,
    write_asset: bool = False,
) -> None:
    source_asset_path = source_asset_path or asset_path
    source_path = root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
    source_text = source().replace(
        "asset_paths: []",
        f"asset_paths: [{source_asset_path}]",
    )
    write(source_path, source_text)

    anchor_hash = quote_sha256 or hashlib.sha256(quote.encode("utf-8")).hexdigest()
    event_text = event().replace(
        "confidence: 0.5\n",
        "confidence: 0.5\n"
        "generation_method: structured\n"
        "source_independence_groups:\n"
        "- - SRC-20260729-001\n"
        "citation_anchors:\n"
        "- fact_id: F1\n"
        "  source_id: SRC-20260729-001\n"
        f"  asset_path: {asset_path}\n"
        "  locator: L1\n"
        f"  quote: {quote}\n"
        f'  quote_sha256: "{anchor_hash}"\n',
    )
    event_text = event_text.replace(
        "## Facts\n",
        "## Facts\n\n- **F1** Evidence line one.\n",
    ).replace(
        "## Alternative explanations\n## Unknowns\n",
        "## Alternative explanations\n\n- A limited sample.\n\n"
        "## Unknowns\n\n- Broader adoption is unknown.\n",
    )
    write(
        root / "04_Evidence" / "Events" / "EVT-20260729-001-event.md",
        event_text,
    )
    if write_asset:
        write(root / asset_path, "Different line contents")


def report(event_status: str = "reviewed") -> str:
    return """---
id: RPT-20260729-test
type: report
title: Report
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: final
review_status: reviewed
report_type: topic
period_start: 2026-07-01
period_end: 2026-07-29
thesis_ids: []
evidence_ids: [EVT-20260729-001]
tags: [EV-PRODUCT]
---

# Report

## One-sentence conclusion
## Research question and scope
## Thesis assessment
## Contrarian view
## Falsification conditions
## Key indicators
## Investment implications
"""


def thesis(thesis_id: str = "THS-001") -> str:
    return f"""---
id: {thesis_id}
type: thesis
title: Thesis
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: pending
thesis_status: active
confidence: 0.25
supporting_evidence: []
contradicting_evidence: []
companies: []
technologies: []
tags: []
---

# Thesis

## Core judgment
## Reasoning chain
## Supporting evidence
## Contradicting evidence
## Alternative explanations
## Falsification conditions
## Unknowns
## Review history
"""


def project() -> str:
    return """---
id: PRJ-001
type: project
title: Test Project
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: active
owner: max
research_question: Test?
charter_path: charter.md
queue_path: queue.md
current_report_id:
review_cadence: Weekly
next_review_date: 2026-08-05
tags: []
---

# Project

## Research question
## Scope
## Success criteria
## Active Thesis
## Open actions
"""


class FrontMatterTests(unittest.TestCase):
    def test_parses_inline_and_block_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "object.md"
            write(
                path,
                """---
id: TEST
tags: [A, B]
items:
  - one
  - two
---
body
""",
            )
            obj = parse_front_matter(path)
            self.assertEqual(["A", "B"], obj.metadata["tags"])
            self.assertEqual(["one", "two"], obj.metadata["items"])

    def test_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "object.md"
            write(path, "---\nid: A\nid: B\n---\n")
            with self.assertRaises(FrontMatterError):
                parse_front_matter(path)


class RepositoryValidationTests(unittest.TestCase):
    def make_root(self, temp: str, *, event_status: str = "pending") -> Path:
        root = Path(temp)
        write(root / "00_System" / "Taxonomy.md", TAXONOMY)
        write(root / "05_Research" / "Projects" / "PRJ-001.md", project())
        write(
            root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md",
            source(),
        )
        write(
            root / "04_Evidence" / "Events" / "EVT-20260729-001-event.md",
            event(status=event_status),
        )
        return root

    def test_valid_minimal_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            _, findings = validate_repository(root)
            errors = [item for item in findings if item.level == "error"]
            self.assertEqual([], errors)

    def test_metadata_only_suppresses_only_unavailable_asset_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            add_generated_event_with_asset(root)

            _, strict_findings = validate_repository(root)
            self.assertIn("AST002", {item.code for item in strict_findings})
            self.assertIn("EVT009", {item.code for item in strict_findings})

            _, metadata_findings = validate_repository(root, mode="metadata-only")
            metadata_codes = {item.code for item in metadata_findings}
            self.assertNotIn("AST002", metadata_codes)
            self.assertNotIn("EVT009", metadata_codes)
            self.assertNotIn("EVT011", metadata_codes)
            self.assertEqual(
                [],
                [item for item in metadata_findings if item.level == "error"],
            )

    def test_metadata_only_keeps_metadata_and_path_safety_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            add_generated_event_with_asset(
                root,
                asset_path="01_Inbox/_assets/SRC-20260729-001/unowned.txt",
                source_asset_path="../outside.txt",
                quote_sha256="0" * 64,
            )

            _, findings = validate_repository(root, mode="metadata-only")
            codes = {item.code for item in findings}
            self.assertTrue({"AST001", "EVT008"} <= codes)

            add_generated_event_with_asset(
                root,
                quote_sha256="0" * 64,
                write_asset=True,
            )
            _, findings = validate_repository(root, mode="metadata-only")
            codes = {item.code for item in findings}
            self.assertIn("EVT010", codes)
            self.assertNotIn("EVT011", codes)

            event_path = root / "04_Evidence" / "Events" / "EVT-20260729-001-event.md"
            write(event_path, event(source_id="SRC-20260729-999"))
            _, findings = validate_repository(root, mode="metadata-only")
            self.assertIn("REF001", {item.code for item in findings})

    def test_missing_reference_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            path = root / "04_Evidence" / "Events" / "EVT-20260729-001-event.md"
            write(path, event(source_id="SRC-20260729-999"))
            _, findings = validate_repository(root)
            self.assertIn("REF001", {item.code for item in findings})

    def test_reviewed_report_rejects_pending_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp, event_status="pending")
            write(
                root / "06_Reports" / "Topics" / "RPT-20260729-test.md",
                report(),
            )
            _, findings = validate_repository(root)
            self.assertIn("REV001", {item.code for item in findings})

    def test_referenced_source_requires_completed_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            path = root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
            write(
                path,
                source().replace(
                    "- [x] Event extraction completed",
                    "- [ ] Event extraction completed",
                ),
            )
            _, findings = validate_repository(root)
            self.assertIn("SRC007", {item.code for item in findings})

            write(
                path,
                source().replace(
                    "- [x] Event extraction completed",
                    "- [X] Event extraction completed",
                ),
            )
            _, findings = validate_repository(root)
            self.assertNotIn("SRC007", {item.code for item in findings})

    def test_final_reviewed_report_rejects_pending_review_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp, event_status="reviewed")
            write(
                root / "06_Reports" / "Topics" / "RPT-20260729-test.md",
                report().replace(
                    "## Investment implications",
                    "结论仍待审核。\n\n## Investment implications",
                ),
            )
            _, findings = validate_repository(root)
            self.assertIn("RPT005", {item.code for item in findings})

    def test_unknown_taxonomy_code_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            path = root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
            write(path, source().replace("EV-PRODUCT", "EV-NOT-DEFINED"))
            _, findings = validate_repository(root)
            self.assertIn("TAX001", {item.code for item in findings})

    def test_missing_required_field_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            path = root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
            write(path, source().replace("publisher: Publisher\n", ""))
            _, findings = validate_repository(root)
            self.assertIn("SCH001", {item.code for item in findings})

    def test_duplicate_id_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            write(
                root / "01_Inbox" / "Articles" / "SRC-20260729-001-copy.md",
                source(),
            )
            _, findings = validate_repository(root)
            self.assertIn("ID004", {item.code for item in findings})

    def test_invalid_review_status_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            path = root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
            write(
                path, source().replace("review_status: pending", "review_status: yes")
            )
            _, findings = validate_repository(root)
            self.assertIn("SCH001", {item.code for item in findings})


class IndexTests(unittest.TestCase):
    def test_indexes_are_deterministic_and_detect_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            objects, findings = validate_repository(root)
            self.assertFalse([item for item in findings if item.level == "error"])
            first = render_indexes(objects)
            second = render_indexes(objects)
            self.assertEqual(first, second)
            self.assertEqual(9, len(index_drift(root, first)))
            apply_indexes(root, first)
            self.assertEqual([], index_drift(root, first))

    def test_index_contains_structured_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            objects, _ = validate_repository(root)
            rendered = render_indexes(objects)
            event_index = rendered[Path("08_Indexes/Event_Index.md")]
            self.assertIn("EVT-20260729-001", event_index)
            self.assertIn("pending", event_index)


class DraftTests(unittest.TestCase):
    def make_root(self, temp: str) -> Path:
        return RepositoryValidationTests().make_root(temp)

    def test_next_id_uses_global_type_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            objects, _ = validate_repository(root)
            self.assertEqual(
                "SRC-20260730-002",
                next_object_id(objects, "source", "2026-07-30"),
            )

    def test_source_draft_is_pending_and_not_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            relative, content = prepare_source_draft(
                root,
                title="New Source",
                slug="new-source",
                created_at="2026-07-30",
                source_type="article",
                publisher="Publisher",
                published_at="2026-07-30",
                url="https://example.com/new",
                local_path="",
                source_grade="A",
                companies=[],
                technologies=["DEV-AGENT-FRAMEWORK"],
                products=[],
                tags=["EV-PRODUCT"],
            )
            self.assertIn("review_status: pending", content)
            self.assertFalse((root / relative).exists())

    def test_source_draft_quotes_yaml_sensitive_scalars(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            relative, content = prepare_source_draft(
                root,
                title="Agentic AI: field evidence",
                slug="agentic-ai-field-evidence",
                created_at="2026-07-30",
                source_type="report",
                publisher="Research: Lab",
                published_at="2026-07-30",
                url="https://example.com/report",
                local_path="",
                source_grade="A",
                companies=[],
                technologies=["DEV-AGENT-FRAMEWORK"],
                products=[],
                tags=["EV-PRODUCT"],
            )
            write_new_file(root, relative, content)
            parsed = parse_front_matter(root / relative)
            self.assertEqual("Agentic AI: field evidence", parsed.metadata["title"])
            self.assertEqual("Research: Lab", parsed.metadata["publisher"])

    def test_event_draft_requires_existing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            with self.assertRaises(ValueError):
                prepare_event_draft(
                    root,
                    title="New Event",
                    slug="new-event",
                    created_at="2026-07-30",
                    event_date="2026-07-30",
                    source_ids=["SRC-20260729-999"],
                    companies=[],
                    technologies=["DEV-AGENT-FRAMEWORK"],
                    products=[],
                    thesis_links=[],
                    confidence=0.5,
                    tags=["EV-PRODUCT"],
                )

    def test_event_draft_with_thesis_link_validates_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            write(
                root / "03_Theses" / "Active" / "THS-001-thesis.md",
                thesis(),
            )
            relative, content = prepare_event_draft(
                root,
                title="Linked Event",
                slug="linked-event",
                created_at="2026-07-30",
                event_date="2026-07-30",
                source_ids=["SRC-20260729-001"],
                companies=[],
                technologies=["DEV-AGENT-FRAMEWORK"],
                products=[],
                thesis_links=["THS-001"],
                confidence=0.5,
                tags=["EV-PRODUCT"],
            )
            self.assertIn("| THS-001 | contextual |", content)
            write_new_file(root, relative, content)
            _, findings = validate_repository(root)
            self.assertEqual(
                [],
                [item for item in findings if item.level == "error"],
            )

    def test_report_draft_stays_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            relative, content = prepare_report_draft(
                root,
                title="New Report",
                slug="new-report",
                created_at="2026-07-30",
                period_start="2026-07-01",
                period_end="2026-07-30",
                thesis_ids=[],
                evidence_ids=["EVT-20260729-001"],
                tags=["EV-PRODUCT"],
            )
            self.assertEqual(
                Path("06_Reports/Topics/RPT-20260730-new-report.md"), relative
            )
            self.assertIn("status: draft", content)
            self.assertIn("review_status: pending", content)

    def test_write_new_file_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            relative = Path("output.md")
            write_new_file(root, relative, "first")
            with self.assertRaises(FileExistsError):
                write_new_file(root, relative, "second")
            self.assertEqual("first", (root / relative).read_text(encoding="utf-8"))


class StatusTests(unittest.TestCase):
    def test_status_reports_queue_coverage_and_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            status = render_status(root)
            self.assertIn("| source | 1 | 1 | 0 | 0 | 0 |", status)
            self.assertIn("SRC-20260729-001", status)
            self.assertIn("| Processing |", status)
            self.assertEqual(
                "partial (1/3)",
                source_processing_state(
                    parse_front_matter(
                        root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
                    )
                ),
            )
            self.assertIn("Validation errors: 0", status)
            self.assertIn("Index drift files: 9", status)


class EndToEndTests(unittest.TestCase):
    def test_source_event_report_index_validation_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)

            source_path, source_content = prepare_source_draft(
                root,
                title="Pipeline Source",
                slug="pipeline-source",
                created_at="2026-07-30",
                source_type="article",
                publisher="Publisher",
                published_at="2026-07-30",
                url="https://example.com/pipeline",
                local_path="",
                source_grade="A",
                companies=[],
                technologies=["DEV-AGENT-FRAMEWORK"],
                products=[],
                tags=["EV-PRODUCT"],
            )
            write_new_file(root, source_path, source_content)
            source_id = parse_front_matter(root / source_path).object_id

            event_path, event_content = prepare_event_draft(
                root,
                title="Pipeline Event",
                slug="pipeline-event",
                created_at="2026-07-30",
                event_date="2026-07-30",
                source_ids=[source_id],
                companies=[],
                technologies=["DEV-AGENT-FRAMEWORK"],
                products=[],
                thesis_links=[],
                confidence=0.5,
                tags=["EV-PRODUCT"],
            )
            write_new_file(root, event_path, event_content)
            mark_sources_extracted(root, [source_id], "2026-07-30")
            event_id = parse_front_matter(root / event_path).object_id

            report_path, report_content = prepare_report_draft(
                root,
                title="Pipeline Report",
                slug="pipeline-report",
                created_at="2026-07-30",
                period_start="2026-07-01",
                period_end="2026-07-30",
                thesis_ids=[],
                evidence_ids=[event_id],
                tags=["EV-PRODUCT"],
            )
            write_new_file(root, report_path, report_content)

            objects, findings = validate_repository(root)
            self.assertEqual([], [item for item in findings if item.level == "error"])
            rendered = render_indexes(objects)
            apply_indexes(root, rendered)
            self.assertEqual([], index_drift(root, rendered))


class MetricsTests(unittest.TestCase):
    def test_metrics_calculate_conversion_and_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            metrics = research_metrics(root, "2026-07-30")
            self.assertEqual(1.0, metrics["source_quality"]["conversion_rate"])
            self.assertEqual(2, metrics["review_queue_total"])
            self.assertEqual(0, metrics["system_health"]["validation_errors"])
            rendered = render_metrics_markdown(metrics)
            self.assertIn("Source→Event conversion: 1/1 (100.0%)", rendered)

    def test_snapshot_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            metrics = research_metrics(root, "2026-07-30")
            path = write_metrics_snapshot(root, metrics)
            self.assertEqual(
                (root / metrics_snapshot_path("2026-07-30")).resolve(),
                path,
            )
            with self.assertRaises(FileExistsError):
                write_metrics_snapshot(root, metrics)

    def test_snapshot_comparison_reports_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            baseline = research_metrics(root, "2026-07-30")
            path = write_metrics_snapshot(root, baseline)
            loaded = load_metrics_snapshot(path)
            current = json.loads(json.dumps(loaded))
            current["as_of"] = "2026-08-01"
            current["object_counts"]["event"]["total"] += 1
            comparison = render_metrics_comparison(loaded, current)
            self.assertIn("2026-07-30 → 2026-08-01", comparison)
            self.assertIn("| event.total | 1 | 2 | +1 |", comparison)

    def test_universe_coverage_reports_completeness(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            write(
                root / "02_Knowledge" / "Companies" / "COM-test.md",
                """---
id: COM-test
type: company
title: Test Co
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
aliases: []
legal_name: "Test Company, Inc."
company_stage: public
headquarters: "Testville, USA"
region_primary: REG-us
coverage_tier: core
sector_ids: []
source_channel_ids: []
evidence_ids: []
---

# Company

## Company role in the value chain
## Business model
## Competitive advantages
## Risks
## Related Thesis
""",
            )
            coverage = universe_coverage(root)
            self.assertEqual(1, coverage["total_companies"])
            # the fixture company has legal_name/HQ/region
            self.assertEqual(1, coverage["identity_completeness"]["complete"])
            # no reviewed event names it, no assertion endpoint -> 0
            self.assertEqual(0, coverage["source_completeness"]["complete"])
            self.assertEqual(
                0, coverage["relationship_completeness"]["complete"]
            )
            rendered = render_universe_coverage(coverage)
            self.assertIn("Total companies: 1", rendered)
            self.assertIn("| Identity (legal_name + HQ + region)", rendered)


class OntologyTests(unittest.TestCase):
    def test_ontology_edges_resolve_and_jsonl_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            nodes, edges = ontology_graph(root)
            node_ids = {node["id"] for node in nodes}
            self.assertTrue(edges)
            self.assertTrue(
                all(
                    edge["source"] in node_ids and edge["target"] in node_ids
                    for edge in edges
                )
            )
            self.assertEqual(ontology_jsonl(root), ontology_jsonl(root))

    def test_sqlite_is_rebuildable_derived_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            output = root / "derived" / "research.sqlite"
            write_sqlite_export(root, output)
            connection = sqlite3.connect(output)
            try:
                node_count = connection.execute(
                    "SELECT COUNT(*) FROM nodes"
                ).fetchone()[0]
                edge_count = connection.execute(
                    "SELECT COUNT(*) FROM edges"
                ).fetchone()[0]
                source_of_truth = connection.execute(
                    "SELECT value FROM metadata WHERE key='source_of_truth'"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(3, node_count)
            self.assertEqual(3, edge_count)
            self.assertEqual("Markdown", source_of_truth)
            with self.assertRaises(FileExistsError):
                write_sqlite_export(root, output)

    def test_impact_and_scale_views(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            impact = render_impact(root, "EVT-20260729-001", depth=1)
            self.assertIn("SUPPORTS_EVENT", impact)
            scale = render_scale_assessment(root)
            self.assertIn("Recommended mode: **File-first**", scale)
            self.assertIn("Events: 1/500 trigger", scale)


if __name__ == "__main__":
    unittest.main()
