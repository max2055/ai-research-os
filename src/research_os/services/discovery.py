"""B-007 Discovery run service.

Maps a reviewed+enabled Channel to its DiscoveryAdapter, runs preflight,
executes bounded discovery, and writes candidates + a run record to the
Candidate operational store.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from research_os.adapters.discovery import (
    ArxivDiscoveryAdapter,
    DiscoveryAdapter,
    GitHubReleaseDiscoveryAdapter,
    RSSDiscoveryAdapter,
    SECDiscoveryAdapter,
    SourceCandidate,
)
from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.candidate_queue import enrich_candidates
from research_os.services.dedup import assign_clusters, normalize_title
from research_os.services.schedule import is_due
from research_os.services.validation import validate_repository


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _candidate_id() -> str:
    return f"CND-{uuid.uuid4().hex[:20]}"


def _content_fingerprint(candidate: SourceCandidate) -> str:
    digest = hashlib.sha256()
    digest.update(candidate.title.encode("utf-8", errors="replace"))
    digest.update((candidate.url or "").encode("utf-8", errors="replace"))
    return digest.hexdigest()


def _build_adapter(channel: dict[str, Any]) -> DiscoveryAdapter:
    channel_type = channel["channel_type"]
    locator = channel["locator"]
    allowed_hosts = frozenset(channel.get("allow_hosts", []) or [])
    limit = int(channel.get("max_candidates_per_run") or 20)
    if channel_type == "rss":
        return RSSDiscoveryAdapter(
            locator,
            allowed_hosts=allowed_hosts,
            publisher=channel.get("publisher", ""),
            limit=limit,
        )
    if channel_type == "github_release":
        return GitHubReleaseDiscoveryAdapter(
            _github_repo_from_locator(locator),
            limit=limit,
        )
    if channel_type == "arxiv":
        return ArxivDiscoveryAdapter(
            channel.get("query") or "",
            limit=limit,
        )
    if channel_type == "sec":
        # locator may carry CIKs; fall back to entity_ids for CIK resolution.
        ciks = _ciks_from_locator(locator)
        if not ciks:
            raise ValueError("SEC channel requires a CIK in locator or entity_ids")
        return SECDiscoveryAdapter(
            ciks[0],
            forms=frozenset((channel.get("query") or "10-Q,10-K,8-K,20-F").split(",")),
            user_agent=channel.get("user_agent")
            or "AI-Research-OS/0.3 max wu_chenlong@hotmail.com",
            limit=limit,
        )
    raise ValueError(f"unsupported channel_type for discovery: {channel_type}")


def _github_repo_from_locator(locator: str) -> str:
    match = re.search(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", locator)
    if not match:
        raise ValueError(f"GitHub channel locator must be a repository URL: {locator}")
    return match.group(1)


def _ciks_from_locator(locator: str) -> list[str]:
    return re.findall(r"\d{1,10}", locator)


def preflight_channel(channel: dict[str, Any]) -> None:
    """B-007 preflight: reviewed/enabled/license/limit checks."""
    if channel.get("review_status") != "reviewed":
        raise ValueError(
            f"channel {channel['id']} not reviewed (RCP-v03-005 RP-4)"
        )
    if not channel.get("enabled"):
        raise ValueError(f"channel {channel['id']} not enabled")
    if channel.get("license_status") == "restricted":
        raise ValueError(
            f"channel {channel['id']} license restricted (RP-6 — no scheduling)"
        )
    limit = int(channel.get("max_candidates_per_run") or 20)
    if not 1 <= limit <= 100:
        raise ValueError(f"channel {channel['id']} per-run limit out of range")


LOCK_STALE = timedelta(minutes=30)


def _acquire_channel_lock(
    db_path: Path,
    channel_id: str,
    started_at: str,
) -> None:
    """B-021 no-overlap lock: reclaim stale running runs, refuse a live one.

    A crashed run leaves a ``running`` discovery_runs row; rows older than
    ``LOCK_STALE`` are reclaimed as failed so a restart can proceed, giving
    launchd recovery after reboot without overlapping runs.
    """
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("BEGIN")
        stale_before = (
            _parse_iso(started_at) - LOCK_STALE
        ).isoformat().replace("+00:00", "Z")
        connection.execute(
            "UPDATE discovery_runs SET status = 'failed', "
            "finished_at = started_at "
            "WHERE status = 'running' AND started_at < ?",
            (stale_before,),
        )
        row = connection.execute(
            "SELECT run_id FROM discovery_runs "
            "WHERE channel_id = ? AND status = 'running'",
            (channel_id,),
        ).fetchone()
        if row is not None:
            raise ValueError(
                f"channel {channel_id} already has a running discovery run"
            )
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise TransactionError(f"discovery lock failed: {exc}") from exc
    finally:
        connection.close()


def run_discovery(
    root: Path,
    channel_id: str,
    *,
    db_path: Path | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Run one bounded discovery for a channel; write run + candidates if apply."""
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before discovery")
    channel = next(
        (obj for obj in objects if obj.object_id == channel_id), None
    )
    if channel is None or channel.object_type != "source_channel":
        raise ValueError(f"unknown source_channel {channel_id}")
    meta = dict(channel.metadata)
    meta["id"] = channel.object_id
    preflight_channel(meta)

    db_path = db_path or candidate_db.candidate_db_path(root)
    started_at = _utc_now()
    run_id = f"RUN-{uuid.uuid4().hex[:16]}"
    adapter = _build_adapter(meta)
    if apply:
        candidate_db.apply_migrations(db_path)
        _acquire_channel_lock(db_path, channel_id, started_at)
        candidate_db.record_discovery_run(
            db_path,
            run_id,
            channel_id,
            started_at,
            status="running",
            software_version="0.3",
        )
    try:
        discovered = adapter.discover()
    except Exception as exc:  # bounded failure -> close the run as failed
        if apply:
            candidate_db.finish_discovery_run(
                db_path,
                run_id,
                status="failed",
                finished_at=_utc_now(),
            )
        raise ValueError(f"discovery failed for {channel_id}: {exc}") from exc

    if not apply:
        return {
            "run_id": run_id,
            "channel_id": channel_id,
            "candidate_count": len(discovered),
            "candidates": [
                {
                    "title": candidate.title,
                    "url": candidate.url,
                    "published_at_proposal": candidate.published_at,
                    "publisher": candidate.publisher,
                }
                for candidate in discovered
            ],
        }

    candidates: list[dict[str, object]] = [
        {
            "candidate_id": _candidate_id(),
            "published_at_proposal": candidate.published_at,
            "title": candidate.title,
            "canonical_url": candidate.url,
            "publisher": candidate.publisher,
            "content_fingerprint": _content_fingerprint(candidate),
            "language": None,
        }
        for candidate in discovered
    ]
    # B-014 dedup: extend existing clusters across runs, never drop records.
    existing = candidate_db.existing_candidates(root)
    existing_index: dict[str, str] = {}
    for prior in existing:
        key = prior.get("title") or ""
        cluster = prior.get("duplicate_cluster_id")
        if key and cluster:
            existing_index[normalize_title(str(key))] = str(cluster)
    candidates = assign_clusters(candidates, existing=existing_index)
    inserted = candidate_db.insert_candidates(
        db_path,
        candidates,
        channel_id,
        started_at,
    )
    # B-018: score the new candidates so the review queue can sort by priority.
    enrich_candidates(root, db_path, apply=True)
    candidate_db.finish_discovery_run(
        db_path,
        run_id,
        status="succeeded",
        candidate_count=len(discovered),
        finished_at=_utc_now(),
    )
    return {
        "run_id": run_id,
        "channel_id": channel_id,
        "candidate_count": len(discovered),
        "inserted": inserted,
        "db_path": str(db_path),
    }


def render_discovery_result(result: dict[str, Any]) -> str:
    lines = [
        f"# Discovery run {result.get('run_id', '')}",
        "",
        f"Channel: {result.get('channel_id', '')}",
        f"Candidates: {result.get('candidate_count', 0)}",
    ]
    if "db_path" in result:
        lines.append(f"DB: {result['db_path']}")
        lines.append(f"Inserted: {result.get('inserted', 0)}")
    else:
        lines.append("")
        lines.append("| Title | URL | Published | Publisher |")
        lines.append("|---|---|---|---|")
        for candidate in result.get("candidates", []):
            lines.append(
                f"| {candidate['title']} | {candidate['url']} | "
                f"{candidate.get('published_at_proposal') or ''} | "
                f"{candidate['publisher']} |"
            )
    return "\n".join(lines) + "\n"


def due_channels(
    root: Path,
    *,
    as_of: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Reviewed+enabled channels whose schedule says they are due (B-021).

    A channel with no prior discovery run is always due; an unparseable
    schedule is never due (surfaced via ``discover check`` instead).
    """
    objects, _ = validate_repository(root)
    db_path = db_path or candidate_db.candidate_db_path(root)
    last_runs: dict[str, str] = {}
    if db_path.exists():
        connection = sqlite3.connect(db_path)
        try:
            rows = connection.execute(
                "SELECT channel_id, MAX(started_at) FROM discovery_runs "
                "WHERE status != 'running' GROUP BY channel_id"
            ).fetchall()
            last_runs = {str(row[0]): str(row[1]) for row in rows}
        finally:
            connection.close()
    as_of_value = as_of or _utc_now()
    try:
        as_of_dt = _parse_iso(as_of_value)
    except ValueError as exc:
        raise ValueError(f"as_of must be an ISO date-time: {as_of_value}") from exc

    due: list[dict[str, Any]] = []
    for obj in objects:
        if obj.object_type != "source_channel":
            continue
        meta = dict(obj.metadata)
        if meta.get("review_status") != "reviewed" or not meta.get("enabled"):
            continue
        if meta.get("license_status") == "restricted":
            continue
        schedule = str(meta.get("schedule") or "")
        previous = last_runs.get(obj.object_id)
        previous_dt = None
        if previous:
            try:
                previous_dt = _parse_iso(previous)
            except ValueError:
                previous_dt = None
        if is_due(previous_dt, schedule, as_of_dt):
            due.append(
                {
                    "channel_id": obj.object_id,
                    "schedule": schedule,
                    "last_run": previous,
                }
            )
    return sorted(due, key=lambda item: item["channel_id"])
