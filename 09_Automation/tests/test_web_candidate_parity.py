from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from research_os.adapters.file import FileCaptureAdapter
from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.mutation_audit import normalized_input_digest
from research_os.services.mutation_gateway import MutationGateway
from research_os.services.triage import dismiss_candidate
from research_os.services.web_candidate_mutations import (
    commit_candidate_promote,
    commit_candidate_restore,
    prepare_candidate_promote,
    prepare_candidate_restore,
)
from research_os.ui.app import create_app
from test_m5_dashboard_jobs import prepared_root
from test_promote import PromoteTests


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


class CandidatePromoteAdapterTests(unittest.TestCase):
    def _root(self, temp: str) -> tuple[Path, Path]:
        fixtures = PromoteTests()
        root = fixtures._make_root(temp)
        fixtures._insert_and_enrich(root)
        return root, fixtures._html_file(root)

    def _prepared(self, root: Path, capture: Path):
        return prepare_candidate_promote(
            root,
            "CND-0000",
            actor="max",
            adapter=FileCaptureAdapter(capture),
        )

    def _preview(self, prepared):
        gateway = MutationGateway(
            b"s" * 64,
            now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
        )
        return gateway.issue(prepared.preview_input).preview

    def _database_rows(self, root: Path) -> tuple[tuple, list[tuple], list[tuple]]:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            candidate = connection.execute(
                "SELECT status, promoted_source_id FROM candidates "
                "WHERE candidate_id = 'CND-0000'"
            ).fetchone()
            actions = connection.execute(
                "SELECT action_id, action, actor FROM candidate_actions "
                "WHERE candidate_id = 'CND-0000' AND action = 'promote'"
            ).fetchall()
            audits = connection.execute(
                "SELECT mutation_id, event_status, domain_action_id, input_digest "
                "FROM mutation_audit WHERE operation = 'candidate.promote'"
            ).fetchall()
            return candidate, actions, audits
        finally:
            connection.close()

    def test_promote_preview_freezes_bounded_source_and_asset_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, capture = self._root(temp)
            before = self._database_rows(root)
            prepared = self._prepared(root, capture)
            after = self._database_rows(root)

        value = prepared.preview_input
        self.assertEqual(before, after)
        self.assertEqual("candidate.promote", value.operation)
        self.assertEqual("max", value.actor)
        self.assertEqual("candidate", value.target_type)
        self.assertEqual("CND-0000", value.target_id)
        self.assertRegex(value.target_version, r"^[0-9a-f]{64}$")
        self.assertEqual(prepared.plan.source_id, value.normalized_input["source_id"])
        self.assertEqual(
            prepared.plan.capture.content_sha256,
            value.normalized_input["content_sha256"],
        )
        self.assertEqual(2, len(value.normalized_input["assets"]))
        serialized = json.dumps(value.normalized_input, sort_keys=True)
        self.assertNotIn("HBM production capacity announcement", serialized)
        self.assertNotIn("preview_token", serialized)
        self.assertNotIn("secret", serialized.lower())
        self.assertEqual(64, len(normalized_input_digest(value.normalized_input)))
        self.assertFalse((root / prepared.plan.source_path).exists())

    def test_promote_commit_coordinates_files_candidate_action_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, capture = self._root(temp)
            prepared = self._prepared(root, capture)
            preview = self._preview(prepared)
            result = commit_candidate_promote(root, preview, prepared.plan)
            candidate, actions, audits = self._database_rows(root)

            self.assertEqual(("promoted", prepared.plan.source_id), candidate)
            self.assertTrue((root / prepared.plan.source_path).is_file())
            self.assertTrue(
                all((root / path).is_file() for path in prepared.plan.capture.assets)
            )
            self.assertEqual([("promote", "max")], [row[1:] for row in actions])
            self.assertEqual(
                [
                    (
                        preview.mutation_id,
                        "committed",
                        actions[0][0],
                        normalized_input_digest(preview.normalized_input),
                    )
                ],
                audits,
            )
            self.assertEqual(prepared.plan.source_id, result["source_id"])
            self.assertEqual(actions[0][0], result["action_id"])

    def test_promote_audit_failure_compensates_files_and_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, capture = self._root(temp)
            prepared = self._prepared(root, capture)
            preview = self._preview(prepared)
            with (
                patch(
                    "research_os.services.web_candidate_mutations."
                    "record_mutation_event",
                    side_effect=sqlite3.OperationalError("injected audit failure"),
                ),
                self.assertRaises(TransactionError),
            ):
                commit_candidate_promote(root, preview, prepared.plan)

            candidate, actions, audits = self._database_rows(root)
            self.assertEqual(("new", None), candidate)
            self.assertEqual([], actions)
            self.assertEqual([], audits)
            self.assertFalse((root / prepared.plan.source_path).exists())
            self.assertTrue(
                all(not (root / path).exists() for path in prepared.plan.capture.assets)
            )
            manifest = (
                root
                / "09_Automation"
                / "operational"
                / "mutation-recovery"
                / f"{preview.mutation_id}.json"
            )
            record = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual("compensated", record["status"])
            self.assertEqual("candidate.promote", record["operation"])
            self.assertEqual(prepared.plan.source_id, record["source_id"])
            serialized = manifest.read_text(encoding="utf-8")
            self.assertNotIn("HBM production capacity announcement", serialized)
            self.assertNotIn("secret", serialized.lower())

    def test_promote_rejects_changed_candidate_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, capture = self._root(temp)
            prepared = self._prepared(root, capture)
            preview = self._preview(prepared)
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET status = 'dismissed' "
                    "WHERE candidate_id = 'CND-0000'"
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaisesRegex(ValueError, "changed"):
                commit_candidate_promote(root, preview, prepared.plan)
            self.assertFalse((root / prepared.plan.source_path).exists())


class CandidateRestoreHttpTests(unittest.TestCase):
    def _root(self, temp: str, *, status: str = "dismissed") -> Path:
        root = prepared_root(temp)
        config = root / "00_System" / "web.local.json"
        config.write_text(
            json.dumps(
                {
                    "researcher_id": "max",
                    "mutation_signing_secret": "s" * 64,
                }
            ),
            encoding="utf-8",
        )
        config.chmod(0o600)
        candidate_db.insert_candidates(
            candidate_db.candidate_db_path(root),
            [
                {
                    "candidate_id": "CND-restore-http",
                    "title": "Restore <unsafe>",
                    "canonical_url": "https://example.com/restore-http",
                }
            ],
            "CHN-test",
            "2026-08-13T00:00:00Z",
        )
        if status == "dismissed":
            dismiss_candidate(
                root,
                "CND-restore-http",
                actor="max",
                reason="noise",
                apply=True,
            )
        elif status != "new":
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET status = ? WHERE candidate_id = ?",
                    (status, "CND-restore-http"),
                )
                connection.commit()
            finally:
                connection.close()
        return root

    def _client(self, root: Path) -> TestClient:
        return TestClient(create_app(root), base_url="http://127.0.0.1")

    def _hidden(self, text: str, name: str) -> str:
        match = re.search(
            rf'<input[^>]+name="{re.escape(name)}"[^>]+value="([^"]+)"',
            text,
        )
        self.assertIsNotNone(match, f"missing hidden field {name}")
        assert match is not None
        return match.group(1)

    def _counts(self, root: Path) -> tuple[str, int, int]:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            status = connection.execute(
                "SELECT status FROM candidates WHERE candidate_id = ?",
                ("CND-restore-http",),
            ).fetchone()[0]
            actions = connection.execute(
                "SELECT COUNT(*) FROM candidate_actions WHERE action = 'restore'"
            ).fetchone()[0]
            audits = connection.execute(
                "SELECT COUNT(*) FROM mutation_audit "
                "WHERE operation = 'candidate.restore' AND event_status = 'committed'"
            ).fetchone()[0]
            return str(status), int(actions), int(audits)
        finally:
            connection.close()

    def test_restore_http_preview_commit_redirect_refresh_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = self._client(root)
            detail = client.get("/pipeline/queue/CND-restore-http")
            self.assertEqual(200, detail.status_code)
            self.assertIn("恢复候选", detail.text)
            csrf = self._hidden(detail.text, "csrf_token")

            preview = client.post(
                "/pipeline/queue/CND-restore-http/restore/preview",
                data={"csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(200, preview.status_code)
            self.assertIn("Restore &lt;unsafe&gt;", preview.text)
            self.assertEqual(("dismissed", 0, 0), self._counts(root))
            self.assertNotRegex(
                preview.text,
                r'name="(?:actor|target_id|reason|status_after)"',
            )
            token = self._hidden(preview.text, "preview_token")
            csrf = self._hidden(preview.text, "csrf_token")

            committed = client.post(
                "/pipeline/queue/CND-restore-http/restore/commit",
                data={"preview_token": token, "csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
                follow_redirects=False,
            )
            self.assertEqual(303, committed.status_code)
            result = client.get(committed.headers["location"])
            self.assertEqual(200, result.status_code)
            self.assertEqual(
                result.text,
                client.get(committed.headers["location"]).text,
            )
            self.assertIn("已恢复", result.text)
            self.assertEqual(("new", 1, 1), self._counts(root))

            replay = client.post(
                "/pipeline/queue/CND-restore-http/restore/commit",
                data={"preview_token": token, "csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(409, replay.status_code)
            self.assertEqual(("new", 1, 1), self._counts(root))

    def test_restore_http_requires_browser_boundary_and_valid_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(temp)
            client = self._client(root)
            detail = client.get("/pipeline/queue/CND-restore-http")
            csrf = self._hidden(detail.text, "csrf_token")
            path = "/pipeline/queue/CND-restore-http/restore/preview"
            for headers, token in (
                ({}, csrf),
                ({"Origin": "https://attacker.example"}, csrf),
                ({"Origin": "http://127.0.0.1"}, "wrong"),
            ):
                response = client.post(
                    path,
                    data={"csrf_token": token},
                    headers=headers,
                )
                self.assertEqual(403, response.status_code)
            self.assertEqual(("dismissed", 0, 0), self._counts(root))

        for status in ("new", "promoted"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = self._root(temp, status=status)
                client = self._client(root)
                detail = client.get("/pipeline/queue/CND-restore-http")
                self.assertNotIn("恢复候选", detail.text)


if __name__ == "__main__":
    unittest.main()
