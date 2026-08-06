"""Tests for the Channel Registry (B-006)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from research_os.services.channels import (
    channel_rows,
    render_channel_check,
    render_channel_list,
    set_channel_enabled,
)

AUTOMATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMATION))

import test_research_os_core as fixtures  # noqa: E402

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
channel_type: web_page
locator: "https://example.com"
allow_hosts: [example.com]
publisher: "Test"
source_grade_proposal: B
entity_ids: []
sector_ids: []
query: ""
schedule: "daily"
timezone: "Asia/Shanghai"
max_candidates_per_run: 20
rate_limit: ""
retention_days: 30
license_status: reviewed
license_notes: ""
robots_checked_at: "2026-08-06"
enabled: {enabled}
---

# Source Channel

## Channel

Test channel.
"""


class ChannelRegistryTests(unittest.TestCase):
    def _make_channel(self, root: Path, cid: str, review: str, enabled: bool) -> None:
        path = root / "02_Knowledge" / "Channels" / f"{cid}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            CHANNEL_TMPL.format(cid=cid, review=review, enabled=str(enabled).lower()),
            encoding="utf-8",
        )

    def _make_root(self, temp: str) -> Path:
        return fixtures.RepositoryValidationTests().make_root(temp)
    def test_list_reports_channels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test-a", "pending", False)
            self._make_channel(root, "CHN-test-b", "reviewed", True)
            rows = channel_rows(root)
            self.assertEqual(2, len(rows))
            rendered = render_channel_list(rows)
            self.assertIn("CHN-test-a", rendered)
            self.assertIn("CHN-test-b", rendered)

    def test_check_marks_only_reviewed_enabled_schedulable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test-a", "pending", True)
            self._make_channel(root, "CHN-test-b", "reviewed", True)
            rows = channel_rows(root)
            rendered = render_channel_check(rows)
            self.assertIn("| CHN-test-b | reviewed | Y | Y |", rendered)
            self.assertIn("| CHN-test-a | pending | Y | N |", rendered)

    def test_enable_refuses_unreviewed_channel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test-a", "pending", False)
            with self.assertRaises(ValueError):
                set_channel_enabled(root, "CHN-test-a", True)

    def test_enable_unknown_channel_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            with self.assertRaises(ValueError):
                set_channel_enabled(root, "CHN-nope", True)

    def test_enable_refuses_restricted_license_channel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            # reviewed but restricted license must not be schedulable (RP-6)
            path = root / "02_Knowledge" / "Channels" / "CHN-test-c.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                CHANNEL_TMPL.format(
                    cid="CHN-test-c", review="reviewed", enabled="false"
                ).replace("license_status: reviewed", "license_status: restricted"),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                set_channel_enabled(root, "CHN-test-c", True)

    def test_enable_reviewed_channel_returns_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test-b", "reviewed", False)
            path = set_channel_enabled(root, "CHN-test-b", True)
            # CLI writes the metadata change; verify the returned target path
            self.assertEqual("CHN-test-b.md", path.name)


if __name__ == "__main__":
    unittest.main()
