"""Tests for the B-025 Pilot status service."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from research_os.services import candidate_db
from research_os.services.brief import write_daily_brief
from research_os.services.jobs import run_job
from research_os.services.pilot import pilot_status, render_pilot_status

AUTOMATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMATION))

DATE = "2026-08-06"

CHANNEL_TMPL = """---
id: CHN-test
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
entity_ids: []
sector_ids: []
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


class PilotStatusTests(unittest.TestCase):
    def _make_root(self, temp: str) -> Path:
        import test_research_os_core as fixtures

        root = fixtures.RepositoryValidationTests().make_root(temp)
        (root / "02_Knowledge" / "Channels").mkdir(parents=True, exist_ok=True)
        (root / "02_Knowledge" / "Channels" / "CHN-test.md").write_text(
            CHANNEL_TMPL, encoding="utf-8"
        )
        return root

    def test_pilot_status_reports_gate_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            db_path = candidate_db.candidate_db_path(root)
            candidate_db.insert_candidates(
                db_path,
                [
                    {
                        "candidate_id": "CND-prom",
                        "published_at_proposal": None,
                        "title": "A",
                        "canonical_url": "https://example.com/a",
                        "publisher": "P",
                        "content_fingerprint": "fp-a",
                        "language": None,
                        "duplicate_cluster_id": None,
                    },
                    {
                        "candidate_id": "CND-new",
                        "published_at_proposal": None,
                        "title": "B",
                        "canonical_url": "https://example.com/b",
                        "publisher": "P",
                        "content_fingerprint": "fp-b",
                        "language": None,
                        "duplicate_cluster_id": None,
                    },
                ],
                "CHN-test",
                f"{DATE}T00:00:00Z",
            )
            import sqlite3

            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'promoted', "
                    "promoted_source_id = 'SRC-20260806-001' "
                    "WHERE candidate_id = 'CND-prom'"
                )
                connection.execute(
                    "INSERT INTO candidate_actions (action_id, candidate_id, "
                    "action, reason, actor, acted_at) "
                    "VALUES ('CA-1', 'CND-prom', 'promote', 'x', "
                    "'max', '2026-08-06T01:00:00Z')"
                )
                connection.commit()
            finally:
                connection.close()
            write_daily_brief(root, DATE, "# Daily Brief\n")
            failed = run_job(
                root,
                "source-process",
                target="SRC-20990101-999",
                started_at=datetime(2026, 8, 6, 10, 0, 0, tzinfo=UTC),
            )
            self.assertEqual("failed", failed.status)

            status = pilot_status(root, since=DATE)
            self.assertEqual(DATE, status["since"])
            self.assertEqual(1, status["days_elapsed"])
            self.assertEqual(1, status["candidates"]["promoted"])
            self.assertEqual(0, status["candidates"]["dismissed"])
            self.assertEqual(2, status["candidates"]["discovered_since"])
            self.assertEqual(1, status["gate"]["channels"])
            self.assertIn(DATE, status["briefs"])
            self.assertEqual(1, status["jobs"]["failed"])
            self.assertEqual(1, len(status["job_failures"]))
            rendered = render_pilot_status(status)
            self.assertIn("Promoted: 1/20", rendered)
            self.assertIn("SRC-20990101-999", rendered)


if __name__ == "__main__":
    unittest.main()
