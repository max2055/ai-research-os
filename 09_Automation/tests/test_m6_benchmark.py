from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research_os.services import benchmark as benchmark_service
from research_os.services.benchmark import (
    CandidateQueueBenchmark,
    _nearest_rank_p95,
    benchmark_candidate_queue,
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

    def test_candidate_queue_benchmark_uses_disposable_10k_fixture(self) -> None:
        root = Path(__file__).resolve().parents[2]
        real_db = root / "09_Automation" / "operational" / "candidates.db"
        before = (
            real_db.read_bytes() if real_db.is_file() else None,
            real_db.stat() if real_db.is_file() else None,
        )
        with (
            mock.patch.object(
                benchmark_service,
                "queue_rows",
                wraps=benchmark_service.queue_rows,
            ) as queue_spy,
            mock.patch.object(
                benchmark_service,
                "render_candidate_list",
                wraps=benchmark_service.render_candidate_list,
            ) as render_spy,
        ):
            result = benchmark_candidate_queue(
                root,
                rows=10_000,
                repeats=1,
                warmups=0,
                page_size=20,
                offset=20,
                max_seconds=10.0,
            )

        self.assertIsInstance(result, CandidateQueueBenchmark)
        self.assertEqual(10_000, result.rows)
        self.assertEqual(10_000, result.fixture_distribution["total_rows"])
        self.assertEqual(2, result.fixture_distribution["schema_version"])
        self.assertEqual(1, len(result.samples_seconds))
        self.assertEqual(result.samples_seconds[0], result.p95_seconds)
        self.assertTrue(result.query_plan)
        self.assertGreater(result.db_size_bytes, 0)
        self.assertTrue(result.environment["python"])
        self.assertEqual("temporary_directory", result.environment["fixture_storage"])
        self.assertEqual(
            result.environment["real_candidate_store"]["before"],
            result.environment["real_candidate_store"]["after"],
        )
        self.assertEqual((), result.authoritative_writes)
        self.assertTrue(result.real_candidate_store_unchanged)
        self.assertEqual(1, queue_spy.call_count)
        self.assertEqual(1, render_spy.call_count)
        after = (
            real_db.read_bytes() if real_db.is_file() else None,
            real_db.stat() if real_db.is_file() else None,
        )
        self.assertEqual(before, after)

    def test_candidate_queue_benchmark_uses_nearest_rank_p95(self) -> None:
        self.assertEqual(7.0, _nearest_rank_p95((7.0, 1.0, 3.0, 2.0)))
        self.assertEqual(18.0, _nearest_rank_p95(tuple(float(i) for i in range(20))))

    def test_candidate_queue_benchmark_rejects_invalid_inputs(self) -> None:
        root = Path.cwd()
        invalid = (
            {"rows": 0},
            {"repeats": 0},
            {"warmups": -1},
            {"page_size": 0},
            {"offset": -1},
            {"max_seconds": 0},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                benchmark_candidate_queue(root, **values)

    def test_cli_candidate_benchmark_emits_json(self) -> None:
        root = Path(__file__).resolve().parents[2]
        result = run_cli(
            root,
            "benchmark-candidates",
            "--rows",
            "100",
            "--repeats",
            "1",
            "--warmups",
            "0",
            "--page-size",
            "10",
            "--offset",
            "10",
            "--max-seconds",
            "10",
        )
        self.assertEqual(0, result.returncode, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(100, payload["rows"])
        self.assertEqual(1, len(payload["samples_seconds"]))
        self.assertEqual([], payload["authoritative_writes"])
        self.assertTrue(payload["real_candidate_store_unchanged"])
