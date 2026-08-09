"""Synthetic scale benchmark for repository validation and index rendering."""

from __future__ import annotations

import math
import sqlite3
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from research_os.services.candidate_db import candidate_db_path
from research_os.services.candidate_queue import queue_rows
from research_os.services.indexing import render_indexes, render_project_indexes
from research_os.services.read_model import (
    company_snapshot,
    impact_explorer_snapshot,
    industry_home_snapshot,
    sector_snapshot,
)
from research_os.services.validation import validate_repository


@dataclass(frozen=True)
class BenchmarkResult:
    sources: int
    events: int
    objects: int
    validation_errors: int
    validation_seconds: float
    global_index_seconds: float
    project_index_seconds: float
    total_query_seconds: float
    passed: bool
    max_seconds: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SloMeasurement:
    samples_seconds: list[float]
    p95_seconds: float
    threshold_seconds: float
    passed: bool


@dataclass(frozen=True)
class DashboardBenchmark:
    repeats: int
    scale: dict[str, int]
    measurements: dict[str, SloMeasurement]
    authoritative_writes: list[str]

    @property
    def passed(self) -> bool:
        return not self.authoritative_writes and all(
            measurement.passed for measurement in self.measurements.values()
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"passed": self.passed}


_DASHBOARD_SLO = {
    "home": 2.0,
    "candidate_queue": 2.0,
    "company": 2.0,
    "sector": 2.0,
    "impact_3_hop": 3.0,
    "validate": 30.0,
    "index_render": 30.0,
}


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _formal_state(objects: list[Any]) -> dict[str, tuple[int, int]]:
    return {
        str(obj.path): (obj.path.stat().st_size, obj.path.stat().st_mtime_ns)
        for obj in objects
    }


def _candidate_count(root: Path) -> int:
    path = candidate_db_path(root)
    if not path.is_file():
        return 0
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT COUNT(*) FROM candidates").fetchone()
        return int(row[0]) if row else 0
    finally:
        connection.close()


def benchmark_dashboard(root: Path, *, repeats: int = 5) -> DashboardBenchmark:
    """Measure real read models against Phase 6 SLOs without writing."""
    if repeats < 3:
        raise ValueError("benchmark requires at least 3 repeats")
    root = root.resolve()
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before benchmark")
    companies = sorted(
        obj.object_id for obj in objects if obj.object_type == "company"
    )
    sectors = sorted(obj.object_id for obj in objects if obj.object_type == "sector")
    if not companies or not sectors:
        raise ValueError("benchmark requires at least one Company and Sector")
    before = _formal_state(objects)
    functions: dict[str, Callable[[], object]] = {
        "home": lambda: industry_home_snapshot(root),
        "candidate_queue": lambda: queue_rows(root, limit=200),
        "company": lambda: company_snapshot(root, companies[0]),
        "sector": lambda: sector_snapshot(root, sectors[0]),
        "impact_3_hop": lambda: impact_explorer_snapshot(root, max_depth=3),
        "validate": lambda: validate_repository(root),
        "index_render": lambda: (
            render_indexes(objects),
            render_project_indexes(objects, "PRJ-001"),
        ),
    }
    measurements: dict[str, SloMeasurement] = {}
    for name, operation in functions.items():
        samples = []
        for _ in range(repeats):
            started = time.perf_counter()
            operation()
            samples.append(round(time.perf_counter() - started, 6))
        p95 = _p95(samples)
        threshold = _DASHBOARD_SLO[name]
        measurements[name] = SloMeasurement(
            samples_seconds=samples,
            p95_seconds=p95,
            threshold_seconds=threshold,
            passed=p95 < threshold,
        )
    after_objects, _ = validate_repository(root)
    after = _formal_state(after_objects)
    changed = sorted(
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )
    return DashboardBenchmark(
        repeats=repeats,
        scale={
            "formal_objects": len(objects),
            "candidates": _candidate_count(root),
            "companies": len(companies),
            "sectors": len(sectors),
            "impact_assertions": sum(
                obj.object_type == "impact_assertion" for obj in objects
            ),
            "ontology_assertions": sum(
                obj.object_type == "ontology_assertion" for obj in objects
            ),
        },
        measurements=measurements,
        authoritative_writes=changed,
    )


def _dated_id(prefix: str, index: int) -> str:
    zero_based = index - 1
    object_date = date(2026, 1, 1) + timedelta(days=zero_based // 999)
    sequence = zero_based % 999 + 1
    return f"{prefix}-{object_date.strftime('%Y%m%d')}-{sequence:03d}"


def _source_text(source_id: str, index: int) -> str:
    return f"""---
id: {source_id}
type: source
title: Synthetic Source {index}
created_at: 2026-01-01
updated_at: 2026-01-01
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: pending
source_type: article
publisher: Synthetic
authors: []
published_at: 2026-01-01
accessed_at: 2026-01-01
url: https://example.com/source/{index}
local_path:
source_grade: A
companies: []
technologies: []
products: []
canonical_url: https://example.com/source/{index}
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered
processing_error:
published_date_proposal:
tags: []
---

# Source

## Processing status

- [x] Event extraction completed
- [ ] Entity links reviewed
- [ ] Thesis links reviewed
"""


def _event_text(event_id: str, source_id: str, index: int) -> str:
    return f"""---
id: {event_id}
type: event
title: Synthetic Event {index}
created_at: 2026-01-01
updated_at: 2026-01-01
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: pending
event_date: 2026-01-01
source_ids: [{source_id}]
companies: []
technologies: []
products: []
thesis_links: []
confidence: 0.5
tags: []
---

# Event

## Facts
## Inferences
## Research judgment
## Thesis impact
## Alternative explanations
## Unknowns
## Follow-up indicators
"""


def _project_text() -> str:
    return """---
id: PRJ-001
type: project
title: Synthetic Scale Project
created_at: 2026-01-01
updated_at: 2026-01-01
schema_version: 1
project_ids: [PRJ-001]
status: active
owner: benchmark
research_question: Can the repository scale?
charter_path: charter.md
queue_path: queue.md
current_report_id:
review_cadence: Weekly
next_review_date: 2026-01-08
tags: []
---

# Synthetic Scale Project

## Research question
## Scope
## Success criteria
## Active Thesis
## Open actions
"""


def generate_synthetic_repository(
    root: Path,
    *,
    sources: int,
    events: int,
) -> None:
    if sources < 1 or events < 0 or events > sources:
        raise ValueError("benchmark requires sources >= 1 and 0 <= events <= sources")
    taxonomy = root / "00_System" / "Taxonomy.md"
    taxonomy.parent.mkdir(parents=True, exist_ok=True)
    taxonomy.write_text("# Synthetic Taxonomy\n", encoding="utf-8")
    project = root / "05_Research" / "Projects" / "PRJ-001.md"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text(_project_text(), encoding="utf-8")
    source_folder = root / "01_Inbox" / "Articles"
    event_folder = root / "04_Evidence" / "Events"
    source_folder.mkdir(parents=True, exist_ok=True)
    event_folder.mkdir(parents=True, exist_ok=True)
    source_ids: list[str] = []
    for index in range(1, sources + 1):
        source_id = _dated_id("SRC", index)
        source_ids.append(source_id)
        (source_folder / f"{source_id}-synthetic.md").write_text(
            _source_text(source_id, index),
            encoding="utf-8",
        )
    for index in range(1, events + 1):
        event_id = _dated_id("EVT", index)
        (event_folder / f"{event_id}-synthetic.md").write_text(
            _event_text(event_id, source_ids[index - 1], index),
            encoding="utf-8",
        )


def benchmark_repository(
    root: Path,
    *,
    sources: int,
    events: int,
    max_seconds: float,
) -> BenchmarkResult:
    generate_synthetic_repository(root, sources=sources, events=events)
    start = time.perf_counter()
    objects, findings = validate_repository(root)
    validation_seconds = time.perf_counter() - start
    start = time.perf_counter()
    render_indexes(objects)
    global_seconds = time.perf_counter() - start
    start = time.perf_counter()
    render_project_indexes(objects, "PRJ-001")
    project_seconds = time.perf_counter() - start
    errors = sum(finding.level == "error" for finding in findings)
    total = validation_seconds + global_seconds + project_seconds
    return BenchmarkResult(
        sources=sources,
        events=events,
        objects=len(objects),
        validation_errors=errors,
        validation_seconds=round(validation_seconds, 4),
        global_index_seconds=round(global_seconds, 4),
        project_index_seconds=round(project_seconds, 4),
        total_query_seconds=round(total, 4),
        passed=errors == 0 and total <= max_seconds,
        max_seconds=max_seconds,
    )


def run_scale_benchmark(
    *,
    sources: int = 1000,
    events: int = 500,
    max_seconds: float = 10.0,
) -> BenchmarkResult:
    with tempfile.TemporaryDirectory(prefix="research-os-benchmark-") as temp:
        return benchmark_repository(
            Path(temp),
            sources=sources,
            events=events,
            max_seconds=max_seconds,
        )
