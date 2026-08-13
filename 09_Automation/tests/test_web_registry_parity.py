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
from research_os.services.web_registry_mutations import (
    prepare_action_close_mutation,
    prepare_action_creation,
    prepare_assertion_creation,
    prepare_company_update_creation,
    prepare_entity_creation,
    prepare_project_creation,
    prepare_project_review_advance,
)
from research_os.services.web_repository_mutations import commit_repository_mutation
from research_os.ui.app import create_app
from test_m4_workflow import add_thesis


class RegistryWebAdapterTests(unittest.TestCase):
    @staticmethod
    def _root(temp: str) -> Path:
        root = fixtures.RepositoryValidationTests().make_root(temp)
        add_thesis(root)
        return root

    @staticmethod
    def _preview(prepared):
        return (
            MutationGateway(
                b"s" * 64,
                now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
            )
            .issue(prepared.preview_input)
            .preview
        )

    def test_project_and_action_create_then_advance_and_close(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            project = prepare_project_creation(
                root,
                actor="max",
                spec_json=json.dumps(
                    {
                        "title": "Web parity project",
                        "slug": "web-parity-project",
                        "created_at": "2026-08-13",
                        "owner": "max",
                        "research_question": "Can every research workflow use the Web?",
                        "charter_path": "00_System/Phase_0_Research_Charter.md",
                        "queue_path": "01_Inbox",
                        "review_cadence": "Weekly",
                        "next_review_date": "2026-08-13",
                        "tags": [],
                    }
                ),
            )
            commit_repository_mutation(root, self._preview(project), project.plan)
            self.assertEqual("PRJ-002", project.preview_input.target_id)
            project_doc = next(root.rglob("PRJ-002-*.md"))
            self.assertEqual(
                "proposed", MarkdownDocument.read(project_doc).metadata["status"]
            )

            advance = prepare_project_review_advance(
                root, actor="max", project_id="PRJ-002", as_of="2026-08-13"
            )
            commit_repository_mutation(root, self._preview(advance), advance.plan)
            self.assertEqual(
                "2026-08-20",
                MarkdownDocument.read(project_doc).metadata["next_review_date"],
            )

            action = prepare_action_creation(
                root,
                actor="max",
                spec_json=json.dumps(
                    {
                        "title": "Verify Web parity",
                        "owner": "max",
                        "created_at": "2026-08-13",
                        "due_date": "2026-08-20",
                        "success_evidence": "Loopback E2E passes.",
                        "project_ids": ["PRJ-002"],
                    }
                ),
            )
            commit_repository_mutation(root, self._preview(action), action.plan)
            close = prepare_action_close_mutation(
                root,
                actor="max",
                action_id=action.preview_input.target_id,
                closed_at="2026-08-14",
                success_evidence="Verified through Web.",
            )
            commit_repository_mutation(root, self._preview(close), close.plan)
            action_doc = next(root.rglob(f"{action.preview_input.target_id}.md"))
            self.assertEqual(
                "done", MarkdownDocument.read(action_doc).metadata["status"]
            )

    def test_entity_assertion_and_company_proposal_are_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            thesis = next(root.rglob("THS-001*.md"))
            thesis_before = thesis.read_bytes()
            entity = prepare_entity_creation(
                root,
                actor="max",
                spec_json=json.dumps(
                    {
                        "entity_type": "company",
                        "slug": "web-co",
                        "title": "Web Co",
                        "created_at": "2026-08-13",
                        "legal_name": "Web Co, Inc.",
                        "company_stage": "public",
                        "headquarters": "Shanghai",
                    }
                ),
            )
            commit_repository_mutation(root, self._preview(entity), entity.plan)
            entity_doc = root / "02_Knowledge/Companies/COM-web-co.md"
            self.assertEqual(
                "pending", MarkdownDocument.read(entity_doc).metadata["review_status"]
            )

            assertion = prepare_assertion_creation(
                root,
                actor="max",
                spec_json=json.dumps(
                    {
                        "subject_id": "COM-web-co",
                        "predicate": "COMPETES_WITH",
                        "object_id": "COM-web-co",
                        "created_at": "2026-08-13",
                        "valid_from": "2026-08-13",
                        "as_of": "2026-08-13",
                    }
                ),
            )
            commit_repository_mutation(root, self._preview(assertion), assertion.plan)
            assertion_doc = next(root.rglob("REL-20260813-*.md"))
            self.assertEqual(
                "pending",
                MarkdownDocument.read(assertion_doc).metadata["review_status"],
            )

            event_path = next(root.rglob("EVT-20260729-001*.md"))
            event_doc = MarkdownDocument.read(event_path)
            event_doc.set_metadata("review_status", "reviewed")
            event_doc.set_metadata("companies", ["COM-web-co"])
            event_path.write_text(event_doc.render(), encoding="utf-8")
            proposal = prepare_company_update_creation(
                root,
                actor="max",
                spec_json=json.dumps(
                    {
                        "company_id": "COM-web-co",
                        "event_ids": ["EVT-20260729-001"],
                        "created_at": "2026-08-13",
                    }
                ),
            )
            commit_repository_mutation(root, self._preview(proposal), proposal.plan)
            self.assertTrue(
                (
                    root / "05_Research/Reviews/Knowledge_Proposals/KUP-20260813-001.md"
                ).is_file()
            )
            self.assertEqual(thesis_before, thesis.read_bytes())

    def test_unknown_references_extra_fields_and_blank_close_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            with self.assertRaisesRegex(ValueError, "unknown project"):
                prepare_action_creation(
                    root,
                    actor="max",
                    spec_json=json.dumps(
                        {
                            "title": "Bad",
                            "owner": "max",
                            "created_at": "2026-08-13",
                            "due_date": "2026-08-14",
                            "success_evidence": "None",
                            "project_ids": ["PRJ-999"],
                        }
                    ),
                )
            with self.assertRaisesRegex(ValueError, "invalid ProjectSpec"):
                prepare_project_creation(
                    root,
                    actor="max",
                    spec_json=json.dumps(
                        {
                            "title": "Bad",
                            "slug": "bad",
                            "created_at": "2026-08-13",
                            "owner": "max",
                            "research_question": "Bad?",
                            "charter_path": "charter.md",
                            "queue_path": "queue.md",
                            "review_cadence": "Weekly",
                            "next_review_date": "2026-08-20",
                            "tags": [],
                            "actor": "automation",
                        }
                    ),
                )


class RegistryWebHttpTests(unittest.TestCase):
    @staticmethod
    def _root(temp: str) -> Path:
        root = fixtures.RepositoryValidationTests().make_root(temp)
        add_thesis(root)
        config = root / "00_System/web.local.json"
        config.write_text(
            json.dumps({"researcher_id": "max", "mutation_signing_secret": "s" * 64}),
            encoding="utf-8",
        )
        config.chmod(0o600)
        return root

    @staticmethod
    def _hidden(page: str, name: str) -> str:
        marker = f'name="{name}" value="'
        return page.split(marker, 1)[1].split('"', 1)[0]

    def test_project_http_preview_commit_result_replay_and_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            thesis = next(root.rglob("THS-001*.md"))
            thesis_before = thesis.read_bytes()
            client = TestClient(create_app(root), base_url="http://localhost")
            page = client.get("/projects/new")
            self.assertEqual(200, page.status_code)
            csrf = self._hidden(page.text, "csrf_token")
            spec = json.dumps(
                {
                    "title": "Web project",
                    "slug": "web-project",
                    "created_at": "2026-08-13",
                    "owner": "max",
                    "research_question": "Does Web parity hold?",
                    "charter_path": "00_System/Phase_0_Research_Charter.md",
                    "queue_path": "01_Inbox",
                    "review_cadence": "Weekly",
                    "next_review_date": "2026-08-20",
                    "tags": [],
                }
            )
            hostile = client.post(
                "/projects/new/preview",
                content=urlencode({"spec_json": spec, "csrf_token": csrf}),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://evil.example",
                },
            )
            self.assertEqual(403, hostile.status_code)
            preview = client.post(
                "/projects/new/preview",
                content=urlencode({"spec_json": spec, "csrf_token": csrf}),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(200, preview.status_code, preview.text)
            self.assertNotIn("05_Research/Projects", preview.text)
            token = self._hidden(preview.text, "preview_token")
            body = urlencode({"preview_token": token, "csrf_token": csrf})
            committed = client.post(
                "/projects/new/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(303, committed.status_code, committed.text)
            self.assertIn("/research-mutations/", committed.headers["location"])
            self.assertEqual(200, client.get(committed.headers["location"]).status_code)
            replay = client.post(
                "/projects/new/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(409, replay.status_code)
            self.assertEqual(thesis_before, thesis.read_bytes())

    def test_registry_forms_exist_and_commit_rejects_extra_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = TestClient(create_app(root), base_url="http://localhost")
            for route in (
                "/projects",
                "/projects/new",
                "/projects/PRJ-001",
                "/operations/actions",
                "/operations/actions/new",
                "/universe/entities/new",
                "/ontology/assertions/new",
                "/companies/COM-test/update-proposals/new",
            ):
                with self.subTest(route=route):
                    self.assertEqual(200, client.get(route).status_code)
            page = client.get("/universe/entities/new")
            csrf = self._hidden(page.text, "csrf_token")
            rejected = client.post(
                "/universe/entities/new/commit",
                content=urlencode(
                    {"preview_token": "invalid", "csrf_token": csrf, "actor": "max"}
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(422, rejected.status_code)


if __name__ == "__main__":
    unittest.main()
