"""Synthetic scale benchmark for repository validation and index rendering."""

from __future__ import annotations

import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from research_os.services.indexing import render_indexes, render_project_indexes
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
