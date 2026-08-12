"""Tests for the F-026 Web mutation security and transaction boundary."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.mutation_gateway import (
    MutationConflict,
    MutationForbidden,
    MutationGateway,
    MutationPreviewInput,
)
from research_os.services.web_identity import (
    BrowserSessionRegistry,
    load_web_identity,
)
from research_os.ui.app import _commit_candidate_dismiss


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class WebIdentityTests(unittest.TestCase):
    def _write_config(
        self,
        root: Path,
        *,
        researcher_id: object = "max",
        signing_secret: object = "s" * 64,
        mode: int = 0o600,
    ) -> Path:
        path = root / "00_System" / "web.local.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "researcher_id": researcher_id,
                    "mutation_signing_secret": signing_secret,
                }
            ),
            encoding="utf-8",
        )
        path.chmod(mode)
        return path

    def test_identity_loads_only_from_private_local_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self._write_config(root)
            identity = load_web_identity(root)
            self.assertIsNotNone(identity)
            assert identity is not None
            self.assertEqual("max", identity.researcher_id)
            self.assertEqual(b"s" * 64, identity.mutation_signing_secret)

            if os.name == "posix":
                path.chmod(0o644)
                self.assertIsNone(load_web_identity(root))

    def test_missing_or_invalid_identity_disables_mutations_without_raising(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertIsNone(load_web_identity(root))
            path = self._write_config(root, signing_secret="short")
            self.assertIsNone(load_web_identity(root))
            path.write_text("{not-json", encoding="utf-8")
            self.assertIsNone(load_web_identity(root))
            self._write_config(root, researcher_id=7)
            self.assertIsNone(load_web_identity(root))
            self._write_config(root, researcher_id="x" * 129)
            self.assertIsNone(load_web_identity(root))

    def test_session_csrf_is_opaque_bound_expiring_and_process_local(self) -> None:
        clock = MutableClock(datetime(2026, 8, 12, tzinfo=UTC))
        sessions = BrowserSessionRegistry(now=clock, ttl=timedelta(hours=1))
        session_id, csrf_token = sessions.issue()
        other_session_id, other_csrf = sessions.issue()

        self.assertNotIn("max", session_id + csrf_token)
        self.assertNotEqual(session_id, csrf_token)
        self.assertTrue(sessions.validate(session_id, csrf_token))
        self.assertFalse(sessions.validate(session_id, other_csrf))
        self.assertFalse(sessions.validate(other_session_id, csrf_token))
        self.assertFalse(sessions.validate("missing", csrf_token))

        clock.value += timedelta(hours=1, seconds=1)
        self.assertFalse(sessions.validate(session_id, csrf_token))
        sessions.clear()
        self.assertFalse(sessions.validate(other_session_id, other_csrf))


class MutationGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock(datetime(2026, 8, 12, tzinfo=UTC))
        self.gateway = MutationGateway(b"s" * 64, now=self.clock)

    def _issue(self):
        return self.gateway.issue(
            MutationPreviewInput(
                operation="candidate.dismiss",
                actor="max",
                target_type="candidate",
                target_id="CND-1",
                target_version="a" * 64,
                normalized_input={"reason": "out of scope"},
                summary={"status_before": "new", "status_after": "dismissed"},
            )
        )

    def _commit(self, token: str, **overrides):
        values = {
            "actor": "max",
            "operation": "candidate.dismiss",
            "current_target_version": lambda _: "a" * 64,
            "execute": lambda _: {"action_id": "CA-1"},
        }
        values.update(overrides)
        return self.gateway.commit(token, **values)

    def test_preview_is_canonical_signed_and_token_contains_no_business_data(
        self,
    ) -> None:
        grant = self._issue()
        self.assertEqual("candidate.dismiss", grant.preview.operation)
        self.assertEqual("out of scope", grant.preview.normalized_input["reason"])
        lifetime = grant.preview.expires_at - grant.preview.issued_at
        self.assertEqual(600, int(lifetime.total_seconds()))
        self.assertNotIn("CND-1", grant.token)
        self.assertNotIn("out of scope", grant.token)
        self.assertNotIn("max", grant.token)

    def test_commit_rejects_tamper_actor_operation_and_changed_target(self) -> None:
        grant = self._issue()
        with self.assertRaisesRegex(MutationForbidden, "invalid_token"):
            self._commit(grant.token[:-1] + ("A" if grant.token[-1] != "A" else "B"))
        grant = self._issue()
        with self.assertRaisesRegex(MutationForbidden, "actor_mismatch"):
            self._commit(grant.token, actor="other")
        grant = self._issue()
        with self.assertRaisesRegex(MutationForbidden, "operation_mismatch"):
            self._commit(grant.token, operation="candidate.restore")
        grant = self._issue()
        with self.assertRaisesRegex(MutationConflict, "target_changed"):
            self._commit(grant.token, current_target_version=lambda _: "b" * 64)

    def test_commit_consumes_nonce_and_restart_invalidates_token(self) -> None:
        grant = self._issue()
        result = self._commit(grant.token)
        self.assertEqual("CA-1", result["action_id"])
        self.assertEqual("consumed", self.gateway.nonce_state(grant.preview.nonce))
        with self.assertRaisesRegex(MutationConflict, "replayed"):
            self._commit(grant.token)

        restarted = MutationGateway(b"s" * 64, now=self.clock)
        with self.assertRaisesRegex(MutationConflict, "unknown_preview"):
            restarted.commit(
                grant.token,
                actor="max",
                operation="candidate.dismiss",
                current_target_version=lambda _: "a" * 64,
                execute=lambda _: {},
            )

    def test_expired_nonce_never_executes(self) -> None:
        grant = self._issue()
        self.clock.value += timedelta(minutes=10, seconds=1)
        called = False

        def execute(_):
            nonlocal called
            called = True
            return {}

        with self.assertRaisesRegex(MutationConflict, "expired"):
            self._commit(grant.token, execute=execute)
        self.assertFalse(called)

    def test_only_transaction_error_restores_unchanged_unexpired_nonce(self) -> None:
        grant = self._issue()

        def fail(_):
            raise TransactionError("database locked")

        with self.assertRaises(TransactionError):
            self._commit(grant.token, execute=fail)
        self.assertEqual("issued", self.gateway.nonce_state(grant.preview.nonce))
        self.assertEqual("CA-1", self._commit(grant.token)["action_id"])

    def test_concurrent_commit_enters_adapter_once(self) -> None:
        grant = self._issue()
        entered = Event()
        release = Event()
        outcomes: list[str] = []

        def execute(_):
            entered.set()
            release.wait(timeout=3)
            return {"action_id": "CA-1"}

        def commit() -> None:
            try:
                self._commit(grant.token, execute=execute)
            except MutationConflict as exc:
                outcomes.append(exc.reason_code)
            else:
                outcomes.append("committed")

        first = Thread(target=commit)
        first.start()
        self.assertTrue(entered.wait(timeout=3))
        second = Thread(target=commit)
        second.start()
        second.join(timeout=3)
        release.set()
        first.join(timeout=3)
        self.assertCountEqual(["committing", "committed"], outcomes)


class CandidateDismissTransactionTests(unittest.TestCase):
    def _root_and_preview(self, temp: str):
        root = Path(temp)
        path = candidate_db.candidate_db_path(root)
        candidate_db.apply_migrations(path)
        candidate_db.insert_candidates(
            path,
            [
                {
                    "candidate_id": "CND-1",
                    "title": "Candidate one",
                    "canonical_url": "https://example.com/one",
                }
            ],
            "CHN-test",
            "2026-08-12T00:00:00Z",
        )
        gateway = MutationGateway(
            b"s" * 64,
            now=lambda: datetime(2026, 8, 12, tzinfo=UTC),
        )
        grant = gateway.issue(
            MutationPreviewInput(
                operation="candidate.dismiss",
                actor="max",
                target_type="candidate",
                target_id="CND-1",
                target_version=candidate_db.candidate_version(root, "CND-1"),
                normalized_input={"reason": "out of scope"},
                summary={"status_before": "new", "status_after": "dismissed"},
            )
        )
        return root, grant.preview

    def _rows(self, root: Path):
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            status = connection.execute(
                "SELECT status FROM candidates WHERE candidate_id = 'CND-1'"
            ).fetchone()[0]
            actions = connection.execute(
                "SELECT action_id, actor, reason FROM candidate_actions"
            ).fetchall()
            audits = connection.execute(
                "SELECT mutation_id, event_status, domain_action_id "
                "FROM mutation_audit"
            ).fetchall()
            return status, actions, audits
        finally:
            connection.close()

    def test_candidate_action_and_committed_audit_share_one_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, preview = self._root_and_preview(temp)
            result = _commit_candidate_dismiss(root, preview)
            status, actions, audits = self._rows(root)
        self.assertEqual("dismissed", status)
        self.assertEqual([("max", "out of scope")], [row[1:] for row in actions])
        self.assertEqual(
            [(preview.mutation_id, "committed", actions[0][0])],
            audits,
        )
        self.assertEqual(actions[0][0], result["action_id"])
        self.assertEqual(preview.mutation_id, result["mutation_id"])

    def test_domain_action_failure_rolls_back_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, preview = self._root_and_preview(temp)
            with patch(
                "research_os.services.triage._record_action",
                side_effect=sqlite3.OperationalError("injected action failure"),
            ), self.assertRaises(TransactionError):
                _commit_candidate_dismiss(root, preview)
            self.assertEqual(("new", [], []), self._rows(root))

    def test_commit_audit_failure_rolls_back_candidate_and_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, preview = self._root_and_preview(temp)
            with patch(
                "research_os.ui.app.record_mutation_event",
                side_effect=sqlite3.OperationalError("injected audit failure"),
            ), self.assertRaises(TransactionError):
                _commit_candidate_dismiss(root, preview)
            self.assertEqual(("new", [], []), self._rows(root))


if __name__ == "__main__":
    unittest.main()
