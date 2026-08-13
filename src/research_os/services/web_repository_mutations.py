"""Frozen, audited repository write sets for local Web mutations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_os.repositories.transaction import FileTransaction, TransactionError
from research_os.services import candidate_db
from research_os.services.mutation_audit import (
    MutationAuditEvent,
    record_mutation_event,
    record_repository_mutation_recovery_manifest,
)
from research_os.services.mutation_gateway import MutationPreview, MutationPreviewInput


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class RepositoryWrite:
    path: Path
    mode: str
    content: bytes
    before_content: bytes | None

    @property
    def before_sha256(self) -> str | None:
        return None if self.before_content is None else _sha256(self.before_content)

    @property
    def after_sha256(self) -> str:
        return _sha256(self.content)

    def manifest(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "mode": self.mode,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "byte_count": len(self.content),
        }


@dataclass(frozen=True)
class RepositoryMutationPlan:
    operation: str
    actor: str
    target_type: str
    target_id: str
    writes: tuple[RepositoryWrite, ...]
    normalized_input: Mapping[str, Any]


@dataclass(frozen=True)
class PreparedRepositoryMutation:
    preview_input: MutationPreviewInput
    plan: RepositoryMutationPlan


def _relative_path(root: Path, path: Path) -> tuple[Path, Path]:
    target = path if path.is_absolute() else root / path
    target = target.resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"path escapes repository root: {path}")
    return target.relative_to(root), target


def _version_payload(
    root: Path,
    writes: tuple[RepositoryWrite, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for write in writes:
        target = root / write.path
        if target.is_file():
            content = target.read_bytes()
            rows.append(
                {
                    "path": str(write.path),
                    "state": "file",
                    "sha256": _sha256(content),
                    "byte_count": len(content),
                }
            )
        elif target.exists():
            rows.append({"path": str(write.path), "state": "non_file"})
        else:
            rows.append({"path": str(write.path), "state": "absent"})
    return rows


def repository_target_version(root: Path, plan: RepositoryMutationPlan) -> str:
    payload = json.dumps(
        _version_payload(root.resolve(), plan.writes),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(payload)


def prepare_repository_mutation(
    root: Path,
    *,
    operation: str,
    actor: str,
    target_type: str,
    target_id: str,
    writes: Mapping[Path, bytes],
    normalized_input: Mapping[str, Any] | None = None,
    summary: Mapping[str, Any] | None = None,
) -> PreparedRepositoryMutation:
    root = root.resolve()
    if not writes:
        raise ValueError("repository mutation requires at least one write")
    if not all(value.strip() for value in (operation, actor, target_type, target_id)):
        raise ValueError("repository mutation authority fields are required")

    frozen: list[RepositoryWrite] = []
    seen: set[Path] = set()
    for supplied_path, content in writes.items():
        relative, target = _relative_path(root, supplied_path)
        if relative in seen:
            raise ValueError(f"path staged more than once: {relative}")
        seen.add(relative)
        if target.exists() and not target.is_file():
            raise ValueError(f"repository mutation target is not a file: {relative}")
        before = target.read_bytes() if target.is_file() else None
        frozen.append(
            RepositoryWrite(
                path=relative,
                mode="replace" if before is not None else "create",
                content=bytes(content),
                before_content=before,
            )
        )
    ordered = tuple(sorted(frozen, key=lambda item: str(item.path)))
    signed_input = dict(normalized_input or {})
    signed_input["write_manifest"] = [write.manifest() for write in ordered]
    plan = RepositoryMutationPlan(
        operation=operation,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        writes=ordered,
        normalized_input=signed_input,
    )
    preview_input = MutationPreviewInput(
        operation=operation,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        target_version=repository_target_version(root, plan),
        normalized_input=signed_input,
        summary=dict(summary or {}),
    )
    return PreparedRepositoryMutation(preview_input=preview_input, plan=plan)


def _validate_preview(preview: MutationPreview, plan: RepositoryMutationPlan) -> None:
    if (
        preview.operation != plan.operation
        or preview.actor != plan.actor
        or preview.target_type != plan.target_type
        or preview.target_id != plan.target_id
    ):
        raise ValueError("repository plan does not match preview authority")
    if preview.normalized_input != plan.normalized_input:
        raise ValueError("repository plan does not match signed preview")
    if preview.target_version != _prepared_version(plan):
        raise ValueError("repository plan does not match preview version")


def _publish(root: Path, plan: RepositoryMutationPlan) -> list[Path]:
    transaction = FileTransaction(root)
    for write in plan.writes:
        if write.mode == "create":
            transaction.stage_create_bytes(write.path, write.content)
        else:
            transaction.stage_replace_bytes(write.path, write.content)
    return [path.relative_to(root) for path in transaction.commit()]


def _compensate(root: Path, plan: RepositoryMutationPlan) -> bool:
    replacements = [write for write in plan.writes if write.before_content is not None]
    if replacements:
        transaction = FileTransaction(root)
        for write in replacements:
            transaction.stage_replace_bytes(write.path, write.before_content or b"")
        transaction.commit()
    for write in reversed(plan.writes):
        if write.before_content is None:
            (root / write.path).unlink(missing_ok=True)
    return repository_target_version(root, plan) == _prepared_version(plan)


def _prepared_version(plan: RepositoryMutationPlan) -> str:
    rows: list[dict[str, Any]] = []
    for write in plan.writes:
        if write.before_content is None:
            rows.append({"path": str(write.path), "state": "absent"})
        else:
            rows.append(
                {
                    "path": str(write.path),
                    "state": "file",
                    "sha256": write.before_sha256,
                    "byte_count": len(write.before_content),
                }
            )
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(payload)


def commit_repository_mutation(
    root: Path,
    preview: MutationPreview,
    plan: RepositoryMutationPlan,
) -> dict[str, str]:
    _validate_preview(preview, plan)
    root = root.resolve()
    if repository_target_version(root, plan) != preview.target_version:
        raise ValueError("repository target changed after preview")

    created_or_replaced: list[Path] = []
    connection: sqlite3.Connection | None = None
    try:
        created_or_replaced = _publish(root, plan)
        candidate_db.apply_migrations(candidate_db.candidate_db_path(root))
        connection = sqlite3.connect(candidate_db.candidate_db_path(root))
        connection.execute("BEGIN IMMEDIATE")
        audit_id = record_mutation_event(
            connection,
            MutationAuditEvent.from_preview(
                preview,
                event_status="committed",
                event_at=_utc_now(),
            ),
        )
        connection.commit()
        return {
            "mutation_id": preview.mutation_id,
            "operation": preview.operation,
            "target_id": preview.target_id,
            "audit_id": audit_id,
            "write_count": str(len(created_or_replaced)),
        }
    except (OSError, sqlite3.Error, TransactionError) as exc:
        if connection is not None:
            connection.rollback()
        if created_or_replaced:
            try:
                compensated = _compensate(root, plan)
            except (OSError, TransactionError):
                compensated = False
            try:
                record_repository_mutation_recovery_manifest(
                    root,
                    preview,
                    writes=[write.manifest() for write in plan.writes],
                    status="compensated" if compensated else "manual_recovery_required",
                    event_at=_utc_now(),
                    reason_code="commit_failed",
                )
            except (OSError, TransactionError) as manifest_error:
                raise TransactionError(
                    "repository mutation failed and recovery manifest "
                    "could not be recorded"
                ) from manifest_error
            if not compensated:
                raise TransactionError(
                    "repository mutation compensation requires manual recovery"
                ) from exc
        raise TransactionError(f"repository Web mutation failed: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
