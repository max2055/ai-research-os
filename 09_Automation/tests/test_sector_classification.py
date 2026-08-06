"""Tests for the B-016 sector classification service."""

from __future__ import annotations

import unittest

from research_os.services.sector_classification import (
    SectorIndex,
    classify,
)


class _FakeSector:
    def __init__(self, object_id: str, metadata: dict) -> None:
        self.object_id = object_id
        self.metadata = metadata


class SectorClassificationTests(unittest.TestCase):
    def _index(self) -> SectorIndex:
        sectors = [
            _FakeSector(
                "SEG-memory-storage",
                {"in_scope": ["HBM", "DRAM", "NAND"], "definition": ""},
            ),
            _FakeSector(
                "SEG-compute-silicon",
                {"in_scope": ["GPU", "ASIC", "CPU"], "definition": ""},
            ),
            _FakeSector(
                "SEG-cloud-ai-infrastructure",
                {"in_scope": ["cloud", "inference"], "definition": ""},
            ),
            _FakeSector(
                "SEG-foundry-packaging-test",
                {"in_scope": ["foundry", "advanced-packaging"], "definition": ""},
            ),
        ]
        return SectorIndex.from_objects(sectors)

    def test_single_sector_match(self) -> None:
        index = self._index()
        result = classify(index, title="SK hynix HBM4 for NVIDIA")
        self.assertEqual(["SEG-memory-storage"], result["sector_ids"])
        self.assertIn("hbm", result["reasons"]["SEG-memory-storage"])

    def test_multi_label_match(self) -> None:
        index = self._index()
        result = classify(index, title="NVIDIA GPU and HBM supply")
        sector_ids = result["sector_ids"]
        self.assertIn("SEG-compute-silicon", sector_ids)
        self.assertIn("SEG-memory-storage", sector_ids)

    def test_unknown_when_no_match(self) -> None:
        index = self._index()
        result = classify(index, title="Quantum computing startup raises funding")
        self.assertEqual([], result["sector_ids"])
        self.assertEqual({}, result["reasons"])

    def test_hyphenated_keyword_also_matches_spaced(self) -> None:
        index = self._index()
        result = classify(index, title="TSMC advanced packaging revenue")
        self.assertEqual(["SEG-foundry-packaging-test"], result["sector_ids"])

    def test_reason_records_keyword_hits(self) -> None:
        index = self._index()
        result = classify(index, title="Micron DRAM and NAND prices rise")
        reasons = result["reasons"]["SEG-memory-storage"]
        self.assertIn("dram", reasons)
        self.assertIn("nand", reasons)


if __name__ == "__main__":
    unittest.main()
