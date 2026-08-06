"""Tests for the B-020 candidate dismiss/expire/restore service."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from research_os.services import candidate_db
from research_os.services.triage import (
    dismiss_candidate,
    expire_candidates,
    purge_candidates,
    render_triage_result,
    restore_candidate,
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


class TriageTests(unittest.TestCase):
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
        candidate_id: str,
        *,
        discovered_at: str = "2026-08-06T00:00:00Z",
    ) -> None:
        candidate_db.insert_candidates(
            candidate_db.candidate_db_path(root),
            [
                {
                    "candidate_id": candidate_id,
                    "published_at_proposal": None,
                    "title": f"Title {candidate_id}",
                    "canonical_url": f"https://example.com/{candidate_id}",
                    "publisher": "Test",
                    "content_fingerprint": f"fp-{candidate_id}",
                    "language": None,
                    "duplicate_cluster_id": None,
                }
            ],
            "CHN-test",
            discovered_at,
        )

    def _status(self, root: Path, candidate_id: str) -> str:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            row = connection.execute(
                "SELECT status FROM candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            return str(row[0]) if row else "missing"
        finally:
            connection.close()

    def _actions(self, root: Path, candidate_id: str) -> list[tuple]:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            return connection.execute(
                "SELECT action, reason, actor FROM candidate_actions "
                "WHERE candidate_id = ? ORDER BY acted_at ASC",
                (candidate_id,),
            ).fetchall()
        finally:
            connection.close()

    def test_dismiss_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-0000")
            result = dismiss_candidate(
                root, "CND-0000", actor="max", reason="not in scope"
            )
            self.assertFalse(result["applied"])
            self.assertEqual("new", self._status(root, "CND-0000"))
            self.assertEqual([], self._actions(root, "CND-0000"))
            self.assertIn("DRY-RUN", render_triage_result(result))

    def test_dismiss_records_action_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-0000")
            result = dismiss_candidate(
                root, "CND-0000", actor="max", reason="not in scope",
                apply=True,
            )
            self.assertTrue(result["applied"])
            self.assertTrue(result["action_id"])
            self.assertEqual("dismissed", self._status(root, "CND-0000"))
            self.assertEqual(
                [("dismiss", "not in scope", "max")],
                self._actions(root, "CND-0000"),
            )

    def test_dismiss_refuses_promoted_and_missing_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-0000")
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'promoted', "
                    "promoted_source_id = 'SRC-20260806-001' "
                    "WHERE candidate_id = 'CND-0000'"
                )
                connection.commit()
            finally:
                connection.close()
            with self.assertRaises(ValueError):
                dismiss_candidate(
                    root, "CND-0000", actor="max", reason="x", apply=True
                )
            with self.assertRaises(ValueError):
                dismiss_candidate(root, "CND-0000", actor="max", reason="  ")

    def test_restore_records_action_and_actions_never_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-0000")
            dismiss_candidate(
                root, "CND-0000", actor="max", reason="noise", apply=True
            )
            result = restore_candidate(root, "CND-0000", actor="max", apply=True)
            self.assertTrue(result["applied"])
            self.assertEqual("new", self._status(root, "CND-0000"))
            actions = self._actions(root, "CND-0000")
            self.assertEqual(2, len(actions))
            self.assertEqual(
                [
                    ("dismiss", "noise", "max"),
                    (
                        "restore",
                        "restore from dismissed to review queue",
                        "max",
                    ),
                ],
                actions,
            )
            with self.assertRaises(ValueError):
                restore_candidate(root, "CND-0000", actor="max")

    def test_restore_refuses_promoted_and_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-0000")
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'expired' "
                    "WHERE candidate_id = 'CND-0000'"
                )
                connection.commit()
            finally:
                connection.close()
            result = restore_candidate(root, "CND-0000", actor="max", apply=True)
            self.assertEqual("new", result["status_after"])
            with self.assertRaises(ValueError):
                restore_candidate(root, "CND-zzz", actor="max")

    def test_expire_marks_only_candidates_past_retention(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-old", discovered_at="2026-06-01T00:00:00Z")
            self._insert(root, "CND-new", discovered_at="2026-08-05T00:00:00Z")
            result = expire_candidates(
                root, as_of="2026-08-06T00:00:00Z", apply=True
            )
            expired_ids = [i["candidate_id"] for i in result["expired"]]
            self.assertEqual(["CND-old"], expired_ids)
            self.assertEqual("expired", self._status(root, "CND-old"))
            self.assertEqual("new", self._status(root, "CND-new"))
            self.assertEqual(
                [("expire", "past retention (30 days)", "system")],
                self._actions(root, "CND-old"),
            )
            self.assertEqual([], self._actions(root, "CND-new"))

    def test_expire_dry_run_writes_nothing_and_respects_channel_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-old", discovered_at="2026-06-01T00:00:00Z")
            result = expire_candidates(
                root,
                channel_id="CHN-other",
                as_of="2026-08-06T00:00:00Z",
                apply=False,
            )
            self.assertEqual([], result["expired"])
            self.assertEqual("new", self._status(root, "CND-old"))

    def test_purge_deletes_terminal_candidates_but_keeps_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-0000")
            dismiss_candidate(
                root, "CND-0000", actor="max", reason="noise", apply=True
            )
            result = purge_candidates(root, apply=True)
            purged_ids = [i["candidate_id"] for i in result["purged"]]
            self.assertEqual(["CND-0000"], purged_ids)
            self.assertEqual("missing", self._status(root, "CND-0000"))
            self.assertEqual(
                [("dismiss", "noise", "max")],
                self._actions(root, "CND-0000"),
            )

    def test_purge_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._insert(root, "CND-0000")
            result = purge_candidates(root, apply=False)
            self.assertEqual([], result["purged"])
            self.assertEqual("new", self._status(root, "CND-0000"))


if __name__ == "__main__":
    unittest.main()
