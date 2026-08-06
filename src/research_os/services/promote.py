"""B-019 promote-to-Source transaction.

Turns a triaged Candidate into a permanent Source in the authoritative
repository, then records the Candidate↔Source link on the operational
candidate (status='promoted', promoted_source_id) with an append-only
action. The Source + captured assets commit atomically (FileTransaction);
if the candidate link then fails, the just-created files are removed so a
failure never leaves a half Source/asset (Phase 2 §13).
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from research_os.adapters.base import CaptureAdapter
from research_os.adapters.url import UrlCaptureAdapter
from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.ingestion import (
    CapturePlan,
    commit_new_source_capture,
    prepare_new_source_capture,
)
from research_os.services.validation import validate_repository

DEFAULT_USER_AGENT = "AI-Research-OS/0.3 max wu_chenlong@hotmail.com"

_SOURCE_TYPE_BY_CHANNEL = {
    "rss": "article",
    "web_page": "article",
    "arxiv": "paper",
    "github_release": "other",
    "sec": "report",
}
_SOURCE_ID_RE = re.compile(r"^(SRC-\d{8}-\d{3})")


class AlreadyPromoted(ValueError):
    """The candidate already has a permanent Source (idempotent promote)."""

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        super().__init__(f"candidate already promoted to {source_id}")


@dataclass(frozen=True)
class PromotePlan:
    candidate_id: str
    source_id: str
    source_path: Path
    title: str
    capture: CapturePlan
    action_id: str
    actor: str
    acted_at: str
    source_type: str
    source_grade: str
    publisher: str
    published_at: str
    url: str
    companies: list[str]
    reason: str


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (slug or "source")[:60].strip("-")


def _source_id_from_path(path: Path) -> str:
    match = _SOURCE_ID_RE.match(path.name)
    if not match:
        raise ValueError(f"cannot derive Source ID from {path}")
    return match.group(1)


def _load_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _candidate_row(db_path: Path, candidate_id: str) -> dict[str, Any] | None:
    if not db_path.exists():
        return None
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        return dict(zip(row.keys(), row, strict=True)) if row else None
    finally:
        connection.close()


def prepare_promote(
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
) -> PromotePlan:
    """Capture the candidate URL and build the promote plan (no writes).

    Only ``new``/``triaged`` candidates are promotable; a ``promoted``
    candidate raises :class:`AlreadyPromoted` (idempotent); dismissed,
    expired or failed candidates are refused.
    """
    if not actor or not actor.strip():
        raise ValueError("actor is required to promote")
    root = root.resolve()
    db_path = candidate_db.candidate_db_path(root)
    if not db_path.exists():
        raise ValueError(f"no candidate store at {db_path}")
    candidate = _candidate_row(db_path, candidate_id)
    if candidate is None:
        raise ValueError(f"unknown candidate {candidate_id}")
    status = str(candidate["status"])
    promoted_source_id = candidate.get("promoted_source_id")
    if status == "promoted" and promoted_source_id:
        raise AlreadyPromoted(str(promoted_source_id))
    if status in {"dismissed", "expired", "failed"}:
        raise ValueError(f"candidate {candidate_id} is {status}; cannot promote")

    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before promote")
    channel = next(
        (
            obj
            for obj in objects
            if obj.object_id == str(candidate["channel_id"])
            and obj.object_type == "source_channel"
        ),
        None,
    )
    channel_meta = dict(channel.metadata) if channel else {}

    url = candidate.get("canonical_url")
    if not url:
        raise ValueError(f"candidate {candidate_id} has no canonical URL to capture")

    entity = _load_json(candidate.get("entity_proposals_json"))
    entity_id = entity.get("entity_id")
    companies = (
        [str(entity_id)]
        if entity.get("status") == "matched" and str(entity_id or "").startswith("COM-")
        else []
    )
    resolved_type = source_type or _SOURCE_TYPE_BY_CHANNEL.get(
        str(channel_meta.get("channel_type") or ""), "article"
    )
    resolved_grade = source_grade or str(
        channel_meta.get("source_grade_proposal") or "B"
    )
    resolved_publisher = (
        publisher
        or str(candidate.get("publisher") or "")
        or str(channel_meta.get("publisher") or "")
        or "Unknown"
    )
    published_at = str(candidate.get("published_at_proposal") or "") or "unknown"
    title = str(candidate["title"])

    capture_kwargs: dict[str, Any] = {
        "user_agent": user_agent or DEFAULT_USER_AGENT,
    }
    if max_bytes is not None:
        capture_kwargs["max_bytes"] = max_bytes
    capture_adapter = adapter or UrlCaptureAdapter(url, **capture_kwargs)
    capture = prepare_new_source_capture(
        root,
        capture_adapter,
        title=title,
        slug=_slugify(title),
        created_at=date.today().isoformat(),
        source_type=resolved_type,
        publisher=resolved_publisher,
        published_at=published_at,
        source_grade=resolved_grade,
        companies=companies,
        technologies=[],
        products=[],
        tags=[],
        project_ids=[project_id],
        allow_duplicate=False,
    )
    return PromotePlan(
        candidate_id=candidate_id,
        source_id=_source_id_from_path(capture.source_path),
        source_path=capture.source_path,
        title=title,
        capture=capture,
        action_id=f"CA-{uuid.uuid4().hex[:16]}",
        actor=actor,
        acted_at=_utc_now(),
        source_type=resolved_type,
        source_grade=resolved_grade,
        publisher=resolved_publisher,
        published_at=published_at,
        url=url,
        companies=companies,
        reason="promoted from candidate triage",
    )


def commit_promote(root: Path, plan: PromotePlan) -> dict[str, Any]:
    """Commit the Source (atomic) and link the candidate to it.

    Ordering: Source + assets commit first as one FileTransaction; the
    candidate link follows. If the link write fails, the just-created files
    are removed so no orphan Source remains (Phase 2 §13).
    """
    root = root.resolve()
    created = commit_new_source_capture(root, plan.capture)
    db_path = candidate_db.candidate_db_path(root)
    try:
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("BEGIN")
            connection.execute(
                "UPDATE candidates SET status = 'promoted', "
                "promoted_source_id = ? WHERE candidate_id = ?",
                (plan.source_id, plan.candidate_id),
            )
            connection.execute(
                "INSERT INTO candidate_actions ("
                "action_id, candidate_id, action, reason, actor, acted_at, "
                "payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    plan.action_id,
                    plan.candidate_id,
                    "promote",
                    plan.reason,
                    plan.actor,
                    plan.acted_at,
                    json.dumps(
                        {
                            "source_id": plan.source_id,
                            "source_path": str(plan.source_path),
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise TransactionError(f"candidate promote link failed: {exc}") from exc
        finally:
            connection.close()
    except TransactionError:
        for path in created:
            (root / path).unlink(missing_ok=True)
        raise
    return {
        "candidate_id": plan.candidate_id,
        "source_id": plan.source_id,
        "source_path": str(plan.source_path),
        "created_paths": [str(path) for path in created],
        "action_id": plan.action_id,
    }


def render_promote_plan(plan: PromotePlan) -> str:
    capture = plan.capture
    duplicates = capture.duplicate_matches
    duplicate_text = (
        ", ".join(f"{match.source_id}:{match.reason}" for match in duplicates)
        or "none"
    )
    lines = [
        "# Candidate promote (dry-run)",
        "",
        f"Candidate: {plan.candidate_id}",
        f"Source ID: {plan.source_id}",
        f"Source path: {plan.source_path}",
        f"Title: {plan.title}",
        f"Publisher: {plan.publisher}",
        f"Published: {plan.published_at}",
        f"Source type: {plan.source_type}",
        f"Source grade: {plan.source_grade}",
        f"URL: {plan.url}",
        f"Companies: {', '.join(plan.companies) or '—'}",
        f"Content SHA256: {capture.content_sha256}",
        f"Canonical URL: {capture.canonical_url or '—'}",
        f"Published date proposal: {capture.published_date_proposal or '—'}",
        f"Duplicate matches: {duplicate_text}",
        "Assets:",
    ]
    for path in sorted(capture.assets):
        lines.append(f"- {path}")
    lines.append("")
    lines.append(capture.source_content)
    lines.append("DRY-RUN: no files changed; rerun with --apply to create the Source")
    return "\n".join(lines) + "\n"
