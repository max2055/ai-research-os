"""Tests for the B-018 candidate queue service."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from research_os.services import candidate_db
from research_os.services.candidate_queue import (
    enrich_candidates,
    queue_rows,
    queue_show,
    render_candidate_detail,
    render_candidate_list,
    render_enrichment,
)

AUTOMATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMATION))

CHANNEL_TMPL = """---
id: {cid}
type: source_channel
title: "Test Channel"
created_at: 2026-08-06
updated_at: '2026-08-06'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "Test"
channel_type: rss
locator: "https://example.com/feed"
allow_hosts: [example.com]
publisher: "Test"
source_grade_proposal: B
entity_ids: [COM-test]
sector_ids: [SEG-test]
query: ""
schedule: "daily"
timezone: "Asia/Shanghai"
max_candidates_per_run: 5
rate_limit: ""
retention_days: 30
license_status: reviewed
robots_checked_at: "2026-08-06"
enabled: true
---

# Source Channel

## Channel

Test.
"""

COMPANY_TMPL = """---
id: COM-test
type: company
title: "Test Co"
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
sector_ids: [SEG-test]
source_channel_ids: []
evidence_ids: []
---

# Company

## Company role in the value chain

Test.

## Business model

Test.

## Competitive advantages

Test.

## Risks

Test.

## Related Thesis

Test.
"""

SECTOR_TMPL = """---
id: SEG-test
type: sector
schema_version: 2
title: "Test Sector"
created_at: 2026-08-06
updated_at: '2026-08-06'
project_ids: []
status: active
review_status: reviewed
tags: []
definition: "HBM, DRAM"
in_scope: [HBM, DRAM]
out_of_scope: []
value_chain_position: "upstream"
key_inputs: []
key_outputs: []
key_metrics: []
core_company_ids: []
tracked_company_ids: []
source_channel_ids: []
evidence_ids: []
---

# Sector

## Definition

HBM, DRAM

## Value chain position

upstream
"""


class CandidateQueueTests(unittest.TestCase):
    def _make_root(self, temp: str) -> Path:
        import test_research_os_core as fixtures

        root = fixtures.RepositoryValidationTests().make_root(temp)
        (root / "02_Knowledge" / "Companies").mkdir(parents=True, exist_ok=True)
        (root / "02_Knowledge" / "Sectors").mkdir(parents=True, exist_ok=True)
        (root / "02_Knowledge" / "Channels").mkdir(parents=True, exist_ok=True)
        (root / "02_Knowledge" / "Companies" / "COM-test.md").write_text(
            COMPANY_TMPL, encoding="utf-8"
        )
        (root / "02_Knowledge" / "Sectors" / "SEG-test.md").write_text(
            SECTOR_TMPL, encoding="utf-8"
        )
        (root / "02_Knowledge" / "Channels" / "CHN-test.md").write_text(
            CHANNEL_TMPL.format(cid="CHN-test"), encoding="utf-8"
        )
        return root

    def _insert(
        self,
        root: Path,
        titles: list[str],
        *,
        discovered_at: str = "2026-08-06T00:00:00Z",
        cluster_ids: list[str | None] | None = None,
    ) -> None:
        db_path = candidate_db.candidate_db_path(root)
        candidates = [
            {
                "candidate_id": f"CND-{index:04d}",
                "published_at_proposal": None,
                "title": title,
                "canonical_url": f"https://example.com/{index}",
                "publisher": "Test",
                "content_fingerprint": f"fp-{index}",
                "language": None,
                "duplicate_cluster_id": (
                    cluster_ids[index] if cluster_ids else None
                ),
            }
            for index, title in enumerate(titles)
        ]
        candidate_db.insert_candidates(
            db_path, candidates, "CHN-test", discovered_at
        )

    def _priority(self, root: Path, candidate_id: str) -> float | None:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            row = connection.execute(
                "SELECT priority_score FROM candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            return row[0] if row else None
        finally:
            connection.close()

    def test_enrich_writes_proposals_and_scores(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, ["Test Co HBM Production"])
            enriched = enrich_candidates(root, apply=True)
            self.assertEqual(1, len(enriched))
            self.assertEqual("matched", enriched[0]["entity_status"])
            self.assertEqual("COM-test", enriched[0]["entity_id"])
            self.assertEqual(1, enriched[0]["sector_count"])
            self.assertGreater(enriched[0]["priority_score"], 0)
            self.assertIsNotNone(self._priority(root, "CND-0000"))

    def test_enrich_dry_run_writes_nothing_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, ["Test Co HBM Production"])
            preview = enrich_candidates(root, apply=False)
            self.assertEqual(1, len(preview))
            self.assertIsNone(self._priority(root, "CND-0000"))
            self.assertIn("DRY-RUN", render_enrichment(preview, applied=False))
            enrich_candidates(root, apply=True)
            first = self._priority(root, "CND-0000")
            rerun = enrich_candidates(root, apply=True)
            self.assertEqual([], rerun)
            self.assertEqual(first, self._priority(root, "CND-0000"))

    def test_queue_sorts_by_priority_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(
                root,
                [
                    "Test Co HBM Production",
                    "Other Company DRAM Guidance",
                    "Unrelated Announcement",
                ],
            )
            enrich_candidates(root, apply=True)
            queue = queue_rows(root)
            self.assertEqual(3, len(queue))
            self.assertEqual("CND-0000", queue[0]["candidate_id"])
            self.assertGreaterEqual(
                queue[0]["priority_score"], queue[1]["priority_score"]
            )
            by_entity = queue_rows(root, entity_id="COM-test")
            self.assertEqual(["CND-0000"], [r["candidate_id"] for r in by_entity])
            by_tier = queue_rows(root, tier="core")
            self.assertEqual(["CND-0000"], [r["candidate_id"] for r in by_tier])
            by_min = queue_rows(root, min_priority=0.1)
            self.assertEqual(["CND-0000"], [r["candidate_id"] for r in by_min])
            self.assertIn("|", render_candidate_list(queue))

    def test_queue_show_detail_and_action_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, ["Test Co HBM Production"])
            enrich_candidates(root, apply=True)
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "INSERT INTO candidate_actions "
                    "(action_id, candidate_id, action, reason, actor, acted_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        "ACT-x",
                        "CND-0000",
                        "dismiss",
                        "test",
                        "max",
                        "2026-08-06T01:00:00Z",
                    ),
                )
                connection.commit()
            finally:
                connection.close()
            detail = queue_show(root, "CND-0000")
            self.assertIsNotNone(detail)
            assert detail is not None
            self.assertEqual("COM-test", detail["entity_proposals"]["entity_id"])
            self.assertEqual("new", detail["status"])
            self.assertTrue(detail["reason_codes"])
            self.assertEqual(1, len(detail["actions"]))
            self.assertIn("CND-0000", render_candidate_detail(detail))
            self.assertIsNone(queue_show(root, "CND-nope"))

    def test_cluster_variant_scores_below_representative(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(
                root,
                ["Test Co HBM Production", "Test Co HBM Production"],
                discovered_at="2026-08-06T00:00:00Z",
                cluster_ids=["CLU-x", "CLU-x"],
            )
            enrich_candidates(root, apply=True)
            representative = queue_show(root, "CND-0000")
            variant = queue_show(root, "CND-0001")
            assert representative is not None and variant is not None
            self.assertGreater(
                representative["priority_score"], variant["priority_score"]
            )
            self.assertIn(
                "duplication_penalty",
                " ".join(variant["reason_codes"]),
            )

    def test_queue_collapses_duplicate_clusters_to_lead(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(
                root,
                [
                    "Test Co HBM Production",
                    "Test Co HBM Production",
                    "Test Co HBM Production",
                    "Other Announcement",
                ],
                discovered_at="2026-08-06T00:00:00Z",
                cluster_ids=["CLU-x", "CLU-x", "CLU-x", None],
            )
            enrich_candidates(root, apply=True)
            collapsed = queue_rows(root)
            self.assertEqual(2, len(collapsed))
            by_id = {row["candidate_id"]: row for row in collapsed}
            self.assertEqual(2, by_id["CND-0000"]["dup_count"])
            self.assertTrue(by_id["CND-0000"]["is_representative"])
            self.assertEqual(0, by_id["CND-0003"]["dup_count"])
            self.assertTrue(by_id["CND-0003"]["is_representative"])
            expanded = queue_rows(root, show_dups=True)
            self.assertEqual(4, len(expanded))
            rep = {row["candidate_id"]: row["is_representative"] for row in expanded}
            self.assertTrue(rep["CND-0000"])
            self.assertFalse(rep["CND-0001"])
            self.assertFalse(rep["CND-0002"])
            self.assertTrue(rep["CND-0003"])

    def test_queue_marks_already_sourced_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            # the fixture repo already has SRC-20260729-001 with
            # canonical_url "https://example.com"; make a candidate repeat it.
            self._insert(root, ["Duplicate of existing source"])
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET canonical_url = ? "
                    "WHERE candidate_id = 'CND-0000'",
                    ("https://example.com",),
                )
                connection.commit()
            finally:
                connection.close()
            rows = queue_rows(root)
            self.assertEqual(1, len(rows))
            self.assertEqual("SRC-20260729-001", rows[0]["existing_source_id"])
            self.assertTrue(rows[0]["already_sourced"])


if __name__ == "__main__":
    unittest.main()
