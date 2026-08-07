from __future__ import annotations

import unittest
from pathlib import Path

try:
    from research_os.services.impact_gate import (
        QUOTA,
        gate_metrics,
        gate_metrics_from_reviews,
        gate_sample,
        render_gate_packet,
    )
    from research_os.services.validation import load_objects
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Schema tests") from exc

ROOT = Path(__file__).resolve().parents[2]


class _Fake:
    def __init__(self, object_id: str, object_type: str, metadata: dict) -> None:
        self.object_id = object_id
        self.object_type = object_type
        self.metadata = metadata


class GateSampleTests(unittest.TestCase):
    """C-018: balanced sample selection + honest shortfall reporting."""

    def test_real_repo_assigns_events_and_reports_shortfalls(self) -> None:
        objects, findings = load_objects(ROOT)
        self.assertEqual([], findings)
        assigned, shortfalls = gate_sample(objects)
        self.assertTrue(assigned)
        for event_id, bucket in assigned.items():
            self.assertTrue(event_id.startswith("EVT-"))
            self.assertIn(bucket, QUOTA)
        self.assertIsInstance(shortfalls, list)

    def test_shortfall_reports_missing_buckets(self) -> None:
        objects, findings = load_objects(ROOT)
        self.assertEqual([], findings)
        _, shortfalls = gate_sample(objects)
        self.assertTrue(any("0/2" in line for line in shortfalls))


class GateMetricsTests(unittest.TestCase):
    """C-018: precision metrics vs §11 thresholds."""

    def test_metrics_compute_rates_and_pass(self) -> None:
        judgments = [
            {"event_id": f"EVT-{i}", "direct_precision": True,
             "mechanism_backed": True, "direction_ok": True,
             "horizon_ok": True, "contrary_omitted": False}
            for i in range(20)
        ]
        metrics = gate_metrics(judgments)
        self.assertEqual(20, metrics["n"])
        self.assertEqual(1.0, metrics["direct_precision"])
        self.assertTrue(metrics["gate_direct_precision"])
        self.assertTrue(metrics["gate_mechanism_backing"])
        self.assertTrue(metrics["gate_contrary_omissions"])

    def test_metrics_fail_below_threshold(self) -> None:
        judgments = [
            {"event_id": "EVT-1", "direct_precision": False,
             "mechanism_backed": True, "direction_ok": True,
             "horizon_ok": True, "contrary_omitted": True},
            {"event_id": "EVT-2", "direct_precision": True,
             "mechanism_backed": True, "direction_ok": True,
             "horizon_ok": True, "contrary_omitted": False},
        ]
        metrics = gate_metrics(judgments)
        self.assertEqual(0.5, metrics["direct_precision"])
        self.assertFalse(metrics["gate_direct_precision"])  # < 85%
        self.assertTrue(metrics["gate_mechanism_backing"])
        self.assertFalse(metrics["gate_contrary_omissions"])  # omission present

    def test_empty_judgments(self) -> None:
        self.assertEqual({}, gate_metrics([]))


class GateMetricsFromReviewsTests(unittest.TestCase):
    """Approve-rate proxy from review outcomes."""

    def test_approve_rate(self) -> None:
        objects = [
            _Fake("IMP-1", "impact_assertion", {"review_status": "reviewed"}),
            _Fake("IMP-2", "impact_assertion", {"review_status": "reviewed"}),
            _Fake("IMP-3", "impact_assertion", {"review_status": "rejected"}),
            _Fake("IMP-4", "impact_assertion", {"review_status": "pending"}),
        ]
        metrics = gate_metrics_from_reviews(objects)
        self.assertEqual(4, metrics["total"])
        self.assertEqual(2, metrics["approved"])
        self.assertEqual(0.5, metrics["approve_rate"])

    def test_no_impacts(self) -> None:
        self.assertEqual({}, gate_metrics_from_reviews([]))


class RenderGatePacketTests(unittest.TestCase):
    """C-018: packet is a reviewable human artifact."""

    def test_packet_contains_headers_and_rows(self) -> None:
        objects, findings = load_objects(ROOT)
        self.assertEqual([], findings)
        assigned, _ = gate_sample(objects)
        packet = render_gate_packet(objects, bucket_map=assigned)
        self.assertIn("# C-018 Field Gate", packet)
        self.assertIn("| Event | 桶 | 事件 |", packet)
        self.assertIn("全部 approve", packet)
        self.assertTrue(packet.count("| EVT-") >= 1)


if __name__ == "__main__":
    unittest.main()
