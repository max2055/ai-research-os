"""Web mutation adapters for Candidate workflows beyond F-026 dismiss."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.mutation_audit import (
    MutationAuditEvent,
    record_mutation_event,
)
from research_os.services.mutation_gateway import MutationPreview, MutationPreviewInput
from research_os.services.triage import restore_candidate


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def prepare_candidate_restore(
    root: Path,
    candidate_id: str,
    *,
    actor: str,
) -> MutationPreviewInput:
    """Validate a restore and return the exact data that must be signed."""

    dry_run = restore_candidate(root, candidate_id, actor=actor)
    reason = f"restore from {dry_run['status_before']} to review queue"
    return MutationPreviewInput(
        operation="candidate.restore",
        actor=actor,
        target_type="candidate",
        target_id=candidate_id,
        target_version=candidate_db.candidate_version(root, candidate_id),
        normalized_input={"reason": reason},
        summary={
            "status_before": dry_run["status_before"],
            "status_after": dry_run["status_after"],
        },
    )


def commit_candidate_restore(
    root: Path,
    preview: MutationPreview,
) -> dict[str, str]:
    """Atomically restore Candidate state and record action plus audit."""

    if preview.operation != "candidate.restore":
        raise ValueError("invalid restore operation")
    if preview.target_type != "candidate":
        raise ValueError("invalid restore target type")
    expected_reason = (
        f"restore from {preview.summary.get('status_before')} to review queue"
    )
    if preview.normalized_input != {"reason": expected_reason}:
        raise ValueError("invalid restore input")
    path = candidate_db.candidate_db_path(root.resolve())
    connection = sqlite3.connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        if (
            candidate_db.candidate_version_on_connection(connection, preview.target_id)
            != preview.target_version
        ):
            raise ValueError("candidate changed during restore")
        result: dict[str, Any] = restore_candidate(
            root,
            preview.target_id,
            actor=preview.actor,
            apply=True,
            connection=connection,
        )
        action_id = str(result["action_id"])
        audit_id = record_mutation_event(
            connection,
            MutationAuditEvent.from_preview(
                preview,
                event_status="committed",
                event_at=_utc_now(),
                domain_action_id=action_id,
            ),
        )
        connection.commit()
        return {
            "mutation_id": preview.mutation_id,
            "action_id": action_id,
            "audit_id": audit_id,
            "candidate_id": preview.target_id,
            "status": "new",
        }
    except (sqlite3.Error, ValueError) as exc:
        connection.rollback()
        if isinstance(exc, ValueError):
            raise
        raise TransactionError(f"candidate restore Web mutation failed: {exc}") from exc
    finally:
        connection.close()
