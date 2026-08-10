"""Tests for monthly Discovery cost health."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from research_os.services.candidate_db import apply_migrations
from research_os.services.cost_monitoring import monthly_cost_report


class MonthlyCostReportTests(unittest.TestCase):
    def make_db(self, base: Path) -> Path:
        db_path = base / "candidates.db"
        apply_migrations(db_path)
        return db_path

    def add_run(
        self,
        db_path: Path,
        run_id: str,
        started_at: str,
        cost_estimate: str | None,
    ) -> None:
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                "INSERT INTO discovery_runs (run_id, channel_id, started_at, "
                "cost_estimate, status) VALUES (?, 'CHN-test', ?, ?, 'succeeded')",
                (run_id, started_at, cost_estimate),
            )
            connection.commit()
        finally:
            connection.close()

    def test_unconfigured_budget_is_distinct_from_zero_spend(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db_path = self.make_db(Path(temp))
            self.add_run(db_path, "RUN-1", "2026-08-03T12:00:00Z", "0")

            report = monthly_cost_report(db_path, as_of="2026-08-10")

            self.assertEqual("unconfigured", report.status)
            self.assertEqual(Decimal("0"), report.known_total)
            self.assertIsNone(report.budget)
            self.assertIsNone(report.utilization)

    def test_configured_budget_without_known_cost_is_no_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db_path = self.make_db(Path(temp))
            self.add_run(db_path, "RUN-1", "2026-08-03T12:00:00Z", None)

            report = monthly_cost_report(db_path, as_of="2026-08-10", budget="100")

            self.assertEqual("no_data", report.status)
            self.assertIsNone(report.known_total)
            self.assertEqual(1, report.record_count)
            self.assertEqual(1, report.unknown_record_count)
            self.assertEqual(0, report.invalid_record_count)

    def test_budget_thresholds_use_exact_decimal_boundaries(self) -> None:
        cases = (
            ("79.999", "ok", Decimal("0.79999")),
            ("80", "warning", Decimal("0.8")),
            ("99.999", "warning", Decimal("0.99999")),
            ("100", "exceeded", Decimal("1")),
        )
        for cost, expected_status, expected_utilization in cases:
            with self.subTest(cost=cost), tempfile.TemporaryDirectory() as temp:
                db_path = self.make_db(Path(temp))
                self.add_run(db_path, "RUN-1", "2026-08-03T12:00:00Z", cost)

                report = monthly_cost_report(db_path, as_of="2026-08-10", budget="100")

                self.assertEqual(expected_status, report.status)
                self.assertEqual(Decimal(cost), report.known_total)
                self.assertEqual(expected_utilization, report.utilization)

    def test_only_current_natural_month_is_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db_path = self.make_db(Path(temp))
            self.add_run(db_path, "RUN-jul", "2026-07-31T23:59:59Z", "90")
            self.add_run(db_path, "RUN-aug-1", "2026-08-01T00:00:00Z", "10.25")
            self.add_run(db_path, "RUN-aug-2", "2026-08-31T23:59:59Z", "20.75")
            self.add_run(db_path, "RUN-sep", "2026-09-01T00:00:00Z", "90")

            report = monthly_cost_report(db_path, as_of="2026-08-10", budget="100")

            self.assertEqual("2026-08-01", report.period_start)
            self.assertEqual("2026-08-31", report.period_end)
            self.assertEqual(2, report.record_count)
            self.assertEqual(Decimal("31.00"), report.known_total)
            self.assertEqual("ok", report.status)

    def test_invalid_costs_and_budgets_are_not_coerced(self) -> None:
        invalid_costs = ("bad", "-1", "NaN", "Infinity")
        for cost in invalid_costs:
            with self.subTest(cost=cost), tempfile.TemporaryDirectory() as temp:
                db_path = self.make_db(Path(temp))
                self.add_run(db_path, "RUN-1", "2026-08-03T12:00:00Z", cost)
                report = monthly_cost_report(db_path, as_of="2026-08-10", budget="100")
                self.assertEqual("invalid", report.status)
                self.assertIsNone(report.known_total)
                self.assertEqual(1, report.invalid_record_count)

        for budget in ("bad", "0", "-1", "NaN", "Infinity"):
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as temp:
                db_path = self.make_db(Path(temp))
                report = monthly_cost_report(db_path, as_of="2026-08-10", budget=budget)
                self.assertEqual("invalid", report.status)
                self.assertIsNone(report.budget)
                self.assertIsNone(report.utilization)

    def test_missing_database_is_reported_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "missing.db"

            report = monthly_cost_report(db_path, as_of="2026-08-10", budget="100")

            self.assertEqual("no_data", report.status)
            self.assertEqual(0, report.record_count)
            self.assertFalse(db_path.exists())


if __name__ == "__main__":
    unittest.main()
