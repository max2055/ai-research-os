from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_os.services.benchmark import (
    benchmark_dashboard,
    benchmark_repository,
    run_scale_benchmark,
)
from test_cli import run_cli


class ScaleBenchmarkTests(unittest.TestCase):
    def test_real_read_model_benchmark_reports_slo_without_writes(self) -> None:
        root = Path(__file__).resolve().parents[2]
        result = benchmark_dashboard(root, repeats=3)
        for operation in (
            "home",
            "candidate_queue",
            "company",
            "sector",
            "impact_3_hop",
            "validate",
            "index_render",
        ):
            measurement = result.measurements[operation]
            self.assertEqual(3, len(measurement.samples_seconds))
            self.assertGreaterEqual(measurement.p95_seconds, 0)
            self.assertGreater(measurement.threshold_seconds, 0)
        self.assertEqual([], result.authoritative_writes)
        self.assertGreater(result.scale["formal_objects"], 1000)
        self.assertTrue(result.measurements["home"].passed)
        self.assertTrue(result.measurements["company"].passed)

    def test_dashboard_benchmark_rejects_too_few_repeats(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 3"):
            benchmark_dashboard(Path.cwd(), repeats=2)

    def test_small_synthetic_repository_validates_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = benchmark_repository(
                Path(temp),
                sources=30,
                events=15,
                max_seconds=5,
            )
            self.assertTrue(result.passed)
            self.assertEqual(46, result.objects)
            self.assertEqual(0, result.validation_errors)

    def test_benchmark_rejects_invalid_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "events <= sources"):
            run_scale_benchmark(sources=2, events=3)

    def test_cli_benchmark_reports_machine_readable_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_cli(
                root,
                "benchmark",
                "--sources",
                "20",
                "--events",
                "10",
                "--max-seconds",
                "5",
            )
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("sources: 20", result.stdout)
            self.assertIn("events: 10", result.stdout)
            self.assertIn("passed: True", result.stdout)
