from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from research_os.services import candidate_db
from research_os.services.runtime_reconciliation import (
    RuntimeReconciliationError,
    reconcile_candidate_databases,
)


def _candidate(
    candidate_id: str, url: str, fingerprint: str, *, title: str | None = None
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "title": title or candidate_id,
        "canonical_url": url,
        "content_fingerprint": fingerprint,
    }


def _rows(path: Path, table: str) -> list[tuple[object, ...]]:
    with sqlite3.connect(path) as connection:
        return connection.execute(f"SELECT * FROM {table}").fetchall()


def test_reconciliation_preserves_new_records_and_unions_runs_idempotently(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "canonical.db"
    incoming = tmp_path / "incoming.db"
    candidate_db.insert_candidates(
        canonical,
        [_candidate("CND-main", "https://example.test/a", "hash-a")],
        "CHN-main",
        "2026-08-18T00:00:00Z",
    )
    candidate_db.insert_candidates(
        incoming,
        [
            _candidate("CND-other-id", "https://example.test/a", "hash-a"),
            _candidate("CND-new-1", "https://example.test/new", "hash-new"),
        ],
        "CHN-one",
        "2026-08-18T01:00:00Z",
    )
    candidate_db.insert_candidates(
        incoming,
        [_candidate("CND-new-2", "https://example.test/new", "hash-new")],
        "CHN-two",
        "2026-08-18T01:01:00Z",
    )
    candidate_db.record_discovery_run(
        canonical,
        "RUN-main",
        "CHN-main",
        "2026-08-18T00:00:00Z",
    )
    candidate_db.record_discovery_run(
        incoming,
        "RUN-incoming",
        "CHN-one",
        "2026-08-18T01:00:00Z",
    )

    preview = reconcile_candidate_databases(canonical, incoming, apply=False)
    assert preview.new_candidate_rows == 2
    assert preview.new_content_items == 1
    assert preview.semantic_duplicates_skipped == 1
    assert preview.new_discovery_runs == 1
    assert len(_rows(canonical, "candidates")) == 1

    applied = reconcile_candidate_databases(canonical, incoming, apply=True)
    assert applied == preview
    assert {row[0] for row in _rows(canonical, "candidates")} == {
        "CND-main",
        "CND-new-1",
        "CND-new-2",
    }
    assert {row[0] for row in _rows(canonical, "discovery_runs")} == {
        "RUN-main",
        "RUN-incoming",
    }

    second = reconcile_candidate_databases(canonical, incoming, apply=True)
    assert second.new_candidate_rows == 0
    assert second.new_discovery_runs == 0


def test_reconciliation_refuses_conflicting_shared_candidate_id(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.db"
    incoming = tmp_path / "incoming.db"
    candidate_db.insert_candidates(
        canonical,
        [_candidate("CND-shared", "https://example.test/a", "hash-a")],
        "CHN-main",
        "2026-08-18T00:00:00Z",
    )
    candidate_db.insert_candidates(
        incoming,
        [
            _candidate(
                "CND-shared",
                "https://example.test/changed",
                "hash-changed",
            )
        ],
        "CHN-main",
        "2026-08-18T00:00:00Z",
    )

    with pytest.raises(RuntimeReconciliationError, match="Candidate ID conflict"):
        reconcile_candidate_databases(canonical, incoming, apply=True)

    assert len(_rows(canonical, "candidates")) == 1
