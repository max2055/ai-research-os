"""Signed preview and one-use nonce lifecycle for Web mutations."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from research_os.repositories.transaction import TransactionError

_DEFAULT_TTL = timedelta(minutes=10)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class MutationPreviewInput:
    operation: str
    actor: str
    target_type: str
    target_id: str
    target_version: str
    normalized_input: Mapping[str, Any]
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class MutationPreview:
    mutation_id: str
    operation: str
    actor: str
    target_type: str
    target_id: str
    target_version: str
    normalized_input: Mapping[str, Any]
    summary: Mapping[str, Any]
    issued_at: datetime
    expires_at: datetime
    nonce: str

    @property
    def issued_at_iso(self) -> str:
        return _iso(self.issued_at)

    @property
    def expires_at_iso(self) -> str:
        return _iso(self.expires_at)

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            {
                "actor": self.actor,
                "expires_at": self.expires_at_iso,
                "issued_at": self.issued_at_iso,
                "mutation_id": self.mutation_id,
                "nonce": self.nonce,
                "normalized_input": self.normalized_input,
                "operation": self.operation,
                "summary": self.summary,
                "target_id": self.target_id,
                "target_type": self.target_type,
                "target_version": self.target_version,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


@dataclass(frozen=True)
class PreviewGrant:
    preview: MutationPreview
    token: str


@dataclass
class _NonceRecord:
    preview: MutationPreview
    signature: str
    state: str = "issued"


class MutationError(Exception):
    def __init__(
        self,
        reason_code: str,
        preview: MutationPreview | None = None,
    ) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.preview = preview


class MutationForbidden(MutationError):
    """A signed preview failed an authorization or integrity check."""


class MutationConflict(MutationError):
    """A valid preview can no longer be committed."""


class MutationGateway:
    def __init__(
        self,
        signing_secret: bytes,
        *,
        now: Callable[[], datetime] | None = None,
        ttl: timedelta = _DEFAULT_TTL,
    ) -> None:
        self._secret = signing_secret
        self._now = now or (lambda: datetime.now(UTC))
        self._ttl = ttl
        self._nonces: dict[str, _NonceRecord] = {}
        self._lock = Lock()

    def issue(self, value: MutationPreviewInput) -> PreviewGrant:
        now = self._now()
        preview = MutationPreview(
            mutation_id=f"MUT-{uuid.uuid4().hex[:16]}",
            operation=value.operation,
            actor=value.actor,
            target_type=value.target_type,
            target_id=value.target_id,
            target_version=value.target_version,
            normalized_input=dict(value.normalized_input),
            summary=dict(value.summary),
            issued_at=now,
            expires_at=now + self._ttl,
            nonce=secrets.token_urlsafe(24),
        )
        signature = self._signature(preview)
        with self._lock:
            self._nonces[preview.nonce] = _NonceRecord(preview, signature)
        return PreviewGrant(preview, f"{preview.nonce}.{signature}")

    def commit(
        self,
        token: str,
        *,
        actor: str,
        operation: str,
        current_target_version: Callable[[str], str],
        execute: Callable[[MutationPreview], dict[str, str]],
    ) -> dict[str, str]:
        nonce, signature = self._parse_token(token)
        with self._lock:
            record = self._nonces.get(nonce)
            if record is None:
                raise MutationConflict("unknown_preview")
            preview = record.preview
            if not hmac.compare_digest(signature, record.signature):
                record.state = "consumed"
                raise MutationForbidden("invalid_token", preview)
            if record.state == "committing":
                raise MutationConflict("committing", preview)
            if record.state == "consumed":
                raise MutationConflict("replayed", preview)
            if self._now() >= preview.expires_at:
                record.state = "consumed"
                raise MutationConflict("expired", preview)
            if actor != preview.actor:
                record.state = "consumed"
                raise MutationForbidden("actor_mismatch", preview)
            if operation != preview.operation:
                record.state = "consumed"
                raise MutationForbidden("operation_mismatch", preview)
            if current_target_version(preview.target_id) != preview.target_version:
                record.state = "consumed"
                raise MutationConflict("target_changed", preview)
            record.state = "committing"

        try:
            result = execute(preview)
        except TransactionError:
            with self._lock:
                unchanged = False
                with suppress(OSError, ValueError):
                    unchanged = (
                        current_target_version(preview.target_id)
                        == preview.target_version
                    )
                retryable = self._now() < preview.expires_at and unchanged
                record.state = "issued" if retryable else "consumed"
            raise
        except Exception:
            with self._lock:
                record.state = "consumed"
            raise
        else:
            with self._lock:
                record.state = "consumed"
            return result

    def nonce_state(self, nonce: str) -> str | None:
        with self._lock:
            record = self._nonces.get(nonce)
            return record.state if record is not None else None

    def _signature(self, preview: MutationPreview) -> str:
        return hmac.new(
            self._secret,
            preview.canonical_bytes(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _parse_token(token: str) -> tuple[str, str]:
        try:
            nonce, signature = token.split(".", 1)
        except ValueError as exc:
            raise MutationForbidden("invalid_token") from exc
        if not nonce or len(signature) != 64:
            raise MutationForbidden("invalid_token")
        return nonce, signature
