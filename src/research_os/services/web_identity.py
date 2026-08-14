"""Fixed local researcher identity and process-local browser sessions."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock

_CONFIG_PATH = Path("00_System/web.local.json")
_MAX_RESEARCHER_ID_LENGTH = 128
_MIN_SIGNING_SECRET_LENGTH = 32


@dataclass(frozen=True)
class WebIdentity:
    researcher_id: str
    mutation_signing_secret: bytes


def initialize_web_identity(root: Path, researcher_id: str) -> str:
    """Create the one local Web identity atomically; never replace an existing one."""
    normalized_id = " ".join(researcher_id.split())
    if not 1 <= len(normalized_id) <= _MAX_RESEARCHER_ID_LENGTH:
        raise ValueError("researcher_id must contain 1-128 characters")
    path = root.resolve() / _CONFIG_PATH
    if path.exists():
        raise FileExistsError("Web identity is already initialized")
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "researcher_id": normalized_id,
        "mutation_signing_secret": secrets.token_urlsafe(48),
    }
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            temp_path.replace(path)
        except OSError:
            if path.exists():
                raise FileExistsError("Web identity is already initialized") from None
            raise
        if os.name == "posix":
            path.chmod(0o600)
        return normalized_id
    finally:
        if temp_path.exists():
            temp_path.unlink()


def load_web_identity(root: Path) -> WebIdentity | None:
    """Load the ignored local identity, returning None for any invalid config."""
    path = root.resolve() / _CONFIG_PATH
    try:
        if os.name == "posix" and path.stat().st_mode & 0o077:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        researcher_value = value["researcher_id"]
        secret_value = value["mutation_signing_secret"]
        if not isinstance(researcher_value, str) or not isinstance(secret_value, str):
            return None
        researcher_id = researcher_value.strip()
        if not 1 <= len(researcher_id) <= _MAX_RESEARCHER_ID_LENGTH:
            return None
        if len(secret_value) < _MIN_SIGNING_SECRET_LENGTH:
            return None
        return WebIdentity(
            researcher_id=researcher_id,
            mutation_signing_secret=secret_value.encode("utf-8"),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


@dataclass(frozen=True)
class _BrowserSession:
    csrf_digest: bytes
    expires_at: datetime


class BrowserSessionRegistry:
    """Maintain opaque, session-bound CSRF tokens for one Web process."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        ttl: timedelta = timedelta(hours=1),
    ) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._ttl = ttl
        self._sessions: dict[str, _BrowserSession] = {}
        self._lock = Lock()

    def issue(self) -> tuple[str, str]:
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        session = _BrowserSession(
            csrf_digest=self._digest(csrf_token),
            expires_at=self._now() + self._ttl,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session_id, csrf_token

    def validate(self, session_id: str, csrf_token: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if self._now() >= session.expires_at:
                del self._sessions[session_id]
                return False
            return hmac.compare_digest(
                session.csrf_digest,
                self._digest(csrf_token),
            )

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    @staticmethod
    def _digest(value: str) -> bytes:
        return hashlib.sha256(value.encode("utf-8")).digest()
