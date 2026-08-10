"""B-007 Discovery run service.

Maps a reviewed+enabled Channel to its DiscoveryAdapter, runs preflight,
executes bounded discovery, and writes candidates + a run record to the
Candidate operational store.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any, NoReturn
from xml.etree import ElementTree

from research_os.adapters.discovery import (
    ArxivDiscoveryAdapter,
    CompositeDiscoveryAdapter,
    DiscoveryAdapter,
    DiscoveryTransportError,
    FetchTelemetry,
    GitHubReleaseDiscoveryAdapter,
    RSSDiscoveryAdapter,
    SECDiscoveryAdapter,
    SourceCandidate,
    TextFetcher,
    fetch_text,
)
from research_os.domain.models import ResearchObject
from research_os.repositories.transaction import TransactionError
from research_os.services import candidate_db
from research_os.services.candidate_queue import (
    enrich_candidates,
    existing_source_urls,
)
from research_os.services.dedup import assign_clusters, normalize_title
from research_os.services.redaction import redact_secrets
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
    # fingerprint the redacted URL so it matches the stored canonical_url.
    digest.update(
        (redact_secrets(candidate.url) or "").encode("utf-8", errors="replace")
    )
    return digest.hexdigest()


class DiscoveryRunError(ValueError):
    """Safe run-scoped error suitable for Job and CLI output."""

    def __init__(self, run_id: str, failure_class: str, attempts: int) -> None:
        self.run_id = run_id
        self.failure_class = failure_class
        self.attempts = attempts
        super().__init__(
            f"discovery run {run_id} failed: {failure_class} after {attempts} attempts"
        )


def _telemetry_fetcher(
    allowed_hosts: frozenset[str],
    telemetry: FetchTelemetry | None,
) -> TextFetcher | None:
    if telemetry is None:
        return None
    return partial(
        fetch_text,
        allowed_hosts=allowed_hosts,
        telemetry=telemetry,
    )


def _build_adapter(
    channel: dict[str, Any],
    *,
    telemetry: FetchTelemetry | None = None,
) -> DiscoveryAdapter:
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
            fetcher=_telemetry_fetcher(allowed_hosts, telemetry),
        )
    if channel_type == "github_release":
        repos = _github_repos_from_locator(locator)
        github_adapters = [
            GitHubReleaseDiscoveryAdapter(
                repo,
                limit=limit,
                fetcher=_telemetry_fetcher(frozenset({"api.github.com"}), telemetry),
            )
            for repo in repos
        ]
        if len(github_adapters) == 1:
            return github_adapters[0]
        return CompositeDiscoveryAdapter(github_adapters, limit=limit)
    if channel_type == "arxiv":
        return ArxivDiscoveryAdapter(
            channel.get("query") or "",
            limit=limit,
            fetcher=_telemetry_fetcher(
                frozenset({"arxiv.org", "export.arxiv.org"}), telemetry
            ),
        )
    if channel_type == "sec":
        # locator carries the CIK allowlist; one adapter per CIK.
        ciks = _ciks_from_locator(locator)
        if not ciks:
            raise ValueError("SEC channel requires a CIK in locator or entity_ids")
        forms = frozenset((channel.get("query") or "10-Q,10-K,8-K,20-F").split(","))
        user_agent = (
            channel.get("user_agent")
            or "AI-Research-OS/0.3 max wu_chenlong@hotmail.com"
        )
        sec_adapters = [
            SECDiscoveryAdapter(
                cik,
                forms=forms,
                user_agent=user_agent,
                limit=limit,
                fetcher=_telemetry_fetcher(
                    frozenset({"data.sec.gov", "www.sec.gov"}), telemetry
                ),
            )
            for cik in ciks
        ]
        if len(sec_adapters) == 1:
            return sec_adapters[0]
        return CompositeDiscoveryAdapter(sec_adapters, limit=limit)
    raise ValueError(f"unsupported channel_type for discovery: {channel_type}")


def _github_repos_from_locator(locator: str) -> list[str]:
    repos = re.findall(
        r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)",
        locator,
    )
    if not repos:
        raise ValueError(
            f"GitHub channel locator must carry a repository URL: {locator}"
        )
    return list(dict.fromkeys(repos))


def _ciks_from_locator(locator: str) -> list[str]:
    return re.findall(r"\d{1,10}", locator)


def preflight_channel(channel: dict[str, Any]) -> None:
    """B-007 preflight: reviewed/enabled/license/limit checks."""
    if channel.get("review_status") != "reviewed":
        raise ValueError(f"channel {channel['id']} not reviewed (RCP-v03-005 RP-4)")
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
            (_parse_iso(started_at) - LOCK_STALE).isoformat().replace("+00:00", "Z")
        )
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


def _candidate_records(
    discovered: Sequence[SourceCandidate],
) -> list[dict[str, object]]:
    """Build insertable candidate rows; URLs are redacted (B-024)."""
    return [
        {
            "candidate_id": _candidate_id(),
            "published_at_proposal": candidate.published_at,
            "title": candidate.title,
            "canonical_url": redact_secrets(candidate.url),
            "publisher": candidate.publisher,
            "content_fingerprint": _content_fingerprint(candidate),
            "language": None,
        }
        for candidate in discovered
    ]


def _sourced_urls(objects: list[Any], db_path: Path) -> set[str]:
    """canonical URLs already captured as authoritative content.

    Combines formal Sources (Markdown) and candidates that promoted into a
    Source, so discovery can skip re-inserting content already in the
    repository (inbound skip, G4).
    """
    urls = set(existing_source_urls(objects))
    if db_path.exists():
        connection = sqlite3.connect(db_path)
        try:
            rows = connection.execute(
                "SELECT canonical_url FROM candidates "
                "WHERE status = 'promoted' AND canonical_url IS NOT NULL"
            ).fetchall()
            urls.update(str(row[0]) for row in rows if row[0])
        finally:
            connection.close()
    return urls


def _is_parse_failure(adapter: DiscoveryAdapter, exc: Exception) -> bool:
    if isinstance(exc, (ElementTree.ParseError, json.JSONDecodeError)):
        return True
    if isinstance(adapter, GitHubReleaseDiscoveryAdapter):
        return (
            isinstance(exc, ValueError)
            and str(exc) == "GitHub releases response must be a list"
        )
    if isinstance(adapter, SECDiscoveryAdapter):
        detail = str(exc)
        return (
            isinstance(exc, AttributeError)
            and re.fullmatch(r"'[^']+' object has no attribute 'get'", detail)
            is not None
        ) or (
            isinstance(exc, TypeError)
            and re.fullmatch(r"'[^']+' object is not iterable", detail) is not None
        )
    return False


@dataclass
class _DiscoveryParseTelemetry:
    failures: list[Exception] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return len(self.failures)

    def records(self, exc: Exception) -> bool:
        return any(failure is exc for failure in self.failures)


def _discover_with_parse_telemetry(
    adapter: DiscoveryAdapter,
    telemetry: _DiscoveryParseTelemetry,
) -> tuple[SourceCandidate, ...]:
    if not isinstance(adapter, CompositeDiscoveryAdapter):
        try:
            return adapter.discover()
        except Exception as exc:
            if _is_parse_failure(adapter, exc):
                telemetry.failures.append(exc)
            raise

    # Preserve CompositeDiscoveryAdapter ordering, failure, nesting, and limit
    # semantics while observing exceptions that its public method must swallow.
    results: list[SourceCandidate] = []
    failures: list[Exception] = []
    for child in adapter.adapters:
        try:
            results.extend(_discover_with_parse_telemetry(child, telemetry))
        except Exception as exc:
            failures.append(exc)
        if len(results) >= adapter.limit:
            break
    if not results and failures:
        raise failures[0]
    return tuple(results[: adapter.limit])


def _safe_failure_details(
    exc: Exception,
    *,
    telemetry: FetchTelemetry,
    parse_telemetry: _DiscoveryParseTelemetry,
) -> tuple[str, int]:
    if isinstance(exc, DiscoveryTransportError):
        failure_class = exc.failure_class
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", failure_class):
            failure_class = "transport"
        return failure_class, max(0, exc.attempts)
    if parse_telemetry.records(exc):
        return "response_format", telemetry.attempts
    return type(exc).__name__, telemetry.attempts


def _raise_run_failure(
    run_id: str,
    failure: Exception,
    *,
    telemetry: FetchTelemetry,
    parse_telemetry: _DiscoveryParseTelemetry,
    finalization_failure: Exception | None = None,
) -> NoReturn:
    failure_class, attempts = _safe_failure_details(
        failure,
        telemetry=telemetry,
        parse_telemetry=parse_telemetry,
    )
    error = DiscoveryRunError(run_id, failure_class, attempts)
    if finalization_failure is not None:
        error.add_note(
            "discovery terminal update also failed: "
            f"{type(finalization_failure).__name__}"
        )
    raise error from failure


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
    channel = next((obj for obj in objects if obj.object_id == channel_id), None)
    if channel is None or channel.object_type != "source_channel":
        raise ValueError(f"unknown source_channel {channel_id}")
    meta = dict(channel.metadata)
    meta["id"] = channel.object_id
    preflight_channel(meta)

    db_path = db_path or candidate_db.candidate_db_path(root)
    started_at = _utc_now()
    run_id = f"RUN-{uuid.uuid4().hex[:16]}"
    telemetry = FetchTelemetry()
    parse_telemetry = _DiscoveryParseTelemetry()
    if not apply:
        try:
            adapter = _build_adapter(meta, telemetry=telemetry)
            discovered = _discover_with_parse_telemetry(adapter, parse_telemetry)
            sourced_urls = _sourced_urls(objects, db_path)
            return {
                "run_id": run_id,
                "channel_id": channel_id,
                "candidate_count": len(discovered),
                "skipped": sum(
                    1 for c in discovered if redact_secrets(c.url) in sourced_urls
                ),
                "attempts": telemetry.attempts,
                "retries": telemetry.retries,
                "http_errors": telemetry.http_errors,
                "parse_errors": parse_telemetry.errors,
                "candidates": [
                    {
                        "title": candidate.title,
                        "url": candidate.url,
                        "published_at_proposal": candidate.published_at,
                        "publisher": candidate.publisher,
                        "already_sourced": (
                            redact_secrets(candidate.url) in sourced_urls
                        ),
                    }
                    for candidate in discovered
                ],
            }
        except Exception as exc:
            _raise_run_failure(
                run_id,
                exc,
                telemetry=telemetry,
                parse_telemetry=parse_telemetry,
            )

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

    failure: Exception | None = None
    candidate_count = 0
    result: dict[str, Any] | None = None
    try:
        adapter = _build_adapter(meta, telemetry=telemetry)
        discovered = _discover_with_parse_telemetry(adapter, parse_telemetry)

        sourced_urls = _sourced_urls(objects, db_path)
        candidates = [
            candidate
            for candidate in _candidate_records(discovered)
            if str(candidate.get("canonical_url") or "") not in sourced_urls
        ]
        candidate_count = len(candidates)
        skipped = len(discovered) - candidate_count
        if candidates:
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
            # B-018: score the new candidates so the review queue can sort.
            enrich_candidates(root, db_path, apply=True)
        else:
            inserted = 0
        result = {
            "run_id": run_id,
            "channel_id": channel_id,
            "candidate_count": candidate_count,
            "inserted": inserted,
            "skipped": skipped,
            "attempts": telemetry.attempts,
            "retries": telemetry.retries,
            "http_errors": telemetry.http_errors,
            "parse_errors": parse_telemetry.errors,
            "db_path": str(db_path),
        }
    except Exception as exc:
        failure = exc

    finalization_failure: Exception | None = None
    try:
        candidate_db.finish_discovery_run(
            db_path,
            run_id,
            status="failed" if failure is not None else "succeeded",
            candidate_count=candidate_count,
            finished_at=_utc_now(),
            retries=telemetry.retries,
            http_errors=telemetry.http_errors,
            parse_errors=parse_telemetry.errors,
        )
    except Exception as exc:
        finalization_failure = exc

    if failure is not None:
        _raise_run_failure(
            run_id,
            failure,
            telemetry=telemetry,
            parse_telemetry=parse_telemetry,
            finalization_failure=finalization_failure,
        )
    if finalization_failure is not None:
        _raise_run_failure(
            run_id,
            finalization_failure,
            telemetry=telemetry,
            parse_telemetry=parse_telemetry,
        )
    if result is None:
        raise AssertionError("successful discovery run produced no result")
    return result


def render_discovery_result(result: dict[str, Any]) -> str:
    lines = [
        f"# Discovery run {result.get('run_id', '')}",
        "",
        f"Channel: {result.get('channel_id', '')}",
        f"Candidates: {result.get('candidate_count', 0)}",
        f"Fetch attempts: {result.get('attempts', 0)}",
        f"Retries: {result.get('retries', 0)}",
        f"HTTP errors: {result.get('http_errors', 0)}",
        f"Parse errors: {result.get('parse_errors', 0)}",
    ]
    if result.get("skipped"):
        lines.append(f"Skipped (already sourced): {result['skipped']}")
    if "db_path" in result:
        lines.append(f"DB: {result['db_path']}")
        lines.append(f"Inserted: {result.get('inserted', 0)}")
    else:
        lines.append("")
        lines.append("| Title | URL | Published | Publisher | Status |")
        lines.append("|---|---|---|---|---|")
        for candidate in result.get("candidates", []):
            status = "already sourced" if candidate.get("already_sourced") else "new"
            lines.append(
                f"| {candidate['title']} | {candidate['url']} | "
                f"{candidate.get('published_at_proposal') or ''} | "
                f"{candidate['publisher']} | {status} |"
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
    return due_channels_from_objects(
        objects,
        as_of=as_of,
        db_path=db_path or candidate_db.candidate_db_path(root),
    )


def due_channels_from_objects(
    objects: list[ResearchObject],
    *,
    as_of: str | None = None,
    db_path: Path,
) -> list[dict[str, Any]]:
    """Pure-metadata schedule query over preloaded repository objects."""
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
