from __future__ import annotations

import unittest
from pathlib import Path

try:
    from research_os.domain.policies import (
        DEFAULT_IMPACT_DIRECTION,
        PRIMARY_IMPACT_TYPE,
    )
    from research_os.services.impact_path import (
        dedup_paths,
        detect_contradictions,
        expand_impact_paths,
        is_valid_as_of,
        path_confidence,
    )
    from research_os.services.impact_proposal import validate_mechanism
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Schema tests") from exc

ROOT = Path(__file__).resolve().parents[2]


class _Fake:
    def __init__(self, object_id: str, object_type: str, metadata: dict) -> None:
        self.object_id = object_id
        self.object_type = object_type
        self.metadata = metadata


def _event(**extra: object) -> _Fake:
    meta: dict[str, object] = {
        "id": "EVT-1",
        "type": "event",
        "title": "ASML EUV platform ramp",
        "review_status": "reviewed",
        "companies": ["COM-a", "COM-b"],
        "technologies": [],
        "products": [],
        "confidence": 0.7,
        "event_date": "2026-08-01",
    }
    meta.update(extra)
    return _Fake("EVT-1", "event", meta)


def _rel(rel_id: str, **extra: object) -> _Fake:
    meta: dict[str, object] = {
        "id": rel_id,
        "type": "ontology_assertion",
        "subject_id": "COM-a",
        "predicate": "SUPPLIES",
        "object_id": "COM-b",
        "evidence_ids": ["EVT-1"],
        "review_status": "reviewed",
        "valid_from": "2026-01-01",
        "valid_to": None,
        "confidence": 0.6,
    }
    meta.update(extra)
    return _Fake(rel_id, "ontology_assertion", meta)


def _entities() -> list[_Fake]:
    return [
        _Fake("COM-a", "company", {"title": "Alpha"}),
        _Fake("COM-b", "company", {"title": "Beta"}),
        _Fake("COM-c", "company", {"title": "Gamma"}),
        _Fake("TEC-x", "technology", {"title": "Tech-X"}),
    ]


def _three_hop_graph() -> list[_Fake]:
    """EVT-1 -> (COM-a, COM-b); COM-b USES TEC-x; TEC-x CONSTRAINS COM-c."""
    return [
        _event(),
        _rel("REL-1"),  # COM-a SUPPLIES COM-b, evidence=EVT-1 (bridge)
        _rel(
            "REL-2",
            subject_id="COM-b",
            predicate="USES",
            object_id="TEC-x",
            evidence_ids=[],
            confidence=0.5,
        ),
        _rel(
            "REL-3",
            subject_id="TEC-x",
            predicate="CONSTRAINS",
            object_id="COM-c",
            evidence_ids=[],
            confidence=0.4,
        ),
        *_entities(),
    ]


class TemporalFilterTests(unittest.TestCase):
    """C-007: valid_from/valid_to windows."""

    def test_open_ended_window(self) -> None:
        self.assertTrue(
            is_valid_as_of({"valid_from": "2026-01-01", "valid_to": None}, "2026-06-01")
        )

    def test_within_window(self) -> None:
        meta = {"valid_from": "2026-01-01", "valid_to": "2026-12-31"}
        self.assertTrue(is_valid_as_of(meta, "2026-06-01"))

    def test_before_valid_from(self) -> None:
        self.assertFalse(is_valid_as_of({"valid_from": "2026-06-01"}, "2026-01-01"))

    def test_after_valid_to(self) -> None:
        self.assertFalse(is_valid_as_of({"valid_to": "2026-06-01"}, "2026-12-31"))

    def test_missing_window_is_open(self) -> None:
        self.assertTrue(is_valid_as_of({}, "2026-06-01"))


class PathExpansionTests(unittest.TestCase):
    """C-006: BFS expansion, cycle/fan-out control, pruning records."""

    def test_default_max_depth_3_is_multi_hop_active(self) -> None:
        paths, pruned = expand_impact_paths(_three_hop_graph(), event_id="EVT-1")
        depths = sorted(len(p["hops"]) for p in paths)
        self.assertIn(3, depths)  # multi-hop active since C-018 approval
        self.assertIsInstance(pruned, list)

    def test_max_depth_2_expands_neighbors(self) -> None:
        paths, _ = expand_impact_paths(
            _three_hop_graph(), event_id="EVT-1", max_depth=2
        )
        depths = sorted(len(p["hops"]) for p in paths)
        self.assertIn(2, depths)
        deep = [p for p in paths if len(p["hops"]) == 2]
        self.assertTrue(any(p["terminal_id"] == "TEC-x" for p in deep))

    def test_max_depth_3_reaches_terminal(self) -> None:
        paths, _ = expand_impact_paths(
            _three_hop_graph(), event_id="EVT-1", max_depth=3
        )
        deep = [p for p in paths if p["terminal_id"] == "COM-c"]
        self.assertTrue(deep)
        self.assertEqual(3, len(deep[0]["hops"]))
        self.assertEqual(
            ["EVT-1", "COM-b", "TEC-x", "COM-c"], deep[0]["entity_sequence"]
        )

    def test_hop_semantics_come_from_rule_map(self) -> None:
        paths, _ = expand_impact_paths(
            _three_hop_graph(), event_id="EVT-1", max_depth=3
        )
        for path in paths:
            for hop in path["hops"]:
                self.assertEqual(
                    PRIMARY_IMPACT_TYPE[hop["predicate"]], hop["impact_type"]
                )
                self.assertEqual(
                    DEFAULT_IMPACT_DIRECTION[hop["predicate"]], hop["direction"]
                )
                self.assertEqual("unknown", hop["horizon"])
                self.assertEqual([], validate_mechanism(hop["mechanism"]))

    def test_cycle_is_pruned_per_path(self) -> None:
        objects = [
            _event(),
            _rel("REL-1"),
            _rel(
                "REL-4",
                subject_id="COM-b",
                predicate="SUPPLIES",
                object_id="COM-a",
                evidence_ids=[],
            ),
            *_entities(),
        ]
        paths, _ = expand_impact_paths(objects, event_id="EVT-1", max_depth=3)
        # COM-a -> COM-b (REL-1); COM-b -> COM-a (REL-4) is a cycle on that path.
        target = next(
            p for p in paths if p["entity_sequence"] == ["EVT-1", "COM-a", "COM-b"]
        )
        self.assertIn("cycle", [r["reason"] for r in target["pruned"]])

    def test_fan_out_cap_is_recorded(self) -> None:
        objects = [
            _event(),
            _rel("REL-1"),
            _rel(
                "REL-2",
                subject_id="COM-b",
                predicate="USES",
                object_id="TEC-x",
                evidence_ids=[],
            ),
            _rel(
                "REL-5a",
                subject_id="COM-b",
                predicate="SUPPLIES",
                object_id="COM-d1",
                evidence_ids=[],
            ),
            _rel(
                "REL-5b",
                subject_id="COM-b",
                predicate="SUPPLIES",
                object_id="COM-d2",
                evidence_ids=[],
            ),
            _rel(
                "REL-5c",
                subject_id="COM-b",
                predicate="SUPPLIES",
                object_id="COM-d3",
                evidence_ids=[],
            ),
            *_entities(),
            _Fake("COM-d1", "company", {"title": "D1"}),
            _Fake("COM-d2", "company", {"title": "D2"}),
            _Fake("COM-d3", "company", {"title": "D3"}),
        ]
        paths, _ = expand_impact_paths(
            objects, event_id="EVT-1", max_depth=2, fan_out=2
        )
        # COM-b has 4 adjacency entries (USES + 3 SUPPLIES); fan_out=2 caps to 2.
        capped = [
            p
            for p in paths
            if any(r["reason"] == "fan-out-capped" for r in p["pruned"])
        ]
        self.assertTrue(capped)
        self.assertIn("cut", capped[0]["pruned"][0])
        # Each terminal expanded at most fan_out new neighbors.
        expanded = [p for p in paths if len(p["hops"]) == 2]
        self.assertLessEqual(len(expanded), 4)  # 2 direct x min(fan_out, neighbors)

    def test_skips_non_reviewed_relation(self) -> None:
        objects = [
            _event(),
            _rel("REL-1", review_status="pending"),
            *_entities(),
        ]
        paths, _ = expand_impact_paths(objects, event_id="EVT-1")
        self.assertEqual([], paths)

    def test_skips_as_of_invalid_relation(self) -> None:
        objects = [
            _event(),
            _rel("REL-1", valid_to="2026-01-01"),
            *_entities(),
        ]
        paths, _ = expand_impact_paths(objects, event_id="EVT-1", as_of="2026-06-01")
        self.assertEqual([], paths)

    def test_no_rule_map_predicate_is_pruned_and_reported(self) -> None:
        objects = [
            _event(),
            _rel("REL-1", predicate="RELATES_TO"),
            *_entities(),
        ]
        paths, pruned = expand_impact_paths(objects, event_id="EVT-1")
        self.assertEqual([], paths)
        self.assertTrue(pruned)
        self.assertTrue(all(r["reason"] == "no-rule-map-predicate" for r in pruned))

    def test_rejects_pending_event(self) -> None:
        objects = [_event(review_status="pending"), _rel("REL-1"), *_entities()]
        with self.assertRaises(ValueError):
            expand_impact_paths(objects, event_id="EVT-1")

    def test_rejects_unknown_event(self) -> None:
        with self.assertRaises(ValueError):
            expand_impact_paths(_three_hop_graph(), event_id="EVT-missing")

    def test_rejects_max_depth_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            expand_impact_paths(_three_hop_graph(), event_id="EVT-1", max_depth=4)

    def test_confidence_is_weakest_link(self) -> None:
        paths, _ = expand_impact_paths(
            _three_hop_graph(), event_id="EVT-1", max_depth=3
        )
        terminal = [p for p in paths if p["terminal_id"] == "COM-c"][0]
        self.assertEqual(0.4, terminal["confidence"])  # min of 0.6/0.5/0.4


class DedupTests(unittest.TestCase):
    """C-009: same entity sequence + same relation sequence folds."""

    def _paths(self) -> list[dict]:
        a_to_b = {
            "entity_sequence": ["EVT-1", "COM-a", "COM-b"],
            "hops": [{"rel_id": "REL-1"}],
        }
        b_to_tech = {
            "entity_sequence": ["EVT-1", "COM-b", "TEC-x"],
            "hops": [{"rel_id": "REL-2"}],
        }
        return [a_to_b, a_to_b, b_to_tech]

    def test_identical_path_folds_with_variant_count(self) -> None:
        deduped = dedup_paths(self._paths())
        self.assertEqual(2, len(deduped))
        reps = {p["entity_sequence"][-1]: p["variant_count"] for p in deduped}
        self.assertEqual(2, reps["COM-b"])
        self.assertEqual(1, reps["TEC-x"])


class ContradictionTests(unittest.TestCase):
    """C-008: positive+negative and multi-horizon coexist are surfaced."""

    def _imp(self, target: str, direction: str, horizon: str) -> dict:
        return {"target_id": target, "direction": direction, "horizon": horizon}

    def test_direction_conflict_surfaced(self) -> None:
        conflicts = detect_contradictions(
            [
                self._imp("COM-a", "positive", "quarter"),
                self._imp("COM-a", "negative", "quarter"),
            ]
        )
        self.assertEqual(1, len(conflicts))
        self.assertEqual("COM-a", conflicts[0]["target_id"])
        self.assertIn("positive-and-negative-coexist", conflicts[0]["conflicts"])

    def test_multiple_horizons_surfaced(self) -> None:
        conflicts = detect_contradictions(
            [
                self._imp("COM-a", "positive", "quarter"),
                self._imp("COM-a", "positive", "year"),
            ]
        )
        self.assertEqual(1, len(conflicts))
        self.assertIn("multiple-horizons-coexist", conflicts[0]["conflicts"])

    def test_no_conflict_when_single_direction_and_unknown_horizon(self) -> None:
        conflicts = detect_contradictions(
            [
                self._imp("COM-a", "positive", "unknown"),
                self._imp("COM-a", "mixed", "unknown"),
            ]
        )
        self.assertEqual([], conflicts)

    def test_empty_input(self) -> None:
        self.assertEqual([], detect_contradictions([]))


class PathConfidenceTests(unittest.TestCase):
    """C-010: weakest-link, never the product; unknown hop => None."""

    def test_min_of_hop_confidences(self) -> None:
        path = {"hops": [{"confidence": 0.6}, {"confidence": 0.4}, {"confidence": 0.5}]}
        self.assertEqual(0.4, path_confidence(path))

    def test_unknown_hop_yields_none(self) -> None:
        path = {"hops": [{"confidence": 0.6}, {"confidence": None}]}
        self.assertIsNone(path_confidence(path))

    def test_empty_hops_yield_none(self) -> None:
        self.assertIsNone(path_confidence({"hops": []}))


class RealRepositorySmokeTests(unittest.TestCase):
    """Real data: EVT-20260225-034 direct paths; depth-2 on real REL graph."""

    def test_real_event_multi_hop_paths(self) -> None:
        from research_os.services.validation import load_objects

        objects, findings = load_objects(ROOT)
        self.assertEqual([], findings)
        # default max_depth=3 (multi-hop active since C-018 approval)
        paths, pruned = expand_impact_paths(objects, event_id="EVT-20260225-034")
        self.assertTrue(paths)
        # direct (depth 1) paths still reach the event's own entities
        direct = [p for p in paths if len(p["hops"]) == 1]
        self.assertTrue(direct)
        for path in direct:
            self.assertIn(path["terminal_id"], {"COM-asml", "COM-tsmc"})
        # and multi-hop extends beyond them
        multi = [p for p in paths if len(p["hops"]) >= 2]
        self.assertTrue(multi)
        for path in paths:
            for hop in path["hops"]:
                self.assertEqual([], validate_mechanism(hop["mechanism"]))
        self.assertIsInstance(pruned, list)


if __name__ == "__main__":
    unittest.main()
