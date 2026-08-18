from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from fastapi.testclient import TestClient

import test_research_os_core as fixtures
from research_os.repositories.markdown import MarkdownDocument
from research_os.services.mutation_gateway import MutationGateway
from research_os.services.web_repository_mutations import commit_repository_mutation
from research_os.services.web_review_mutations import prepare_review_mutation
from research_os.ui.app import ResearchObject, create_app, object_url


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

    def test_object_url_uses_registered_routes_for_assertions_and_runs(self) -> None:
        def obj(object_type: str, object_id: str) -> ResearchObject:
            return ResearchObject(
                path=Path(object_id),
                metadata={"type": object_type, "id": object_id},
                body="",
            )

        self.assertEqual(
            "/impact/IMP-001",
            object_url(obj("impact_assertion", "IMP-001")),
        )
        self.assertEqual(
            "/impact/ONT-001",
            object_url(obj("ontology_assertion", "ONT-001")),
        )
        self.assertEqual(
            "/analysis/runs/ANL-001",
            object_url(obj("analysis_run", "ANL-001")),
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

    def test_review_preview_cancel_returns_to_review_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(
                create_app(self._root(temp)), base_url="http://localhost"
            )
            queue = client.get("/reviews")
            self.assertEqual(200, queue.status_code)
            csrf = self._hidden(queue.text, "csrf_token")
            preview = client.post(
                "/reviews/apply/preview",
                content=urlencode(
                    {
                        "target_ids": "EVT-20260729-001",
                        "decision": "approve",
                        "reviewed_at": "2026-08-13",
                        "notes": "Checked.",
                        "csrf_token": csrf,
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(200, preview.status_code, preview.text)
            self.assertIn('href="/reviews">取消</a>', preview.text)
            self.assertNotIn("/sources/REV-", preview.text)

    def test_review_action_bar_is_before_table_and_submits_existing_form(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(
                create_app(self._root(temp)), base_url="http://localhost"
            )
            page = client.get("/reviews")
            self.assertEqual(200, page.status_code)
            action_bar = page.text.index('id="review-action-bar"')
            table = page.text.index('id="review-table"')
            self.assertLess(action_bar, table)
            self.assertIn(
                '<form class="mutation-form review-form" id="review-form"',
                page.text,
            )
            self.assertIn('<div class="review-toolbar">', page.text)
            self.assertIn('<button type="submit">预览评审</button>', page.text)
            self.assertNotIn(
                '<div class="mutation-actions">'
                '<button type="submit">预览评审</button></div>',
                page.text,
            )
            table = page.text.index('id="review-table"')
            self.assertLess(page.text.index('name="decision"'), table)
            self.assertLess(page.text.index('name="reviewed_at"'), table)
            self.assertLess(page.text.index('name="notes"'), table)
            self.assertNotIn("<h3>记录评审决定</h3>", page.text)
            self.assertIn("event.target.matches('.review-target')", page.text)

    def test_review_queue_exposes_ai_assistance_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(
                create_app(self._root(temp)), base_url="http://localhost"
            )
            page = client.get("/reviews")
            self.assertEqual(200, page.status_code)
            self.assertIn('action="/reviews/assist/start"', page.text)
            self.assertIn('id="review-ai-form"', page.text)
            self.assertIn("分析已选", page.text)
            self.assertIn("AI 建议", page.text)
            self.assertIn("正在提交 AI 分析", page.text)

    def test_review_ai_start_returns_accepted_background_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with patch(
                "research_os.ui.app._configured_model_defaults",
                return_value=("echo", "echo"),
            ):
                client = TestClient(
                    create_app(self._root(temp)), base_url="http://localhost"
                )
                queue = client.get("/reviews")
                csrf = self._hidden(queue.text, "csrf_token")
                response = client.post(
                    "/reviews/assist/start",
                    content=urlencode(
                        {
                            "target_ids": "EVT-20260729-001",
                            "csrf_token": csrf,
                        }
                    ),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": "http://localhost",
                    },
                )
            self.assertEqual(202, response.status_code, response.text)
            payload = response.json()
            self.assertEqual(["EVT-20260729-001"], payload["accepted"])
            self.assertIn(
                payload["states"]["EVT-20260729-001"],
                {"queued", "running", "completed"},
            )

    def test_review_list_exposes_ai_state_and_detail_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with patch(
                "research_os.ui.app._configured_model_defaults",
                return_value=("echo", "echo"),
            ):
                client = TestClient(
                    create_app(self._root(temp)), base_url="http://localhost"
                )
                queue = client.get("/reviews")
                csrf = self._hidden(queue.text, "csrf_token")
                started = client.post(
                    "/reviews/assist/start",
                    content=urlencode(
                        {"target_ids": "EVT-20260729-001", "csrf_token": csrf}
                    ),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": "http://localhost",
                    },
                )
                self.assertEqual(202, started.status_code, started.text)
                detail = client.get("/reviews/assist/EVT-20260729-001")
            self.assertEqual(200, detail.status_code, detail.text)
            self.assertIn("AI 建议", detail.text)
            self.assertIn("批准", detail.text)
            self.assertIn("修改", detail.text)
            self.assertIn("拒绝", detail.text)
            self.assertIn("/reviews/apply/preview", detail.text)
            self.assertNotIn("/reviews/apply/commit", detail.text)

    def test_review_ai_assistance_requires_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(
                create_app(self._root(temp)), base_url="http://localhost"
            )
            queue = client.get("/reviews")
            csrf = self._hidden(queue.text, "csrf_token")
            response = client.post(
                "/reviews/assist/preview",
                content=urlencode({"target_ids": "", "csrf_token": csrf}),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(422, response.status_code)

    def test_review_ai_assistance_is_read_only_and_degrades_without_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with patch(
                "research_os.ui.app._configured_model_defaults",
                return_value=("echo", "echo"),
            ):
                client = TestClient(
                    create_app(self._root(temp)), base_url="http://localhost"
                )
                queue = client.get("/reviews")
                csrf = self._hidden(queue.text, "csrf_token")
                response = client.post(
                    "/reviews/assist/preview",
                    content=urlencode(
                        {"target_ids": "EVT-20260729-001", "csrf_token": csrf}
                    ),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": "http://localhost",
                    },
                )
            self.assertEqual(200, response.status_code, response.text)
            self.assertIn("AI 辅助评审", response.text)
            self.assertIn("EVT-20260729-001", response.text)
            self.assertIn("规则预检查", response.text)
            self.assertNotIn('name="preview_token"', response.text)
            self.assertNotIn("确认写入", response.text)

    def test_review_ai_assistance_provider_failure_does_not_block_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with (
                patch(
                    "research_os.services.ai_assistance.build_adapter",
                    side_effect=RuntimeError("provider down"),
                ),
                patch(
                    "research_os.ui.app._configured_model_defaults",
                    return_value=("deepseek", "deepseek-chat"),
                ),
            ):
                client = TestClient(
                    create_app(self._root(temp)), base_url="http://localhost"
                )
                queue = client.get("/reviews")
                csrf = self._hidden(queue.text, "csrf_token")
                response = client.post(
                    "/reviews/assist/preview",
                    content=urlencode(
                        {"target_ids": "EVT-20260729-001", "csrf_token": csrf}
                    ),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": "http://localhost",
                    },
                )
            self.assertEqual(200, response.status_code, response.text)
            self.assertIn("模型调用失败", response.text)
            self.assertIn("仍可继续人工评审", response.text)

    def test_review_ai_assistance_shows_configured_model_output(self) -> None:
        class FakeAdapter:
            def generate(self, prompt, **kwargs):
                self.prompt = prompt
                self.kwargs = kwargs
                return "模型建议：先核验来源锚点，再决定。"

        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as temp:
            with (
                patch(
                    "research_os.services.ai_assistance.build_adapter",
                    return_value=adapter,
                ),
                patch(
                    "research_os.ui.app._configured_model_defaults",
                    return_value=("deepseek", "deepseek-chat"),
                ),
            ):
                client = TestClient(
                    create_app(self._root(temp)), base_url="http://localhost"
                )
                queue = client.get("/reviews")
                csrf = self._hidden(queue.text, "csrf_token")
                response = client.post(
                    "/reviews/assist/preview",
                    content=urlencode(
                        {"target_ids": "EVT-20260729-001", "csrf_token": csrf}
                    ),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": "http://localhost",
                    },
                )
            self.assertEqual(200, response.status_code, response.text)
            self.assertIn("模型建议：先核验来源锚点，再决定。", response.text)
            self.assertIn("已生成模型建议", response.text)
            self.assertIn("EVT-20260729-001", adapter.prompt)
            self.assertEqual(0.2, adapter.kwargs["model_parameters"]["temperature"])

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
            self.assertNotIn('id="review-action-bar"', queue.text)
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

    def test_global_health_does_not_turn_display_label_into_project_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(
                create_app(self._root(temp)), base_url="http://localhost"
            )
            response = client.get("/health")
            self.assertEqual(200, response.status_code)
            self.assertNotIn("project=%E5%85%A8%E5%B1%80", response.text)
            self.assertNotIn("project=全局", response.text)

    def test_workspace_routes_forward_project_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = TestClient(create_app(root), base_url="http://localhost")
            with patch(
                "research_os.ui.app._impact_page", return_value="impact"
            ) as impact_page:
                response = client.get("/impact?project=PRJ-001")
                self.assertEqual(200, response.status_code)
                self.assertEqual("PRJ-001", impact_page.call_args.kwargs["project_id"])
            with patch(
                "research_os.ui.app._analysis_page", return_value="analysis"
            ) as analysis_page:
                response = client.get("/analysis?project=PRJ-001")
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    "PRJ-001", analysis_page.call_args.kwargs["project_id"]
                )
            with patch(
                "research_os.ui.app._decision_page", return_value="decision"
            ) as decision_page:
                response = client.get("/decision?project=PRJ-001")
                self.assertEqual(200, response.status_code)
                self.assertEqual(
                    "PRJ-001", decision_page.call_args.kwargs["project_id"]
                )


if __name__ == "__main__":
    unittest.main()
