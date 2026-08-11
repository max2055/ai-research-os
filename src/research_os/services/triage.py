"""B-020 Candidate dismiss/expire/restore (append-only actions).

Status transitions on the operational candidate store, each recorded as an
append-only ``candidate_actions`` row so state never changes silently
(Phase 2 §4). Audit rows are never physically deleted; the physical purge
of dismissed/expired candidate rows (ADR §3 retention) is a separate
retention sweep, not part of this service.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.validation import validate_repository

DEFAULT_RETENTION_DAYS = 30
_SYSTEM_ACTOR = "system"

_RESTORABLE = {"dismissed", "expired"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _candidate_status(db_path: Path, candidate_id: str) -> str | None:
    if not db_path.exists():
        return None
    connection = _connect(db_path)
    try:
        row = connection.execute(
            "SELECT status FROM candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        return str(row["status"]) if row else None
    finally:
        connection.close()


def _record_action(
    connection: sqlite3.Connection,
    *,
    candidate_id: str,
    action: str,
    reason: str,
    actor: str,
    payload: dict[str, Any],
) -> str:
    action_id = f"CA-{uuid.uuid4().hex[:16]}"
    connection.execute(
        "INSERT INTO candidate_actions ("
        "action_id, candidate_id, action, reason, actor, acted_at, "
        "payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            action_id,
            candidate_id,
            action,
            reason,
            actor,
            _utc_now(),
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        ),
    )
    return action_id


def dismiss_candidate(
    root: Path,
    candidate_id: str,
    *,
    actor: str,
    reason: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Mark a candidate dismissed (human decision, reason recorded)."""
    if not actor or not actor.strip():
        raise ValueError("actor is required to dismiss")
    if not reason or not reason.strip():
        raise ValueError("reason is required to dismiss")
    root = root.resolve()
    db_path = candidate_db.candidate_db_path(root)
    status = _candidate_status(db_path, candidate_id)
    if status is None:
        raise ValueError(f"unknown candidate {candidate_id}")
    if status == "promoted":
        raise ValueError(
            f"candidate {candidate_id} is promoted; dismiss its Source instead"
        )
    if status == "dismissed":
        raise ValueError(f"candidate {candidate_id} is already dismissed")

    result: dict[str, Any] = {
        "candidate_id": candidate_id,
        "status_before": status,
        "status_after": "dismissed",
        "reason": reason,
        "actor": actor,
        "applied": apply,
    }
    if not apply:
        return result
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN")
        connection.execute(
            "UPDATE candidates SET status = 'dismissed' WHERE candidate_id = ?",
            (candidate_id,),
        )
        action_id = _record_action(
            connection,
            candidate_id=candidate_id,
            action="dismiss",
            reason=reason,
            actor=actor,
            payload={"status_before": status},
        )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate dismiss failed: {exc}") from exc
    finally:
        connection.close()
    result["action_id"] = action_id
    return result


def restore_candidate(
    root: Path,
    candidate_id: str,
    *,
    actor: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Return a dismissed/expired candidate to the review queue."""
    if not actor or not actor.strip():
        raise ValueError("actor is required to restore")
    root = root.resolve()
    db_path = candidate_db.candidate_db_path(root)
    status = _candidate_status(db_path, candidate_id)
    if status is None:
        raise ValueError(f"unknown candidate {candidate_id}")
    if status not in _RESTORABLE:
        raise ValueError(
            f"candidate {candidate_id} is {status}; only "
            f"{', '.join(sorted(_RESTORABLE))} can be restored"
        )

    result: dict[str, Any] = {
        "candidate_id": candidate_id,
        "status_before": status,
        "status_after": "new",
        "actor": actor,
        "applied": apply,
    }
    if not apply:
        return result
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN")
        connection.execute(
            "UPDATE candidates SET status = 'new' WHERE candidate_id = ?",
            (candidate_id,),
        )
        action_id = _record_action(
            connection,
            candidate_id=candidate_id,
            action="restore",
            reason=f"restore from {status} to review queue",
            actor=actor,
            payload={"status_before": status},
        )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate restore failed: {exc}") from exc
    finally:
        connection.close()
    result["action_id"] = action_id
    return result


def expire_candidates(
    root: Path,
    *,
    channel_id: str | None = None,
    as_of: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Mark new/triaged candidates past channel retention as expired.

    Retention is per-channel ``retention_days`` (default 30). Automated
    sweep: actions are recorded with actor ``system``. Dry-run returns the
    candidates that would expire without writing.
    """
    root = root.resolve()
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before expire")
    db_path = candidate_db.candidate_db_path(root)
    if not db_path.exists():
        return {"as_of": as_of or _utc_now(), "expired": [], "applied": apply}
    if candidate_db.current_version(db_path) == 0:
        candidate_db.apply_migrations(db_path)

    retention_by_channel: dict[str, int] = {}
    for obj in objects:
        if obj.object_type != "source_channel":
            continue
        days = obj.metadata.get("retention_days")
        try:
            retention_by_channel[obj.object_id] = (
                max(1, int(days)) if days is not None else DEFAULT_RETENTION_DAYS
            )
        except (TypeError, ValueError):
            retention_by_channel[obj.object_id] = DEFAULT_RETENTION_DAYS

    as_of_value = as_of or _utc_now()
    try:
        as_of_dt = _parse_iso(as_of_value)
    except ValueError as exc:
        raise ValueError(f"as_of must be an ISO date-time: {as_of_value}") from exc

    where = ["status IN ('new', 'triaged')"]
    params: list[object] = []
    if channel_id is not None:
        where.append("channel_id = ?")
        params.append(channel_id)

    connection = _connect(db_path)
    expired: list[dict[str, Any]] = []
    try:
        rows = connection.execute(
            f"SELECT candidate_id, channel_id, discovered_at, status "
            f"FROM candidates WHERE {' AND '.join(where)}",
            params,
        ).fetchall()
        for row in rows:
            days = retention_by_channel.get(
                str(row["channel_id"]), DEFAULT_RETENTION_DAYS
            )
            cutoff = as_of_dt - timedelta(days=days)
            try:
                discovered = _parse_iso(str(row["discovered_at"]))
            except ValueError:
                continue
            if discovered >= cutoff:
                continue
            expired.append(
                {
                    "candidate_id": str(row["candidate_id"]),
                    "channel_id": str(row["channel_id"]),
                    "discovered_at": str(row["discovered_at"]),
                    "status_before": str(row["status"]),
                    "retention_days": days,
                }
            )
        if apply and expired:
            connection.execute("BEGIN")
            for item in expired:
                connection.execute(
                    "UPDATE candidates SET status = 'expired' WHERE candidate_id = ?",
                    (item["candidate_id"],),
                )
                _record_action(
                    connection,
                    candidate_id=item["candidate_id"],
                    action="expire",
                    reason=(f"past retention ({item['retention_days']} days)"),
                    actor=_SYSTEM_ACTOR,
                    payload={
                        "discovered_at": item["discovered_at"],
                        "retention_days": item["retention_days"],
                    },
                )
            connection.commit()
        return {
            "as_of": as_of_value,
            "expired": expired,
            "applied": apply,
        }
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate expire failed: {exc}") from exc
    finally:
        connection.close()


def purge_candidates(
    root: Path,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Delete dismissed/expired candidate rows, keeping audit actions (B-021).

    Implements ADR §3 retention: terminal-status candidates are cleaned up
    while ``candidate_actions`` rows are preserved. Requires schema v2, where
    the candidate_actions FK is dropped so actions outlive their candidate.
    """
    root = root.resolve()
    db_path = candidate_db.candidate_db_path(root)
    if not db_path.exists():
        return {"purged": [], "applied": apply}
    candidate_db.apply_migrations(db_path)  # ensure v2 (no FK on actions)
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            "SELECT candidate_id, status FROM candidates "
            "WHERE status IN ('dismissed', 'expired')"
        ).fetchall()
        purged = [
            {
                "candidate_id": str(row["candidate_id"]),
                "status": str(row["status"]),
            }
            for row in rows
        ]
        if apply and purged:
            connection.execute("BEGIN")
            connection.execute(
                "DELETE FROM candidates WHERE status IN ('dismissed', 'expired')"
            )
            connection.commit()
        return {"purged": purged, "applied": apply}
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"candidate purge failed: {exc}") from exc
    finally:
        connection.close()


def render_triage_result(result: dict[str, Any]) -> str:
    mode = "APPLIED" if result.get("applied") else "DRY-RUN"
    if "purged" in result:
        purged = result["purged"]
        lines = [
            f"# Purge candidates ({mode})",
            "",
            f"Terminal candidates: {len(purged)}",
        ]
        if purged:
            lines.append("")
            lines.append("| Candidate | Status |")
            lines.append("|---|---|")
            for item in purged:
                lines.append(f"| {item['candidate_id']} | {item['status']} |")
        if not result.get("applied"):
            lines.append("")
            lines.append("DRY-RUN: no changes written; rerun with --apply")
        return "\n".join(lines) + "\n"
    if "expired" in result:
        expired = result["expired"]
        lines = [
            f"# Expire candidates ({mode})",
            "",
            f"As of: {result['as_of']}",
            f"Past retention: {len(expired)} candidate(s)",
        ]
        if expired:
            lines.append("")
            lines.append("| Candidate | Channel | Discovered | Retention | Status |")
            lines.append("|---|---|---|---|---|")
            for item in expired:
                lines.append(
                    f"| {item['candidate_id']} | {item['channel_id']} | "
                    f"{item['discovered_at']} | {item['retention_days']}d | "
                    f"{item['status_before']} |"
                )
        if not result.get("applied"):
            lines.append("")
            lines.append("DRY-RUN: no changes written; rerun with --apply")
        return "\n".join(lines) + "\n"

    lines = [
        f"# Candidate {result['candidate_id']} "
        f"({result['status_before']} -> {result['status_after']}) {mode}",
        "",
        f"Actor: {result['actor']}",
    ]
    if result.get("reason"):
        lines.append(f"Reason: {result['reason']}")
    if not result.get("applied"):
        lines.append("")
        lines.append("DRY-RUN: no changes written; rerun with --apply")
    return "\n".join(lines) + "\n"
