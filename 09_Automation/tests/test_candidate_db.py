"""Tests for the Candidate operational store (B-004)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_os.repositories.transaction import TransactionError
from research_os.services.candidate_db import (
    SCHEMA_VERSION,
    apply_migrations,
    current_version,
    rollback_migrations,
)


class CandidateDbTests(unittest.TestCase):
    def test_apply_migrations_creates_versioned_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            self.assertEqual(0, current_version(path))
            version = apply_migrations(path)
            self.assertEqual(SCHEMA_VERSION, version)
            self.assertEqual(SCHEMA_VERSION, current_version(path))

    def test_apply_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            apply_migrations(path)
            version = apply_migrations(path)
            self.assertEqual(SCHEMA_VERSION, version)

    def test_rollback_drops_tables_and_resets_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            apply_migrations(path)
            self.assertEqual(SCHEMA_VERSION, current_version(path))
            rollback_migrations(path, to_version=0)
            self.assertEqual(0, current_version(path))

    def test_rollback_refuses_when_nothing_to_roll_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            with self.assertRaises(TransactionError):
                rollback_migrations(path, to_version=0)

    def test_rollback_refuses_non_negative_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            apply_migrations(path)
            with self.assertRaises(TransactionError):
                rollback_migrations(path, to_version=SCHEMA_VERSION)

    def test_candidate_insert_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            apply_migrations(path)
            connection = sqlite_connect(path)
            try:
                connection.execute(
                    "INSERT INTO candidates (candidate_id, channel_id, "
                    "discovered_at, title, created_at, status) "
                    "VALUES (?, ?, ?, ?, ?, 'new')",
                    (
                        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                        "CHN-sec",
                        "2026-08-06T00:00:00Z",
                        "Test candidate",
                        "2026-08-06T00:00:00Z",
                    ),
                )
                connection.commit()
                row = connection.execute(
                    "SELECT title, status FROM candidates "
                    "WHERE candidate_id = ?",
                    ("01ARZ3NDEKTSV4RRFFQ69G5FAV",),
                ).fetchone()
                self.assertEqual("Test candidate", row[0])
                self.assertEqual("new", row[1])
            finally:
                connection.close()


def sqlite_connect(path: Path):
    import sqlite3

    return sqlite3.connect(path)


if __name__ == "__main__":
    unittest.main()
