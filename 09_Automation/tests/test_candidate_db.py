"""Tests for the Candidate operational store (B-004)."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from queue import Queue
from threading import Barrier, Thread
from unittest.mock import patch

from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.candidate_db import (
    SCHEMA_VERSION,
    apply_migrations,
    candidate_db_health,
    current_version,
    finish_discovery_run,
    record_discovery_run,
    rollback_migrations,
)


class CandidateDbTests(unittest.TestCase):
    def test_health_reports_ok_missing_and_corrupt_without_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "candidates.db"
            self.assertEqual("missing", candidate_db_health(path)["status"])

            apply_migrations(path)
            healthy = candidate_db_health(path)
            self.assertEqual("ok", healthy["status"])
            self.assertEqual("ok", healthy["integrity"])
            self.assertEqual(SCHEMA_VERSION, healthy["schema_version"])
            self.assertNotIn("candidates", repr(healthy).lower())

            corrupt = folder / "corrupt.db"
            corrupt.write_bytes(b"not a sqlite database")
            self.assertEqual("corrupt", candidate_db_health(corrupt)["status"])

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
                    "SELECT title, status FROM candidates WHERE candidate_id = ?",
                    ("01ARZ3NDEKTSV4RRFFQ69G5FAV",),
                ).fetchone()
                self.assertEqual("Test candidate", row[0])
                self.assertEqual("new", row[1])
            finally:
                connection.close()

    def test_v2_migration_keeps_action_fk_removed_for_purge(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            apply_migrations(path)
            self.assertEqual(SCHEMA_VERSION, current_version(path))
            connection = sqlite_connect(path)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute(
                    "INSERT INTO candidates (candidate_id, channel_id, "
                    "discovered_at, title, created_at, status) "
                    "VALUES ('CND-x', 'CHN-sec', '2026-08-06T00:00:00Z', "
                    "'X', '2026-08-06T00:00:00Z', 'dismissed')"
                )
                connection.execute(
                    "INSERT INTO candidate_actions (action_id, candidate_id, "
                    "action, reason, actor, acted_at) "
                    "VALUES ('CA-1', 'CND-x', 'dismiss', 'noise', "
                    "'max', '2026-08-06T00:00:00Z')"
                )
                # FK is gone in v2: deleting the candidate must succeed while
                # the audit action row survives.
                connection.execute(
                    "DELETE FROM candidates WHERE candidate_id = 'CND-x'"
                )
                connection.commit()
                row = connection.execute(
                    "SELECT action FROM candidate_actions WHERE action_id = 'CA-1'"
                ).fetchone()
                self.assertEqual("dismiss", row[0])
            finally:
                connection.close()

    def test_v3_migration_preserves_candidate_and_action_on_v2_rollback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            create_v2_schema(path)
            connection = sqlite_connect(path)
            try:
                connection.execute(
                    "INSERT INTO candidates (candidate_id, channel_id, "
                    "discovered_at, title, created_at, status) "
                    "VALUES ('CND-x', 'CHN-sec', '2026-08-06T00:00:00Z', "
                    "'X', '2026-08-06T00:00:00Z', 'dismissed')"
                )
                connection.execute(
                    "INSERT INTO candidate_actions (action_id, candidate_id, "
                    "action, reason, actor, acted_at) "
                    "VALUES ('CA-1', 'CND-x', 'dismiss', 'noise', "
                    "'max', '2026-08-06T00:00:00Z')"
                )
                connection.commit()
            finally:
                connection.close()

            self.assertEqual(3, apply_migrations(path))
            connection = sqlite_connect(path)
            try:
                connection.execute(
                    "INSERT INTO mutation_audit (event_id, mutation_id, "
                    "event_status, operation, actor, target_type, target_id, "
                    "target_version, input_digest, issued_at, event_at, "
                    "expires_at, reason_code, domain_action_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "MA-1",
                        "MUT-1",
                        "previewed",
                        "candidate.dismiss",
                        "max",
                        "candidate",
                        "CND-x",
                        "a" * 64,
                        "b" * 64,
                        "2026-08-12T00:00:00Z",
                        "2026-08-12T00:00:00Z",
                        "2026-08-12T00:10:00Z",
                        None,
                        None,
                    ),
                )
                connection.commit()
            finally:
                connection.close()

            rollback_migrations(path, to_version=2)
            self.assertEqual(2, current_version(path))
            connection = sqlite_connect(path)
            try:
                self.assertEqual(
                    "CND-x",
                    connection.execute(
                        "SELECT candidate_id FROM candidates "
                        "WHERE candidate_id = 'CND-x'"
                    ).fetchone()[0],
                )
                self.assertEqual(
                    "dismiss",
                    connection.execute(
                        "SELECT action FROM candidate_actions "
                        "WHERE action_id = 'CA-1'"
                    ).fetchone()[0],
                )
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute("SELECT * FROM mutation_audit").fetchall()
            finally:
                connection.close()

    def test_candidate_version_changes_when_any_candidate_field_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = candidate_db.candidate_db_path(root)
            apply_migrations(path)
            connection = sqlite_connect(path)
            try:
                connection.execute(
                    "INSERT INTO candidates (candidate_id, channel_id, "
                    "discovered_at, title, snippet, created_at, status) "
                    "VALUES ('CND-x', 'CHN-sec', '2026-08-06T00:00:00Z', "
                    "'X', 'before', '2026-08-06T00:00:00Z', 'new')"
                )
                connection.commit()
            finally:
                connection.close()
            before = candidate_db.candidate_version(root, "CND-x")
            connection = sqlite_connect(path)
            try:
                connection.execute(
                    "UPDATE candidates SET snippet = 'after' "
                    "WHERE candidate_id = 'CND-x'"
                )
                connection.commit()
            finally:
                connection.close()
            after = candidate_db.candidate_version(root, "CND-x")
            self.assertRegex(before, r"^[0-9a-f]{64}$")
            self.assertNotEqual(before, after)

    def test_start_discovery_run_allows_only_one_concurrent_channel_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            apply_migrations(path)
            barrier = Barrier(3)
            outcomes: Queue[tuple[str, str]] = Queue()

            def start(run_id: str) -> None:
                try:
                    barrier.wait(timeout=5)
                    candidate_db.start_discovery_run(
                        path,
                        run_id,
                        "CHN-test",
                        "2026-08-10T00:00:00Z",
                        stale_before="2026-08-09T23:30:00Z",
                    )
                except ValueError as exc:
                    outcomes.put(("refused", str(exc)))
                except Exception as exc:
                    outcomes.put(("unexpected", type(exc).__name__))
                else:
                    outcomes.put(("started", run_id))

            workers = [
                Thread(target=start, args=("RUN-one",)),
                Thread(target=start, args=("RUN-two",)),
            ]
            for worker in workers:
                worker.start()
            barrier.wait(timeout=5)
            for worker in workers:
                worker.join(timeout=5)
                self.assertFalse(worker.is_alive())

            results = [outcomes.get_nowait(), outcomes.get_nowait()]
            self.assertEqual(1, sum(result[0] == "started" for result in results))
            self.assertEqual(1, sum(result[0] == "refused" for result in results))
            self.assertIn(
                (
                    "refused",
                    "channel CHN-test already has a running discovery run",
                ),
                results,
            )
            started_run = next(
                result[1] for result in results if result[0] == "started"
            )
            connection = sqlite_connect(path)
            try:
                rows = connection.execute(
                    "SELECT run_id, status FROM discovery_runs "
                    "WHERE channel_id = 'CHN-test'"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual([(started_run, "running")], rows)

    def test_start_discovery_run_reclaims_stale_and_inserts_new_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            record_discovery_run(
                path,
                "RUN-stale",
                "CHN-test",
                "2026-08-09T23:00:00Z",
                status="running",
            )

            candidate_db.start_discovery_run(
                path,
                "RUN-new",
                "CHN-test",
                "2026-08-10T00:00:00Z",
                stale_before="2026-08-09T23:30:00Z",
            )

            connection = sqlite_connect(path)
            try:
                rows = connection.execute(
                    "SELECT run_id, status FROM discovery_runs ORDER BY run_id"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual([("RUN-new", "running"), ("RUN-stale", "failed")], rows)

    def test_start_discovery_run_rolls_back_stale_reclamation_on_insert_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            record_discovery_run(
                path,
                "RUN-stale",
                "CHN-test",
                "2026-08-09T23:00:00Z",
                status="running",
            )

            def deny_run_insert(db_path: Path) -> sqlite3.Connection:
                connection = sqlite3.connect(db_path)

                def authorize(
                    action: int,
                    table: str | None,
                    column: str | None,
                    database: str | None,
                    trigger: str | None,
                ) -> int:
                    del column, database, trigger
                    if action == sqlite3.SQLITE_INSERT and table == "discovery_runs":
                        return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK

                connection.set_authorizer(authorize)
                return connection

            with (
                patch.object(candidate_db, "_connect", side_effect=deny_run_insert),
                self.assertRaises(TransactionError),
            ):
                candidate_db.start_discovery_run(
                    path,
                    "RUN-new",
                    "CHN-test",
                    "2026-08-10T00:00:00Z",
                    stale_before="2026-08-09T23:30:00Z",
                )

            connection = sqlite_connect(path)
            try:
                rows = connection.execute(
                    "SELECT run_id, status FROM discovery_runs ORDER BY run_id"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual([("RUN-stale", "running")], rows)

    def test_start_discovery_run_ignores_live_run_on_another_channel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            record_discovery_run(
                path,
                "RUN-other",
                "CHN-other",
                "2026-08-10T00:00:00Z",
                status="running",
            )

            candidate_db.start_discovery_run(
                path,
                "RUN-new",
                "CHN-test",
                "2026-08-10T00:00:00Z",
                stale_before="2026-08-09T23:30:00Z",
            )

            connection = sqlite_connect(path)
            try:
                rows = connection.execute(
                    "SELECT channel_id, status FROM discovery_runs ORDER BY run_id"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual([("CHN-test", "running"), ("CHN-other", "running")], rows)

    def test_finish_discovery_run_updates_terminal_fields_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            record_discovery_run(
                path,
                "RUN-terminal",
                "CHN-test",
                "2026-08-10T00:00:00Z",
                status="running",
            )

            finish_discovery_run(
                path,
                "RUN-terminal",
                status="failed",
                candidate_count=2,
                finished_at="2026-08-10T00:00:03Z",
                retries=2,
                http_errors=3,
                parse_errors=1,
            )

            connection = sqlite_connect(path)
            try:
                row = connection.execute(
                    "SELECT status, candidate_count, finished_at, retries, "
                    "http_errors, parse_errors FROM discovery_runs "
                    "WHERE run_id = 'RUN-terminal'"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(("failed", 2, "2026-08-10T00:00:03Z", 2, 3, 1), row)
            with self.assertRaises(TransactionError):
                finish_discovery_run(
                    path,
                    "RUN-terminal",
                    status="succeeded",
                    finished_at="2026-08-10T00:00:04Z",
                )

    def test_finish_discovery_run_preserves_omitted_optional_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.db"
            record_discovery_run(
                path,
                "RUN-compatible",
                "CHN-test",
                "2026-08-10T00:00:00Z",
                status="running",
                candidate_count=4,
                retries=2,
                http_errors=3,
                parse_errors=1,
            )

            finish_discovery_run(
                path,
                "RUN-compatible",
                status="failed",
                finished_at="2026-08-10T00:00:03Z",
            )

            connection = sqlite_connect(path)
            try:
                row = connection.execute(
                    "SELECT candidate_count, retries, http_errors, parse_errors "
                    "FROM discovery_runs WHERE run_id = 'RUN-compatible'"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual((4, 2, 3, 1), row)


def sqlite_connect(path: Path):
    import sqlite3

    return sqlite3.connect(path)


def create_v2_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite_connect(path)
    try:
        connection.executescript(candidate_db._SCHEMA_V1)
        connection.executescript(candidate_db._SCHEMA_V2)
        connection.execute("PRAGMA user_version = 2")
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    unittest.main()
