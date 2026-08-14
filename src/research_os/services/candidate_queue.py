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
from research_os.services.scoring import SCORING_MODEL, score_candidate
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


def existing_source_urls(objects: list[Any]) -> dict[str, str]:
    """Map canonical_url -> source_id for authoritative Sources.

    Read-only: lets a candidate that repeats content already promoted into
    the repository be flagged (``existing_source_id``) so a human can dismiss
    it without a second lookup. Never writes the candidate store.
    """
    urls: dict[str, str] = {}
    for obj in objects:
        if obj.object_type != "source":
            continue
        url = str(obj.metadata.get("canonical_url") or "").strip()
        if url:
            urls.setdefault(url, obj.object_id)
    return urls


def _is_representative(
    row: dict[str, Any],
    cluster_stats: dict[str, dict[str, Any]],
) -> bool:
    cluster_id = row.get("duplicate_cluster_id")
    if not cluster_id:
        return True
    stats = cluster_stats.get(str(cluster_id))
    return bool(stats and str(row["candidate_id"]) == stats["representative_id"])


def _collapse_rows(
    rows: list[dict[str, Any]],
    cluster_stats: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse duplicate clusters to one lead row each (view-layer only).

    Groups the already-filtered rows by cluster (singletons are their own
    group), keeps the highest-priority member as the lead, and folds the
    rest into ``dup_count``. ``already_sourced`` is OR-ed across the group so
    a collapsed non-representative that is already a Source is not hidden.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["_cluster_id"], []).append(row)
    collapsed: list[dict[str, Any]] = []
    for members in groups.values():
        # SQL already supplies the canonical queue order, so the first member
        # is the cluster lead and dict insertion order keeps clusters stable.
        lead = members[0]
        lead["dup_count"] = len(members) - 1
        lead["is_representative"] = _is_representative(lead, cluster_stats)
        sourced = [
            member["existing_source_id"]
            for member in members
            if member.get("existing_source_id")
        ]
        lead["already_sourced"] = bool(sourced)
        if sourced:
            lead["existing_source_id"] = sourced[0]
        collapsed.append(lead)
    return collapsed


def enrich_candidates(
    root: Path,
    db_path: Path | None = None,
    *,
    apply: bool = False,
    rescore: bool = False,
) -> list[dict[str, Any]]:
    """Backfill entity/sector/priority proposals for unscored new candidates.

    Deterministic and idempotent: normally only unscored ``new`` candidates are
    touched. ``rescore`` recomputes every ``new`` candidate after a model or
    classifier change, while preserving promoted/dismissed/expired rows. Without
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
        scoring_filter = "" if rescore else "AND priority_score IS NULL "
        rows = connection.execute(
            "SELECT candidate_id, channel_id, title, publisher, "
            "duplicate_cluster_id, created_at FROM candidates "
            f"WHERE status = 'new' {scoring_filter}"
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
            # A singleton (no cluster) is trivially its own representative;
            # only a non-representative member of a real cluster is a dup.
            is_representative = not cluster or (
                str(row["candidate_id"]) == cluster["representative_id"]
            )
            channel_meta = channels.get(str(row["channel_id"])) or {}
            score = score_candidate(
                title=title,
                source_grade=str(channel_meta.get("source_grade_proposal") or "B"),
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
        raise TransactionError(f"candidate enrichment failed: {exc}") from exc
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
    offset: int = 0,
    show_dups: bool = False,
) -> list[dict[str, Any]]:
    """Read the review queue, highest priority first.

    Filters are proposals-level: entity/tier resolve through the stored
    entity proposal and the Universe coverage tier. Rows carry the resolved
    entity/sector proposal so a human can triage without a second lookup.

    By default duplicate clusters are collapsed to one lead row (``dup_count``
    members folded in) so triage works on clusters, not variants; pass
    ``show_dups`` to see every member. ``existing_source_id`` marks a
    candidate (or a collapsed member) whose canonical URL is already an
    authoritative Source.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if offset < 0:
        raise ValueError("offset must be non-negative")
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
            f"{_ORDER_BY_PRIORITY}",
            params,
        ).fetchall()
        cluster_stats = _cluster_stats(connection)
    finally:
        connection.close()

    objects, _ = validate_repository(root)
    tier_by_entity = {
        obj.object_id: str(obj.metadata.get("coverage_tier") or "")
        for obj in objects
        if obj.object_type == "company"
    }
    source_urls = existing_source_urls(objects)
    queue: list[dict[str, Any]] = []
    for row in rows:
        entity = _load_json(row["entity_proposals_json"])
        sector = _load_json(row["sector_proposals_json"])
        resolved_entity = entity.get("entity_id")
        if entity_id is not None and resolved_entity != entity_id:
            continue
        if tier is not None and tier_by_entity.get(resolved_entity) != tier:
            continue
        cluster_id = row["duplicate_cluster_id"]
        queue.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "channel_id": str(row["channel_id"]),
                "title": str(row["title"]),
                "canonical_url": row["canonical_url"],
                "published_at_proposal": row["published_at_proposal"],
                "discovered_at": str(row["discovered_at"]),
                "status": str(row["status"]),
                "duplicate_cluster_id": cluster_id,
                "priority_score": row["priority_score"],
                "entity_status": entity.get("status", "unknown"),
                "entity_id": resolved_entity,
                "sector_ids": sector.get("sector_ids", []),
                "existing_source_id": source_urls.get(str(row["canonical_url"] or "")),
                "already_sourced": False,
                "is_representative": False,
                "dup_count": 0,
                "_cluster_id": (
                    str(cluster_id) if cluster_id else str(row["candidate_id"])
                ),
            }
        )
    if not show_dups:
        queue = _collapse_rows(queue, cluster_stats)
    else:
        for row in queue:
            row["is_representative"] = _is_representative(row, cluster_stats)
    return queue[offset : offset + limit]


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
        cluster_stats = _cluster_stats(connection)
    finally:
        connection.close()
    detail = dict(zip(row.keys(), row, strict=True))
    detail["entity_proposals"] = _load_json(detail.pop("entity_proposals_json", None))
    detail["sector_proposals"] = _load_json(detail.pop("sector_proposals_json", None))
    detail["reason_codes"] = _load_json(detail.pop("reason_codes_json", None))
    detail["actions"] = [dict(action) for action in actions]
    objects, _ = validate_repository(root)
    detail["existing_source_id"] = existing_source_urls(objects).get(
        str(detail.get("canonical_url") or "")
    )
    detail["is_representative"] = _is_representative(detail, cluster_stats)
    detail["scoring"] = _recompute_scoring(detail, objects, cluster_stats)
    return detail


def _recompute_scoring(
    detail: dict[str, Any],
    objects: list[Any],
    cluster_stats: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Deterministically recompute the score breakdown (WP-601 F-006).

    Sub-scores are not persisted (only priority_score + reason_codes are),
    so recompute via :func:`score_candidate` when the stored model version
    matches the current scoring version; return ``None`` on mismatch.
    """
    if str(detail.get("model_version") or "") != SCORING_MODEL:
        return None
    channel = next(
        (
            obj
            for obj in objects
            if obj.object_type == "source_channel"
            and obj.object_id == detail.get("channel_id")
        ),
        None,
    )
    entity_status = str(
        (detail.get("entity_proposals") or {}).get("status") or "unknown"
    )
    sector_count = len((detail.get("sector_proposals") or {}).get("sector_ids") or [])
    cluster_size = 1
    if detail.get("duplicate_cluster_id"):
        stats = cluster_stats.get(str(detail["duplicate_cluster_id"]))
        if stats:
            cluster_size = int(stats["size"])
    score = score_candidate(
        title=str(detail.get("title") or ""),
        source_grade=(
            str(channel.metadata.get("source_grade_proposal") or "B")
            if channel
            else "B"
        ),
        entity_status=entity_status,
        sector_count=sector_count,
        is_duplicate_representative=bool(detail.get("is_representative", True)),
        cluster_size=cluster_size,
        channel_type=(
            str(channel.metadata.get("channel_type") or "web_page")
            if channel
            else "web_page"
        ),
    )
    return {
        "subscores": score["subscores"],
        "priority_score": score["priority_score"],
        "scoring_version": score["scoring_version"],
        "model": score["model"],
    }


def render_candidate_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "# Candidate Queue\n\n(empty)\n"
    lines = [
        "# Candidate Queue",
        "",
        "| Priority | Status | Dup | Entity | Sectors | Channel | Title |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        priority = (
            f"{row['priority_score']:.3f}" if row["priority_score"] is not None else "—"
        )
        if row.get("existing_source_id"):
            dup = f"SRC:{row['existing_source_id']}"
        elif row.get("dup_count"):
            dup = f"+{row['dup_count']}"
        elif not row.get("is_representative", True):
            dup = "variant"
        else:
            dup = ""
        entity = row["entity_id"] or row["entity_status"]
        lines.append(
            f"| {priority} | {row['status']} | {dup} | {entity} | "
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


def promoted_rows(
    root: Path,
    db_path: Path | None = None,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Read candidates that promoted into authoritative Sources (read-only).

    Rows link back to the permanent Source id and carry the originating
    channel and resolved entity, so the dashboard can show what the pipeline
    produced without touching the repository.
    """
    db_path = db_path or candidate_db.candidate_db_path(root)
    if not db_path.exists():
        return []
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            "SELECT candidate_id, promoted_source_id, channel_id, title, "
            "publisher, discovered_at, entity_proposals_json FROM candidates "
            "WHERE status = 'promoted' AND promoted_source_id IS NOT NULL "
            "ORDER BY promoted_source_id DESC, candidate_id ASC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    promoted: list[dict[str, Any]] = []
    for row in rows:
        entity = _load_json(row["entity_proposals_json"])
        promoted.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "promoted_source_id": str(row["promoted_source_id"]),
                "channel_id": str(row["channel_id"]),
                "title": str(row["title"]),
                "publisher": str(row["publisher"] or ""),
                "discovered_at": str(row["discovered_at"]),
                "entity_id": entity.get("entity_id"),
            }
        )
    return promoted


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
