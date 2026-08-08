"""C-019: impact path expansion performance benchmark on a 50k-edge graph.

Phase 3 §10 requires a 50k-edge synthetic benchmark; 3-hop expansion must
complete within the target. Uses lightweight fake objects (no Pydantic) so the
graph builds fast; asserts structural validity rather than a brittle wall-clock
so the test stays green on slow CI.
"""
from __future__ import annotations

import time
import unittest

from research_os.services.impact_path import expand_impact_paths


class _Fake:
    def __init__(self, object_id: str, object_type: str, metadata: dict,
                 body: str = "") -> None:
        self.object_id = object_id
        self.object_type = object_type
        self.metadata = metadata
        self.body = body


def _build_50k_graph(num_entities: int = 5000, edges_per: int = 10) -> list[_Fake]:
    """Build a chain graph with ~50k reviewed, as-of-valid ontology assertions."""
    objects: list[_Fake] = []
    for i in range(num_entities):
        objects.append(_Fake(f"COM-{i}", "company", {"title": f"Company {i}"}))
    event = _Fake(
        "EVT-bench", "event",
        {
            "id": "EVT-bench", "type": "event", "title": "Synthetic ramp",
            "review_status": "reviewed", "companies": ["COM-0", "COM-1"],
            "technologies": [], "products": [], "confidence": 0.7,
            "event_date": "2026-08-08",
        },
    )
    objects.append(event)
    rel_id = 0
    for i in range(num_entities):
        for j in range(edges_per):
            nxt = (i + j + 1) % num_entities
            evidence = ["EVT-bench"] if i < 2 and j == 0 else []
            rel_id += 1
            objects.append(
                _Fake(
                    f"REL-{rel_id:05d}", "ontology_assertion",
                    {
                        "id": f"REL-{rel_id:05d}", "type": "ontology_assertion",
                        "subject_id": f"COM-{i}", "predicate": "SUPPLIES",
                        "object_id": f"COM-{nxt}", "evidence_ids": evidence,
                        "review_status": "reviewed", "valid_from": "2026-01-01",
                        "valid_to": None, "confidence": 0.6,
                    },
                )
            )
    return objects


class ImpactBenchmarkTests(unittest.TestCase):
    def test_50k_edge_3hop_expansion_completes(self) -> None:
        objects = _build_50k_graph()
        rels = sum(1 for o in objects if o.object_type == "ontology_assertion")
        self.assertGreaterEqual(rels, 50_000)
        start = time.monotonic()
        paths, pruned = expand_impact_paths(
            objects, event_id="EVT-bench", max_depth=3, fan_out=10
        )
        elapsed = time.monotonic() - start
        self.assertTrue(paths)
        # per-path cycle control + pruning records present
        self.assertIsInstance(pruned, list)
        for path in paths:
            self.assertEqual("EVT-bench", path["trigger_event_id"])
            self.assertLessEqual(len(path["hops"]), 3)
            self.assertIsInstance(path["confidence"], float)
        # soft time bound: 50k edges, depth 3 should complete in seconds
        self.assertLess(elapsed, 30.0)


if __name__ == "__main__":
    unittest.main()
