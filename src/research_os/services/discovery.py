"""B-007 Discovery run service.

Maps a reviewed+enabled Channel to its DiscoveryAdapter, runs preflight,
executes bounded discovery, and writes candidates + a run record to the
Candidate operational store.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
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
from research_os.services import candidate_db
from research_os.services.dedup import assign_clusters, normalize_title
from research_os.services.validation import validate_repository


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


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
    try:
        discovered = adapter.discover()
    except Exception as exc:  # bounded failure -> record run as failed (apply only)
        if apply:
            candidate_db.apply_migrations(db_path)
            candidate_db.record_discovery_run(
                db_path,
                run_id,
                channel_id,
                started_at,
                status="failed",
                software_version="0.3",
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
    candidate_db.apply_migrations(db_path)
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
    candidate_db.record_discovery_run(
        db_path,
        run_id,
        channel_id,
        started_at,
        candidate_count=len(discovered),
        software_version="0.3",
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
