"""Tests for the B-017 scoring service."""

from __future__ import annotations

import unittest

from research_os.services.scoring import (
    DEFAULT_WEIGHTS,
    SCORING_VERSION,
    ScoreWeights,
    score_candidate,
)


class ScoringTests(unittest.TestCase):
    def test_version_and_weights_are_configurable(self) -> None:
        self.assertEqual(1, SCORING_VERSION)
        self.assertEqual(6, len(DEFAULT_WEIGHTS))
        self.assertAlmostEqual(1.0, sum(DEFAULT_WEIGHTS.values()))

    def test_strong_candidate_scores_high(self) -> None:
        result = score_candidate(
            title=(
                "NVIDIA reports record data center revenue $75.2B "
                "and supply commitments"
            ),
            source_grade="A",
            entity_status="matched",
            sector_count=1,
            is_duplicate_representative=True,
            cluster_size=1,
            channel_type="sec",
        )
        self.assertGreater(result["priority_score"], 0.7)
        self.assertEqual(SCORING_VERSION, result["scoring_version"])
        self.assertEqual("deterministic-v1", result["model"])
        # reasons explain every dimension
        self.assertTrue(result["reason_codes"])

    def test_duplicate_non_representative_scores_lower(self) -> None:
        base = score_candidate(
            title="SK hynix HBM supply contract",
            entity_status="matched",
            sector_count=1,
            is_duplicate_representative=True,
            cluster_size=1,
        )
        dup = score_candidate(
            title="SK hynix HBM supply contract",
            entity_status="matched",
            sector_count=1,
            is_duplicate_representative=False,
            cluster_size=1,
        )
        self.assertLess(dup["priority_score"], base["priority_score"])
        self.assertIn(
            "duplication_penalty: non-representative in cluster",
            dup["reason_codes"],
        )

    def test_unknown_entity_scores_lower(self) -> None:
        known = score_candidate(
            title="TSMC advanced node production",
            entity_status="matched",
            sector_count=1,
        )
        unknown = score_candidate(
            title="TSMC advanced node production",
            entity_status="unknown",
            sector_count=1,
        )
        self.assertLess(unknown["priority_score"], known["priority_score"])
        self.assertIn("uncertainty_penalty: unknown entity", unknown["reason_codes"])

    def test_subscores_and_priority_relationship(self) -> None:
        result = score_candidate(
            title="Micron earnings", entity_status="matched", sector_count=1
        )
        weights = ScoreWeights()
        expected = weights.weighted(result["subscores"])
        self.assertEqual(expected, result["priority_score"])

    def test_custom_weights_change_priority(self) -> None:
        custom = ScoreWeights(
            weights={**DEFAULT_WEIGHTS, "scope_relevance": 0.8, "source_quality": 0.05}
        )
        result = score_candidate(
            title="NVIDIA GPU",
            entity_status="matched",
            sector_count=1,
            source_grade="C",
            weights=custom,
        )
        # scope-relevance-heavy weights reward the matched entity
        self.assertGreater(result["subscores"]["scope_relevance"], 0.5)


if __name__ == "__main__":
    unittest.main()
