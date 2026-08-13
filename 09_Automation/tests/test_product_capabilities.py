from __future__ import annotations

import tempfile
import unittest

from research_os.cli import cli_capability_keys
from research_os.services.product_capabilities import (
    PRODUCT_CAPABILITIES,
    registered_mutation_routes,
)
from research_os.ui.app import create_app
from test_m5_dashboard_jobs import prepared_root


class ProductCapabilityTests(unittest.TestCase):
    def test_every_cli_leaf_has_one_product_disposition(self) -> None:
        cli_keys = cli_capability_keys()
        registry_keys = {item.cli_key for item in PRODUCT_CAPABILITIES}

        self.assertEqual(96, len(cli_keys))
        self.assertEqual(cli_keys, registry_keys)
        self.assertEqual(len(registry_keys), len(PRODUCT_CAPABILITIES))
        for item in PRODUCT_CAPABILITIES:
            self.assertTrue(item.owner)
            self.assertIn(item.disposition, {"web", "internal", "remove"})
            self.assertTrue(item.authority)
            self.assertIn(item.delivery_feature, {"F-026", "F-027", "F-028", "F-029"})
            if item.disposition == "web":
                self.assertTrue(item.web_routes, item.cli_key)

    def test_current_candidate_and_llm_mutation_routes_are_declared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            routes = registered_mutation_routes(create_app(prepared_root(temp)))
        declared = {
            route
            for item in PRODUCT_CAPABILITIES
            for route in item.web_routes
            if item.disposition == "web"
        }

        self.assertEqual(
            {
                "/llm/config",
                "/llm/models",
                "/llm/test",
                "/pipeline/queue/{candidate_id}/dismiss/preview",
                "/pipeline/queue/{candidate_id}/dismiss/commit",
                "/pipeline/queue/{candidate_id}/promote/preview",
                "/pipeline/queue/{candidate_id}/promote/commit",
                "/pipeline/queue/{candidate_id}/restore/preview",
                "/pipeline/queue/{candidate_id}/restore/commit",
                "/sources/new/preview",
                "/sources/new/commit",
                "/sources/{source_id}/fetch/preview",
                "/sources/{source_id}/fetch/commit",
                "/sources/{source_id}/process/preview",
                "/sources/{source_id}/process/commit",
                "/sources/{source_id}/confirm-date/preview",
                "/sources/{source_id}/confirm-date/commit",
                "/evidence/events/new/preview",
                "/evidence/events/new/commit",
                "/reports/new/preview",
                "/reports/new/commit",
                "/reviews/apply/preview",
                "/reviews/apply/commit",
                "/projects/new/preview",
                "/projects/new/commit",
                "/projects/{project_id}/advance/preview",
                "/projects/{project_id}/advance/commit",
                "/operations/actions/new/preview",
                "/operations/actions/new/commit",
                "/operations/actions/{action_id}/close/preview",
                "/operations/actions/{action_id}/close/commit",
                "/universe/entities/new/preview",
                "/universe/entities/new/commit",
                "/ontology/assertions/new/preview",
                "/ontology/assertions/new/commit",
                "/companies/{company_id}/update-proposals/new/preview",
                "/companies/{company_id}/update-proposals/new/commit",
                "/impact/proposals/new/preview",
                "/impact/proposals/new/commit",
                "/analysis/runs/new/preview",
                "/analysis/runs/new/commit",
                "/analysis/runs/{run_id}/replay/preview",
                "/analysis/runs/{run_id}/replay/commit",
                "/analysis/thesis-proposals/new/preview",
                "/analysis/thesis-proposals/new/commit",
            },
            routes,
        )
        self.assertLessEqual(routes, declared)

    def test_approval_capabilities_remain_named_human_only(self) -> None:
        approval_keys = {
            "review.apply",
            "project.advance-review",
            "forecast.open",
            "forecast.resolve",
            "recommendation.activate",
            "recommendation.close",
        }
        by_key = {item.cli_key: item for item in PRODUCT_CAPABILITIES}

        for key in approval_keys:
            self.assertEqual("named_human", by_key[key].authority)
            self.assertEqual("web", by_key[key].disposition)


if __name__ == "__main__":
    unittest.main()
