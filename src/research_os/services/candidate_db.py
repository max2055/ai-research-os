"""Candidate operational store (B-004).

A rebuildable, versioned SQLite store for discovery candidates. Not an
authoritative fact source: reviewed Markdown Source/Event remains canonical.
Schema version is tracked via ``PRAGMA user_version``; migrations apply and
roll back atomically.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_os.repositories.transaction import TransactionError

SCHEMA_VERSION = 2
_DEFAULT_PATH = Path("09_Automation/operational/candidates.db")

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    published_at_proposal TEXT,
    title TEXT NOT NULL,
    canonical_url TEXT,
    publisher TEXT,
    content_fingerprint TEXT,
    snippet TEXT,
    language TEXT,
    fetch_status TEXT NOT NULL DEFAULT 'new',
    duplicate_cluster_id TEXT,
    relevance_score REAL,
    novelty_score REAL,
    quality_score_proposal REAL,
    priority_score REAL,
    entity_proposals_json TEXT,
    sector_proposals_json TEXT,
    reason_codes_json TEXT,
    model_version TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    promoted_source_id TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS candidates_status_idx
    ON candidates(status);
CREATE INDEX IF NOT EXISTS candidates_channel_idx
    ON candidates(channel_id);

CREATE TABLE IF NOT EXISTS discovery_runs (
    run_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    candidate_count INTEGER DEFAULT 0,
    http_errors INTEGER DEFAULT 0,
    parse_errors INTEGER DEFAULT 0,
    retries INTEGER DEFAULT 0,
    cost_estimate TEXT,
    software_version TEXT,
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS discovery_runs_channel_idx
    ON discovery_runs(channel_id, started_at);

CREATE TABLE IF NOT EXISTS duplicate_clusters (
    cluster_id TEXT PRIMARY KEY,
    canonical_url TEXT,
    content_hash TEXT,
    title_similarity REAL,
    common_upstream TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_actions (
    action_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
    action TEXT NOT NULL,
    reason TEXT,
    actor TEXT NOT NULL,
    acted_at TEXT NOT NULL,
    payload_json TEXT
);
CREATE INDEX IF NOT EXISTS candidate_actions_candidate_idx
    ON candidate_actions(candidate_id, acted_at);
"""

# v2: drop the candidate_actions FK so a purged candidate keeps its audit
# rows (ADR retention: dismissed/expired cleaned up, audit actions retained).
_SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS candidate_actions_v2 (
    action_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT,
    actor TEXT NOT NULL,
    acted_at TEXT NOT NULL,
    payload_json TEXT
);
INSERT INTO candidate_actions_v2 (
    action_id, candidate_id, action, reason, actor, acted_at, payload_json
) SELECT action_id, candidate_id, action, reason, actor, acted_at, payload_json
  FROM candidate_actions;
DROP TABLE candidate_actions;
ALTER TABLE candidate_actions_v2 RENAME TO candidate_actions;
CREATE INDEX IF NOT EXISTS candidate_actions_candidate_idx
    ON candidate_actions(candidate_id, acted_at);
"""


def candidate_db_path(root: Path) -> Path:
    return root / _DEFAULT_PATH


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def current_version(path: Path) -> int:
    if not path.exists():
        return 0
    connection = sqlite3.connect(path)
    try:
        row = connection.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row else 0
    finally:
        connection.close()


def candidate_db_health(path: Path) -> dict[str, Any]:
    """Inspect the operational SQLite store without creating or mutating it."""
    if not path.is_file():
        return {
            "status": "missing",
            "integrity": "unknown",
            "schema_version": 0,
            "expected_schema_version": SCHEMA_VERSION,
            "size_bytes": 0,
            "modified_at": None,
        }
    stat = path.stat()
    result: dict[str, Any] = {
        "status": "ok",
        "integrity": "unknown",
        "schema_version": 0,
        "expected_schema_version": SCHEMA_VERSION,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    connection: sqlite3.Connection | None = None
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        version = connection.execute("PRAGMA user_version").fetchone()
        result["integrity"] = str(integrity[0]) if integrity else "unknown"
        result["schema_version"] = int(version[0]) if version else 0
        if result["integrity"] != "ok":
            result["status"] = "corrupt"
        elif result["schema_version"] != SCHEMA_VERSION:
            result["status"] = "migration_required"
    except sqlite3.DatabaseError:
        result["status"] = "corrupt"
        result["integrity"] = "corrupt"
    finally:
        if connection is not None:
            connection.close()
    return result


def apply_migrations(path: Path) -> int:
    """Apply pending migrations atomically; return version applied to."""
    version = current_version(path)
    if version == 0 and path.exists():
        raise TransactionError(f"candidate db exists at unversioned state: {path}")
    connection = _connect(path)
    try:
        if version < 1:
            connection.executescript("BEGIN")
            connection.executescript(_SCHEMA_V1)
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
            version = 1
        if version < 2:
            connection.executescript("BEGIN")
            connection.executescript(_SCHEMA_V2)
            connection.execute("PRAGMA user_version = 2")
            connection.commit()
            version = 2
        return version
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate migration failed: {exc}") from exc
    finally:
        connection.close()


def rollback_migrations(path: Path, to_version: int = 0) -> None:
    """Roll the operational schema back to an earlier version."""
    version = current_version(path)
    if not path.exists() or version == 0:
        raise TransactionError(f"no candidate db to roll back: {path}")
    if to_version >= version:
        raise TransactionError(
            f"rollback target {to_version} not below current {version}"
        )
    connection = sqlite3.connect(path)
    try:
        connection.executescript("BEGIN")
        for table in (
            "candidate_actions",
            "duplicate_clusters",
            "discovery_runs",
            "candidates",
        ):
            connection.execute(f"DROP TABLE IF EXISTS {table}")
        connection.execute(f"PRAGMA user_version = {to_version}")
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate rollback failed: {exc}") from exc
    finally:
        connection.close()


def insert_candidates(
    path: Path,
    candidates: list[dict[str, object]],
    channel_id: str,
    discovered_at: str,
) -> int:
    """Insert discovery candidates into the operational store."""
    if current_version(path) == 0:
        apply_migrations(path)
    connection = _connect(path)
    inserted = 0
    try:
        connection.executescript("BEGIN")
        for candidate in candidates:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO candidates ("
                "candidate_id, channel_id, discovered_at, published_at_proposal, "
                "title, canonical_url, publisher, content_fingerprint, snippet, "
                "language, fetch_status, status, duplicate_cluster_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', 'new', ?, ?)",
                (
                    str(candidate["candidate_id"]),
                    channel_id,
                    discovered_at,
                    candidate.get("published_at_proposal"),
                    str(candidate["title"]),
                    candidate.get("canonical_url"),
                    candidate.get("publisher"),
                    candidate.get("content_fingerprint"),
                    candidate.get("snippet"),
                    candidate.get("language"),
                    candidate.get("duplicate_cluster_id"),
                    discovered_at,
                ),
            )
            inserted += cursor.rowcount
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate insert failed: {exc}") from exc
    finally:
        connection.close()
    return inserted


def record_discovery_run(
    path: Path,
    run_id: str,
    channel_id: str,
    started_at: str,
    *,
    candidate_count: int = 0,
    http_errors: int = 0,
    parse_errors: int = 0,
    retries: int = 0,
    software_version: str = "",
    status: str = "succeeded",
    finished_at: str | None = None,
) -> None:
    if current_version(path) == 0:
        apply_migrations(path)
    connection = _connect(path)
    try:
        connection.execute(
            "INSERT INTO discovery_runs (run_id, channel_id, started_at, "
            "finished_at, candidate_count, http_errors, parse_errors, retries, "
            "software_version, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                channel_id,
                started_at,
                finished_at or started_at,
                candidate_count,
                http_errors,
                parse_errors,
                retries,
                software_version,
                status,
            ),
        )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"discovery run insert failed: {exc}") from exc
    finally:
        connection.close()


def finish_discovery_run(
    path: Path,
    run_id: str,
    *,
    status: str,
    candidate_count: int | None = None,
    finished_at: str | None = None,
    retries: int | None = None,
    http_errors: int | None = None,
    parse_errors: int | None = None,
) -> None:
    """Close a running discovery run with a terminal status (B-021 lock)."""
    if not path.exists():
        raise TransactionError(f"no candidate db to finish run: {path}")
    connection = _connect(path)
    try:
        assignments = ["status = ?", "finished_at = ?"]
        values: list[object] = [status, finished_at]
        for column, value in (
            ("candidate_count", candidate_count),
            ("retries", retries),
            ("http_errors", http_errors),
            ("parse_errors", parse_errors),
        ):
            if value is not None:
                assignments.append(f"{column} = ?")
                values.append(value)
        values.append(run_id)
        cursor = connection.execute(
            f"UPDATE discovery_runs SET {', '.join(assignments)} "
            "WHERE run_id = ? AND status = 'running'",
            values,
        )
        if cursor.rowcount != 1:
            connection.rollback()
            raise TransactionError(
                f"unknown or already finalized discovery run {run_id}"
            )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"discovery run update failed: {exc}") from exc
    finally:
        connection.close()


def list_candidates(
    path: Path,
    *,
    status: str = "new",
    limit: int = 50,
) -> list[dict[str, object]]:
    if not path.exists():
        return []
    connection = _connect(path)
    try:
        rows = connection.execute(
            "SELECT candidate_id, channel_id, title, canonical_url, "
            "published_at_proposal, status, created_at "
            "FROM candidates WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
        return [
            {
                "candidate_id": row[0],
                "channel_id": row[1],
                "title": row[2],
                "canonical_url": row[3],
                "published_at_proposal": row[4],
                "status": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]
    finally:
        connection.close()


def existing_candidates(root: Path) -> list[dict[str, object]]:
    """Return prior candidates for dedup indexing (title/fingerprint/url)."""
    path = candidate_db_path(root)
    if not path.exists():
        return []
    connection = _connect(path)
    try:
        rows = connection.execute(
            "SELECT candidate_id, title, canonical_url, content_fingerprint, "
            "duplicate_cluster_id FROM candidates "
            "WHERE duplicate_cluster_id IS NOT NULL"
        ).fetchall()
        return [
            {
                "candidate_id": row[0],
                "title": row[1],
                "canonical_url": row[2],
                "content_fingerprint": row[3],
                "duplicate_cluster_id": row[4],
            }
            for row in rows
        ]
    finally:
        connection.close()
