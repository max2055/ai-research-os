"""Tests for B-024 secret redaction (tokens/cookies never persisted)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from research_os.adapters.discovery import SourceCandidate
from research_os.adapters.url import canonicalize_url
from research_os.services import jobs as jobs_module
from research_os.services.discovery import _candidate_records
from research_os.services.jobs import run_job
from research_os.services.redaction import REDACTED, redact_secrets

AUTOMATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMATION))


class RedactionTests(unittest.TestCase):
    def test_canonicalize_url_drops_sensitive_params(self) -> None:
        self.assertEqual(
            "https://example.com/res?id=1",
            canonicalize_url(
                "https://example.com/res?token=SECRET&id=1&utm_source=x"
            ),
        )
        self.assertEqual(
            "https://example.com/res",
            canonicalize_url(
                "https://example.com/res?access_token=abc&apikey=xyz"
            ),
        )

    def test_canonicalize_url_keeps_normal_params(self) -> None:
        self.assertEqual(
            "https://example.com/res?page=2&q=memory",
            canonicalize_url("https://example.com/res?q=memory&page=2"),
        )

    def test_redact_secrets_scrubs_query_and_headers(self) -> None:
        text = (
            "GET /r?token=abc123&id=2 HTTP/1.1\n"
            "Authorization: Bearer tok-secret\n"
            "Cookie: session=0123456789abcdef\n"
            "Accept: text/html"
        )
        redacted = redact_secrets(text)
        self.assertNotIn("abc123", redacted)
        self.assertNotIn("tok-secret", redacted)
        self.assertNotIn("0123456789abcdef", redacted)
        self.assertIn(REDACTED, redacted)
        self.assertIn("Accept: text/html", redacted)

    def test_redact_secrets_keeps_benign_text(self) -> None:
        benign = "Q2 earnings up 20%; revenue guidance raised"
        self.assertEqual(benign, redact_secrets(benign))

    def test_candidate_records_redact_urls(self) -> None:
        records = _candidate_records(
            [
                SourceCandidate(
                    adapter="rss",
                    external_id="1",
                    title="A",
                    url="https://example.com/r?token=TOP-SECRET&page=2",
                    published_at=None,
                    publisher="P",
                )
            ]
        )
        self.assertEqual(
            f"https://example.com/r?token={REDACTED}&page=2",
            records[0]["canonical_url"],
        )

    def test_job_message_is_redacted(self) -> None:
        import test_m5_dashboard_jobs as m5

        def raise_with_token(*args: object, **kwargs: object) -> str:
            raise ValueError("failed at https://x.com/r?token=SECRET123")

        original = jobs_module._execute_job
        jobs_module._execute_job = raise_with_token
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = m5.prepared_root(temp)
                result = run_job(
                    root,
                    "validate",
                    started_at=datetime(2026, 8, 6, 10, 0, 0, tzinfo=UTC),
                )
                self.assertEqual("failed", result.status)
                self.assertNotIn("SECRET123", result.message)
                self.assertIn(REDACTED, result.message)
                record_text = Path(result.path).read_text(encoding="utf-8")
                self.assertNotIn("SECRET123", record_text)
                self.assertIn(REDACTED, record_text)
        finally:
            jobs_module._execute_job = original


if __name__ == "__main__":
    unittest.main()
