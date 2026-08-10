"""Tests for the B-007 discovery run service."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from xml.etree import ElementTree

from research_os.adapters.discovery import (
    ArxivDiscoveryAdapter,
    CompositeDiscoveryAdapter,
    GitHubReleaseDiscoveryAdapter,
    RSSDiscoveryAdapter,
    SECDiscoveryAdapter,
    SourceCandidate,
)
from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.discovery import (
    _acquire_channel_lock,
    _build_adapter,
    _github_repos_from_locator,
    due_channels,
    preflight_channel,
    run_discovery,
)
from research_os.services.jobs import run_job

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

RSS_PAYLOAD = b"""<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>item-1</id>
    <title>Retried item</title>
    <link href="https://example.com/items/1" />
    <published>2026-08-10T00:00:00Z</published>
  </entry>
</feed>"""


class _BytesResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> _BytesResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self.content[:size]


class _OutcomeOpener:
    def __init__(self, outcome: _BytesResponse | Exception) -> None:
        self.outcome = outcome

    def open(self, request: object, timeout: float) -> _BytesResponse:
        del request, timeout
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _http_error(status: int, secret: str = "not-sensitive") -> HTTPError:
    headers = Message()
    headers["Retry-After"] = "0"
    return HTTPError(
        f"https://example.com/feed?token={secret}",
        status,
        f"response body {secret}",
        headers,
        None,
    )


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

    def _fake_adapter(self, urls: list[str]):
        class _Fake:
            def discover(self) -> list[SourceCandidate]:
                return [
                    SourceCandidate(
                        adapter="test",
                        external_id=f"ext-{index}",
                        title=f"Title {index}",
                        url=url,
                        published_at=None,
                        publisher="Test",
                    )
                    for index, url in enumerate(urls)
                ]

        return _Fake()

    def _run_rss_with_outcomes(
        self,
        root: Path,
        outcomes: list[_BytesResponse | Exception],
        *,
        apply: bool = True,
    ) -> dict[str, object]:
        openers = iter(_OutcomeOpener(outcome) for outcome in outcomes)

        def build_opener(
            allowed_hosts: frozenset[str], *, max_bytes: int
        ) -> _OutcomeOpener:
            del allowed_hosts, max_bytes
            return next(openers)

        with patch(
            "research_os.adapters.discovery._build_discovery_opener",
            side_effect=build_opener,
        ):
            return run_discovery(root, "CHN-test", apply=apply)

    def test_retry_success_inserts_candidate_once_and_records_one_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")

            result = self._run_rss_with_outcomes(
                root,
                [_http_error(503), _BytesResponse(RSS_PAYLOAD)],
            )

            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                candidate_rows = connection.execute(
                    "SELECT candidate_id FROM candidates"
                ).fetchall()
                run_rows = connection.execute(
                    "SELECT run_id, status FROM discovery_runs"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(1, result["inserted"])
            self.assertEqual(1, len(candidate_rows))
            self.assertEqual(1, len(run_rows))
            self.assertEqual((result["run_id"], "succeeded"), run_rows[0])

    def test_successful_run_persists_retry_and_http_error_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")

            result = self._run_rss_with_outcomes(
                root,
                [_http_error(429), _BytesResponse(RSS_PAYLOAD)],
            )

            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                row = connection.execute(
                    "SELECT status, retries, http_errors, parse_errors "
                    "FROM discovery_runs WHERE run_id = ?",
                    (result["run_id"],),
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(("succeeded", 1, 1, 0), row)

    def test_post_fetch_insert_failure_finalizes_run_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            original = TransactionError("candidate insert failed")
            real_finish = candidate_db.finish_discovery_run
            with (
                patch(
                    "research_os.services.discovery._build_adapter",
                    return_value=self._fake_adapter(
                        ["https://fresh.example.com/insert-failure"]
                    ),
                ),
                patch(
                    "research_os.services.discovery.candidate_db.insert_candidates",
                    side_effect=original,
                ),
                patch(
                    "research_os.services.discovery.candidate_db.finish_discovery_run",
                    wraps=real_finish,
                ) as finish,
                self.assertRaises(ValueError) as caught,
            ):
                run_discovery(root, "CHN-test", apply=True)

            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                row = connection.execute(
                    "SELECT status, finished_at, parse_errors FROM discovery_runs"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual("failed", row[0])
            self.assertIsNotNone(row[1])
            self.assertEqual(0, row[2])
            self.assertIs(original, caught.exception.__cause__)
            finish.assert_called_once()

    def test_parse_failure_finalizes_run_and_increments_parse_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")

            with self.assertRaises(ValueError) as caught:
                self._run_rss_with_outcomes(
                    root,
                    [_BytesResponse(b"<feed><entry>")],
                )

            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                row = connection.execute(
                    "SELECT status, retries, http_errors, parse_errors "
                    "FROM discovery_runs"
                ).fetchone()
                running = connection.execute(
                    "SELECT COUNT(*) FROM discovery_runs WHERE status = 'running'"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(("failed", 0, 0, 1), row)
            self.assertEqual(0, running)
            self.assertIsInstance(caught.exception.__cause__, ElementTree.ParseError)

    def test_adapter_programming_failure_is_not_counted_as_parse_error(self) -> None:
        class _BuggyAdapter:
            def discover(self) -> tuple[SourceCandidate, ...]:
                raise RuntimeError("programming failure token=do-not-expose")

        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            with (
                patch(
                    "research_os.services.discovery._build_adapter",
                    return_value=_BuggyAdapter(),
                ),
                self.assertRaises(ValueError) as caught,
            ):
                run_discovery(root, "CHN-test", apply=True)

            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                row = connection.execute(
                    "SELECT status, parse_errors FROM discovery_runs"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(("failed", 0), row)
            self.assertIsInstance(caught.exception.__cause__, RuntimeError)
            self.assertNotIn("do-not-expose", str(caught.exception))

    def test_response_format_failure_increments_parse_errors(self) -> None:
        adapter = GitHubReleaseDiscoveryAdapter(
            "example/repository",
            fetcher=lambda url, **kwargs: "{}",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            with (
                patch(
                    "research_os.services.discovery._build_adapter",
                    return_value=adapter,
                ),
                self.assertRaises(ValueError),
            ):
                run_discovery(root, "CHN-test", apply=True)

            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                row = connection.execute(
                    "SELECT status, parse_errors FROM discovery_runs"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(("failed", 1), row)

    def test_finalization_failure_is_not_retried_and_keeps_original_cause(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            original = TransactionError("candidate insert failed")
            with (
                patch(
                    "research_os.services.discovery._build_adapter",
                    return_value=self._fake_adapter(
                        ["https://fresh.example.com/finalize-failure"]
                    ),
                ),
                patch(
                    "research_os.services.discovery.candidate_db.insert_candidates",
                    side_effect=original,
                ),
                patch(
                    "research_os.services.discovery.candidate_db.finish_discovery_run",
                    side_effect=TransactionError("terminal update failed"),
                ) as finish,
                self.assertRaises(ValueError) as caught,
            ):
                run_discovery(root, "CHN-test", apply=True)

            finish.assert_called_once()
            self.assertIs(original, caught.exception.__cause__)

    def test_successful_dry_run_writes_no_db_candidate_or_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            jobs_dir = root / "05_Research" / "Operations" / "Jobs"
            before_jobs = sorted(jobs_dir.glob("*.md"))

            result = self._run_rss_with_outcomes(
                root,
                [_BytesResponse(RSS_PAYLOAD)],
                apply=False,
            )

            self.assertEqual(1, result["candidate_count"])
            self.assertFalse(candidate_db.candidate_db_path(root).exists())
            self.assertEqual(before_jobs, sorted(jobs_dir.glob("*.md")))

    def test_inbound_skip_excludes_existing_source_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            # the fixture repo already has SRC-20260729-001 (canonical_url
            # "https://example.com"); rediscovering it must be skipped.
            with patch(
                "research_os.services.discovery._build_adapter",
                return_value=self._fake_adapter(
                    ["https://example.com", "https://fresh.example.com/1"]
                ),
            ):
                result = run_discovery(root, "CHN-test", apply=True)
            self.assertEqual(1, result["skipped"])
            self.assertEqual(1, result["inserted"])
            self.assertEqual(1, result["candidate_count"])
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                urls = {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT canonical_url FROM candidates"
                    )
                }
            finally:
                connection.close()
            self.assertNotIn("https://example.com", urls)
            self.assertIn("https://fresh.example.com/1", urls)

    def test_inbound_skip_excludes_promoted_candidate_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            db_path = candidate_db.candidate_db_path(root)
            candidate_db.insert_candidates(
                db_path,
                [
                    {
                        "candidate_id": "CND-prom",
                        "published_at_proposal": None,
                        "title": "Promoted already",
                        "canonical_url": "https://promoted.example.com",
                        "publisher": "Test",
                        "content_fingerprint": "fp-prom",
                        "language": None,
                        "duplicate_cluster_id": None,
                    }
                ],
                "CHN-test",
                "2026-08-07T00:00:00Z",
            )
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'promoted', "
                    "promoted_source_id = 'SRC-20260807-001' "
                    "WHERE candidate_id = 'CND-prom'"
                )
                connection.commit()
            finally:
                connection.close()
            with patch(
                "research_os.services.discovery._build_adapter",
                return_value=self._fake_adapter(
                    ["https://promoted.example.com", "https://fresh2.example.com"]
                ),
            ):
                result = run_discovery(root, "CHN-test", apply=True)
            self.assertEqual(1, result["skipped"])
            self.assertEqual(1, result["inserted"])
            connection = sqlite3.connect(db_path)
            try:
                urls = {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT canonical_url FROM candidates"
                    )
                }
            finally:
                connection.close()
            self.assertIn("https://fresh2.example.com", urls)

    def test_inbound_skip_dry_run_marks_already_sourced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            with patch(
                "research_os.services.discovery._build_adapter",
                return_value=self._fake_adapter(
                    ["https://example.com", "https://fresh.example.com/2"]
                ),
            ):
                result = run_discovery(root, "CHN-test", apply=False)
            self.assertEqual(1, result["skipped"])
            statuses = {
                candidate["url"]: candidate["already_sourced"]
                for candidate in result["candidates"]
            }
            self.assertTrue(statuses["https://example.com"])
            self.assertFalse(statuses["https://fresh.example.com/2"])
            self.assertFalse(candidate_db.candidate_db_path(root).exists())

    def test_job_message_reports_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            self._make_channel(root, "CHN-test")
            with patch(
                "research_os.services.discovery._build_adapter",
                return_value=self._fake_adapter(
                    ["https://example.com", "https://fresh.example.com/3"]
                ),
            ):
                result = run_job(root, "discover", target="CHN-test")
            self.assertIn("skipped (already sourced)", result.message)

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
            row = (
                sqlite3.connect(db_path)
                .execute("SELECT status FROM discovery_runs WHERE run_id = 'RUN-lock'")
                .fetchone()
            )
            self.assertEqual("running", row[0])

    def test_lock_reclaims_stale_running_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._make_root(temp)
            db_path = candidate_db.candidate_db_path(root)
            now = "2026-08-06T12:00:00Z"
            self._running_run(root, "2026-08-06T11:00:00Z")  # 1h old
            _acquire_channel_lock(db_path, "CHN-test", now)  # no raise
            row = (
                sqlite3.connect(db_path)
                .execute("SELECT status FROM discovery_runs WHERE run_id = 'RUN-lock'")
                .fetchone()
            )
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
            "https://github.com/a/b; https://github.com/c/d; https://github.com/a/b"
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


class AdapterFetcherCompatibilityTests(unittest.TestCase):
    @staticmethod
    def _payload_for(url: str) -> str:
        if "api.github.com" in url:
            return "[]"
        if "data.sec.gov" in url:
            return '{"filings": {"recent": {}}}'
        return "<feed/>"

    def test_all_adapters_accept_legacy_three_argument_fetcher(self) -> None:
        calls: list[str] = []

        def legacy_fetcher(
            url: str,
            *,
            headers: dict[str, str],
            max_bytes: int,
        ) -> str:
            del headers, max_bytes
            calls.append(url)
            return self._payload_for(url)

        rss_hosts = frozenset({"feeds.example", "articles.example"})
        adapters = (
            RSSDiscoveryAdapter(
                "https://feeds.example/rss",
                allowed_hosts=rss_hosts,
                publisher="Example",
                fetcher=legacy_fetcher,
            ),
            GitHubReleaseDiscoveryAdapter("org/repo", fetcher=legacy_fetcher),
            ArxivDiscoveryAdapter("all:agent", fetcher=legacy_fetcher),
            SECDiscoveryAdapter(
                "1",
                forms=frozenset({"10-K"}),
                user_agent="Researcher contact@example.com",
                fetcher=legacy_fetcher,
            ),
        )

        for adapter in adapters:
            adapter.discover()

        self.assertEqual(4, len(calls))

    def test_default_fetcher_binds_each_adapters_explicit_transport_hosts(self) -> None:
        calls: list[tuple[str, frozenset[str]]] = []

        def default_fetcher(
            url: str,
            *,
            headers: dict[str, str],
            allowed_hosts: frozenset[str],
            max_bytes: int,
        ) -> str:
            del headers, max_bytes
            calls.append((url, allowed_hosts))
            return self._payload_for(url)

        rss_hosts = frozenset({"feeds.example", "articles.example"})
        with (
            patch(
                "research_os.adapters.discovery.fetch_text",
                side_effect=default_fetcher,
            ),
            patch(
                "research_os.adapters.discovery._build_discovery_opener",
                side_effect=AssertionError("patched fetch_text was bypassed"),
            ) as build_opener,
        ):
            adapters = (
                RSSDiscoveryAdapter(
                    "https://feeds.example/rss",
                    allowed_hosts=rss_hosts,
                    publisher="Example",
                ),
                GitHubReleaseDiscoveryAdapter("org/repo"),
                ArxivDiscoveryAdapter("all:agent"),
                SECDiscoveryAdapter(
                    "1",
                    forms=frozenset({"10-K"}),
                    user_agent="Researcher contact@example.com",
                ),
            )

            for adapter in adapters:
                adapter.discover()

        self.assertEqual(
            [
                ("https://feeds.example/rss", rss_hosts),
                (
                    "https://api.github.com/repos/org/repo/releases?per_page=20",
                    frozenset({"api.github.com"}),
                ),
                (
                    "https://export.arxiv.org/api/query?search_query=all%3Aagent&"
                    "start=0&max_results=20&sortBy=submittedDate&"
                    "sortOrder=descending",
                    frozenset({"arxiv.org", "export.arxiv.org"}),
                ),
                (
                    "https://data.sec.gov/submissions/CIK0000000001.json",
                    frozenset({"data.sec.gov", "www.sec.gov"}),
                ),
            ],
            calls,
        )
        build_opener.assert_not_called()

    def test_legacy_fetcher_internal_type_error_propagates_without_retry(self) -> None:
        calls = 0

        def failing_fetcher(
            url: str,
            *,
            headers: dict[str, str],
            max_bytes: int,
        ) -> str:
            nonlocal calls
            del url, headers, max_bytes
            calls += 1
            raise TypeError("legacy fetcher body failed")

        adapter = RSSDiscoveryAdapter(
            "https://feeds.example/rss",
            allowed_hosts=frozenset({"feeds.example"}),
            publisher="Example",
            fetcher=failing_fetcher,
        )
        with self.assertRaisesRegex(TypeError, "legacy fetcher body failed"):
            adapter.discover()
        self.assertEqual(1, calls)


if __name__ == "__main__":
    unittest.main()
