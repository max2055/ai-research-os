"""WP-512 (E-016~018): CLI completion, decision dashboard, alerts job tests.

E-016 calibration mode/sector filters + list renderers; E-017 /decision
dashboard page; E-018 decision_alerts (due/overdue forecast + stale active
recommendation). Validation is patched to controlled object lists; dashboard
routes are exercised read-only against the real repo.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from fastapi.testclient import TestClient

    from research_os.domain.models import ResearchObject
    from research_os.services.calibration import calibration_report
    from research_os.services.decision_alerts import (
        decision_alerts,
        render_decision_alerts,
    )
    from research_os.services.recommendation import render_recommendation_rows
    from research_os.services.valuation import render_valuation_rows
    from research_os.ui.app import create_app
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-512 tests") from exc

ROOT = Path(__file__).resolve().parents[2]


def _obj(object_id: str, object_type: str, **meta: object) -> ResearchObject:
    full: dict[str, object] = {
        "id": object_id,
        "type": object_type,
        "title": object_id,
        "review_status": "reviewed",
    }
    full.update(meta)
    path = Path(f"{object_type}s/{object_id}.md")
    return ResearchObject(path=path, metadata=full, body="")


def _forecast(object_id: str, **meta: object) -> ResearchObject:
    return _obj(object_id, "forecast", **meta)


def _resolution(object_id: str, forecast_id: str, **meta: object) -> ResearchObject:
    return _obj(
        object_id,
        "forecast_resolution",
        forecast_id=forecast_id,
        **meta,
    )


def _sample_objects() -> list[ResearchObject]:
    run_vc = _obj("ANL-1", "analysis_run", mode_id="MOD-ANL-value-chain-v1")
    run_sc = _obj("ANL-2", "analysis_run", mode_id="MOD-ANL-scenario-v2")
    f1 = _forecast(
        "FCT-1",
        outcome_type="binary",
        probability=0.8,
        analysis_run_ids=["ANL-1"],
        scope_ids=["SEG-memory-storage"],
        resolution_date="2026-08-01",
    )
    f2 = _forecast(
        "FCT-2",
        outcome_type="binary",
        probability=0.7,
        analysis_run_ids=["ANL-2"],
        scope_ids=["SEG-compute"],
        resolution_date="2026-08-01",
    )
    r1 = _resolution("RES-1", "FCT-1", decision="correct", resolved_at="2026-08-01")
    r2 = _resolution("RES-2", "FCT-2", decision="incorrect", resolved_at="2026-08-02")
    return [run_vc, run_sc, f1, f2, r1, r2]


def _patch(module: str, objects: list[ResearchObject]):
    return mock.patch(
        f"research_os.services.{module}.validate_repository",
        return_value=(objects, []),
    )


class E016CalibrationFilterTests(unittest.TestCase):
    """E-016: calibration restricted by analysis mode / scope sector."""

    def test_mode_filter_counts_only_matching_forecasts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch("calibration", _sample_objects()):
                all_report = calibration_report(root)
                vc_report = calibration_report(root, mode="value-chain")
                sc_report = calibration_report(root, mode="scenario")
            self.assertEqual(2, all_report["n_resolutions"])
            self.assertEqual(1, vc_report["n_resolutions"])
            self.assertEqual(1, sc_report["n_resolutions"])
            self.assertAlmostEqual(0.04, vc_report["brier"]["brier"])  # (0.8-1)^2

    def test_sector_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch("calibration", _sample_objects()):
                report = calibration_report(root, sector="SEG-memory-storage")
            self.assertEqual(1, report["n_resolutions"])


class E016ListRendererTests(unittest.TestCase):
    """E-016: recommendation/valuation list renderers."""

    def test_render_recommendation_rows_empty_and_populated(self) -> None:
        self.assertIn("No matching recommendations", render_recommendation_rows([]))
        rec = _obj("REC-1", "recommendation", company_id="COM-micron", status="active")
        rendered = render_recommendation_rows([rec])
        self.assertIn("REC-1", rendered)
        self.assertIn("active", rendered)

    def test_render_valuation_rows_empty_and_populated(self) -> None:
        self.assertIn("No valuation snapshots", render_valuation_rows([]))
        val = _obj("VAL-1", "valuation_snapshot", company_id="COM-micron")
        self.assertIn("VAL-1", render_valuation_rows([val]))


class E018DecisionAlertsTests(unittest.TestCase):
    """E-018: due/overdue forecasts + stale active recommendation alerts."""

    def _alert_objects(self) -> list[ResearchObject]:
        due = _forecast(
            "FCT-DUE",
            status="open",
            review_status="reviewed",
            resolution_date="2026-08-09",
        )
        overdue = _forecast(
            "FCT-OVER",
            status="open",
            review_status="reviewed",
            resolution_date="2026-08-01",
        )
        fresh_rec = _obj(
            "REC-FRESH",
            "recommendation",
            status="active",
            review_status="reviewed",
            research_posture="investment_candidate",
            freshness_date="2026-08-09",
            catalysts=["HBM 出货增长"],
            falsification_conditions=["DRAM 价格下行"],
        )
        stale_rec = _obj(
            "REC-STALE",
            "recommendation",
            status="active",
            review_status="reviewed",
            freshness_date="2026-01-01",
        )
        return [due, overdue, fresh_rec, stale_rec]

    def test_due_and_overdue_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch("decision_alerts", self._alert_objects()):
                report = decision_alerts(root, as_of="2026-08-09")
            self.assertEqual(2, report["due_count"])
            self.assertEqual(1, report["overdue_count"])
            self.assertIn("FCT-DUE", str(report["alerts"]))
            self.assertIn("FCT-OVER", str(report["alerts"]))

    def test_stale_active_recommendation_alerted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch("decision_alerts", self._alert_objects()):
                report = decision_alerts(root, as_of="2026-08-09")
            self.assertEqual(2, report["active_recommendations"])
            self.assertTrue(any("REC-STALE" in a for a in report["alerts"]))
            self.assertFalse(any("REC-FRESH 已过期" in a for a in report["alerts"]))
            self.assertTrue(
                any("REC-FRESH 催化剂" in a for a in report["alerts"])
            )

    def test_no_alerts_when_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            future = _forecast(
                "FCT-FUTURE",
                status="open",
                review_status="reviewed",
                resolution_date="2026-12-01",
            )
            with _patch("decision_alerts", [future]):
                report = decision_alerts(root, as_of="2026-08-09")
            self.assertEqual(0, report["due_count"])
            self.assertTrue(report["alerts"])
            rendered = render_decision_alerts(report)
            self.assertIn("# Decision alerts", rendered)


class E017DecisionDashboardTests(unittest.TestCase):
    """E-017: /decision page renders read-only (real repo, empty Phase 5 data)."""

    def test_decision_route_returns_200(self) -> None:
        client = TestClient(create_app(ROOT))
        response = client.get("/decision")
        self.assertEqual(200, response.status_code)
        self.assertIn("决策工作区", response.text)
        self.assertIn("到期提醒", response.text)

    def test_decision_detail_route_404_on_missing(self) -> None:
        client = TestClient(create_app(ROOT))
        self.assertEqual(404, client.get("/decision/forecast/FCT-999").status_code)


if __name__ == "__main__":
    unittest.main()
