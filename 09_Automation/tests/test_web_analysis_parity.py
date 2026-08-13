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
from research_os.domain.models import ResearchObject
from research_os.repositories.markdown import MarkdownDocument
from research_os.services.analysis_runner import RunPlan
from research_os.services.mutation_gateway import MutationGateway
from research_os.services.web_analysis_mutations import (
    prepare_analysis_creation,
    prepare_analysis_replay,
    prepare_thesis_proposal_creation,
)
from research_os.services.web_repository_mutations import commit_repository_mutation
from research_os.ui.app import create_app


def _run_plan(run_id: str = "ANL-20260813-001") -> RunPlan:
    return RunPlan(
        run_id=run_id,
        mode_id="MOD-ANL-value-chain-v1",
        scope_ids=[],
        input_source_ids=[],
        input_event_ids=["EVT-20260729-001"],
        input_impact_ids=[],
        input_thesis_ids=[],
        as_of="2026-08-13",
        input_snapshot_hash="a" * 64,
        model_provider="echo",
        model_id="echo",
        model_parameters={},
        prompt_hash="b" * 64,
        output_hash="c" * 64,
        generation_method="mode-runner",
        body="## Judgments\nA bounded judgment.\n",
        relative_path=Path("05_Research/Analysis") / f"{run_id}.md",
        content=(
            "---\n"
            f"id: {run_id}\n"
            "type: analysis_run\n"
            "status: completed\n"
            "review_status: pending\n"
            "mode_id: MOD-ANL-value-chain-v1\n"
            "as_of: 2026-08-13\n"
            "input_event_ids: [EVT-20260729-001]\n"
            "---\n\n"
            "## Judgments\nA bounded judgment.\n"
        ),
    )


class AnalysisWebAdapterTests(unittest.TestCase):
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

    @staticmethod
    def _root(temp: str) -> Path:
        return fixtures.RepositoryValidationTests().make_root(temp)

    def test_analysis_preview_freezes_plan_and_commit_does_not_rerun_provider(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            spec = json.dumps(
                {
                    "mode_id": "MOD-ANL-value-chain-v1",
                    "as_of": "2026-08-13",
                    "input_event_ids": ["EVT-20260729-001"],
                    "model_provider": "echo",
                    "model_id": "echo",
                }
            )
            with patch(
                "research_os.services.web_analysis_mutations.prepare_run",
                return_value=_run_plan(),
            ) as prepare:
                prepared = prepare_analysis_creation(root, actor="max", spec_json=spec)
            self.assertEqual("analysis.run", prepared.preview_input.operation)
            self.assertEqual(
                "pending", prepared.preview_input.summary["review_status_after"]
            )
            commit_repository_mutation(root, self._preview(prepared), prepared.plan)
            prepare.assert_called_once()
            document = MarkdownDocument.read(root / prepared.plan.writes[0].path)
            self.assertEqual("pending", document.metadata["review_status"])

    def test_replay_binds_source_run_and_thesis_proposal_is_non_authoritative(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            source = root / "05_Research/Analysis/ANL-20260812-001.md"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(
                "---\n"
                "id: ANL-20260812-001\n"
                "type: analysis_run\n"
                "status: completed\n"
                "review_status: reviewed\n"
                "mode_id: MOD-ANL-value-chain-v1\n"
                "as_of: 2026-08-12\n"
                "scope_ids: []\n"
                "input_source_ids: []\n"
                "input_event_ids: [EVT-20260729-001]\n"
                "input_impact_ids: []\n"
                "input_thesis_ids: []\n"
                "---\n\n## Judgments\nDone.\n",
                encoding="utf-8",
            )
            with (
                patch(
                    "research_os.services.web_analysis_mutations.prepare_run",
                    return_value=_run_plan("ANL-20260813-002"),
                ),
                patch(
                    "research_os.services.web_analysis_mutations.validate_repository",
                    return_value=(
                        [
                            ResearchObject(
                                path=source,
                                metadata={
                                    "id": "ANL-20260812-001",
                                    "type": "analysis_run",
                                    "status": "completed",
                                    "review_status": "reviewed",
                                    "mode_id": "MOD-ANL-value-chain-v1",
                                    "as_of": "2026-08-12",
                                    "scope_ids": [],
                                    "input_source_ids": [],
                                    "input_event_ids": ["EVT-20260729-001"],
                                    "input_impact_ids": [],
                                    "input_thesis_ids": [],
                                },
                                body="## Judgments\nDone.\n",
                            )
                        ],
                        [],
                    ),
                ),
            ):
                replay = prepare_analysis_replay(
                    root,
                    actor="max",
                    spec_json=json.dumps(
                        {
                            "run_id": "ANL-20260812-001",
                            "model_provider": "echo",
                            "model_id": "echo",
                        }
                    ),
                )
            self.assertEqual("analysis.replay", replay.preview_input.operation)
            self.assertEqual("ANL-20260813-002", replay.preview_input.target_id)
            self.assertEqual(
                "ANL-20260812-001",
                replay.preview_input.normalized_input["source_run_id"],
            )

            with patch(
                "research_os.services.web_analysis_mutations.prepare_thesis_proposal",
                return_value=(
                    Path(
                        "05_Research/Analysis_Proposals/Thesis_Proposal_ANL-20260812-001.md"
                    ),
                    "---\nstatus: pending\n---\n",
                ),
            ):
                proposal = prepare_thesis_proposal_creation(
                    root,
                    actor="max",
                    spec_json=json.dumps(
                        {"run_id": "ANL-20260812-001", "created_at": "2026-08-13"}
                    ),
                )
            self.assertFalse(
                proposal.preview_input.summary["authoritative_thesis_write"]
            )
            self.assertNotIn("03_Theses", str(proposal.plan.writes[0].path))


class AnalysisWebHttpTests(unittest.TestCase):
    @staticmethod
    def _root(temp: str) -> Path:
        root = fixtures.RepositoryValidationTests().make_root(temp)
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

    def test_analysis_forms_exist_and_commit_rejects_browser_actor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            client = TestClient(
                create_app(self._root(temp)), base_url="http://localhost"
            )
            for route in (
                "/impact/proposals/new",
                "/analysis/runs/new",
                "/analysis/runs/ANL-20260812-001/replay",
                "/analysis/thesis-proposals/new",
            ):
                with self.subTest(route=route):
                    self.assertEqual(200, client.get(route).status_code)
            page = client.get("/analysis/runs/new")
            csrf = self._hidden(page.text, "csrf_token")
            response = client.post(
                "/analysis/runs/new/commit",
                content=urlencode(
                    {
                        "preview_token": "invalid",
                        "csrf_token": csrf,
                        "actor": "automation",
                    }
                ),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "http://localhost",
                },
            )
            self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
