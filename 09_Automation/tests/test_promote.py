"""Tests for the B-019 promote-to-Source transaction."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from research_os.adapters.file import FileCaptureAdapter
from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.candidate_queue import enrich_candidates
from research_os.services.promote import (
    AlreadyPromoted,
    commit_promote,
    prepare_promote,
    render_promote_plan,
)
from research_os.services.validation import validate_repository

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


class PromoteTests(unittest.TestCase):
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

    def _insert_and_enrich(self, root: Path) -> None:
        db_path = candidate_db.candidate_db_path(root)
        candidate_db.insert_candidates(
            db_path,
            [
                {
                    "candidate_id": "CND-0000",
                    "published_at_proposal": None,
                    "title": "Test Co HBM Production",
                    "canonical_url": "https://example.com/0",
                    "publisher": "Test",
                    "content_fingerprint": "fp-0",
                    "language": None,
                    "duplicate_cluster_id": None,
                }
            ],
            "CHN-test",
            "2026-08-06T00:00:00Z",
        )
        enrich_candidates(root, apply=True)

    def _html_file(self, root: Path) -> Path:
        path = root / "capture.html"
        path.write_text(
            "<html><head><title>Test Co HBM Production</title></head>"
            "<body><p>HBM production capacity announcement.</p></body></html>",
            encoding="utf-8",
        )
        return path

    def _status(self, root: Path) -> tuple[str, str | None]:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            row = connection.execute(
                "SELECT status, promoted_source_id FROM candidates "
                "WHERE candidate_id = 'CND-0000'"
            ).fetchone()
            return (row[0], row[1]) if row else ("missing", None)
        finally:
            connection.close()

    def test_promote_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert_and_enrich(root)
            plan = prepare_promote(
                root,
                "CND-0000",
                actor="max",
                adapter=FileCaptureAdapter(self._html_file(root)),
            )
            self.assertTrue(plan.source_id.startswith("SRC-"))
            self.assertEqual(["COM-test"], plan.companies)
            self.assertEqual("article", plan.source_type)
            self.assertEqual("B", plan.source_grade)
            self.assertFalse((root / plan.source_path).exists())
            self.assertEqual(("new", None), self._status(root))
            self.assertIn("Test Co HBM Production", render_promote_plan(plan))

    def test_promote_commits_source_and_links_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert_and_enrich(root)
            plan = prepare_promote(
                root,
                "CND-0000",
                actor="max",
                adapter=FileCaptureAdapter(self._html_file(root)),
            )
            result = commit_promote(root, plan)
            self.assertEqual(plan.source_id, result["source_id"])
            self.assertTrue((root / plan.source_path).is_file())
            self.assertEqual(("promoted", plan.source_id), self._status(root))
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                action = connection.execute(
                    "SELECT action, actor FROM candidate_actions "
                    "WHERE candidate_id = 'CND-0000' AND action = 'promote'"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(("promote", "max"), action)
            objects, findings = validate_repository(root)
            self.assertEqual(
                [],
                [item for item in findings if item.level == "error"],
            )
            self.assertIn(
                "COM-test",
                next(
                    obj.metadata["companies"]
                    for obj in objects
                    if obj.object_id == plan.source_id
                ),
            )

    def test_promote_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert_and_enrich(root)
            plan = prepare_promote(
                root,
                "CND-0000",
                actor="max",
                adapter=FileCaptureAdapter(self._html_file(root)),
            )
            commit_promote(root, plan)
            with self.assertRaises(AlreadyPromoted) as ctx:
                prepare_promote(root, "CND-0000", actor="max")
            self.assertEqual(plan.source_id, ctx.exception.source_id)

    def test_promote_refuses_dismissed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert_and_enrich(root)
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'dismissed' "
                    "WHERE candidate_id = 'CND-0000'"
                )
                connection.commit()
            finally:
                connection.close()
            with self.assertRaises(ValueError):
                prepare_promote(root, "CND-0000", actor="max")

    def test_promote_unknown_candidate_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert_and_enrich(root)
            with self.assertRaises(ValueError):
                prepare_promote(root, "CND-nope", actor="max")

    def test_promote_refuses_restricted_channel_and_invalid_sec_user_agent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert_and_enrich(root)
            channel = root / "02_Knowledge" / "Channels" / "CHN-test.md"
            original = channel.read_text(encoding="utf-8")
            channel.write_text(
                original.replace(
                    "license_status: reviewed", "license_status: restricted"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "license"):
                prepare_promote(
                    root,
                    "CND-0000",
                    actor="max",
                    adapter=FileCaptureAdapter(self._html_file(root)),
                )

            channel.write_text(
                original.replace("channel_type: rss", "channel_type: sec"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "contact User-Agent"):
                prepare_promote(
                    root,
                    "CND-0000",
                    actor="max",
                    user_agent="anonymous-client",
                    adapter=FileCaptureAdapter(self._html_file(root)),
                )

    def test_promote_changed_candidate_compensates_published_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert_and_enrich(root)
            plan = prepare_promote(
                root,
                "CND-0000",
                actor="max",
                adapter=FileCaptureAdapter(self._html_file(root)),
            )
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'dismissed' "
                    "WHERE candidate_id = 'CND-0000'"
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaisesRegex(TransactionError, "changed during promote"):
                commit_promote(root, plan)
            self.assertFalse((root / plan.source_path).exists())
            self.assertTrue(
                all(not (root / path).exists() for path in plan.capture.assets)
            )


if __name__ == "__main__":
    unittest.main()
