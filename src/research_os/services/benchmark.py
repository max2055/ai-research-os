"""Disposable scale benchmarks for repository and Candidate read paths."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sqlite3
import stat
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from research_os.repositories.markdown import OBJECT_PATTERNS
from research_os.services import candidate_db
from research_os.services.candidate_db import candidate_db_path
from research_os.services.candidate_queue import queue_rows, render_candidate_list
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


@dataclass(frozen=True)
class CandidateQueueBenchmark:
    rows: int
    repeats: int
    warmups: int
    page_size: int
    offset: int
    fixture_distribution: dict[str, Any]
    samples_seconds: tuple[float, ...]
    p95_seconds: float
    threshold_seconds: float
    query_plan: tuple[str, ...]
    db_size_bytes: int
    environment: dict[str, Any]
    authoritative_writes: tuple[str, ...]
    real_candidate_store_unchanged: bool

    @property
    def passed(self) -> bool:
        return (
            self.p95_seconds < self.threshold_seconds
            and not self.authoritative_writes
            and self.real_candidate_store_unchanged
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


@dataclass(frozen=True)
class _FormalPathState:
    kind: str
    mode: int | None
    size_bytes: int | None
    mtime_ns: int | None
    sha256: str | None
    link_target: str | None = None
    error: str | None = None


_DIRECTORY_OPEN_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_OPEN_FLAGS = (
    os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
)
_SKIPPED_RECURSIVE_DIRECTORIES = frozenset(
    {".git", ".worktrees", ".venv", "__pycache__", "_assets", "operational"}
)


def _nearest_rank_p95(samples: tuple[float, ...] | list[float]) -> float:
    if not samples:
        raise ValueError("p95 requires at least one sample")
    ordered = sorted(samples)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _p95(samples: list[float]) -> float:
    return _nearest_rank_p95(samples)


def _observed_state(
    kind: str,
    path_stat: os.stat_result | None,
    *,
    sha256: str | None = None,
    link_target: str | None = None,
    error: str | None = None,
) -> _FormalPathState:
    return _FormalPathState(
        kind=kind,
        mode=path_stat.st_mode if path_stat is not None else None,
        size_bytes=path_stat.st_size if path_stat is not None else None,
        mtime_ns=path_stat.st_mtime_ns if path_stat is not None else None,
        sha256=sha256,
        link_target=link_target,
        error=error,
    )


def _record_error(
    state: dict[str, _FormalPathState],
    path: Path,
    path_stat: os.stat_result | None,
    error: OSError | str,
) -> None:
    state[str(path)] = _observed_state("error", path_stat, error=str(error))


def _symlink_state_at(
    directory_fd: int,
    name: str,
    path_stat: os.stat_result,
) -> _FormalPathState:
    try:
        target = os.readlink(name, dir_fd=directory_fd)
    except OSError as exc:
        return _observed_state("symlink", path_stat, error=str(exc))
    return _observed_state("symlink", path_stat, link_target=target)


def _snapshot(path_stat: os.stat_result) -> tuple[int, ...]:
    return (
        path_stat.st_dev,
        path_stat.st_ino,
        path_stat.st_mode,
        path_stat.st_size,
        path_stat.st_mtime_ns,
        path_stat.st_ctime_ns,
    )


def _component_problem_at(
    directory_fd: int,
    name: str,
    path_stat: os.stat_result,
    error: str,
) -> _FormalPathState:
    if stat.S_ISLNK(path_stat.st_mode):
        return _symlink_state_at(directory_fd, name, path_stat)
    return _observed_state("error", path_stat, error=error)


def _formal_entry_state_at(
    directory_fd: int,
    name: str,
    path_stat: os.stat_result,
) -> _FormalPathState:
    if stat.S_ISLNK(path_stat.st_mode):
        return _symlink_state_at(directory_fd, name, path_stat)
    if stat.S_ISDIR(path_stat.st_mode):
        return _observed_state("directory", path_stat)
    if not stat.S_ISREG(path_stat.st_mode):
        return _observed_state("other", path_stat)

    try:
        descriptor = os.open(name, _FILE_OPEN_FLAGS, dir_fd=directory_fd)
    except OSError as exc:
        return _observed_state("error", path_stat, error=str(exc))
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode) or (
            opened_stat.st_dev,
            opened_stat.st_ino,
        ) != (path_stat.st_dev, path_stat.st_ino):
            return _observed_state(
                "error", path_stat, error="path changed while opening formal file"
            )
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        final_stat = os.fstat(descriptor)
        try:
            current_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as exc:
            return _observed_state("error", final_stat, error=str(exc))
        if _snapshot(opened_stat) != _snapshot(final_stat):
            return _observed_state(
                "error", final_stat, error="formal file changed while hashing"
            )
        if _snapshot(final_stat) != _snapshot(current_stat):
            return _component_problem_at(
                directory_fd,
                name,
                current_stat,
                "formal path changed while hashing",
            )
        return _observed_state("regular", final_stat, sha256=digest.hexdigest())
    finally:
        os.close(descriptor)


def _open_managed_directory(
    parent_fd: int,
    name: str,
    path: Path,
    path_stat: os.stat_result,
    state: dict[str, _FormalPathState],
) -> int | None:
    try:
        descriptor = os.open(name, _DIRECTORY_OPEN_FLAGS, dir_fd=parent_fd)
        opened_stat = os.fstat(descriptor)
    except OSError as exc:
        _record_error(state, path, path_stat, exc)
        return None
    try:
        current_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        os.close(descriptor)
        _record_error(state, path, opened_stat, exc)
        return None
    valid = (
        stat.S_ISDIR(opened_stat.st_mode)
        and stat.S_ISDIR(current_stat.st_mode)
        and (opened_stat.st_dev, opened_stat.st_ino)
        == (path_stat.st_dev, path_stat.st_ino)
        == (current_stat.st_dev, current_stat.st_ino)
    )
    if not valid:
        os.close(descriptor)
        state[str(path)] = _component_problem_at(
            parent_fd,
            name,
            current_stat,
            "managed directory changed while opening",
        )
        return None
    return descriptor


def _verify_managed_directory(
    parent_fd: int,
    name: str,
    path: Path,
    original_stat: os.stat_result,
    state: dict[str, _FormalPathState],
) -> None:
    try:
        current_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        _record_error(state, path, original_stat, exc)
        return
    if _snapshot(original_stat) != _snapshot(current_stat):
        state[str(path)] = _component_problem_at(
            parent_fd,
            name,
            current_stat,
            "managed directory changed during inventory",
        )


def _directory_entries(
    directory_fd: int,
    directory_path: Path,
    state: dict[str, _FormalPathState],
    *,
    skip_ignored: bool,
) -> list[tuple[str, os.stat_result]]:
    try:
        with os.scandir(directory_fd) as entries:
            names = sorted(entry.name for entry in entries)
    except OSError as exc:
        _record_error(state, directory_path, os.fstat(directory_fd), exc)
        return []
    result: list[tuple[str, os.stat_result]] = []
    for name in names:
        if skip_ignored and name in _SKIPPED_RECURSIVE_DIRECTORIES:
            continue
        path = directory_path / name
        try:
            path_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as exc:
            _record_error(state, path, None, exc)
            continue
        result.append((name, path_stat))
    return result


def _walk_formal_pattern(
    directory_fd: int,
    directory_path: Path,
    parts: tuple[str, ...],
    state: dict[str, _FormalPathState],
) -> None:
    part = parts[0]
    if part == "**":
        leaf_pattern = parts[1]
        for name, path_stat in _directory_entries(
            directory_fd,
            directory_path,
            state,
            skip_ignored=True,
        ):
            path = directory_path / name
            matches_leaf = fnmatchcase(name, leaf_pattern)
            if matches_leaf:
                state[str(path)] = _formal_entry_state_at(directory_fd, name, path_stat)
            if stat.S_ISLNK(path_stat.st_mode):
                if not matches_leaf:
                    state[str(path)] = _symlink_state_at(directory_fd, name, path_stat)
                continue
            if not stat.S_ISDIR(path_stat.st_mode):
                continue
            child_fd = _open_managed_directory(
                directory_fd, name, path, path_stat, state
            )
            if child_fd is None:
                continue
            try:
                _walk_formal_pattern(child_fd, path, parts, state)
                _verify_managed_directory(directory_fd, name, path, path_stat, state)
            finally:
                os.close(child_fd)
        return

    if len(parts) == 1:
        for name, path_stat in _directory_entries(
            directory_fd,
            directory_path,
            state,
            skip_ignored=False,
        ):
            if fnmatchcase(name, part):
                path = directory_path / name
                state[str(path)] = _formal_entry_state_at(directory_fd, name, path_stat)
        return

    path = directory_path / part
    try:
        path_stat = os.stat(part, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        _record_error(state, path, None, exc)
        return
    if not stat.S_ISDIR(path_stat.st_mode):
        state[str(path)] = _component_problem_at(
            directory_fd,
            part,
            path_stat,
            "managed path component is not a directory",
        )
        return
    child_fd = _open_managed_directory(directory_fd, part, path, path_stat, state)
    if child_fd is None:
        return
    try:
        _walk_formal_pattern(child_fd, path, parts[1:], state)
        _verify_managed_directory(directory_fd, part, path, path_stat, state)
    finally:
        os.close(child_fd)


def _formal_state(root: Path) -> dict[str, _FormalPathState]:
    try:
        root_stat = root.lstat()
    except OSError as exc:
        return {str(root): _observed_state("error", None, error=str(exc))}
    if stat.S_ISLNK(root_stat.st_mode):
        try:
            target = os.readlink(root)
        except OSError as exc:
            return {str(root): _observed_state("symlink", root_stat, error=str(exc))}
        return {str(root): _observed_state("symlink", root_stat, link_target=target)}
    if not stat.S_ISDIR(root_stat.st_mode):
        return {str(root): _observed_state("other", root_stat)}

    try:
        root_fd = os.open(root, _DIRECTORY_OPEN_FLAGS)
        opened_root_stat = os.fstat(root_fd)
    except OSError as exc:
        return {str(root): _observed_state("error", root_stat, error=str(exc))}
    try:
        if not stat.S_ISDIR(opened_root_stat.st_mode) or (
            root_stat.st_dev,
            root_stat.st_ino,
        ) != (opened_root_stat.st_dev, opened_root_stat.st_ino):
            return {
                str(root): _observed_state(
                    "error",
                    opened_root_stat,
                    error="repository root changed while opening",
                )
            }
        state: dict[str, _FormalPathState] = {}
        for pattern in OBJECT_PATTERNS:
            _walk_formal_pattern(
                root_fd,
                root,
                tuple(pattern.split("/")),
                state,
            )
        try:
            current_root_stat = root.lstat()
        except OSError as exc:
            _record_error(state, root, opened_root_stat, exc)
        else:
            if _snapshot(opened_root_stat) != _snapshot(current_root_stat):
                _record_error(
                    state,
                    root,
                    current_root_stat,
                    "repository root changed during inventory",
                )
        return dict(sorted(state.items()))
    finally:
        os.close(root_fd)


def _non_regular_formal_paths(
    state: dict[str, _FormalPathState],
) -> tuple[str, ...]:
    return tuple(
        sorted(path for path, value in state.items() if value.kind != "regular")
    )


def _require_regular_formal_paths(state: dict[str, _FormalPathState]) -> None:
    unsafe = _non_regular_formal_paths(state)
    if unsafe:
        raise ValueError(
            "formal Markdown paths must be regular files: " + ", ".join(unsafe)
        )


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


def _file_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "size_bytes": 0, "mtime_ns": None, "sha256": None}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }


def _candidate_fixture(
    path: Path,
    *,
    rows: int,
    entity_id: str,
) -> dict[str, Any]:
    """Create a deterministic schema-current Candidate fixture at ``path``."""
    candidate_db.apply_migrations(path)
    statuses = {"new": 0, "dismissed": 0}
    channels = {f"CHN-benchmark-{index}": 0 for index in range(4)}
    entities = {entity_id: 0, "COM-benchmark-other": 0}
    priority_null = 0
    duplicate_members = 0
    duplicate_ids: set[str] = set()
    values: list[tuple[object, ...]] = []
    for index in range(rows):
        candidate_id = f"CND-BENCH-{index:05d}"
        channel_id = f"CHN-benchmark-{index % 4}"
        status = "dismissed" if index % 5 == 0 else "new"
        resolved_entity = entity_id if index % 2 == 0 else "COM-benchmark-other"
        priority = None if index % 10 == 0 else ((index * 37) % 1000) / 1000
        cluster_id = None
        if index % 8 in (0, 4):
            cluster_id = f"CLU-BENCH-{index // 8:05d}"
            duplicate_members += 1
            duplicate_ids.add(cluster_id)
        discovered_at = (
            f"2026-08-{1 + (index // 86400):02d}T00:"
            f"{(index // 60) % 60:02d}:{index % 60:02d}Z"
        )
        entity_json = json.dumps(
            {"status": "matched", "entity_id": resolved_entity},
            sort_keys=True,
            separators=(",", ":"),
        )
        sector_json = '{"sector_ids":["SEG-benchmark"]}'
        values.append(
            (
                candidate_id,
                channel_id,
                discovered_at,
                f"Synthetic candidate {index:05d}",
                f"https://benchmark.invalid/candidate/{index:05d}",
                "Synthetic Benchmark",
                f"fixture-{index:05d}",
                cluster_id,
                priority,
                entity_json,
                sector_json,
                '["deterministic_fixture"]',
                "benchmark-v1",
                status,
                discovered_at,
            )
        )
        statuses[status] += 1
        channels[channel_id] += 1
        entities[resolved_entity] += 1
        priority_null += priority is None

    connection = sqlite3.connect(path)
    try:
        connection.executemany(
            "INSERT INTO candidates (candidate_id, channel_id, discovered_at, "
            "title, canonical_url, publisher, content_fingerprint, "
            "duplicate_cluster_id, priority_score, entity_proposals_json, "
            "sector_proposals_json, reason_codes_json, model_version, status, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        connection.commit()
        stored = connection.execute("SELECT COUNT(*) FROM candidates").fetchone()
        version = connection.execute("PRAGMA user_version").fetchone()
    finally:
        connection.close()
    stored_rows = int(stored[0]) if stored else 0
    if stored_rows != rows:
        raise RuntimeError(
            f"candidate fixture expected {rows} rows, found {stored_rows}"
        )
    schema_version = int(version[0]) if version else 0
    if schema_version != candidate_db.SCHEMA_VERSION:
        raise RuntimeError(
            "candidate fixture schema version "
            f"{schema_version} != {candidate_db.SCHEMA_VERSION}"
        )
    return {
        "total_rows": stored_rows,
        "schema_version": schema_version,
        "statuses": statuses,
        "channels": channels,
        "entities": entities,
        "priority_null": priority_null,
        "priority_non_null": rows - priority_null,
        "duplicate_cluster_members": duplicate_members,
        "duplicate_clusters": len(duplicate_ids),
        "rules": (
            "channel=index modulo 4",
            "dismissed=index modulo 5 equals 0; otherwise new",
            "target entity=even index; alternate entity=odd index",
            "NULL priority=index modulo 10 equals 0; otherwise "
            "(index*37 modulo 1000)/1000",
            "duplicate pair=index modulo 8 in {0,4}",
            "candidate_id is zero-padded ascending index",
        ),
    }


def _candidate_query_plan(path: Path) -> tuple[str, ...]:
    connection = sqlite3.connect(path)
    try:
        statements = (
            (
                "filter-order",
                "EXPLAIN QUERY PLAN SELECT candidate_id, channel_id, title, "
                "canonical_url, published_at_proposal, discovered_at, status, "
                "duplicate_cluster_id, priority_score, entity_proposals_json, "
                "sector_proposals_json FROM candidates WHERE status = ? "
                "AND channel_id = ? AND priority_score >= ? "
                "ORDER BY priority_score IS NULL, priority_score DESC, "
                "discovered_at DESC, candidate_id ASC",
                ("new", "CHN-benchmark-0", 0.25),
            ),
            (
                "cluster-scan",
                "EXPLAIN QUERY PLAN SELECT duplicate_cluster_id, candidate_id, "
                "created_at FROM candidates WHERE duplicate_cluster_id IS NOT NULL",
                (),
            ),
        )
        plan: list[str] = []
        for label, sql, params in statements:
            for row in connection.execute(sql, params):
                plan.append(f"{label}: {' | '.join(str(value) for value in row)}")
        return tuple(plan)
    finally:
        connection.close()


def benchmark_candidate_queue(
    root: Path,
    *,
    rows: int = 10_000,
    repeats: int = 7,
    warmups: int = 1,
    page_size: int = 200,
    offset: int = 200,
    max_seconds: float = 2.0,
) -> CandidateQueueBenchmark:
    """Measure the real Candidate filter/order/collapse/page/render path."""
    if rows <= 0:
        raise ValueError("rows must be positive")
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    if warmups < 0:
        raise ValueError("warmups must be non-negative")
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("max_seconds must be finite and positive")

    root = root.resolve()
    real_db = candidate_db_path(root)
    real_db_before = _file_state(real_db)
    formal_before = _formal_state(root)
    _require_regular_formal_paths(formal_before)
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before benchmark")
    companies = sorted(
        (
            obj.object_id,
            str(obj.metadata.get("coverage_tier") or ""),
        )
        for obj in objects
        if obj.object_type == "company" and str(obj.metadata.get("coverage_tier") or "")
    )
    if not companies:
        raise ValueError("candidate benchmark requires a Company with coverage_tier")
    entity_id, tier = companies[0]
    with tempfile.TemporaryDirectory(prefix="research-os-candidate-benchmark-") as temp:
        fixture_path = Path(temp) / "candidates.db"
        distribution = _candidate_fixture(
            fixture_path,
            rows=rows,
            entity_id=entity_id,
        )
        query_plan = _candidate_query_plan(fixture_path)
        db_size_bytes = fixture_path.stat().st_size

        def operation() -> str:
            page = queue_rows(
                root,
                fixture_path,
                status="new",
                channel_id="CHN-benchmark-0",
                entity_id=entity_id,
                tier=tier,
                min_priority=0.25,
                limit=page_size,
                offset=offset,
                show_dups=False,
            )
            return render_candidate_list(page)

        for _ in range(warmups):
            operation()
        samples: list[float] = []
        for _ in range(repeats):
            started = time.perf_counter()
            operation()
            samples.append(round(time.perf_counter() - started, 6))

    formal_after = _formal_state(root)
    authoritative_writes = {
        path
        for path in set(formal_before) | set(formal_after)
        if formal_before.get(path) != formal_after.get(path)
    }
    if not _non_regular_formal_paths(formal_after):
        _, after_findings = validate_repository(root)
        authoritative_writes.update(
            str(finding.path) for finding in after_findings if finding.level == "error"
        )
    real_db_after = _file_state(real_db)
    real_db_unchanged = real_db_before == real_db_after
    sample_tuple = tuple(samples)
    return CandidateQueueBenchmark(
        rows=rows,
        repeats=repeats,
        warmups=warmups,
        page_size=page_size,
        offset=offset,
        fixture_distribution=distribution,
        samples_seconds=sample_tuple,
        p95_seconds=_nearest_rank_p95(sample_tuple),
        threshold_seconds=max_seconds,
        query_plan=query_plan,
        db_size_bytes=db_size_bytes,
        environment={
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "sqlite": sqlite3.sqlite_version,
            "cpu_count": os.cpu_count(),
            "formal_paths_compared": len(formal_before),
            "fixture_storage": "temporary_directory",
            "real_candidate_store": {
                "path": str(real_db.relative_to(root)),
                "before": real_db_before,
                "after": real_db_after,
            },
        },
        authoritative_writes=tuple(sorted(authoritative_writes)),
        real_candidate_store_unchanged=real_db_unchanged,
    )


def benchmark_dashboard(root: Path, *, repeats: int = 5) -> DashboardBenchmark:
    """Measure real read models against Phase 6 SLOs without writing."""
    if repeats < 3:
        raise ValueError("benchmark requires at least 3 repeats")
    root = root.resolve()
    before = _formal_state(root)
    _require_regular_formal_paths(before)
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before benchmark")
    companies = sorted(obj.object_id for obj in objects if obj.object_type == "company")
    sectors = sorted(obj.object_id for obj in objects if obj.object_type == "sector")
    if not companies or not sectors:
        raise ValueError("benchmark requires at least one Company and Sector")
    functions: dict[str, Callable[[], object]] = {
        "home": lambda: industry_home_snapshot(root),
        "candidate_queue": lambda: queue_rows(root, limit=200),
        "company": lambda: company_snapshot(root, companies[0]),
        "sector": lambda: sector_snapshot(root, sectors[0]),
        "impact_3_hop": lambda: impact_explorer_snapshot(
            root,
            max_depth=3,
            objects=objects,
        ),
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
    after = _formal_state(root)
    changed = {
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    }
    if not _non_regular_formal_paths(after):
        _, after_findings = validate_repository(root)
        changed.update(
            str(finding.path) for finding in after_findings if finding.level == "error"
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
        authoritative_writes=sorted(changed),
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
