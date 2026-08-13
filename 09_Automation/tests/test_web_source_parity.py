from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

import test_research_os_core as fixtures
from research_os.adapters.base import CapturedAsset
from research_os.repositories.markdown import MarkdownDocument
from research_os.services.mutation_gateway import MutationGateway
from research_os.services.web_repository_mutations import (
    commit_repository_mutation,
    repository_target_version,
)
from research_os.services.web_source_workflows import (
    UploadedCaptureAdapter,
    capture_adapter,
    prepare_source_create,
    prepare_source_date_confirmation,
    prepare_source_process,
)
from research_os.ui.app import create_app


class CountingAdapter:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls = 0

    def capture(self) -> CapturedAsset:
        self.calls += 1
        return CapturedAsset(
            content=self.content,
            media_type="text/html",
            original_locator="https://example.com/article",
            final_locator="https://example.com/article",
            captured_at="2026-08-13T00:00:00+00:00",
            published_date_proposal="2026-08-12",
        )


class SourceWebWorkflowTests(unittest.TestCase):
    def _root(self, temp: str) -> Path:
        return fixtures.RepositoryValidationTests().make_root(temp)

    def _fields(self) -> dict[str, str]:
        return {
            "title": "Web Captured Source",
            "slug": "web-captured-source",
            "created_at": "2026-08-13",
            "source_type": "article",
            "publisher": "Example Publisher",
            "published_at": "unknown",
            "source_grade": "B",
            "companies": "",
            "technologies": "",
            "products": "",
            "tags": "",
            "project_ids": "PRJ-001",
            "allow_duplicate": "false",
        }

    def _preview(self, prepared):
        return MutationGateway(
            b"s" * 64,
            now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
        ).issue(prepared.preview_input).preview

    def test_new_source_preview_captures_once_and_freezes_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            adapter = CountingAdapter(b"<p>Traceable fact.</p>")
            before = {path for path in root.rglob("*") if path.is_file()}

            prepared = prepare_source_create(
                root, actor="max", adapter=adapter, fields=self._fields()
            )
            preview = self._preview(prepared)
            result = commit_repository_mutation(root, preview, prepared.plan)

            self.assertEqual(1, adapter.calls)
            self.assertEqual("source.create", preview.operation)
            self.assertEqual("SRC-20260813-002", preview.target_id)
            serialized = json.dumps(preview.normalized_input)
            self.assertNotIn("Traceable fact", serialized)
            self.assertEqual("pending", preview.summary["status_after"])
            source_path = next(
                path
                for path in root.rglob("SRC-20260813-002*.md")
                if path.is_file()
            )
            source = MarkdownDocument.read(source_path)
            self.assertEqual("pending", source.metadata["review_status"])
            self.assertEqual("captured", source.metadata["processing_status"])
            self.assertEqual(preview.mutation_id, result["mutation_id"])
            self.assertGreater(
                len({path for path in root.rglob("*") if path.is_file()}),
                len(before),
            )

    def test_uploaded_capture_is_bounded_and_never_persists_client_path(self) -> None:
        adapter = UploadedCaptureAdapter(
            "evidence.html",
            b'<meta name="datePublished" content="2026-08-11"><p>Fact</p>',
            captured_at="2026-08-13T00:00:00+00:00",
        )
        asset = adapter.capture()
        self.assertEqual("web-upload://evidence.html", asset.final_locator)
        self.assertEqual("2026-08-11", asset.published_date_proposal)
        with self.assertRaisesRegex(ValueError, "basename"):
            UploadedCaptureAdapter("../../secret.txt", b"secret").capture()
        with self.assertRaisesRegex(ValueError, "cannot include"):
            capture_adapter(
                capture_mode="upload",
                locator="/etc/passwd",
                upload_filename="evidence.txt",
                upload_content=b"fact",
            )

    def test_process_preview_is_read_only_and_commit_is_stale_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = prepare_source_create(
                root,
                actor="max",
                adapter=CountingAdapter(b"<p>Extract this fact.</p>"),
                fields=self._fields(),
            )
            commit_repository_mutation(root, self._preview(prepared), prepared.plan)
            process = prepare_source_process(
                root, "SRC-20260813-002", actor="max"
            )
            source_path = next(root.rglob("SRC-20260813-002*.md"))
            source_before = source_path.read_bytes()
            self.assertFalse(any(root.rglob("*.extracted.txt")))
            self.assertEqual(source_before, source_path.read_bytes())

            preview = self._preview(process)
            source_path.write_text(
                source_path.read_text(encoding="utf-8") + "\nexternal edit\n",
                encoding="utf-8",
            )
            self.assertNotEqual(
                preview.target_version,
                repository_target_version(root, process.plan),
            )
            with self.assertRaisesRegex(ValueError, "changed"):
                commit_repository_mutation(root, preview, process.plan)
            self.assertFalse(any(root.rglob("*.extracted.txt")))

    def test_date_confirmation_requires_explicit_proposal_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = prepare_source_create(
                root,
                actor="max",
                adapter=CountingAdapter(b"<p>Fact.</p>"),
                fields=self._fields(),
            )
            commit_repository_mutation(root, self._preview(prepared), prepared.plan)

            with self.assertRaisesRegex(ValueError, "override"):
                prepare_source_date_confirmation(
                    root,
                    "SRC-20260813-002",
                    actor="max",
                    confirmed_date="2026-08-10",
                    allow_proposal_override=False,
                )
            date_plan = prepare_source_date_confirmation(
                root,
                "SRC-20260813-002",
                actor="max",
                confirmed_date="2026-08-10",
                allow_proposal_override=True,
            )
            self.assertTrue(date_plan.preview_input.summary["proposal_override"])


class SourceWebHttpTests(unittest.TestCase):
    def _root(self, temp: str) -> Path:
        root = fixtures.RepositoryValidationTests().make_root(temp)
        config = root / "00_System/web.local.json"
        config.write_text(
            json.dumps(
                {
                    "researcher_id": "max",
                    "mutation_signing_secret": "s" * 64,
                }
            ),
            encoding="utf-8",
        )
        config.chmod(0o600)
        return root

    @staticmethod
    def _hidden(page: str, name: str) -> str:
        marker = f'name="{name}" value="'
        return page.split(marker, 1)[1].split('"', 1)[0]

    def _source_form(self, csrf: str) -> dict[str, str]:
        return {
            "capture_mode": "upload",
            "locator": "",
            "title": "Uploaded Web Source",
            "slug": "uploaded-web-source",
            "created_at": "2026-08-13",
            "source_type": "article",
            "publisher": "Example Publisher",
            "published_at": "unknown",
            "source_grade": "B",
            "companies": "",
            "technologies": "",
            "products": "",
            "tags": "",
            "project_ids": "PRJ-001",
            "allow_duplicate": "false",
            "csrf_token": csrf,
        }

    def test_upload_preview_commit_result_refresh_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = TestClient(create_app(root), base_url="http://localhost")
            form_page = client.get("/sources/new")
            self.assertEqual(200, form_page.status_code)
            csrf = self._hidden(form_page.text, "csrf_token")
            preview = client.post(
                "/sources/new/preview",
                data=self._source_form(csrf),
                files={
                    "source_file": (
                        "evidence.html",
                        b"<p>Captured body must stay server-side.</p>",
                        "text/html",
                    )
                },
                headers={"Origin": "http://localhost"},
            )
            self.assertEqual(200, preview.status_code, preview.text)
            self.assertNotIn("Captured body", preview.text)
            token = self._hidden(preview.text, "preview_token")
            commit_body = {"preview_token": token, "csrf_token": csrf}
            committed = client.post(
                "/sources/new/commit",
                content=urlencode(commit_body),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(303, committed.status_code, committed.text)
            location = committed.headers["location"]
            self.assertIn("/sources/SRC-20260813-002/mutations/", location)
            self.assertEqual(200, client.get(location).status_code)
            self.assertEqual(200, client.get(location).status_code)
            replay = client.post(
                "/sources/new/commit",
                content=urlencode(commit_body),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(409, replay.status_code)
            source = next(root.rglob("SRC-20260813-002*.md"))
            self.assertEqual(
                "pending", MarkdownDocument.read(source).metadata["review_status"]
            )

    def test_source_preview_rejects_hostile_origin_and_extra_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = TestClient(create_app(root), base_url="http://localhost")
            page = client.get("/sources/new")
            csrf = self._hidden(page.text, "csrf_token")
            form = self._source_form(csrf)
            files = {"source_file": ("evidence.txt", b"fact", "text/plain")}
            hostile = client.post(
                "/sources/new/preview",
                data=form,
                files=files,
                headers={"Origin": "https://evil.example"},
            )
            self.assertEqual(403, hostile.status_code)
            form["actor"] = "attacker"
            extra = client.post(
                "/sources/new/preview",
                data=form,
                files=files,
                headers={"Origin": "http://localhost"},
            )
            self.assertEqual(422, extra.status_code)
            self.assertFalse(any(root.rglob("SRC-20260813-002*.md")))


if __name__ == "__main__":
    unittest.main()
