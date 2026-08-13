"""Web mutation adapters for Candidate workflows beyond F-026 dismiss."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_os.adapters.base import CaptureAdapter
from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.mutation_audit import (
    MutationAuditEvent,
    record_mutation_event,
    record_mutation_recovery_manifest,
)
from research_os.services.mutation_gateway import MutationPreview, MutationPreviewInput
from research_os.services.promote import (
    PromotePlan,
    compensate_promote_files,
    link_promoted_candidate,
    prepare_promote,
    publish_promote_files,
)
from research_os.services.triage import restore_candidate


@dataclass(frozen=True)
class PreparedCandidatePromote:
    preview_input: MutationPreviewInput
    plan: PromotePlan


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _promote_normalized_input(plan: PromotePlan) -> dict[str, Any]:
    assets = [
        {
            "path": str(path),
            "sha256": _sha256(content),
            "byte_count": len(content),
        }
        for path, content in sorted(plan.capture.assets.items())
    ]
    return {
        "source_id": plan.source_id,
        "source_path": str(plan.source_path),
        "title": plan.title,
        "publisher": plan.publisher,
        "published_at": plan.published_at,
        "source_type": plan.source_type,
        "source_grade": plan.source_grade,
        "url": plan.url,
        "project_id": plan.project_id,
        "companies": list(plan.companies),
        "content_sha256": plan.capture.content_sha256,
        "source_record_sha256": _sha256(plan.capture.source_content.encode("utf-8")),
        "canonical_url": plan.capture.canonical_url,
        "published_date_proposal": plan.capture.published_date_proposal,
        "assets": assets,
    }


def prepare_candidate_promote(
    root: Path,
    candidate_id: str,
    *,
    actor: str,
    source_type: str | None = None,
    source_grade: str | None = None,
    publisher: str | None = None,
    project_id: str = "PRJ-001",
    user_agent: str | None = None,
    max_bytes: int | None = None,
    adapter: CaptureAdapter | None = None,
) -> PreparedCandidatePromote:
    """Capture once and freeze the bounded promotion data for signed preview."""

    plan = prepare_promote(
        root,
        candidate_id,
        actor=actor,
        source_type=source_type,
        source_grade=source_grade,
        publisher=publisher,
        project_id=project_id,
        user_agent=user_agent,
        max_bytes=max_bytes,
        adapter=adapter,
    )
    normalized = _promote_normalized_input(plan)
    return PreparedCandidatePromote(
        preview_input=MutationPreviewInput(
            operation="candidate.promote",
            actor=actor,
            target_type="candidate",
            target_id=candidate_id,
            target_version=candidate_db.candidate_version(root, candidate_id),
            normalized_input=normalized,
            summary={
                "status_before": "new",
                "status_after": "promoted",
                "source_id": plan.source_id,
                "source_path": str(plan.source_path),
                "asset_count": len(plan.capture.assets),
                "content_sha256": plan.capture.content_sha256,
            },
        ),
        plan=plan,
    )


def _promote_path_digests(plan: PromotePlan) -> dict[str, str]:
    return {
        str(plan.source_path): _sha256(plan.capture.source_content.encode("utf-8")),
        **{
            str(path): _sha256(content)
            for path, content in sorted(plan.capture.assets.items())
        },
    }


def _validate_promote_preview(
    preview: MutationPreview,
    plan: PromotePlan,
) -> None:
    if preview.operation != "candidate.promote":
        raise ValueError("invalid promote operation")
    if preview.target_type != "candidate":
        raise ValueError("invalid promote target type")
    if preview.target_id != plan.candidate_id or preview.actor != plan.actor:
        raise ValueError("promote plan does not match preview authority")
    expected: Mapping[str, Any] = _promote_normalized_input(plan)
    if preview.normalized_input != expected:
        raise ValueError("promote plan does not match signed preview")


def commit_candidate_promote(
    root: Path,
    preview: MutationPreview,
    plan: PromotePlan,
) -> dict[str, str]:
    """Coordinate frozen Source publish with Candidate action and audit."""

    _validate_promote_preview(preview, plan)
    root = root.resolve()
    path = candidate_db.candidate_db_path(root)
    connection = sqlite3.connect(path)
    created: list[Path] = []
    try:
        connection.execute("BEGIN IMMEDIATE")
        if (
            candidate_db.candidate_version_on_connection(connection, preview.target_id)
            != preview.target_version
        ):
            raise ValueError("candidate changed during promote")
        created = publish_promote_files(root, plan)
        action_id = link_promoted_candidate(connection, plan)
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
            "operation": preview.operation,
            "candidate_id": preview.target_id,
            "source_id": plan.source_id,
            "source_path": str(plan.source_path),
            "action_id": action_id,
            "audit_id": audit_id,
        }
    except ValueError:
        connection.rollback()
        if created:
            _compensate_promote_failure(root, preview, plan, created, "conflict")
        raise
    except (OSError, sqlite3.Error, TransactionError) as exc:
        connection.rollback()
        if created:
            _compensate_promote_failure(
                root,
                preview,
                plan,
                created,
                "commit_failed",
            )
        if isinstance(exc, TransactionError):
            raise
        raise TransactionError(f"candidate promote Web mutation failed: {exc}") from exc
    finally:
        connection.close()


def _compensate_promote_failure(
    root: Path,
    preview: MutationPreview,
    plan: PromotePlan,
    created: list[Path],
    reason_code: str,
) -> None:
    compensated = compensate_promote_files(root, created)
    try:
        record_mutation_recovery_manifest(
            root,
            preview,
            source_id=plan.source_id,
            created_paths=created,
            path_digests=_promote_path_digests(plan),
            status="compensated" if compensated else "manual_recovery_required",
            event_at=_utc_now(),
            reason_code=reason_code,
        )
    except (OSError, TransactionError) as exc:
        raise TransactionError(
            "promotion compensated but recovery manifest could not be recorded"
        ) from exc
    if not compensated:
        raise TransactionError("promotion compensation requires manual recovery")


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
            "operation": preview.operation,
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
