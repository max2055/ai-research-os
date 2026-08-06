"""Tests for the B-007 discovery run service."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from research_os.adapters.discovery import (
    CompositeDiscoveryAdapter,
    GitHubReleaseDiscoveryAdapter,
    SECDiscoveryAdapter,
)
from research_os.services import candidate_db
from research_os.services.discovery import (
    _acquire_channel_lock,
    _build_adapter,
    _github_repos_from_locator,
    due_channels,
    preflight_channel,
    run_discovery,
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
review_status: {review}
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
license_status: {license}
robots_checked_at: "2026-08-06"
enabled: {enabled}
---

# Source Channel

## Channel

Test.
"""


class DiscoveryServiceTests(unittest.TestCase):
    def _make_root(self, temp: str) -> Path:
        import test_research_os_core as fixtures

        return fixtures.RepositoryValidationTests().make_root(temp)

    def _make_channel(
        self,
        root: Path,
        cid: str,
        *,
        review: str = "reviewed",
        enabled: bool = True,
        license_status: str = "reviewed",
    ) -> None:
        path = root / "02_Knowledge" / "Channels" / f"{cid}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            CHANNEL_TMPL.format(
                cid=cid,
                review=review,
                enabled=str(enabled).lower(),
                license=license_status,
            ),
            encoding="utf-8",
        )

    def _channel_meta(self, **overrides: object) -> dict:
        meta = {
            "id": "CHN-a",
            "review_status": "reviewed",
            "enabled": True,
            "license_status": "reviewed",
            "max_candidates_per_run": 5,
        }
        meta.update(overrides)
        return meta

    def test_preflight_refuses_unreviewed(self) -> None:
        with self.assertRaises(ValueError):
            preflight_channel(self._channel_meta(review_status="pending"))

    def test_preflight_refuses_disabled(self) -> None:
        with self.assertRaises(ValueError):
            preflight_channel(self._channel_meta(enabled=False))

    def test_preflight_refuses_restricted(self) -> None:
        with self.assertRaises(ValueError):
            preflight_channel(self._channel_meta(license_status="restricted"))

    def test_dry_run_does_not_write_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            db_path = candidate_db.candidate_db_path(root)
            with self.assertRaises(ValueError):
                # network fetch fails in test env; run_discovery records a failed
                # run even on dry-run? check contract: apply=False should not write.
                run_discovery(root, "CHN-test", db_path=db_path, apply=False)
            # dry-run path: adapter.discover() raises -> run recorded as failed
            # only when apply; for dry-run we raise before writing. Either way the
            # db should be absent for a never-before-initialized root.
            self.assertFalse(db_path.exists())

    def test_disabled_channel_unknown_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            with self.assertRaises(ValueError):
                run_discovery(root, "CHN-nope")

    def _running_run(self, root: Path, started_at: str) -> None:
        candidate_db.apply_migrations(candidate_db.candidate_db_path(root))
        candidate_db.record_discovery_run(
            candidate_db.candidate_db_path(root),
            "RUN-lock",
            "CHN-test",
            started_at,
            status="running",
        )

    def test_lock_refuses_live_running_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            db_path = candidate_db.candidate_db_path(root)
            now = "2026-08-06T12:00:00Z"
            self._running_run(root, now)
            with self.assertRaises(ValueError):
                _acquire_channel_lock(db_path, "CHN-test", now)
            row = sqlite3.connect(db_path).execute(
                "SELECT status FROM discovery_runs WHERE run_id = 'RUN-lock'"
            ).fetchone()
            self.assertEqual("running", row[0])

    def test_lock_reclaims_stale_running_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            db_path = candidate_db.candidate_db_path(root)
            now = "2026-08-06T12:00:00Z"
            self._running_run(root, "2026-08-06T11:00:00Z")  # 1h old
            _acquire_channel_lock(db_path, "CHN-test", now)  # no raise
            row = sqlite3.connect(db_path).execute(
                "SELECT status FROM discovery_runs WHERE run_id = 'RUN-lock'"
            ).fetchone()
            self.assertEqual("failed", row[0])

    def test_due_channels_respects_schedule_and_last_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            candidate_db.apply_migrations(candidate_db.candidate_db_path(root))
            candidate_db.record_discovery_run(
                candidate_db.candidate_db_path(root),
                "RUN-a",
                "CHN-test",
                "2026-08-06T00:00:00Z",
                status="succeeded",
            )
            # never-run channel CHN-other stays due; CHN-test due only after 1 day
            self._make_channel(root, "CHN-other")
            self.assertEqual(
                ["CHN-other"],
                [
                    d["channel_id"]
                    for d in due_channels(root, as_of="2026-08-06T12:00:00Z")
                ],
            )
            self.assertEqual(
                ["CHN-other", "CHN-test"],
                [
                    d["channel_id"]
                    for d in due_channels(root, as_of="2026-08-07T00:00:01Z")
                ],
            )


def _github_release_payload() -> str:
    return json.dumps(
        [
            {
                "html_url": "https://github.com/a/b/releases/tag/v1.0",
                "tag_name": "v1.0",
                "name": "Release One",
                "id": 1,
                "published_at": "2026-01-01T00:00:00Z",
            }
        ]
    )


def _raising_fetcher(url: str, **kwargs: object) -> str:
    raise ValueError("fetch failed")


class MultiTargetDiscoveryTests(unittest.TestCase):
    def test_multi_repo_locator_parses_all_repos(self) -> None:
        locator = (
            "https://github.com/a/b; https://github.com/c/d; "
            "https://github.com/a/b"
        )
        self.assertEqual(["a/b", "c/d"], _github_repos_from_locator(locator))

    def test_composite_skips_failing_target(self) -> None:
        good = GitHubReleaseDiscoveryAdapter(
            "a/b",
            limit=10,
            fetcher=lambda url, **kw: _github_release_payload(),
        )
        bad = GitHubReleaseDiscoveryAdapter(
            "c/d",
            limit=10,
            fetcher=_raising_fetcher,
        )
        composite = CompositeDiscoveryAdapter([bad, good], limit=10)
        results = composite.discover()
        self.assertEqual(1, len(results))
        self.assertEqual("Release One", results[0].title)

    def test_composite_raises_when_all_fail(self) -> None:
        def _failing(repo: str) -> GitHubReleaseDiscoveryAdapter:
            return GitHubReleaseDiscoveryAdapter(
                repo, limit=10, fetcher=_raising_fetcher
            )

        composite = CompositeDiscoveryAdapter(
            [_failing("a/b"), _failing("c/d")],
            limit=10,
        )
        with self.assertRaises(ValueError):
            composite.discover()

    def test_build_adapter_multi_target_returns_composite(self) -> None:
        github = _build_adapter(
            {
                "channel_type": "github_release",
                "locator": "https://github.com/a/b; https://github.com/c/d",
                "max_candidates_per_run": 10,
            }
        )
        self.assertIsInstance(github, CompositeDiscoveryAdapter)
        sec = _build_adapter(
            {
                "channel_type": "sec",
                "locator": "https://www.sec.gov/cgi-bin/browse-edgar?cik=1045810,1046179",
                "query": "10-K,10-Q,20-F",
                "max_candidates_per_run": 10,
            }
        )
        self.assertIsInstance(sec, CompositeDiscoveryAdapter)

    def test_build_adapter_single_target_returns_plain_adapter(self) -> None:
        github = _build_adapter(
            {
                "channel_type": "github_release",
                "locator": "https://github.com/a/b",
                "max_candidates_per_run": 10,
            }
        )
        self.assertIsInstance(github, GitHubReleaseDiscoveryAdapter)
        sec = _build_adapter(
            {
                "channel_type": "sec",
                "locator": "https://www.sec.gov/cgi-bin/browse-edgar?cik=1045810",
                "query": "10-K,10-Q,20-F",
                "max_candidates_per_run": 10,
            }
        )
        self.assertIsInstance(sec, SECDiscoveryAdapter)


if __name__ == "__main__":
    unittest.main()
