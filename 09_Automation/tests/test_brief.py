"""Tests for the B-022 Daily Brief generator."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from research_os.services import candidate_db
from research_os.services.brief import (
    brief_path,
    daily_brief,
    render_daily_brief,
    write_daily_brief,
)
from research_os.services.candidate_queue import enrich_candidates
from research_os.services.jobs import run_job

AUTOMATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMATION))

DATE = "2026-07-29"

CHANNEL_TMPL = """---
id: {cid}
type: source_channel
title: "Channel {cid}"
created_at: 2026-07-29
updated_at: '2026-07-29'
schema_version: 2
project_ids: []
status: active
review_status: reviewed
tags: []
name: "Channel"
channel_type: {ctype}
locator: "https://example.com/feed"
allow_hosts: [example.com]
publisher: "Test"
source_grade_proposal: B
entity_ids: []
sector_ids: []
query: ""
schedule: "daily"
timezone: "Asia/Shanghai"
max_candidates_per_run: 5
rate_limit: ""
retention_days: 30
license_status: reviewed
robots_checked_at: "2026-07-29"
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
created_at: 2026-07-29
updated_at: '2026-07-29'
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
title: "Memory & Storage"
created_at: 2026-07-29
updated_at: '2026-07-29'
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


class BriefTests(unittest.TestCase):
    def _make_root(self, temp: str) -> Path:
        import test_research_os_core as fixtures

        root = fixtures.RepositoryValidationTests().make_root(
            temp, event_status="reviewed"
        )
        (root / "02_Knowledge" / "Companies").mkdir(parents=True, exist_ok=True)
        (root / "02_Knowledge" / "Sectors").mkdir(parents=True, exist_ok=True)
        (root / "02_Knowledge" / "Channels").mkdir(parents=True, exist_ok=True)
        (root / "02_Knowledge" / "Companies" / "COM-test.md").write_text(
            COMPANY_TMPL, encoding="utf-8"
        )
        (root / "02_Knowledge" / "Sectors" / "SEG-test.md").write_text(
            SECTOR_TMPL, encoding="utf-8"
        )
        self._make_channel(root, "CHN-test", ctype="rss")
        self._make_channel(root, "CHN-arxiv", ctype="arxiv")
        return root

    def _make_channel(
        self, root: Path, cid: str, *, ctype: str = "rss"
    ) -> None:
        (root / "02_Knowledge" / "Channels" / f"{cid}.md").write_text(
            CHANNEL_TMPL.format(cid=cid, ctype=ctype), encoding="utf-8"
        )

    def _seed_candidates(self, root: Path) -> None:
        db_path = candidate_db.candidate_db_path(root)
        candidate_db.insert_candidates(
            db_path,
            [
                {
                    "candidate_id": "CND-testco",
                    "published_at_proposal": None,
                    "title": "Test Co HBM Production",
                    "canonical_url": "https://example.com/hbm",
                    "publisher": "Test",
                    "content_fingerprint": "fp-hbm",
                    "language": None,
                    "duplicate_cluster_id": None,
                },
                {
                    "candidate_id": "CND-arxiv",
                    "published_at_proposal": None,
                    "title": "LLM Memory Paper",
                    "canonical_url": "https://arxiv.org/abs/2501.00001",
                    "publisher": "arXiv",
                    "content_fingerprint": "fp-arxiv",
                    "language": None,
                    "duplicate_cluster_id": None,
                },
                {
                    "candidate_id": "CND-neg",
                    "published_at_proposal": None,
                    "title": "Test Co Capacity Cut Warning",
                    "canonical_url": "https://example.com/cut",
                    "publisher": "Test",
                    "content_fingerprint": "fp-neg",
                    "language": None,
                    "duplicate_cluster_id": None,
                },
            ],
            "CHN-test",
            f"{DATE}T00:00:00Z",
        )
        connection = _sqlite(db_path)
        try:
            connection.execute(
                "UPDATE candidates SET channel_id = 'CHN-arxiv' "
                "WHERE candidate_id = 'CND-arxiv'"
            )
            connection.commit()
        finally:
            connection.close()
        enrich_candidates(root, apply=True)

    def _seed_failed_run(self, root: Path) -> None:
        candidate_db.record_discovery_run(
            candidate_db.candidate_db_path(root),
            "RUN-failed",
            "CHN-test",
            f"{DATE}T08:00:00Z",
            status="failed",
        )

    def test_daily_brief_partitions_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._seed_candidates(root)
            self._seed_failed_run(root)
            data = daily_brief(root, DATE)
            self.assertEqual(DATE, data["date"])
            self.assertEqual(
                ["CND-testco"],
                [c["candidate_id"] for c in data["high_priority"]],
            )
            self.assertEqual(
                ["CND-testco", "CND-neg"],
                [c["candidate_id"] for c in data["core_impact"]],
            )
            self.assertEqual(
                ["CND-neg"], [c["candidate_id"] for c in data["conflicts"]]
            )
            self.assertEqual(
                ["CND-arxiv"], [c["candidate_id"] for c in data["papers"]]
            )
            self.assertEqual(
                ["SRC-20260729-001"],
                [s["object_id"] for s in data["sources_today"]],
            )
            self.assertEqual(
                ["EVT-20260729-001"],
                [e["object_id"] for e in data["events_today"]],
            )
            self.assertEqual(
                ["RUN-failed"],
                [r["run_id"] for r in data["failed_runs"]],
            )
            self.assertIn("CHN-arxiv", data["never_run"])

    def test_render_marks_unreviewed_and_keeps_reviewed_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._seed_candidates(root)
            rendered = render_daily_brief(daily_brief(root, DATE))
            self.assertIn("unreviewed candidate", rendered)
            self.assertIn("Test Co HBM Production", rendered)
            self.assertIn("LLM Memory Paper", rendered)
            self.assertIn("SRC-20260729-001", rendered)
            self.assertIn("EVT-20260729-001", rendered)
            self.assertIn("## 3. 已提升正式 Source", rendered)
            self.assertIn("## 4. 新 reviewed Event", rendered)

    def test_write_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._seed_candidates(root)
            content = render_daily_brief(daily_brief(root, DATE))
            path = write_daily_brief(root, DATE, content)
            self.assertEqual(brief_path(root, DATE).resolve(), path)
            self.assertTrue(path.is_file())
            with self.assertRaises(FileExistsError):
                write_daily_brief(root, DATE, content)

    def test_jobs_daily_brief_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._seed_candidates(root)
            first = run_job(
                root,
                "daily-brief",
                as_of=DATE,
                started_at=datetime(2026, 7, 29, 10, 0, 0, tzinfo=UTC),
            )
            self.assertEqual("success", first.status)
            self.assertIn("daily brief created", first.message)
            second = run_job(
                root,
                "daily-brief",
                as_of=DATE,
                started_at=datetime(2026, 7, 29, 10, 0, 1, tzinfo=UTC),
            )
            self.assertEqual("success", second.status)
            self.assertIn("already exists", second.message)


def _sqlite(path: Path):
    import sqlite3

    return sqlite3.connect(path)


if __name__ == "__main__":
    unittest.main()
