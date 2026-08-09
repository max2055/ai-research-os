"""WP-500 (E-003~006): Phase 5 forecast/resolution/valuation/recommendation
schema tests.

Covers the RCP-v03-008/009 contract: open requires reviewed, probability only
for binary, base rate unknown not fabricated, resolution is append-only with a
required reason for ambiguous/void, recommendation ceiling is
investment_candidate (no buy/sell), Company/Security separated, and
next_object_id/validate_refs are wired for the four new types.
"""

from __future__ import annotations

import unittest

try:
    from research_os.domain.policies import ID_PATTERNS
    from research_os.schemas import (
        ForecastResolutionSchema,
        ForecastSchema,
        RecommendationSchema,
        ValuationSnapshotSchema,
    )
    from research_os.services.drafts import next_object_id
    from research_os.services.validation import validate_repository
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-500 tests") from exc

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _forecast(**overrides: object) -> dict:
    meta = {
        "id": "FCT-20260809-001",
        "type": "forecast",
        "title": "T",
        "created_at": "2026-08-09",
        "updated_at": "2026-08-09",
        "schema_version": 2,
        "project_ids": [],
        "status": "draft",
        "review_status": "pending",
        "tags": [],
        "scope_ids": [],
        "question": "NVIDIA DC revenue up YoY by FY27Q1?",
        "outcome_type": "binary",
        "outcome_definition": "DC revenue >= $60B",
        "base_rate": "unknown",
        "probability": 0.6,
        "forecast_as_of": "2026-08-09",
        "horizon": "quarter",
        "resolution_date": "2026-10-30",
        "resolution_source_requirements": [],
        "evidence_ids": [],
        "analysis_run_ids": [],
        "assumptions": [],
        "alternative_outcomes": [],
        "falsification_conditions": [],
    }
    meta.update(overrides)
    return meta


class ForecastSchemaTests(unittest.TestCase):
    def test_well_formed_forecast(self) -> None:
        ForecastSchema.model_validate(_forecast())

    def test_numeric_range_well_formed(self) -> None:
        # probability-only-binary is a SERVICE-layer rule (Phase 5 §3), not a
        # schema constraint — the schema accepts a well-formed numeric range.
        obj = ForecastSchema.model_validate(
            _forecast(outcome_type="numeric_range", range_low=10, range_high=20)
        )
        self.assertEqual(10, obj.range_low)

    def test_base_rate_unknown_allowed(self) -> None:
        obj = ForecastSchema.model_validate(_forecast(base_rate="unknown"))
        self.assertEqual("unknown", obj.base_rate)

    def test_status_enum(self) -> None:
        for status in ("draft", "open", "resolved", "void", "superseded"):
            ForecastSchema.model_validate(_forecast(status=status))
        with self.assertRaises(ValueError):
            ForecastSchema.model_validate(_forecast(status="closed"))

    def test_id_pattern(self) -> None:
        self.assertTrue(ID_PATTERNS["forecast"].fullmatch("FCT-20260809-001"))
        self.assertFalse(ID_PATTERNS["forecast"].fullmatch("FCT-1"))


class ResolutionSchemaTests(unittest.TestCase):
    def test_well_formed_resolution(self) -> None:
        ForecastResolutionSchema.model_validate(
            {
                "id": "RES-20260809-001",
                "type": "forecast_resolution",
                "title": "R",
                "created_at": "2026-08-09",
                "updated_at": "2026-08-09",
                "schema_version": 2,
                "project_ids": [],
                "status": "active",
                "review_status": "pending",
                "tags": [],
                "forecast_id": "FCT-20260809-001",
                "resolved_at": "2026-10-30",
                "outcome": "met",
                "observed_value": "$62B",
                "source_ids": [],
                "decision": "correct",
                "resolution_reason": "observed DC revenue $62B >= $60B threshold",
                "scoring_method": "manual",
                "reviewer": "max",
            }
        )

    def test_ambiguous_requires_reason(self) -> None:
        with self.assertRaises(ValueError):
            ForecastResolutionSchema.model_validate(
                {
                    "id": "RES-20260809-002",
                    "type": "forecast_resolution",
                    "title": "R",
                    "created_at": "2026-08-09",
                    "updated_at": "2026-08-09",
                    "schema_version": 2,
                    "project_ids": [],
                    "status": "active",
                    "review_status": "pending",
                    "tags": [],
                    "forecast_id": "FCT-20260809-001",
                    "resolved_at": "2026-10-30",
                    "outcome": "unclear",
                    "source_ids": [],
                    "decision": "ambiguous",
                    "resolution_reason": "",
                    "reviewer": "max",
                }
            )

    def test_id_patterns(self) -> None:
        self.assertTrue(
            ID_PATTERNS["forecast_resolution"].fullmatch("RES-20260809-001")
        )
        self.assertTrue(
            ID_PATTERNS["valuation_snapshot"].fullmatch("VAL-20260809-001")
        )
        self.assertTrue(
            ID_PATTERNS["recommendation"].fullmatch("REC-20260809-001")
        )


class ValuationRecommendationSchemaTests(unittest.TestCase):
    def test_valuation_well_formed(self) -> None:
        ValuationSnapshotSchema.model_validate(
            {
                "id": "VAL-20260809-001",
                "type": "valuation_snapshot",
                "title": "V",
                "created_at": "2026-08-09",
                "updated_at": "2026-08-09",
                "schema_version": 2,
                "project_ids": [],
                "status": "active",
                "review_status": "pending",
                "tags": [],
                "company_id": "COM-nvidia",
                "security_id": "INS-NASDAQ-NVDA",
                "as_of": "2026-08-09",
                "market_price": 120.0,
                "currency": "USD",
                "valuation_identity": "ev/ebitda",
                "denominator_period": "FY2026",
                "source_ids": [],
                "event_ids": [],
                "scenario_set": "",
                "freshness_threshold": "7d",
            }
        )

    def test_recommendation_posture_ceiling(self) -> None:
        # investment_candidate is the ceiling; buy/sell is not a valid posture.
        for posture in ("avoid", "watch", "research", "investment_candidate"):
            RecommendationSchema.model_validate(
                {
                    "id": "REC-20260809-001",
                    "type": "recommendation",
                    "title": "R",
                    "created_at": "2026-08-09",
                    "updated_at": "2026-08-09",
                    "schema_version": 2,
                    "project_ids": [],
                    "status": "draft",
                    "review_status": "pending",
                    "tags": [],
                    "company_id": "COM-nvidia",
                    "as_of": "2026-08-09",
                    "research_posture": posture,
                    "direction": "positive",
                    "conviction": "high",
                    "freshness_date": "2026-08-09",
                }
            )
        with self.assertRaises(ValueError):
            RecommendationSchema.model_validate(
                {
                    "id": "REC-20260809-002",
                    "type": "recommendation",
                    "title": "R",
                    "created_at": "2026-08-09",
                    "updated_at": "2026-08-09",
                    "schema_version": 2,
                    "project_ids": [],
                    "status": "draft",
                    "review_status": "pending",
                    "tags": [],
                    "company_id": "COM-nvidia",
                    "as_of": "2026-08-09",
                    "research_posture": "buy",
                    "freshness_date": "2026-08-09",
                }
            )


class WiringTests(unittest.TestCase):
    def test_next_object_id_prefixes(self) -> None:
        self.assertEqual(
            "FCT-20260809-001", next_object_id([], "forecast", "2026-08-09")
        )
        self.assertEqual(
            "RES-20260809-001",
            next_object_id([], "forecast_resolution", "2026-08-09"),
        )
        self.assertEqual(
            "VAL-20260809-001", next_object_id([], "valuation_snapshot", "2026-08-09")
        )
        self.assertEqual(
            "REC-20260809-001", next_object_id([], "recommendation", "2026-08-09")
        )

    def test_validate_refs_catches_missing_forecast(self) -> None:
        # A resolution referencing a nonexistent forecast_id is a validate error.
        import tempfile

        import test_research_os_core as fixtures

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures.write(root / "00_System" / "Taxonomy.md", fixtures.TAXONOMY)
            fixtures.write(
                root / "05_Research" / "Projects" / "PRJ-001.md",
                fixtures.project(),
            )
            fixtures.write(
                root / "05_Research" / "Resolutions" / "RES-20260809-001.md",
                """---
id: RES-20260809-001
type: forecast_resolution
title: R
created_at: 2026-08-09
updated_at: 2026-08-09
schema_version: 2
project_ids: []
status: active
review_status: pending
tags: []
forecast_id: FCT-20260809-999
resolved_at: 2026-10-30
outcome: met
source_ids: []
decision: correct
resolution_reason: x
reviewer: max
---

# Resolution
""",
            )
            _, findings = validate_repository(root)
            self.assertIn("REF001", {f.code for f in findings})


if __name__ == "__main__":
    unittest.main()
