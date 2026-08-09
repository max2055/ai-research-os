"""B-022 Daily Brief generator.

A pending operational report that partitions *unreviewed candidates* (each
row explicitly marked ``unreviewed candidate``, never mixed with reviewed
facts) from reviewed Sources/Events, and surfaces operational signals
(fetch failures, stale channels, coverage gaps) plus a suggested
processing order. Deterministic; render-only unless a writer is called.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.repositories.transaction import (
    FileTransaction,
    TransactionError,
)
from research_os.services import candidate_db
from research_os.services.discovery import due_channels_from_objects
from research_os.services.validation import validate_repository

BRIEFS_DIR = Path("05_Research") / "Operations" / "Briefs"
PRIORITY_CUTOFF = 0.5
TOP_CANDIDATES = 5
_UNREVIEWED_NOTE = "unreviewed candidate（未审阅候选，非已审阅事实）"
_NEGATIVE_WORDS = (
    "recall",
    "breach",
    "delay",
    "postpone",
    "cut",
    "decline",
    "loss",
    "halt",
    "suspend",
    "ban",
    "sanction",
    "shortage",
    "risk",
    "investigation",
    "lawsuit",
    "warning",
    "redundancy",
    "layoff",
)
_PAPER_CHANNEL_TYPES = {"arxiv"}


def brief_path(root: Path, date_str: str) -> Path:
    return root / BRIEFS_DIR / f"Daily_Brief_{date_str}.md"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _candidate_rows(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT candidate_id, channel_id, title, canonical_url, "
            "discovered_at, priority_score, status, entity_proposals_json, "
            "sector_proposals_json FROM candidates "
            "WHERE status = 'new' "
            "ORDER BY priority_score IS NULL, priority_score DESC, "
            "discovered_at DESC, candidate_id ASC"
        ).fetchall()
    finally:
        connection.close()
    result: list[dict[str, Any]] = []
    for row in rows:
        entity = _load_json(row["entity_proposals_json"])
        sector = _load_json(row["sector_proposals_json"])
        result.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "channel_id": str(row["channel_id"]),
                "title": str(row["title"]),
                "url": row["canonical_url"],
                "discovered_at": str(row["discovered_at"]),
                "priority_score": row["priority_score"],
                "status": str(row["status"]),
                "entity_status": entity.get("status", "unknown"),
                "entity_id": entity.get("entity_id"),
                "sector_ids": sector.get("sector_ids", []),
            }
        )
    return result


def _failed_runs(db_path: Path, date_str: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT run_id, channel_id, started_at, candidate_count "
            "FROM discovery_runs WHERE status = 'failed' "
            "AND started_at LIKE ? ORDER BY started_at DESC",
            (f"{date_str}%",),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def _channels_by_id(objects: list[Any]) -> dict[str, dict[str, Any]]:
    return {
        obj.object_id: dict(obj.metadata)
        for obj in objects
        if obj.object_type == "source_channel"
    }


def _tier_by_entity(objects: list[Any]) -> dict[str, str]:
    return {
        obj.object_id: str(obj.metadata.get("coverage_tier") or "")
        for obj in objects
        if obj.object_type == "company"
    }


def daily_brief(
    root: Path,
    date_str: str,
    *,
    db_path: Path | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Collect every Daily Brief section for one date (no writes)."""
    objects, _ = validate_repository(root)
    db_path = db_path or candidate_db.candidate_db_path(root)
    return daily_brief_from_objects(
        objects,
        date_str,
        db_path=db_path,
        as_of=as_of,
    )


def daily_brief_from_objects(
    objects: list[ResearchObject],
    date_str: str,
    *,
    db_path: Path,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Compose a Daily Brief from one validated repository snapshot."""
    channels = _channels_by_id(objects)
    tier_by_entity = _tier_by_entity(objects)

    candidates = _candidate_rows(db_path)
    new_today = [
        candidate
        for candidate in candidates
        if candidate["discovered_at"].startswith(date_str)
    ]
    high_priority = [
        candidate
        for candidate in new_today
        if candidate["priority_score"] is not None
        and candidate["priority_score"] >= PRIORITY_CUTOFF
    ]
    core_impact = [
        candidate
        for candidate in new_today
        if candidate["entity_id"]
        and tier_by_entity.get(candidate["entity_id"]) == "core"
    ]
    title_lower = [candidate["title"].lower() for candidate in new_today]
    conflicts = [
        candidate
        for candidate, lower in zip(new_today, title_lower, strict=True)
        if candidate["entity_status"] == "ambiguous"
        or any(word in lower for word in _NEGATIVE_WORDS)
    ]
    papers = [
        candidate
        for candidate in new_today
        if channels.get(candidate["channel_id"], {}).get("channel_type")
        in _PAPER_CHANNEL_TYPES
    ]

    sources_today = sorted(
        (
            {
                "object_id": obj.object_id,
                "title": str(obj.metadata.get("title") or ""),
                "review_status": str(obj.metadata.get("review_status") or ""),
            }
            for obj in objects
            if obj.object_type == "source"
            and str(obj.metadata.get("created_at") or "") == date_str
        ),
        key=lambda item: item["object_id"],
    )
    events_today = sorted(
        (
            {
                "object_id": obj.object_id,
                "title": str(obj.metadata.get("title") or ""),
            }
            for obj in objects
            if obj.object_type == "event"
            and str(obj.metadata.get("created_at") or "") == date_str
            and obj.metadata.get("review_status") == "reviewed"
        ),
        key=lambda item: item["object_id"],
    )

    failed_runs = _failed_runs(db_path, date_str)
    end_of_day = f"{date_str}T23:59:59Z"
    due = due_channels_from_objects(
        objects,
        as_of=as_of or end_of_day,
        db_path=db_path,
    )
    stale = sorted(
        item["channel_id"] for item in due if item["last_run"]
    )
    never_run = sorted(
        item["channel_id"] for item in due if not item["last_run"]
    )

    return {
        "date": date_str,
        "generated_at": _utc_now(),
        "top": candidates[:TOP_CANDIDATES],
        "high_priority": high_priority,
        "core_impact": core_impact,
        "conflicts": conflicts,
        "papers": papers,
        "sources_today": sources_today,
        "events_today": events_today,
        "failed_runs": failed_runs,
        "stale": stale,
        "never_run": never_run,
    }


def _priority_text(candidate: dict[str, Any]) -> str:
    score = candidate.get("priority_score")
    return f"{score:.3f}" if score is not None else "—"


def _candidate_section(
    lines: list[str],
    heading: str,
    candidates: list[dict[str, Any]],
) -> None:
    lines.append("")
    lines.append(f"## {heading}")
    lines.append("")
    lines.append(f"以下均为 {_UNREVIEWED_NOTE}：")
    if not candidates:
        lines.append("")
        lines.append("(none)")
        return
    lines.append("")
    lines.append("| Priority | Candidate | Entity | Sector | URL |")
    lines.append("|---|---|---|---|---|")
    for candidate in candidates:
        entity = candidate["entity_id"] or candidate["entity_status"]
        sector_count = len(candidate["sector_ids"])
        lines.append(
            f"| {_priority_text(candidate)} | {candidate['title']} "
            f"| {entity} | {sector_count} | {candidate['url'] or '—'} |"
        )


def render_daily_brief(data: dict[str, Any]) -> str:
    lines = [
        f"# Daily Brief — {data['date']}",
        "",
        f"Generated: {data['generated_at']}（operational report，非 reviewed Fact）",
    ]

    _candidate_section(lines, "1. 今日建议处理顺序（Top 5）", data["top"])
    _candidate_section(lines, "2. 新增高优先级 Candidate", data["high_priority"])

    lines.append("")
    lines.append("## 3. 已提升正式 Source（reviewed）")
    lines.append("")
    if not data["sources_today"]:
        lines.append("(none)")
    else:
        for source in data["sources_today"]:
            lines.append(
                f"- {source['object_id']} {source['title']} "
                f"({source['review_status']})"
            )

    lines.append("")
    lines.append("## 4. 新 reviewed Event")
    lines.append("")
    if not data["events_today"]:
        lines.append("(none)")
    else:
        for event in data["events_today"]:
            lines.append(f"- {event['object_id']} {event['title']}")

    _candidate_section(lines, "5. 可能影响 Core Company 的候选", data["core_impact"])
    _candidate_section(lines, "6. 反面或冲突信号", data["conflicts"])
    _candidate_section(lines, "7. 论文与技术信号", data["papers"])

    lines.append("")
    lines.append("## 8. 抓取失败 / stale Channel / coverage gap（operational）")
    lines.append("")
    lines.append(f"- Failed discovery runs: {len(data['failed_runs'])}")
    for run in data["failed_runs"]:
        lines.append(
            f"  - {run['run_id']} {run['channel_id']} {run['started_at']}"
        )
    lines.append(f"- Stale channels (overdue): {', '.join(data['stale']) or '—'}")
    lines.append(f"- Coverage gap (never run): {', '.join(data['never_run']) or '—'}")
    return "\n".join(lines) + "\n"


def write_daily_brief(root: Path, date_str: str, content: str) -> Path:
    """Write the brief for a date; refuses to overwrite an existing one."""
    relative = BRIEFS_DIR / f"Daily_Brief_{date_str}.md"
    transaction = FileTransaction(root)
    transaction.stage_create(relative, content)
    try:
        return transaction.commit()[0]
    except TransactionError as exc:
        if "create target already exists" in str(exc):
            raise FileExistsError(
                f"refusing to overwrite existing file: {relative}"
            ) from exc
        raise
