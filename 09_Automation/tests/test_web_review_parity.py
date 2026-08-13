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
from research_os.services.web_repository_mutations import commit_repository_mutation
from research_os.services.web_review_mutations import prepare_review_mutation
from research_os.ui.app import create_app


class ReviewWebAdapterTests(unittest.TestCase):
    def _root(self, temp: str) -> Path:
        return fixtures.RepositoryValidationTests().make_root(temp)

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

    def test_review_freezes_decision_target_updates_and_fixed_actor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = prepare_review_mutation(
                root,
                actor="max",
                target_ids="EVT-20260729-001",
                decision="approve",
                reviewed_at="2026-08-13",
                notes="Fact and inference boundaries checked.",
            )
            preview = self._preview(prepared)
            self.assertEqual("review.apply", preview.operation)
            self.assertEqual("max", preview.actor)
            self.assertEqual("REV-20260813-001", preview.target_id)
            self.assertEqual(
                ["EVT-20260729-001"], preview.normalized_input["target_ids"]
            )
            commit_repository_mutation(root, preview, prepared.plan)
            event = next(root.rglob("EVT-20260729-001*.md"))
            decision = root / "05_Research/Reviews/Decisions/REV-20260813-001.md"
            self.assertEqual(
                "reviewed", MarkdownDocument.read(event).metadata["review_status"]
            )
            self.assertEqual(
                "max",
                MarkdownDocument.read(decision).metadata["reviewer"],
            )

    def test_edit_and_reject_require_notes_and_unknown_targets_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            for decision in ("edit", "reject"):
                with (
                    self.subTest(decision=decision),
                    self.assertRaisesRegex(ValueError, "requires notes"),
                ):
                    prepare_review_mutation(
                        root,
                        actor="max",
                        target_ids="EVT-20260729-001",
                        decision=decision,
                        reviewed_at="2026-08-13",
                        notes="",
                    )
            with self.assertRaisesRegex(ValueError, "unknown"):
                prepare_review_mutation(
                    root,
                    actor="max",
                    target_ids="EVT-missing",
                    decision="approve",
                    reviewed_at="2026-08-13",
                    notes="Checked.",
                )

    def test_preview_manifest_contains_no_generated_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = prepare_review_mutation(
                root,
                actor="max",
                target_ids="EVT-20260729-001",
                decision="approve",
                reviewed_at="2026-08-13",
                notes="Sensitive manual review note.",
            )
            serialized = json.dumps(prepared.preview_input.normalized_input)
            self.assertNotIn("# Review", serialized)
            self.assertNotIn("# Event", serialized)
            self.assertNotIn("Sensitive manual review note.\n", serialized)


class ReviewWebHttpTests(unittest.TestCase):
    def _root(self, temp: str, *, identity: bool = True) -> Path:
        root = fixtures.RepositoryValidationTests().make_root(temp)
        if identity:
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

    def test_human_review_preview_commit_result_refresh_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = TestClient(create_app(root), base_url="http://localhost")
            queue = client.get("/reviews")
            self.assertEqual(200, queue.status_code)
            self.assertNotIn('name="reviewer"', queue.text)
            csrf = self._hidden(queue.text, "csrf_token")
            preview = client.post(
                "/reviews/apply/preview",
                content=urlencode(
                    {
                        "target_ids": "EVT-20260729-001",
                        "decision": "approve",
                        "reviewed_at": "2026-08-13",
                        "notes": "Fact and inference boundaries checked.",
                        "csrf_token": csrf,
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(200, preview.status_code, preview.text)
            self.assertNotIn("04_Evidence/Events", preview.text)
            self.assertNotIn("# Review", preview.text)
            token = self._hidden(preview.text, "preview_token")
            body = urlencode({"preview_token": token, "csrf_token": csrf})
            committed = client.post(
                "/reviews/apply/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(303, committed.status_code, committed.text)
            self.assertIn("/reviews/mutations/", committed.headers["location"])
            self.assertEqual(200, client.get(committed.headers["location"]).status_code)
            self.assertEqual(200, client.get(committed.headers["location"]).status_code)
            replay = client.post(
                "/reviews/apply/commit",
                content=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
                follow_redirects=False,
            )
            self.assertEqual(409, replay.status_code)

    def test_review_rejects_browser_reviewer_and_missing_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = TestClient(create_app(root), base_url="http://localhost")
            queue = client.get("/reviews")
            csrf = self._hidden(queue.text, "csrf_token")
            response = client.post(
                "/reviews/apply/preview",
                content=urlencode(
                    {
                        "target_ids": "EVT-20260729-001",
                        "decision": "approve",
                        "reviewed_at": "2026-08-13",
                        "notes": "Checked.",
                        "reviewer": "automation",
                        "csrf_token": csrf,
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(422, response.status_code)

        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp, identity=False)
            client = TestClient(create_app(root), base_url="http://localhost")
            queue = client.get("/reviews")
            self.assertEqual(200, queue.status_code)
            self.assertNotIn("记录评审决定", queue.text)
            response = client.post(
                "/reviews/apply/preview",
                content=urlencode(
                    {
                        "target_ids": "EVT-20260729-001",
                        "decision": "approve",
                        "reviewed_at": "2026-08-13",
                        "notes": "Checked.",
                        "csrf_token": "none",
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(503, response.status_code)


if __name__ == "__main__":
    unittest.main()
