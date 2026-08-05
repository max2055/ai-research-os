from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_os.services.benchmark import (
    benchmark_repository,
    run_scale_benchmark,
)
from test_cli import run_cli


class ScaleBenchmarkTests(unittest.TestCase):
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
