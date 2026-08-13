from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

from research_os.domain.models import ResearchObject
from research_os.services.web_decision_mutations import (
    prepare_recommendation_activation,
    prepare_scenario_template,
)
from research_os.ui.app import create_app
from test_research_os_core import RepositoryValidationTests


class DecisionWebAdapterTests(unittest.TestCase):
    def test_recommendation_activation_is_frozen_and_human_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            path = root / "05_Research/Recommendations/REC-20260813-001.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\nid: REC-20260813-001\ntype: recommendation\n"
                "status: draft\nreview_status: reviewed\n---\n",
                encoding="utf-8",
            )
            obj = ResearchObject(
                path=path,
                metadata={
                    "id": "REC-20260813-001",
                    "type": "recommendation",
                    "status": "draft",
                    "review_status": "reviewed",
                },
                body="",
            )
            with (
                patch(
                    "research_os.services.web_decision_mutations.validate_repository",
                    return_value=([obj], []),
                ),
                patch(
                    "research_os.services.recommendation_lifecycle.validate_repository",
                    return_value=([obj], []),
                ),
            ):
                prepared = prepare_recommendation_activation(
                    root,
                    actor="max",
                    spec_json=json.dumps(
                        {"rec_id": "REC-20260813-001", "as_of": "2026-08-13"}
                    ),
                )
            self.assertEqual(
                "recommendation.activate", prepared.preview_input.operation
            )
            self.assertEqual("active", prepared.preview_input.summary["status_after"])

    def test_scenario_template_never_targets_thesis_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            prepared = prepare_scenario_template(
                root,
                actor="max",
                spec_json=json.dumps(
                    {
                        "company_id": "COM-001",
                        "as_of": "2026-08-13",
                        "question": "scenario",
                    }
                ),
            )
            self.assertNotIn("03_Theses", str(prepared.plan.writes[0].path))


class DecisionWebHttpTests(unittest.TestCase):
    def test_decision_forms_are_registered_before_detail_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = RepositoryValidationTests().make_root(temp)
            config = root / "00_System/web.local.json"
            config.write_text(
                json.dumps(
                    {"researcher_id": "max", "mutation_signing_secret": "s" * 64}
                ),
                encoding="utf-8",
            )
            config.chmod(0o600)
            client = __import__(
                "fastapi.testclient", fromlist=["TestClient"]
            ).TestClient(create_app(root), base_url="http://localhost")
            for route in (
                "/decision/forecasts/new",
                "/decision/forecasts/change",
                "/decision/valuations/new",
                "/decision/valuations/change",
                "/decision/scenarios/new",
                "/decision/recommendations/new",
                "/decision/recommendations/change",
            ):
                self.assertEqual(200, client.get(route).status_code, route)


if __name__ == "__main__":
    unittest.main()
