"""Tests for B-023 pipeline operational metrics."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from research_os.services import candidate_db
from research_os.services.candidate_queue import enrich_candidates
from research_os.services.metrics import pipeline_metrics, render_pipeline_metrics

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
title: "Memory & Storage"
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


class PipelineMetricsTests(unittest.TestCase):
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
            CHANNEL_TMPL, encoding="utf-8"
        )
        return root

    def _seed(self, root: Path) -> None:
        db_path = candidate_db.candidate_db_path(root)
        titles = [
            "Test Co HBM Production",  # CND-0000 -> promoted, core
            "Unrelated Announcement",  # CND-0001 -> dismissed
            "Test Co Capacity",  # CND-0002 -> new, core
            "LLM Paper",  # CND-0003 -> new
            "Memory Guidance",  # CND-0004 -> new
        ]
        candidate_db.insert_candidates(
            db_path,
            [
                {
                    "candidate_id": f"CND-{index:04d}",
                    "published_at_proposal": None,
                    "title": title,
                    "canonical_url": f"https://example.com/{index}",
                    "publisher": "Test",
                    "content_fingerprint": f"fp-{index}",
                    "language": None,
                    "duplicate_cluster_id": "CLU-x" if index < 2 else None,
                }
                for index, title in enumerate(titles)
            ],
            "CHN-test",
            f"{DATE}T00:00:00Z",
        )
        enrich_candidates(root, apply=True)
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                "UPDATE candidates SET status = 'promoted', "
                "promoted_source_id = 'SRC-20260806-001' "
                "WHERE candidate_id = 'CND-0000'"
            )
            connection.execute(
                "UPDATE candidates SET status = 'dismissed' "
                "WHERE candidate_id = 'CND-0001'"
            )
            connection.execute(
                "INSERT INTO candidate_actions (action_id, candidate_id, "
                "action, reason, actor, acted_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("CA-prom", "CND-0000", "promote", "promoted from candidate",
                 "max", f"{DATE}T02:00:00Z"),
            )
            connection.execute(
                "INSERT INTO candidate_actions (action_id, candidate_id, "
                "action, reason, actor, acted_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("CA-dis", "CND-0001", "dismiss", "noise",
                 "max", f"{DATE}T01:00:00Z"),
            )
            connection.execute(
                "INSERT INTO discovery_runs (run_id, channel_id, started_at, "
                "finished_at, candidate_count, http_errors, status) "
                "VALUES ('RUN-ok', 'CHN-test', ?, ?, 3, 0, 'succeeded')",
                (f"{DATE}T00:00:00Z", f"{DATE}T00:10:00Z"),
            )
            connection.execute(
                "INSERT INTO discovery_runs (run_id, channel_id, started_at, "
                "status) VALUES ('RUN-bad', 'CHN-test', ?, 'failed')",
                (f"{DATE}T03:00:00Z",),
            )
            connection.commit()
        finally:
            connection.close()

    def test_pipeline_metrics_rates_and_operational(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._seed(root)
            metrics = pipeline_metrics(root, DATE)
            self.assertEqual(5, metrics["discovered"]["total"])
            self.assertEqual(5, metrics["discovered"]["today"])
            self.assertEqual(0.2, metrics["duplicate"]["rate"])
            self.assertEqual(2, metrics["discovery"]["runs"])
            self.assertEqual(0.5, metrics["discovery"]["failure_rate"])
            self.assertEqual(600, metrics["discovery"]["median_latency_seconds"])
            self.assertEqual(1, metrics["triage"]["promoted"])
            self.assertEqual(1, metrics["triage"]["dismissed"])
            self.assertEqual(2, metrics["triage"]["total"])
            self.assertEqual(0.5, metrics["triage"]["promoted_rate"])
            self.assertEqual(0.5, metrics["triage"]["dismissed_rate"])
            self.assertIn(("noise", 1), metrics["triage"]["top_dismiss_reasons"])
            self.assertEqual(2.0, metrics["triage"]["median_conversion_hours"])
            self.assertGreaterEqual(1, metrics["coverage"]["core_matched"])
            self.assertIn("Pipeline Metrics", render_pipeline_metrics(metrics))
            self.assertIn("Triaged: 2", render_pipeline_metrics(metrics))

    def test_pipeline_metrics_counts_audit_after_purge(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            db_path = candidate_db.candidate_db_path(root)
            candidate_db.insert_candidates(
                db_path,
                [
                    {
                        "candidate_id": "CND-0000",
                        "published_at_proposal": None,
                        "title": "Purged dismiss",
                        "canonical_url": "https://example.com/a",
                        "publisher": "P",
                        "content_fingerprint": "fp-a",
                        "language": None,
                        "duplicate_cluster_id": None,
                    }
                ],
                "CHN-test",
                f"{DATE}T00:00:00Z",
            )
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'dismissed' "
                    "WHERE candidate_id = 'CND-0000'"
                )
                connection.execute(
                    "INSERT INTO candidate_actions (action_id, candidate_id, "
                    "action, reason, actor, acted_at) VALUES (?, ?, ?, ?, ?, ?)",
                    ("CA-dis", "CND-0000", "dismiss", "noise", "max",
                     f"{DATE}T01:00:00Z"),
                )
                connection.commit()
            finally:
                connection.close()
            # simulate the retention purge of a terminal dismissed row
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "DELETE FROM candidates WHERE candidate_id = 'CND-0000'"
                )
                connection.commit()
            finally:
                connection.close()
            metrics = pipeline_metrics(root, DATE)
            self.assertEqual(0, metrics["discovered"]["total"])
            self.assertEqual(0, metrics["triage"]["promoted"])
            self.assertEqual(1, metrics["triage"]["dismissed"])
            self.assertEqual(1, metrics["triage"]["total"])
            self.assertEqual(1.0, metrics["triage"]["dismissed_rate"])

    def test_pipeline_metrics_duplicate_rate_is_inbound_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            db_path = candidate_db.candidate_db_path(root)
            specs = [
                ("CND-0000", "2026-08-01T00:00:00Z", "CLU-y"),  # rep, outside window
                ("CND-0001", "2026-08-06T00:00:00Z", "CLU-y"),  # in-window non-rep
                ("CND-0002", "2026-08-08T00:00:00Z", "CLU-y"),  # in-window non-rep
                ("CND-0003", "2026-08-07T00:00:00Z", None),  # in-window singleton
            ]
            for candidate_id, discovered_at, cluster_id in specs:
                candidate_db.insert_candidates(
                    db_path,
                    [
                        {
                            "candidate_id": candidate_id,
                            "published_at_proposal": None,
                            "title": f"Title {candidate_id}",
                            "canonical_url": f"https://example.com/{candidate_id}",
                            "publisher": "P",
                            "content_fingerprint": f"fp-{candidate_id}",
                            "language": None,
                            "duplicate_cluster_id": cluster_id,
                        }
                    ],
                    "CHN-test",
                    discovered_at,
                )
            # window 2026-08-04..2026-08-10: 3 inbound, 2 are cluster non-reps
            duplicate = pipeline_metrics(root, "2026-08-10")["duplicate"]
            self.assertEqual(3, duplicate["inbound_total"])
            self.assertEqual(2, duplicate["inbound_dups"])
            self.assertEqual(round(2 / 3, 4), duplicate["rate"])
            # store: 4 candidates, CLU-y has 3 members -> 2 non-reps
            self.assertEqual(0.5, duplicate["store_rate"])
            # window with no inbound -> rate 0
            empty = pipeline_metrics(root, "2026-08-15")["duplicate"]
            self.assertEqual(0, empty["inbound_total"])
            self.assertEqual(0.0, empty["rate"])

    def test_pipeline_metrics_empty_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            metrics = pipeline_metrics(root, DATE)
            self.assertEqual(0, metrics["discovered"]["total"])
            self.assertEqual(0.0, metrics["duplicate"]["rate"])
            self.assertIsNone(metrics["discovery"]["median_latency_seconds"])
            self.assertIsNone(metrics["discovery"]["cost_estimate"])


if __name__ == "__main__":
    unittest.main()
