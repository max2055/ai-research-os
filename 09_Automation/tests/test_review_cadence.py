"""Review cadence: auto-roll next_review_date forward (D-020 follow-up).

The overview was showing a stale next_review_date (PRJ-001 08-05) because it is
a stored field with no advancement logic. The service derives the current next
review date by rolling an overdue stored date forward by the cadence (Weekly 7d,
Monthly 30d), displays it without writing, and persists atomically with --apply.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from research_os.domain.models import ResearchObject
    from research_os.services.review_cadence import (
        advance_review_date,
        cadence_days,
        current_next_review_date,
        prepare_review_date_update,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest(
        "install product dependencies to run cadence tests"
    ) from exc

ROOT = Path(__file__).resolve().parents[2]


def _project(
    next_review_date: str, *, cadence: str = "Weekly + Monthly"
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / "05_Research/Projects/PRJ-001.md",
        metadata={
            "id": "PRJ-001",
            "type": "project",
            "title": "P",
            "next_review_date": next_review_date,
            "review_cadence": cadence,
            "status": "active",
        },
        body="",
    )


class CadenceDaysTests(unittest.TestCase):
    def test_periods(self) -> None:
        self.assertEqual(7, cadence_days("Weekly + Monthly"))
        self.assertEqual(7, cadence_days("Weekly"))
        self.assertEqual(30, cadence_days("Monthly"))
        self.assertEqual(7, cadence_days("Quarterly"))


class CurrentNextReviewDateTests(unittest.TestCase):
    def test_future_date_unchanged(self) -> None:
        self.assertEqual(
            "2026-08-20",
            current_next_review_date(_project("2026-08-20"), today="2026-08-09"),
        )

    def test_overdue_rolls_forward_weekly(self) -> None:
        # 08-05 overdue on 08-09 -> next weekly boundary 08-12
        self.assertEqual(
            "2026-08-12",
            current_next_review_date(_project("2026-08-05"), today="2026-08-09"),
        )

    def test_overdue_multiple_periods(self) -> None:
        # far overdue: 07-01 on 08-09 -> rolls weekly to 08-12
        self.assertEqual(
            "2026-08-12",
            current_next_review_date(_project("2026-07-01"), today="2026-08-09"),
        )

    def test_monthly_cadence(self) -> None:
        self.assertEqual(
            "2026-08-30",
            current_next_review_date(
                _project("2026-07-31", cadence="Monthly"), today="2026-08-09"
            ),
        )

    def test_no_stored_date(self) -> None:
        self.assertEqual("", current_next_review_date(_project(""), today="2026-08-09"))


class AdvanceReviewDateTests(unittest.TestCase):
    def test_apply_writes_atomically_and_returns_path(self) -> None:
        import test_research_os_core as fixtures

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures.write(root / "00_System" / "Taxonomy.md", fixtures.TAXONOMY)
            fixtures.write(
                root / "05_Research" / "Projects" / "PRJ-001.md",
                fixtures.project(),  # already next_review_date: 2026-08-05
            )

            written = advance_review_date(root, "PRJ-001", today="2026-08-09")
            self.assertIsNotNone(written)
            self.assertIn("2026-08-12", written.read_text(encoding="utf-8"))
            # second run: already current -> None
            self.assertIsNone(advance_review_date(root, "PRJ-001", today="2026-08-09"))

    def test_dry_run_returns_preview_no_write(self) -> None:
        import test_research_os_core as fixtures

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures.write(root / "00_System" / "Taxonomy.md", fixtures.TAXONOMY)
            fixtures.write(
                root / "05_Research" / "Projects" / "PRJ-001.md",
                fixtures.project(),
            )
            path = root / "05_Research" / "Projects" / "PRJ-001.md"
            prepared = prepare_review_date_update(root, "PRJ-001", today="2026-08-09")
            self.assertIsNotNone(prepared)
            computed, relative, content = prepared
            self.assertEqual("2026-08-12", computed)
            self.assertIn("2026-08-12", content)
            # nothing written
            self.assertNotIn("2026-08-12", path.read_text(encoding="utf-8"))

    def test_unknown_project_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                advance_review_date(root, "PRJ-999", today="2026-08-09")


if __name__ == "__main__":
    unittest.main()
