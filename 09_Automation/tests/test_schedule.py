"""Tests for the B-021 channel schedule parser."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from research_os.services.schedule import (
    interval_from_schedule,
    is_due,
    next_run_at,
)

BASE = datetime(2026, 8, 6, 6, 0, 0, tzinfo=UTC)


class ScheduleTests(unittest.TestCase):
    def test_simple_intervals(self) -> None:
        self.assertEqual(timedelta(hours=1), interval_from_schedule("hourly"))
        self.assertEqual(timedelta(days=1), interval_from_schedule("daily"))
        self.assertEqual(timedelta(days=7), interval_from_schedule("weekly"))

    def test_every_n_units(self) -> None:
        self.assertEqual(
            timedelta(hours=6), interval_from_schedule("every 6 hours")
        )
        self.assertEqual(
            timedelta(minutes=30), interval_from_schedule("every 30 minutes")
        )
        self.assertEqual(
            timedelta(days=2), interval_from_schedule("every 2 days")
        )
        self.assertEqual(
            timedelta(weeks=1), interval_from_schedule("every 1 week")
        )

    def test_daily_nx(self) -> None:
        self.assertEqual(timedelta(hours=24), interval_from_schedule("daily 1x"))
        self.assertEqual(timedelta(hours=12), interval_from_schedule("daily 2x"))
        self.assertEqual(timedelta(hours=8), interval_from_schedule("daily 3x"))

    def test_unparseable_returns_none(self) -> None:
        self.assertIsNone(interval_from_schedule(""))
        self.assertIsNone(interval_from_schedule("asap"))
        self.assertIsNone(interval_from_schedule("daily 13x"))
        self.assertIsNone(interval_from_schedule("every 0 hours"))
        self.assertIsNone(interval_from_schedule("0 9 * * *"))

    def test_next_run_and_due(self) -> None:
        six_hours = interval_from_schedule("every 6 hours")
        assert six_hours is not None
        self.assertEqual(BASE + six_hours, next_run_at(BASE, "every 6 hours"))
        self.assertTrue(is_due(BASE, "every 6 hours", BASE + six_hours))
        self.assertFalse(
            is_due(
                BASE,
                "every 6 hours",
                BASE + six_hours - timedelta(minutes=1),
            )
        )

    def test_never_run_is_due_and_unparseable_is_not(self) -> None:
        self.assertTrue(is_due(None, "every 6 hours", BASE))
        self.assertFalse(is_due(BASE, "asap", BASE + timedelta(days=30)))


if __name__ == "__main__":
    unittest.main()
