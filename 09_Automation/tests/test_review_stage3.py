from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "review_stage3.py"
SPEC = importlib.util.spec_from_file_location("review_stage3", SCRIPT)
assert SPEC and SPEC.loader
review_stage3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = review_stage3
SPEC.loader.exec_module(review_stage3)


def event_text(event_id: str, review_status: str = "pending") -> str:
    return f"""---
id: {event_id}
type: event
title: Test
created_at: 2026-07-29
updated_at: 2026-07-29
status: active
review_status: {review_status}
---

# Event
"""


class ReviewStage3Tests(unittest.TestCase):
    def test_packet_parses_valid_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            packet = Path(temp) / "packet.md"
            packet.write_text(
                "| [x] | EVT-20260729-001 | fact | THS-001 | none | approve |\n"
                "| [x] | EVT-20260729-002 | fact | THS-002 | none | "
                "reject: duplicate |\n",
                encoding="utf-8",
            )
            decisions = review_stage3.parse_packet(packet)
            self.assertEqual(["approve", "reject"], [item.action for item in decisions])
            self.assertEqual("duplicate", decisions[1].detail)

    def test_checkbox_and_decision_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            packet = Path(temp) / "packet.md"
            packet.write_text(
                "| [ ] | EVT-20260729-001 | fact | THS-001 | none | approve |\n",
                encoding="utf-8",
            )
            with self.assertRaises(review_stage3.ReviewError):
                review_stage3.parse_packet(packet)

    def test_apply_requires_edit_requests_to_be_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            events = root / "04_Evidence" / "Events"
            events.mkdir(parents=True)
            path = events / "EVT-20260729-001-test.md"
            path.write_text(event_text("EVT-20260729-001"), encoding="utf-8")
            decisions = [
                review_stage3.Decision(
                    "EVT-20260729-001", True, "edit", "rewrite inference"
                )
            ]
            errors = review_stage3.validate(
                decisions, review_stage3.event_files(root), applying=True
            )
            self.assertIn("edit requested", errors[0])

    def test_apply_records_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "EVT-20260729-001-test.md"
            path.write_text(event_text("EVT-20260729-001"), encoding="utf-8")
            changed = review_stage3.apply_decision(
                path,
                review_stage3.Decision("EVT-20260729-001", True, "approve", ""),
                "Researcher",
                "2026-07-30",
            )
            result = path.read_text(encoding="utf-8")
            self.assertTrue(changed)
            self.assertIn("review_status: reviewed", result)
            self.assertIn("updated_at: 2026-07-30", result)
            self.assertIn("- Reviewer: Researcher", result)

    def test_packet_must_cover_all_event_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            events = root / "04_Evidence" / "Events"
            events.mkdir(parents=True)
            for number in (1, 2):
                event_id = f"EVT-20260729-{number:03d}"
                (events / f"{event_id}-test.md").write_text(
                    event_text(event_id), encoding="utf-8"
                )
            decisions = [
                review_stage3.Decision("EVT-20260729-001", False, "pending", "")
            ]
            errors = review_stage3.validate(
                decisions, review_stage3.event_files(root), applying=False
            )
            self.assertIn("EVT-20260729-002", errors[0])


if __name__ == "__main__":
    unittest.main()
