"""Redacted operational audit records for Web mutations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


class MutationPreviewLike(Protocol):
    @property
    def mutation_id(self) -> str: ...

    @property
    def operation(self) -> str: ...

    @property
    def actor(self) -> str: ...

    @property
    def target_type(self) -> str: ...

    @property
    def target_id(self) -> str: ...

    @property
    def target_version(self) -> str: ...

    @property
    def normalized_input(self) -> Mapping[str, Any]: ...

    @property
    def issued_at_iso(self) -> str: ...

    @property
    def expires_at_iso(self) -> str: ...


MUTATION_AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS mutation_audit (
    event_id TEXT PRIMARY KEY,
    mutation_id TEXT NOT NULL,
    event_status TEXT NOT NULL CHECK (
        event_status IN ('previewed', 'committed', 'rejected', 'expired')
    ),
    operation TEXT NOT NULL,
    actor TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_version TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    event_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    reason_code TEXT,
    domain_action_id TEXT
);
CREATE INDEX IF NOT EXISTS mutation_audit_mutation_idx
    ON mutation_audit(mutation_id, event_at);
CREATE INDEX IF NOT EXISTS mutation_audit_target_idx
    ON mutation_audit(target_type, target_id, event_at);
"""


@dataclass(frozen=True)
class MutationAuditEvent:
    mutation_id: str
    event_status: str
    operation: str
    actor: str
    target_type: str
    target_id: str
    target_version: str
    input_digest: str
    issued_at: str
    event_at: str
    expires_at: str
    reason_code: str | None = None
    domain_action_id: str | None = None

    @classmethod
    def from_preview(
        cls,
        preview: MutationPreviewLike,
        *,
        event_status: str,
        event_at: str,
        reason_code: str | None = None,
        domain_action_id: str | None = None,
    ) -> MutationAuditEvent:
        return cls(
            mutation_id=preview.mutation_id,
            event_status=event_status,
            operation=preview.operation,
            actor=preview.actor,
            target_type=preview.target_type,
            target_id=preview.target_id,
            target_version=preview.target_version,
            input_digest=normalized_input_digest(preview.normalized_input),
            issued_at=preview.issued_at_iso,
            event_at=event_at,
            expires_at=preview.expires_at_iso,
            reason_code=reason_code,
            domain_action_id=domain_action_id,
        )


def normalized_input_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def record_mutation_event(
    connection: sqlite3.Connection,
    event: MutationAuditEvent,
) -> str:
    event_id = f"MA-{uuid.uuid4().hex[:16]}"
    connection.execute(
        "INSERT INTO mutation_audit (event_id, mutation_id, event_status, "
        "operation, actor, target_type, target_id, target_version, input_digest, "
        "issued_at, event_at, expires_at, reason_code, domain_action_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event_id,
            event.mutation_id,
            event.event_status,
            event.operation,
            event.actor,
            event.target_type,
            event.target_id,
            event.target_version,
            event.input_digest,
            event.issued_at,
            event.event_at,
            event.expires_at,
            event.reason_code,
            event.domain_action_id,
        ),
    )
    return event_id
