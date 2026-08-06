"""B-018 Candidate Queue.

Reviewable list/detail over the Candidate operational store, plus an
enrichment backfill that computes B-015 entity, B-016 sector and B-017
priority proposals for candidates that lack them. Queue output is a
proposal only (Phase 2 §5.3): sorting and filters never write authoritative
Source/Event facts, and there is no authoritative-write bypass here.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.entity_resolution import EntityIndex, resolve
from research_os.services.scoring import score_candidate
from research_os.services.sector_classification import SectorIndex, classify
from research_os.services.validation import validate_repository

_ORDER_BY_PRIORITY = (
    "ORDER BY priority_score IS NULL, priority_score DESC, "
    "discovered_at DESC, candidate_id ASC"
)


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _load_json(value: Any) -> Any:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, (dict, list)) else {}
    except (TypeError, ValueError):
        return {}


def _cluster_stats(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, Any]]:
    """Cluster id -> {size, representative_id} (earliest created candidate)."""
    members: dict[str, list[tuple[str, str]]] = {}
    for row in connection.execute(
        "SELECT duplicate_cluster_id, candidate_id, created_at "
        "FROM candidates WHERE duplicate_cluster_id IS NOT NULL"
    ):
        members.setdefault(str(row["duplicate_cluster_id"]), []).append(
            (str(row["created_at"]), str(row["candidate_id"]))
        )
    stats: dict[str, dict[str, Any]] = {}
    for cluster_id, items in members.items():
        items.sort()
        stats[cluster_id] = {
            "size": len(items),
            "representative_id": items[0][1],
        }
    return stats


def enrich_candidates(
    root: Path,
    db_path: Path | None = None,
    *,
    apply: bool = False,
) -> list[dict[str, Any]]:
    """Backfill entity/sector/priority proposals for unscored new candidates.

    Deterministic and idempotent: only candidates with ``status='new'`` and
    ``priority_score IS NULL`` are touched, so re-runs converge. Without
    ``apply`` the computed proposals are returned (dry-run); with ``apply``
    they are written to the operational store. Proposals never change
    reviewed facts.
    """
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before enrichment")
    db_path = db_path or candidate_db.candidate_db_path(root)
    if not db_path.exists():
        return []
    if candidate_db.current_version(db_path) == 0:
        candidate_db.apply_migrations(db_path)

    entity_index = EntityIndex.from_objects(
        [obj for obj in objects if obj.object_type == "company"]
    )
    sector_index = SectorIndex.from_objects(
        [obj for obj in objects if obj.object_type == "sector"]
    )
    channels = {
        obj.object_id: obj.metadata
        for obj in objects
        if obj.object_type == "source_channel"
    }

    connection = _connect(db_path)
    try:
        rows = connection.execute(
            "SELECT candidate_id, channel_id, title, publisher, "
            "duplicate_cluster_id, created_at FROM candidates "
            "WHERE status = 'new' AND priority_score IS NULL "
            "ORDER BY created_at ASC, candidate_id ASC"
        ).fetchall()
        clusters = _cluster_stats(connection)
        enriched: list[dict[str, Any]] = []
        for row in rows:
            title = str(row["title"])
            publisher = str(row["publisher"] or "")
            entity = resolve(entity_index, title=title, publisher=publisher)
            sector = classify(sector_index, title=title, publisher=publisher)
            cluster_id = row["duplicate_cluster_id"]
            cluster = clusters.get(str(cluster_id)) if cluster_id else None
            cluster_size = int(cluster["size"]) if cluster else 1
            is_representative = bool(
                cluster and str(row["candidate_id"]) == cluster["representative_id"]
            )
            channel_meta = channels.get(str(row["channel_id"])) or {}
            score = score_candidate(
                title=title,
                source_grade=str(
                    channel_meta.get("source_grade_proposal") or "B"
                ),
                entity_status=str(entity["status"]),
                sector_count=len(sector["sector_ids"]),
                is_duplicate_representative=is_representative,
                cluster_size=cluster_size,
                channel_type=str(channel_meta.get("channel_type") or "web_page"),
            )
            if apply:
                connection.execute(
                    "UPDATE candidates SET entity_proposals_json = ?, "
                    "sector_proposals_json = ?, reason_codes_json = ?, "
                    "priority_score = ?, model_version = ? "
                    "WHERE candidate_id = ?",
                    (
                        json.dumps(entity, ensure_ascii=False, sort_keys=True),
                        json.dumps(sector, ensure_ascii=False, sort_keys=True),
                        json.dumps(score["reason_codes"], ensure_ascii=False),
                        score["priority_score"],
                        score["model"],
                        str(row["candidate_id"]),
                    ),
                )
            enriched.append(
                {
                    "candidate_id": str(row["candidate_id"]),
                    "title": title,
                    "entity_status": entity["status"],
                    "entity_id": entity.get("entity_id"),
                    "sector_count": len(sector["sector_ids"]),
                    "priority_score": score["priority_score"],
                }
            )
        if apply:
            connection.commit()
        return enriched
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(
            f"candidate enrichment failed: {exc}"
        ) from exc
    finally:
        connection.close()


def queue_rows(
    root: Path,
    db_path: Path | None = None,
    *,
    status: str | None = "new",
    channel_id: str | None = None,
    entity_id: str | None = None,
    tier: str | None = None,
    min_priority: float | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Read the review queue, highest priority first.

    Filters are proposals-level: entity/tier resolve through the stored
    entity proposal and the Universe coverage tier. Rows carry the resolved
    entity/sector proposal so a human can triage without a second lookup.
    """
    db_path = db_path or candidate_db.candidate_db_path(root)
    if not db_path.exists():
        return []
    where: list[str] = []
    params: list[object] = []
    if status is not None:
        where.append("status = ?")
        params.append(status)
    if channel_id is not None:
        where.append("channel_id = ?")
        params.append(channel_id)
    if min_priority is not None:
        where.append("priority_score >= ?")
        params.append(min_priority)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    connection = _connect(db_path)
    try:
        rows = connection.execute(
            "SELECT candidate_id, channel_id, title, canonical_url, "
            "published_at_proposal, discovered_at, status, "
            "duplicate_cluster_id, priority_score, entity_proposals_json, "
            f"sector_proposals_json FROM candidates {clause} "
            f"{_ORDER_BY_PRIORITY} LIMIT ?",
            (*params, limit),
        ).fetchall()
    finally:
        connection.close()

    objects, _ = validate_repository(root)
    tier_by_entity = {
        obj.object_id: str(obj.metadata.get("coverage_tier") or "")
        for obj in objects
        if obj.object_type == "company"
    }
    queue: list[dict[str, Any]] = []
    for row in rows:
        entity = _load_json(row["entity_proposals_json"])
        sector = _load_json(row["sector_proposals_json"])
        resolved_entity = entity.get("entity_id")
        if entity_id is not None and resolved_entity != entity_id:
            continue
        if tier is not None and tier_by_entity.get(resolved_entity) != tier:
            continue
        queue.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "channel_id": str(row["channel_id"]),
                "title": str(row["title"]),
                "canonical_url": row["canonical_url"],
                "published_at_proposal": row["published_at_proposal"],
                "discovered_at": str(row["discovered_at"]),
                "status": str(row["status"]),
                "duplicate_cluster_id": row["duplicate_cluster_id"],
                "priority_score": row["priority_score"],
                "entity_status": entity.get("status", "unknown"),
                "entity_id": resolved_entity,
                "sector_ids": sector.get("sector_ids", []),
            }
        )
    return queue


def queue_show(
    root: Path,
    candidate_id: str,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Full detail for one candidate, including its action log."""
    db_path = db_path or candidate_db.candidate_db_path(root)
    if not db_path.exists():
        return None
    connection = _connect(db_path)
    try:
        row = connection.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        actions = connection.execute(
            "SELECT action_id, action, reason, actor, acted_at, payload_json "
            "FROM candidate_actions WHERE candidate_id = ? "
            "ORDER BY acted_at ASC",
            (candidate_id,),
        ).fetchall()
    finally:
        connection.close()
    detail = dict(zip(row.keys(), row, strict=True))
    detail["entity_proposals"] = _load_json(
        detail.pop("entity_proposals_json", None)
    )
    detail["sector_proposals"] = _load_json(
        detail.pop("sector_proposals_json", None)
    )
    detail["reason_codes"] = _load_json(detail.pop("reason_codes_json", None))
    detail["actions"] = [dict(action) for action in actions]
    return detail


def render_candidate_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "# Candidate Queue\n\n(empty)\n"
    lines = [
        "# Candidate Queue",
        "",
        "| Priority | Status | Entity | Sectors | Channel | Title |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        priority = (
            f"{row['priority_score']:.3f}" if row["priority_score"] is not None else "—"
        )
        entity = row["entity_id"] or row["entity_status"]
        lines.append(
            f"| {priority} | {row['status']} | {entity} | "
            f"{len(row['sector_ids'])} | {row['channel_id']} | {row['title']} |"
        )
    lines.append("")
    lines.append(f"{len(rows)} candidate(s)")
    return "\n".join(lines) + "\n"


def render_candidate_detail(detail: dict[str, Any]) -> str:
    lines = [
        f"# Candidate {detail['candidate_id']}",
        "",
        f"Title: {detail['title']}",
        f"Channel: {detail['channel_id']}",
        f"Status: {detail['status']}",
        f"Discovered: {detail['discovered_at']}",
        f"Published (proposal): {detail.get('published_at_proposal') or '—'}",
        f"URL: {detail.get('canonical_url') or '—'}",
        f"Publisher: {detail.get('publisher') or '—'}",
        f"Duplicate cluster: {detail.get('duplicate_cluster_id') or '—'}",
        f"Priority: "
        f"{detail['priority_score'] if detail['priority_score'] is not None else '—'}",
        f"Model: {detail.get('model_version') or '—'}",
        "",
        "Entity proposal: "
        + json.dumps(detail["entity_proposals"], ensure_ascii=False),
        "",
        "Sector proposal: "
        + json.dumps(detail["sector_proposals"], ensure_ascii=False),
    ]
    reasons = detail.get("reason_codes") or []
    if reasons:
        lines += ["", "Reason codes:"] + [f"- {code}" for code in reasons]
    actions = detail.get("actions") or []
    if actions:
        lines += ["", "Actions:"] + [
            f"- {action['acted_at']} {action['action']} by "
            f"{action['actor']}: {action.get('reason') or '—'}"
            for action in actions
        ]
    return "\n".join(lines) + "\n"


def render_enrichment(enriched: list[dict[str, Any]], *, applied: bool) -> str:
    mode = "APPLIED" if applied else "DRY-RUN"
    if not enriched:
        return f"# {mode}: no candidates to enrich\n"
    lines = [
        f"# {mode}: {len(enriched)} candidate(s)",
        "",
        "| Candidate | Entity | Sectors | Priority |",
        "|---|---|---|---|",
    ]
    for row in enriched:
        lines.append(
            f"| {row['candidate_id']} | {row['entity_id'] or row['entity_status']} "
            f"| {row['sector_count']} | {row['priority_score']:.3f} |"
        )
    if not applied:
        lines.append("")
        lines.append("DRY-RUN: no changes written; rerun with --apply")
    return "\n".join(lines) + "\n"
