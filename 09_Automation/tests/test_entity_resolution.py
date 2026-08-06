"""Tests for the B-015 entity resolution service."""

from __future__ import annotations

import unittest

from research_os.services.entity_resolution import (
    EntityIndex,
    resolve,
)


class _FakeCompany:
    def __init__(self, object_id: str, metadata: dict) -> None:
        self.object_id = object_id
        self.metadata = metadata


class EntityResolutionTests(unittest.TestCase):
    def _index(self) -> EntityIndex:
        companies = [
            _FakeCompany("COM-nvidia", {"title": "NVIDIA", "aliases": ["NVDA"]}),
            _FakeCompany("COM-tsmc", {"title": "TSMC", "aliases": ["台积电"]}),
            _FakeCompany("COM-sk-hynix", {"title": "SK hynix", "aliases": []}),
            _FakeCompany("COM-microsoft", {"title": "Microsoft", "aliases": ["MSFT"]}),
            _FakeCompany(
                "COM-aliyun",
                {"title": "Alibaba Cloud (阿里云)", "aliases": []},
            ),
        ]
        return EntityIndex.from_objects(companies)

    def test_matched_by_title(self) -> None:
        index = self._index()
        result = resolve(index, title="NVIDIA reports record Q1 earnings")
        self.assertEqual("matched", result["status"])
        self.assertEqual("COM-nvidia", result["entity_id"])

    def test_matched_by_ticker_alias(self) -> None:
        index = self._index()
        result = resolve(index, title="MSFT Azure AI infrastructure investment")
        self.assertEqual("matched", result["status"])
        self.assertEqual("COM-microsoft", result["entity_id"])

    def test_matched_by_chinese_name(self) -> None:
        index = self._index()
        result = resolve(index, title="台积电先进制程营收占比")
        self.assertEqual("matched", result["status"])
        self.assertEqual("COM-tsmc", result["entity_id"])

    def test_matched_publisher(self) -> None:
        index = self._index()
        result = resolve(index, title="2Q26 financial results", publisher="SK hynix")
        self.assertEqual("matched", result["status"])
        self.assertEqual("COM-sk-hynix", result["entity_id"])

    def test_ambiguous_when_multiple_entities(self) -> None:
        index = self._index()
        # "SK hynix" and a generic token both match when title mentions both
        result = resolve(index, title="SK hynix vs TSMC HBM competition")
        self.assertEqual("ambiguous", result["status"])
        self.assertIsNone(result["entity_id"])

    def test_unknown_when_no_match(self) -> None:
        index = self._index()
        result = resolve(index, title="Quantum computing startup raises funding")
        self.assertEqual("unknown", result["status"])
        self.assertIsNone(result["entity_id"])

    def test_chinese_paren_title_parses(self) -> None:
        index = self._index()
        result = resolve(index, title="阿里云百炼上新 DeepSeek 模型")
        self.assertEqual("matched", result["status"])
        self.assertEqual("COM-aliyun", result["entity_id"])


if __name__ == "__main__":
    unittest.main()
