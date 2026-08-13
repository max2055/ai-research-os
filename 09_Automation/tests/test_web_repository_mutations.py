from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.mutation_gateway import MutationGateway
from research_os.services.web_repository_mutations import (
    commit_repository_mutation,
    prepare_repository_mutation,
    repository_target_version,
)


class RepositoryMutationCoordinatorTests(unittest.TestCase):
    def _root(self, temp: str) -> Path:
        root = Path(temp)
        (root / "existing.md").write_text("before\n", encoding="utf-8")
        candidate_db.apply_migrations(candidate_db.candidate_db_path(root))
        return root

    def _prepared(self, root: Path):
        return prepare_repository_mutation(
            root,
            operation="research.test",
            actor="max",
            target_type="event",
            target_id="EVT-20260813-001",
            writes={
                Path("existing.md"): b"after\n",
                Path("nested/new.bin"): b"private captured bytes",
            },
            normalized_input={"decision": "create_pending"},
            summary={"write_count": 2},
        )

    def _preview(self, prepared):
        return MutationGateway(
            b"s" * 64,
            now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
        ).issue(prepared.preview_input).preview

    def test_prepare_freezes_bounded_manifest_and_current_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = self._prepared(root)

            self.assertEqual(
                prepared.preview_input.target_version,
                repository_target_version(root, prepared.plan),
            )
            self.assertEqual("research.test", prepared.preview_input.operation)
            self.assertEqual("max", prepared.preview_input.actor)
            self.assertEqual("event", prepared.preview_input.target_type)
            self.assertEqual("EVT-20260813-001", prepared.preview_input.target_id)
            manifest = prepared.preview_input.normalized_input["write_manifest"]
            self.assertEqual(
                ["existing.md", "nested/new.bin"],
                [row["path"] for row in manifest],
            )
            self.assertEqual(["replace", "create"], [row["mode"] for row in manifest])
            self.assertEqual([6, 22], [row["byte_count"] for row in manifest])
            serialized = json.dumps(prepared.preview_input.normalized_input)
            self.assertNotIn("private captured bytes", serialized)
            self.assertNotIn("before\\n", serialized)
            self.assertNotIn("after\\n", serialized)
            self.assertEqual(b"before\n", prepared.plan.writes[0].before_content)
            self.assertEqual(b"private captured bytes", prepared.plan.writes[1].content)

    def test_commit_applies_one_write_set_and_records_redacted_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = self._prepared(root)
            preview = self._preview(prepared)

            result = commit_repository_mutation(root, preview, prepared.plan)

            self.assertEqual("after\n", (root / "existing.md").read_text())
            self.assertEqual(
                b"private captured bytes", (root / "nested/new.bin").read_bytes()
            )
            self.assertEqual(preview.mutation_id, result["mutation_id"])
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                row = connection.execute(
                    "SELECT event_status, operation, actor, target_id, input_digest "
                    "FROM mutation_audit WHERE mutation_id = ?",
                    (preview.mutation_id,),
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(
                ("committed", "research.test", "max", "EVT-20260813-001"),
                row[:4],
            )
            self.assertRegex(str(row[4]), r"^[0-9a-f]{64}$")

    def test_stale_file_rejects_without_partial_write_or_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = self._prepared(root)
            preview = self._preview(prepared)
            (root / "existing.md").write_text("changed elsewhere\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "changed"):
                commit_repository_mutation(root, preview, prepared.plan)

            self.assertFalse((root / "nested/new.bin").exists())
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                count = connection.execute(
                    "SELECT COUNT(*) FROM mutation_audit WHERE mutation_id = ?",
                    (preview.mutation_id,),
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(0, count)

    def test_audit_failure_restores_files_and_records_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            prepared = self._prepared(root)
            preview = self._preview(prepared)
            before_version = repository_target_version(root, prepared.plan)

            with (
                patch(
                    "research_os.services.web_repository_mutations.record_mutation_event",
                    side_effect=sqlite3.OperationalError("injected audit failure"),
                ),
                self.assertRaises(TransactionError),
            ):
                commit_repository_mutation(root, preview, prepared.plan)

            self.assertEqual(b"before\n", (root / "existing.md").read_bytes())
            self.assertFalse((root / "nested/new.bin").exists())
            self.assertEqual(
                before_version,
                repository_target_version(root, prepared.plan),
            )
            manifest_path = (
                root
                / "09_Automation/operational/mutation-recovery"
                / f"{preview.mutation_id}.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("compensated", manifest["status"])
            self.assertEqual("research.test", manifest["operation"])
            self.assertEqual(
                ["existing.md", "nested/new.bin"],
                [row["path"] for row in manifest["writes"]],
            )
            serialized = manifest_path.read_text(encoding="utf-8")
            self.assertNotIn("private captured bytes", serialized)
            self.assertNotIn("before\\n", serialized)
            self.assertNotIn("after\\n", serialized)

    def test_prepare_rejects_escaping_duplicate_and_empty_write_sets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            for writes, message in (
                ({Path("../escape.md"): b"x"}, "escapes"),
                ({}, "at least one"),
            ):
                with self.subTest(message=message), self.assertRaisesRegex(
                    ValueError, message
                ):
                    prepare_repository_mutation(
                        root,
                        operation="research.test",
                        actor="max",
                        target_type="event",
                        target_id="EVT-1",
                        writes=writes,
                    )


if __name__ == "__main__":
    unittest.main()
