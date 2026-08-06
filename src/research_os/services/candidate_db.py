"""Candidate operational store (B-004).

A rebuildable, versioned SQLite store for discovery candidates. Not an
authoritative fact source: reviewed Markdown Source/Event remains canonical.
Schema version is tracked via ``PRAGMA user_version``; migrations apply and
roll back atomically.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from research_os.repositories.transaction import TransactionError

SCHEMA_VERSION = 1
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


def apply_migrations(path: Path) -> int:
    """Apply pending migrations atomically; return version applied to."""
    version = current_version(path)
    if version == 0 and path.exists():
        raise TransactionError(
            f"candidate db exists at unversioned state: {path}"
        )
    connection = _connect(path)
    try:
        if version < 1:
            connection.executescript("BEGIN")
            connection.executescript(_SCHEMA_V1)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
            version = SCHEMA_VERSION
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
