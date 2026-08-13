from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

import test_research_os_core as fixtures
from research_os.repositories.markdown import MarkdownDocument
from research_os.services.mutation_gateway import MutationGateway
from research_os.services.reviews import apply_review
from research_os.services.web_repository_mutations import commit_repository_mutation
from research_os.services.web_research_drafts import (
    prepare_event_creation,
    prepare_report_creation,
)
from research_os.ui.app import create_app
from test_m4_workflow import (
    add_company,
    add_processed_source,
    add_thesis,
    event_spec,
)


class ResearchDraftWebAdapterTests(unittest.TestCase):
    def _root(self, temp: str) -> tuple[Path, str]:
        root = fixtures.RepositoryValidationTests().make_root(temp)
        add_thesis(root)
        add_company(root)
        return root, add_processed_source(root)

    @staticmethod
    def _preview(prepared):
        return MutationGateway(
            b"s" * 64,
            now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
        ).issue(prepared.preview_input).preview

    def test_event_creation_is_pending_anchored_and_does_not_write_thesis(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, source_id = self._root(temp)
            thesis = next(root.rglob("THS-001*.md"))
            thesis_before = thesis.read_bytes()
            spec = event_spec(source_id).model_copy(
                update={"created_at": "2026-08-13", "event_date": "2026-08-13"}
            )
            prepared = prepare_event_creation(
                root,
                actor="max",
                spec_json=spec.model_dump_json(),
            )
            self.assertEqual("event.create", prepared.preview_input.operation)
            self.assertEqual("pending", prepared.preview_input.summary["status_after"])
            serialized = json.dumps(prepared.preview_input.normalized_input)
            self.assertNotIn("Evidence line one", serialized)
            commit_repository_mutation(root, self._preview(prepared), prepared.plan)
            event = next(root.rglob("EVT-20260813-*.md"))
            self.assertEqual(
                "pending",
                MarkdownDocument.read(event).metadata["review_status"],
            )
            self.assertEqual(thesis_before, thesis.read_bytes())

    def test_event_rejects_unanchored_quote_and_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, source_id = self._root(temp)
            value = event_spec(source_id).model_dump(mode="json")
            value["facts"][0]["quote"] = "not present"
            with self.assertRaisesRegex(ValueError, "not present"):
                prepare_event_creation(root, actor="max", spec_json=json.dumps(value))
            value["unexpected"] = "field"
            with self.assertRaisesRegex(ValueError, "invalid Event"):
                prepare_event_creation(root, actor="max", spec_json=json.dumps(value))

    def test_report_requires_reviewed_evidence_and_remains_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, source_id = self._root(temp)
            event = prepare_event_creation(
                root,
                actor="max",
                spec_json=event_spec(source_id)
                .model_copy(
                    update={
                        "created_at": "2026-08-13",
                        "event_date": "2026-08-13",
                    }
                )
                .model_dump_json(),
            )
            commit_repository_mutation(root, self._preview(event), event.plan)
            report_value = {
                "title": "Evidence Report v0.3",
                "slug": "evidence-report-v0-3",
                "created_at": "2026-08-13",
                "period_start": "2026-08-01",
                "period_end": "2026-08-13",
                "evidence_ids": [event.preview_input.target_id],
                "thesis_ids": ["THS-001"],
                "report_type": "topic",
                "version": "v0.3",
                "tags": [],
                "project_ids": ["PRJ-001"],
            }
            with self.assertRaisesRegex(ValueError, "reviewed Evidence"):
                prepare_report_creation(
                    root, actor="max", spec_json=json.dumps(report_value)
                )
            apply_review(
                root,
                target_ids=[event.preview_input.target_id],
                decision="approve",
                reviewer="max",
                reviewed_at="2026-08-13",
                notes="Anchors checked.",
            )
            report = prepare_report_creation(
                root, actor="max", spec_json=json.dumps(report_value)
            )
            commit_repository_mutation(root, self._preview(report), report.plan)
            path = next(root.rglob("RPT-20260813-evidence-report-v0-3.md"))
            document = MarkdownDocument.read(path)
            self.assertEqual("pending", document.metadata["review_status"])
            self.assertIn("## Contradicting Evidence", document.body)


class ResearchDraftWebHttpTests(unittest.TestCase):
    def _root(self, temp: str) -> tuple[Path, str]:
        root = fixtures.RepositoryValidationTests().make_root(temp)
        add_thesis(root)
        add_company(root)
        source_id = add_processed_source(root)
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
        return root, source_id

    @staticmethod
    def _hidden(page: str, name: str) -> str:
        marker = f'name="{name}" value="'
        return page.split(marker, 1)[1].split('"', 1)[0]

    def test_event_http_preview_commit_result_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, source_id = self._root(temp)
            thesis = next(root.rglob("THS-001*.md"))
            thesis_before = thesis.read_bytes()
            client = TestClient(create_app(root), base_url="http://localhost")
            page = client.get("/evidence/events/new")
            self.assertEqual(200, page.status_code)
            csrf = self._hidden(page.text, "csrf_token")
            spec = event_spec(source_id).model_copy(
                update={"created_at": "2026-08-13", "event_date": "2026-08-13"}
            )
            preview = client.post(
                "/evidence/events/new/preview",
                content=urlencode(
                    {"spec_json": spec.model_dump_json(), "csrf_token": csrf}
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(200, preview.status_code, preview.text)
            self.assertNotIn("Evidence line one", preview.text)
            token = self._hidden(preview.text, "preview_token")
            body = urlencode({"preview_token": token, "csrf_token": csrf})
            commit = client.post(
                "/evidence/events/new/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(303, commit.status_code, commit.text)
            self.assertIn(
                "/research-drafts/EVT-20260813-002/",
                commit.headers["location"],
            )
            self.assertEqual(200, client.get(commit.headers["location"]).status_code)
            replay = client.post(
                "/evidence/events/new/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(409, replay.status_code)
            self.assertEqual(thesis_before, thesis.read_bytes())

    def test_report_http_rejects_pending_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self._root(temp)
            client = TestClient(create_app(root), base_url="http://localhost")
            page = client.get("/reports/new")
            self.assertEqual(200, page.status_code)
            csrf = self._hidden(page.text, "csrf_token")
            payload = {
                "title": "Invalid Pending Report",
                "slug": "invalid-pending-report",
                "created_at": "2026-08-13",
                "period_start": "2026-08-01",
                "period_end": "2026-08-13",
                "evidence_ids": ["EVT-20260729-001"],
                "thesis_ids": ["THS-001"],
                "report_type": "topic",
                "version": "v0.3",
                "tags": [],
                "project_ids": ["PRJ-001"],
            }
            response = client.post(
                "/reports/new/preview",
                content=urlencode(
                    {"spec_json": json.dumps(payload), "csrf_token": csrf}
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
