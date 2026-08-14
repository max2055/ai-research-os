"""Tests for the F-026 Web mutation security and transaction boundary."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

from fastapi.testclient import TestClient

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
    initialize_web_identity,
    load_web_identity,
)
from research_os.ui.app import _commit_candidate_dismiss, create_app
from test_m5_dashboard_jobs import prepared_root


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

    def test_initialize_identity_is_private_generated_and_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            researcher_id = initialize_web_identity(root, "  max  ")
            self.assertEqual("max", researcher_id)
            path = root / "00_System" / "web.local.json"
            self.assertEqual(0, path.stat().st_mode & 0o077)
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("max", raw["researcher_id"])
            self.assertGreaterEqual(len(raw["mutation_signing_secret"]), 32)
            self.assertNotIn(raw["mutation_signing_secret"], researcher_id)
            with self.assertRaisesRegex(FileExistsError, "already initialized"):
                initialize_web_identity(root, "other")
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
                "SELECT mutation_id, event_status, domain_action_id FROM mutation_audit"
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
            with (
                patch(
                    "research_os.services.triage._record_action",
                    side_effect=sqlite3.OperationalError("injected action failure"),
                ),
                self.assertRaises(TransactionError),
            ):
                _commit_candidate_dismiss(root, preview)
            self.assertEqual(("new", [], []), self._rows(root))

    def test_commit_audit_failure_rolls_back_candidate_and_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, preview = self._root_and_preview(temp)
            with (
                patch(
                    "research_os.ui.app.record_mutation_event",
                    side_effect=sqlite3.OperationalError("injected audit failure"),
                ),
                self.assertRaises(TransactionError),
            ):
                _commit_candidate_dismiss(root, preview)
            self.assertEqual(("new", [], []), self._rows(root))


class CandidateDismissHttpTests(unittest.TestCase):
    def _configured_root(self, temp: str, *, configured: bool = True) -> Path:
        root = prepared_root(temp)
        if configured:
            path = root / "00_System" / "web.local.json"
            path.write_text(
                json.dumps(
                    {
                        "researcher_id": "max",
                        "mutation_signing_secret": "s" * 64,
                    }
                ),
                encoding="utf-8",
            )
            path.chmod(0o600)
        candidate_db.insert_candidates(
            candidate_db.candidate_db_path(root),
            [
                {
                    "candidate_id": "CND-web-1",
                    "title": "Candidate <script>unsafe</script>",
                    "canonical_url": "https://example.com/web-1",
                    "snippet": "Test candidate",
                }
            ],
            "CHN-test",
            "2026-08-12T00:00:00Z",
        )
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

    def _status_and_counts(self, root: Path) -> tuple[str, int, int, int]:
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        try:
            status = connection.execute(
                "SELECT status FROM candidates WHERE candidate_id = 'CND-web-1'"
            ).fetchone()[0]
            actions = connection.execute(
                "SELECT COUNT(*) FROM candidate_actions"
            ).fetchone()[0]
            previews = connection.execute(
                "SELECT COUNT(*) FROM mutation_audit WHERE event_status = 'previewed'"
            ).fetchone()[0]
            commits = connection.execute(
                "SELECT COUNT(*) FROM mutation_audit WHERE event_status = 'committed'"
            ).fetchone()[0]
            return str(status), int(actions), int(previews), int(commits)
        finally:
            connection.close()

    def _preview(self, client: TestClient, *, reason: str = "out of scope"):
        detail = client.get("/pipeline/queue/CND-web-1")
        csrf = self._hidden(detail.text, "csrf_token")
        return client.post(
            "/pipeline/queue/CND-web-1/dismiss/preview",
            data={"reason": reason, "csrf_token": csrf},
            headers={"Origin": "http://127.0.0.1"},
        )

    def test_preview_commit_redirect_and_refresh_are_end_to_end_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp)
            client = self._client(root)
            detail = client.get("/pipeline/queue/CND-web-1")
            self.assertEqual(200, detail.status_code)
            self.assertIn("HttpOnly", detail.headers["set-cookie"])
            self.assertIn("SameSite=strict", detail.headers["set-cookie"])
            self.assertIn("驳回候选", detail.text)
            self.assertIn("本地 · 可审计", detail.text)
            self.assertNotIn("写入请走 CLI", detail.text)

            preview = self._preview(client, reason="  out   of scope  ")
            self.assertEqual(200, preview.status_code)
            self.assertEqual(("new", 0, 1, 0), self._status_and_counts(root))
            self.assertIn("Candidate &lt;script&gt;unsafe&lt;/script&gt;", preview.text)
            self.assertIn("out of scope", preview.text)
            self.assertNotRegex(
                preview.text,
                r'name="(?:actor|target_id|reason|status_after)"',
            )
            token = self._hidden(preview.text, "preview_token")
            csrf = self._hidden(preview.text, "csrf_token")

            committed = client.post(
                "/pipeline/queue/CND-web-1/dismiss/commit",
                data={"preview_token": token, "csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
                follow_redirects=False,
            )
            self.assertEqual(303, committed.status_code)
            self.assertNotIn(token, committed.headers["location"])
            result = client.get(committed.headers["location"])
            refreshed = client.get(committed.headers["location"])
            self.assertEqual(200, result.status_code)
            self.assertEqual(result.text, refreshed.text)
            self.assertIn("已驳回", result.text)
            self.assertEqual(("dismissed", 1, 1, 1), self._status_and_counts(root))

            candidate_db.insert_candidates(
                candidate_db.candidate_db_path(root),
                [
                    {
                        "candidate_id": "CND-web-2",
                        "title": "Other candidate",
                        "canonical_url": "https://example.com/web-2",
                    }
                ],
                "CHN-test",
                "2026-08-12T00:01:00Z",
            )
            wrong_target = committed.headers["location"].replace(
                "CND-web-1", "CND-web-2"
            )
            self.assertEqual(404, client.get(wrong_target).status_code)

            replay = client.post(
                "/pipeline/queue/CND-web-1/dismiss/commit",
                data={"preview_token": token, "csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(409, replay.status_code)
            self.assertEqual(("dismissed", 1, 1, 1), self._status_and_counts(root))

    def test_missing_identity_keeps_get_readable_and_blocks_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp, configured=False)
            client = self._client(root)
            detail = client.get("/pipeline/queue/CND-web-1")
            self.assertEqual(200, detail.status_code)
            self.assertNotIn("驳回候选", detail.text)
            self.assertIn("/setup", detail.text)
            response = client.post(
                "/pipeline/queue/CND-web-1/dismiss/preview",
                data={"reason": "noise", "csrf_token": "missing"},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(503, response.status_code)
            self.assertEqual(("new", 0, 0, 0), self._status_and_counts(root))

    def test_setup_initializes_local_identity_and_write_entry_degrades_to_html(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp, configured=False)
            client = self._client(root)
            setup = client.get("/setup")
            self.assertEqual(200, setup.status_code)
            self.assertIn('name="researcher_id"', setup.text)

            source_form = client.get("/sources/new")
            self.assertEqual(200, source_form.status_code)
            self.assertIn("只读模式", source_form.text)
            self.assertIn('href="/setup"', source_form.text)

            initialized = client.post(
                "/setup",
                data={"researcher_id": "max"},
                headers={"Origin": "http://127.0.0.1"},
                follow_redirects=False,
            )
            self.assertEqual(303, initialized.status_code)
            self.assertEqual("/health", initialized.headers["location"])
            identity = load_web_identity(root)
            self.assertIsNotNone(identity)
            assert identity is not None
            self.assertEqual("max", identity.researcher_id)

            ready = client.get("/setup")
            self.assertIn("已初始化", ready.text)
            second = client.post(
                "/setup",
                data={"researcher_id": "other"},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(409, second.status_code)

    def test_setup_rejects_non_loopback_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp, configured=False)
            hostile = TestClient(create_app(root), base_url="http://research.example")
            response = hostile.post(
                "/setup",
                data={"researcher_id": "max"},
                headers={"Origin": "http://research.example"},
            )
            self.assertEqual(403, response.status_code)

    def test_origin_host_session_and_csrf_are_all_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp)
            client = self._client(root)
            detail = client.get("/pipeline/queue/CND-web-1")
            csrf = self._hidden(detail.text, "csrf_token")
            path = "/pipeline/queue/CND-web-1/dismiss/preview"
            for headers, token in (
                ({}, csrf),
                ({"Origin": "https://attacker.example"}, csrf),
                ({"Origin": "http://127.0.0.1"}, "wrong"),
            ):
                response = client.post(
                    path,
                    data={"reason": "noise", "csrf_token": token},
                    headers=headers,
                )
                self.assertEqual(403, response.status_code)
            hostile = TestClient(
                create_app(root),
                base_url="http://research.example",
            ).post(
                path,
                data={"reason": "noise", "csrf_token": csrf},
                headers={"Origin": "http://research.example"},
            )
            self.assertEqual(403, hostile.status_code)
            self.assertEqual(("new", 0, 0, 0), self._status_and_counts(root))

    def test_tampered_and_stale_preview_never_execute(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp)
            client = self._client(root)
            preview = self._preview(client)
            token = self._hidden(preview.text, "preview_token")
            csrf = self._hidden(preview.text, "csrf_token")
            tampered = client.post(
                "/pipeline/queue/CND-web-1/dismiss/commit",
                data={"preview_token": token + "x", "csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(403, tampered.status_code)
            self.assertEqual(("new", 0, 1, 0), self._status_and_counts(root))

        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp)
            client = self._client(root)
            preview = self._preview(client)
            token = self._hidden(preview.text, "preview_token")
            csrf = self._hidden(preview.text, "csrf_token")
            connection = sqlite3.connect(candidate_db.candidate_db_path(root))
            try:
                connection.execute(
                    "UPDATE candidates SET snippet = 'changed' "
                    "WHERE candidate_id = 'CND-web-1'"
                )
                connection.commit()
            finally:
                connection.close()
            stale = client.post(
                "/pipeline/queue/CND-web-1/dismiss/commit",
                data={"preview_token": token, "csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(409, stale.status_code)
            self.assertEqual(("new", 0, 1, 0), self._status_and_counts(root))

    def test_restart_invalidates_preview_and_reason_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._configured_root(temp)
            client = self._client(root)
            for reason in ("   ", "x" * 501):
                response = self._preview(client, reason=reason)
                self.assertEqual(422, response.status_code)
            preview = self._preview(client)
            token = self._hidden(preview.text, "preview_token")

            restarted = self._client(root)
            detail = restarted.get("/pipeline/queue/CND-web-1")
            csrf = self._hidden(detail.text, "csrf_token")
            response = restarted.post(
                "/pipeline/queue/CND-web-1/dismiss/commit",
                data={"preview_token": token, "csrf_token": csrf},
                headers={"Origin": "http://127.0.0.1"},
            )
            self.assertEqual(409, response.status_code)
            self.assertEqual(("new", 0, 1, 0), self._status_and_counts(root))


if __name__ == "__main__":
    unittest.main()
