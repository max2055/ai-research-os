from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.mutation_gateway import MutationGateway
from research_os.services.triage import dismiss_candidate
from research_os.services.web_candidate_mutations import (
    commit_candidate_restore,
    prepare_candidate_restore,
)


class CandidateRestoreAdapterTests(unittest.TestCase):
    def _root(self, temp: str, *, status: str = "dismissed") -> Path:
        root = Path(temp)
        path = candidate_db.candidate_db_path(root)
        candidate_db.apply_migrations(path)
        candidate_db.insert_candidates(
            path,
            [
                {
                    "candidate_id": "CND-restore-1",
                    "title": "Restore candidate",
                    "canonical_url": "https://example.com/restore",
                }
            ],
            "CHN-test",
            "2026-08-13T00:00:00Z",
        )
        if status == "dismissed":
            dismiss_candidate(
                root,
                "CND-restore-1",
                actor="max",
                reason="noise",
                apply=True,
            )
        elif status != "new":
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "UPDATE candidates SET status = ? WHERE candidate_id = ?",
                    (status, "CND-restore-1"),
                )
                connection.commit()
            finally:
                connection.close()
        return root

    def _rows(self, root: Path) -> tuple[str, list[tuple], list[tuple]]:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            status = connection.execute(
                "SELECT status FROM candidates WHERE candidate_id = ?",
                ("CND-restore-1",),
            ).fetchone()[0]
            actions = connection.execute(
                "SELECT action_id, action, actor FROM candidate_actions "
                "WHERE action = 'restore'"
            ).fetchall()
            audits = connection.execute(
                "SELECT mutation_id, event_status, domain_action_id "
                "FROM mutation_audit WHERE operation = 'candidate.restore'"
            ).fetchall()
            return str(status), actions, audits
        finally:
            connection.close()

    def _preview(self, root: Path):
        gateway = MutationGateway(
            b"s" * 64,
            now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
        )
        return gateway.issue(
            prepare_candidate_restore(root, "CND-restore-1", actor="max")
        ).preview

    def test_restore_preview_is_read_only_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            before = self._rows(root)
            preview_input = prepare_candidate_restore(
                root, "CND-restore-1", actor="max"
            )
            after = self._rows(root)

        self.assertEqual(before, after)
        self.assertEqual("candidate.restore", preview_input.operation)
        self.assertEqual("max", preview_input.actor)
        self.assertEqual("candidate", preview_input.target_type)
        self.assertEqual("CND-restore-1", preview_input.target_id)
        self.assertRegex(preview_input.target_version, r"^[0-9a-f]{64}$")
        self.assertEqual(
            {"reason": "restore from dismissed to review queue"},
            preview_input.normalized_input,
        )
        self.assertEqual("dismissed", preview_input.summary["status_before"])
        self.assertEqual("new", preview_input.summary["status_after"])

    def test_restore_action_and_audit_share_one_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            preview = self._preview(root)
            result = commit_candidate_restore(root, preview)
            status, actions, audits = self._rows(root)

        self.assertEqual("new", status)
        self.assertEqual([("restore", "max")], [row[1:] for row in actions])
        self.assertEqual(
            [(preview.mutation_id, "committed", actions[0][0])],
            audits,
        )
        self.assertEqual(actions[0][0], result["action_id"])

    def test_restore_audit_failure_rolls_back_candidate_and_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            preview = self._preview(root)
            with (
                patch(
                    "research_os.services.web_candidate_mutations.record_mutation_event",
                    side_effect=sqlite3.OperationalError("injected audit failure"),
                ),
                self.assertRaises(TransactionError),
            ):
                commit_candidate_restore(root, preview)
            status, actions, audits = self._rows(root)

        self.assertEqual("dismissed", status)
        self.assertEqual([], actions)
        self.assertEqual([], audits)

    def test_restore_adapter_rejects_wrong_operation_and_invalid_status(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            preview = self._preview(root)
            object.__setattr__(preview, "operation", "candidate.dismiss")
            with self.assertRaisesRegex(ValueError, "operation"):
                commit_candidate_restore(root, preview)

        for status in ("new", "promoted"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = self._root(temp, status=status)
                with self.assertRaises(ValueError):
                    prepare_candidate_restore(root, "CND-restore-1", actor="max")


if __name__ == "__main__":
    unittest.main()
