"""Tests for the B-014 candidate dedup service."""

from __future__ import annotations

import unittest

from research_os.services.dedup import assign_clusters, normalize_title


class DedupTests(unittest.TestCase):
    def test_normalize_title_lowercases_and_strips_punctuation(self) -> None:
        self.assertEqual(
            "sk hynix unveils first hbf standard specifications "
            "with sandisk presenting ai memory solutions",
            normalize_title(
                "SK hynix Unveils First HBF Standard Specifications "
                "with Sandisk, Presenting AI Memory Solutions"
            ),
        )

    def test_normalize_title_drops_trailing_variant_suffix(self) -> None:
        self.assertEqual(
            normalize_title("SK hynix Q2 2026 Results -01"),
            normalize_title("SK hynix Q2 2026 Results -02"),
        )
        self.assertEqual(
            "sk hynix q2 2026 results",
            normalize_title("SK hynix Q2 2026 Results -02"),
        )

    def test_exact_url_shares_cluster(self) -> None:
        candidates = [
            {"title": "Alpha", "canonical_url": "https://a.example/x",
             "content_fingerprint": "fp1"},
            {"title": "Alpha", "canonical_url": "https://a.example/x",
             "content_fingerprint": "fp2"},
            {"title": "Beta", "canonical_url": "https://b.example/y",
             "content_fingerprint": "fp3"},
        ]
        result = assign_clusters(candidates)
        clusters = [c["duplicate_cluster_id"] for c in result]
        self.assertEqual(clusters[0], clusters[1])
        self.assertNotEqual(clusters[0], clusters[2])

    def test_exact_fingerprint_shares_cluster(self) -> None:
        candidates = [
            {"title": "One", "canonical_url": "https://a/1",
             "content_fingerprint": "same"},
            {"title": "Two", "canonical_url": "https://a/2",
             "content_fingerprint": "same"},
        ]
        result = assign_clusters(candidates)
        self.assertEqual(
            result[0]["duplicate_cluster_id"],
            result[1]["duplicate_cluster_id"],
        )

    def test_near_title_variants_cluster_together(self) -> None:
        candidates = [
            {"title": "SK hynix Q2 2026 Results",
             "canonical_url": "https://a/1", "content_fingerprint": "f1"},
            {"title": "SK hynix Q2 2026 Results -01",
             "canonical_url": "https://a/1-01", "content_fingerprint": "f2"},
            {"title": "SK hynix Q2 2026 Results -02",
             "canonical_url": "https://a/1-02", "content_fingerprint": "f3"},
        ]
        result = assign_clusters(candidates)
        clusters = {c["duplicate_cluster_id"] for c in result}
        self.assertEqual(1, len(clusters))

    def test_cross_run_existing_cluster_is_extended(self) -> None:
        run1 = assign_clusters(
            [{"title": "SK hynix HBF FMS 2026", "canonical_url": "https://a/hbf",
              "content_fingerprint": "f1"}]
        )
        cluster1 = run1[0]["duplicate_cluster_id"]
        existing = {normalize_title("SK hynix HBF FMS 2026"): cluster1}
        run2 = assign_clusters(
            [{"title": "SK hynix HBF FMS 2026 -01",
              "canonical_url": "https://a/hbf-01", "content_fingerprint": "f2"}],
            existing=existing,
        )
        self.assertEqual(cluster1, run2[0]["duplicate_cluster_id"])

    def test_no_candidate_is_dropped(self) -> None:
        candidates = [
            {"title": "A", "canonical_url": "https://a/1", "content_fingerprint": "f1"},
            {"title": "A", "canonical_url": "https://a/2", "content_fingerprint": "f2"},
            {"title": "B", "canonical_url": "https://b/1", "content_fingerprint": "f3"},
        ]
        result = assign_clusters(candidates)
        self.assertEqual(3, len(result))
        self.assertTrue(all("duplicate_cluster_id" in c for c in result))


if __name__ == "__main__":
    unittest.main()
