from __future__ import annotations

import hashlib
import tempfile
import unittest
from email.message import Message
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

import test_research_os_core as fixtures
from research_os.adapters.discovery import (
    ArxivDiscoveryAdapter,
    GitHubReleaseDiscoveryAdapter,
    RSSDiscoveryAdapter,
    SECDiscoveryAdapter,
    candidates_json,
)
from research_os.adapters.file import FileCaptureAdapter
from research_os.adapters.url import (
    UrlCaptureAdapter,
    canonicalize_url,
    propose_html_published_date,
)
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import TransactionError
from research_os.services.extraction import extract_text
from research_os.services.ingestion import (
    capture_existing_source,
    commit_new_source_capture,
    confirm_published_date,
    prepare_new_source_capture,
    process_source_asset,
    verify_source_assets,
)
from research_os.services.validation import validate_repository


def prepare_capture(root: Path, local_file: Path):
    return prepare_new_source_capture(
        root,
        FileCaptureAdapter(
            local_file,
            captured_at="2026-07-30T10:00:00+00:00",
        ),
        title="Captured Source",
        slug="captured-source",
        created_at="2026-07-30",
        source_type="article",
        publisher="Publisher",
        published_at="unknown",
        source_grade="A",
        companies=[],
        technologies=[],
        products=[],
        tags=[],
        project_ids=["PRJ-001"],
    )


class AdapterTests(unittest.TestCase):
    def test_url_canonicalization_and_date_proposal(self) -> None:
        self.assertEqual(
            "https://example.com/article?a=1",
            canonicalize_url(
                "HTTPS://Example.COM:443/article?utm_source=x&a=1#section"
            ),
        )
        html = b"""<html><head>
<meta property="article:published_time" content="2026-07-28T10:00:00Z">
</head><body>Evidence</body></html>"""
        self.assertEqual("2026-07-28", propose_html_published_date(html))

    def test_url_adapter_uses_final_url_and_bounded_metadata(self) -> None:
        class Response:
            status = 200

            def __init__(self) -> None:
                self.headers = Message()
                self.headers["Content-Type"] = "text/html; charset=utf-8"
                self.headers["ETag"] = '"abc"'

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, size: int) -> bytes:
                del size
                return (
                    b'<meta name="datePublished" content="2026-07-28"><p>Evidence</p>'
                )

            def geturl(self) -> str:
                return "https://example.com/final?utm_source=redirect"

        with patch(
            "research_os.adapters.url.urlopen",
            return_value=Response(),
        ):
            captured = UrlCaptureAdapter(
                "https://example.com/start",
                captured_at="2026-07-30T10:00:00+00:00",
            ).capture()
        self.assertEqual("https://example.com/final", captured.final_locator)
        self.assertEqual("2026-07-28", captured.published_date_proposal)
        self.assertEqual('"abc"', captured.metadata["etag"])

    def test_url_adapter_rejects_oversized_response(self) -> None:
        class OversizedResponse:
            status = 200
            headers = Message()

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, size: int) -> bytes:
                return b"x" * size

            def geturl(self) -> str:
                return "https://example.com/large"

        with (
            patch(
                "research_os.adapters.url.urlopen",
                return_value=OversizedResponse(),
            ),
            self.assertRaisesRegex(ValueError, "exceeds"),
        ):
            UrlCaptureAdapter(
                "https://example.com/large",
                max_bytes=10,
            ).capture()


class DiscoveryAdapterTests(unittest.TestCase):
    @staticmethod
    def fetcher_for(payload: str):
        def fetcher(
            url: str,
            *,
            headers: dict[str, str],
            allowed_hosts: frozenset[str],
            max_bytes: int,
        ) -> str:
            del url, headers, allowed_hosts, max_bytes
            return payload

        return fetcher

    def test_rss_discovery_requires_allowlist_and_bounds_results(self) -> None:
        feed = """<rss><channel>
<item><title>One</title><link>https://official.example/one</link>
<guid>one</guid><pubDate>Tue, 28 Jul 2026 12:00:00 GMT</pubDate></item>
<item><title>Rejected</title><link>https://mirror.example/two</link></item>
</channel></rss>"""
        adapter = RSSDiscoveryAdapter(
            "https://official.example/feed.xml",
            allowed_hosts=frozenset({"official.example"}),
            publisher="Official",
            limit=1,
            fetcher=self.fetcher_for(feed),
        )
        candidates = adapter.discover()
        self.assertEqual(1, len(candidates))
        self.assertEqual("2026-07-28", candidates[0].published_at)
        self.assertNotIn("Rejected", candidates_json(candidates))
        with self.assertRaisesRegex(ValueError, "allowlist"):
            RSSDiscoveryAdapter(
                "https://unapproved.example/feed.xml",
                allowed_hosts=frozenset({"official.example"}),
                publisher="Official",
            )

    def test_github_release_discovery_records_repo_tag_and_date(self) -> None:
        payload = """[{
          "id": 42,
          "tag_name": "v1.2.3",
          "name": "Release 1.2.3",
          "html_url": "https://github.com/org/repo/releases/tag/v1.2.3",
          "published_at": "2026-07-28T12:00:00Z"
        }]"""
        candidate = GitHubReleaseDiscoveryAdapter(
            "org/repo",
            fetcher=self.fetcher_for(payload),
        ).discover()[0]
        self.assertEqual("github_release", candidate.adapter)
        self.assertEqual("v1.2.3", candidate.metadata["tag"])
        self.assertEqual("2026-07-28", candidate.published_at)

    def test_arxiv_discovery_uses_explicit_query_and_atom_results(self) -> None:
        atom = """<feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2607.12345</id><title>Agent Study</title>
<published>2026-07-27T00:00:00Z</published>
<link href="https://arxiv.org/abs/2607.12345" rel="alternate"/></entry>
</feed>"""
        candidate = ArxivDiscoveryAdapter(
            "all:agent",
            limit=2,
            fetcher=self.fetcher_for(atom),
        ).discover()[0]
        self.assertEqual("arxiv", candidate.adapter)
        self.assertEqual("Agent Study", candidate.title)
        with self.assertRaisesRegex(ValueError, "explicit"):
            ArxivDiscoveryAdapter(" ")

    def test_sec_discovery_filters_explicit_forms(self) -> None:
        payload = """{
          "name": "Example Corp",
          "filings": {"recent": {
            "accessionNumber": ["0000000001-26-000001", "0000000001-26-000002"],
            "filingDate": ["2026-07-28", "2026-07-27"],
            "form": ["10-Q", "8-K"],
            "primaryDocument": ["q2.htm", "event.htm"]
          }}
        }"""
        candidates = SECDiscoveryAdapter(
            "1",
            forms=frozenset({"10-Q"}),
            user_agent="Researcher contact@example.com",
            fetcher=self.fetcher_for(payload),
        ).discover()
        self.assertEqual(1, len(candidates))
        self.assertEqual("10-Q", candidates[0].metadata["form"])
        self.assertIn("/edgar/data/1/", candidates[0].url)

    def test_discovery_limit_has_global_hard_bound(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 100"):
            GitHubReleaseDiscoveryAdapter("org/repo", limit=101)


class ExtractionTests(unittest.TestCase):
    def test_html_fixture_extracts_visible_text(self) -> None:
        result = extract_text(
            b"<html><style>hidden</style><p>Visible evidence</p></html>",
            "text/html",
        )
        self.assertEqual("Visible evidence\n", result.text)
        self.assertEqual("stdlib-html-parser", result.method)

    def test_pdf_fixture_extracts_text(self) -> None:
        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=200)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 30 100 Td (PDF Evidence) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/MediaBox")] = ArrayObject(page["/MediaBox"])
        buffer = BytesIO()
        writer.write(buffer)
        result = extract_text(buffer.getvalue(), "application/pdf")
        self.assertIn("PDF Evidence", result.text)
        self.assertEqual("pypdf", result.method)


class IngestionWorkflowTests(unittest.TestCase):
    def test_local_capture_process_verify_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            local_file = root / "input.html"
            local_file.write_text(
                "<html><p>First evidence version.</p></html>",
                encoding="utf-8",
            )
            plan = prepare_capture(root, local_file)
            self.assertEqual(
                hashlib.sha256(local_file.read_bytes()).hexdigest(),
                plan.content_sha256,
            )
            changed = commit_new_source_capture(root, plan)
            self.assertEqual(3, len(changed))
            source_path = root / plan.source_path
            source = MarkdownDocument.read(source_path)
            self.assertEqual("captured", source.metadata["processing_status"])
            self.assertEqual(2, len(source.metadata["asset_paths"]))

            processed = process_source_asset(root, "SRC-20260730-002")
            self.assertEqual(3, len(processed))
            self.assertEqual([], process_source_asset(root, "SRC-20260730-002"))
            extracted = next(
                path for path in processed if path.name.endswith(".extracted.txt")
            )
            self.assertIn(
                "First evidence version.",
                extracted.read_text(encoding="utf-8"),
            )
            verification = {
                row.source_id: row.status for row in verify_source_assets(root)
            }
            self.assertEqual("ok", verification["SRC-20260730-002"])

            local_file.write_text(
                "<html><p>Second evidence version.</p></html>",
                encoding="utf-8",
            )
            versioned = capture_existing_source(
                root,
                "SRC-20260730-002",
                FileCaptureAdapter(
                    local_file,
                    captured_at="2026-07-31T10:00:00+00:00",
                ),
            )
            self.assertEqual(3, len(versioned))
            source = MarkdownDocument.read(source_path)
            self.assertEqual(6, len(source.metadata["asset_paths"]))
            self.assertTrue(all(path.exists() for path in changed[1:]))
            _, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )

    def test_pdf_extraction_failure_sets_explicit_failed_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            writer = PdfWriter()
            writer.add_blank_page(width=300, height=200)
            buffer = BytesIO()
            writer.write(buffer)
            local_file = root / "scan.pdf"
            local_file.write_bytes(buffer.getvalue())
            plan = prepare_capture(root, local_file)
            commit_new_source_capture(root, plan)

            with self.assertRaisesRegex(ValueError, "OCR"):
                process_source_asset(root, "SRC-20260730-002")

            source = MarkdownDocument.read(root / plan.source_path)
            self.assertEqual("failed", source.metadata["processing_status"])
            self.assertIn("OCR", source.metadata["processing_error"])
            _, findings = validate_repository(root)
            self.assertFalse(
                [finding for finding in findings if finding.level == "error"]
            )

    def test_duplicate_content_is_detected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            local_file = root / "input.txt"
            local_file.write_text("same evidence", encoding="utf-8")
            first = prepare_capture(root, local_file)
            commit_new_source_capture(root, first)
            with self.assertRaisesRegex(ValueError, "duplicate Source"):
                prepare_capture(root, local_file)

    def test_commit_conflict_leaves_no_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            local_file = root / "input.txt"
            local_file.write_text("evidence", encoding="utf-8")
            plan = prepare_capture(root, local_file)
            target = root / plan.source_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("conflict", encoding="utf-8")
            with self.assertRaises(TransactionError):
                commit_new_source_capture(root, plan)
            self.assertTrue(all(not (root / path).exists() for path in plan.assets))

    def test_publication_date_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = fixtures.RepositoryValidationTests().make_root(temp)
            source_path = root / "01_Inbox" / "Articles" / "SRC-20260729-001-source.md"
            document = MarkdownDocument.read(source_path)
            document.set_metadata(
                "published_date_proposal",
                "2026-07-28",
            )
            source_path.write_text(document.render(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "override required"):
                confirm_published_date(
                    root,
                    "SRC-20260729-001",
                    "2026-07-27",
                )
            confirm_published_date(
                root,
                "SRC-20260729-001",
                "2026-07-28",
            )
            confirmed = MarkdownDocument.read(source_path)
            self.assertEqual("2026-07-28", confirmed.metadata["published_at"])
            self.assertIsNone(confirmed.metadata["published_date_proposal"])
