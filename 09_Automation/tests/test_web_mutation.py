"""Tests for the F-026 Web mutation security and transaction boundary."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from research_os.services.web_identity import (
    BrowserSessionRegistry,
    load_web_identity,
)


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


if __name__ == "__main__":
    unittest.main()
