"""Deterministic reconciliation for divergent Candidate operational stores."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_os.services.candidate_db import SCHEMA_VERSION


class RuntimeReconciliationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReconciliationReport:
    new_candidate_rows: int
    new_content_items: int
    semantic_duplicates_skipped: int
    new_discovery_runs: int
    new_candidate_actions: int
    new_mutation_audits: int
    new_duplicate_clusters: int


def _table(
    connection: sqlite3.Connection, name: str
) -> tuple[list[str], list[tuple[Any, ...]]]:
    cursor = connection.execute(f"SELECT * FROM {name}")
    return [str(item[0]) for item in cursor.description], cursor.fetchall()


def _healthy(connection: sqlite3.Connection, label: str) -> None:
    integrity = connection.execute("PRAGMA quick_check").fetchone()
    version = connection.execute("PRAGMA user_version").fetchone()
    if integrity is None or integrity[0] != "ok":
        raise RuntimeReconciliationError(f"{label} database integrity check failed")
    if version is None or int(version[0]) != SCHEMA_VERSION:
        raise RuntimeReconciliationError(f"{label} database schema is not current")


def _new_rows_by_id(
    canonical_rows: list[tuple[Any, ...]],
    incoming_rows: list[tuple[Any, ...]],
    *,
    table_label: str,
) -> list[tuple[Any, ...]]:
    canonical = {str(row[0]): row for row in canonical_rows}
    incoming = {str(row[0]): row for row in incoming_rows}
    conflicts = sorted(
        row_id
        for row_id in canonical.keys() & incoming.keys()
        if canonical[row_id] != incoming[row_id]
    )
    if conflicts:
        raise RuntimeReconciliationError(
            f"{table_label} ID conflict: {', '.join(conflicts[:5])}"
        )
    return [row for row_id, row in incoming.items() if row_id not in canonical]


def _insert_rows(
    connection: sqlite3.Connection,
    table: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return
    names = ", ".join(f'"{name}"' for name in columns)
    placeholders = ", ".join("?" for _ in columns)
    connection.executemany(
        f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})', rows
    )


def reconcile_candidate_databases(
    canonical_path: Path,
    incoming_path: Path,
    *,
    apply: bool,
) -> ReconciliationReport:
    """Union distinct operational records without Candidate-ID-only merging."""
    canonical_path = Path(canonical_path).resolve()
    incoming_path = Path(incoming_path).resolve()
    if canonical_path == incoming_path:
        raise RuntimeReconciliationError(
            "canonical and incoming databases are identical"
        )

    with (
        sqlite3.connect(canonical_path) as canonical,
        sqlite3.connect(
            f"file:{incoming_path.as_posix()}?mode=ro", uri=True
        ) as incoming,
    ):
        _healthy(canonical, "canonical")
        _healthy(incoming, "incoming")

        candidate_columns, canonical_candidates = _table(canonical, "candidates")
        incoming_candidate_columns, incoming_candidates = _table(incoming, "candidates")
        if candidate_columns != incoming_candidate_columns:
            raise RuntimeReconciliationError("Candidate schemas differ")
        candidate_id_index = candidate_columns.index("candidate_id")
        url_index = candidate_columns.index("canonical_url")
        fingerprint_index = candidate_columns.index("content_fingerprint")
        canonical_by_id = {
            str(row[candidate_id_index]): row for row in canonical_candidates
        }
        incoming_by_id = {
            str(row[candidate_id_index]): row for row in incoming_candidates
        }
        shared_conflicts = sorted(
            candidate_id
            for candidate_id in canonical_by_id.keys() & incoming_by_id.keys()
            if canonical_by_id[candidate_id] != incoming_by_id[candidate_id]
        )
        if shared_conflicts:
            raise RuntimeReconciliationError(
                "Candidate ID conflict: " + ", ".join(shared_conflicts[:5])
            )
        canonical_content = {
            (row[url_index], row[fingerprint_index]) for row in canonical_candidates
        }
        missing_id_rows = [
            row
            for candidate_id, row in incoming_by_id.items()
            if candidate_id not in canonical_by_id
        ]
        new_candidates = [
            row
            for row in missing_id_rows
            if (row[url_index], row[fingerprint_index]) not in canonical_content
        ]
        semantic_skips = len(missing_id_rows) - len(new_candidates)

        table_plans: dict[str, tuple[list[str], list[tuple[Any, ...]]]] = {}
        labels = {
            "discovery_runs": "Discovery Run",
            "candidate_actions": "Candidate action",
            "mutation_audit": "Mutation audit",
            "duplicate_clusters": "Duplicate cluster",
        }
        for table, label in labels.items():
            columns, canonical_rows = _table(canonical, table)
            incoming_columns, incoming_rows = _table(incoming, table)
            if columns != incoming_columns:
                raise RuntimeReconciliationError(f"{label} schemas differ")
            table_plans[table] = (
                columns,
                _new_rows_by_id(
                    canonical_rows,
                    incoming_rows,
                    table_label=label,
                ),
            )

        report = ReconciliationReport(
            new_candidate_rows=len(new_candidates),
            new_content_items=len(
                {(row[url_index], row[fingerprint_index]) for row in new_candidates}
            ),
            semantic_duplicates_skipped=semantic_skips,
            new_discovery_runs=len(table_plans["discovery_runs"][1]),
            new_candidate_actions=len(table_plans["candidate_actions"][1]),
            new_mutation_audits=len(table_plans["mutation_audit"][1]),
            new_duplicate_clusters=len(table_plans["duplicate_clusters"][1]),
        )
        if not apply:
            return report

        try:
            canonical.execute("BEGIN IMMEDIATE")
            _insert_rows(canonical, "candidates", candidate_columns, new_candidates)
            for table, (columns, rows) in table_plans.items():
                _insert_rows(canonical, table, columns, rows)
            canonical.commit()
        except sqlite3.Error as exc:
            canonical.rollback()
            raise RuntimeReconciliationError(
                f"atomic runtime reconciliation failed: {exc}"
            ) from exc
        return report
