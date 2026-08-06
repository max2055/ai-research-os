"""B-025 14-day Pilot status.

Aggregates the Pilot window (since start) into a Gate-progress summary for
the daily check: discovery runs + failures (including config-level channel
failures recorded as Job Runs), candidate throughput, triage yield and Daily
Brief coverage. Complements the point-in-time ``pipeline_metrics`` with the
windowed view the Pilot Gate (§12) needs.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from research_os.services import candidate_db
from research_os.services.validation import validate_repository

PILOT_DIR = Path("05_Research") / "Operations" / "Pilot"
BRIEFS_DIR = Path("05_Research") / "Operations" / "Briefs"
TARGET_DAYS = 14
TARGET_PROMOTED = 20
TARGET_CHANNELS = 20


def _pilot_start(root: Path) -> str | None:
    state = root / PILOT_DIR / "pilot.json"
    if not state.exists():
        return None
    try:
        value = json.loads(state.read_text(encoding="utf-8"))
        return str(value["started_at"])
    except (OSError, ValueError, KeyError):
        return None


def pilot_status(
    root: Path,
    *,
    since: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Report Pilot progress over the window since ``since`` (no writes)."""
    objects, _ = validate_repository(root)
    db_path = db_path or candidate_db.candidate_db_path(root)
    since_value = since or _pilot_start(root) or date.today().isoformat()

    jobs = [
        obj
        for obj in objects
        if obj.object_type == "job"
        and str(obj.metadata.get("started_at") or "").startswith(since_value)
    ]
    job_failures = sorted(
        (
            {
                "job_id": obj.object_id,
                "job_name": str(obj.metadata.get("job_name") or ""),
                "message": str(obj.metadata.get("message") or ""),
            }
            for obj in jobs
            if obj.metadata.get("status") == "failed"
        ),
        key=lambda item: item["job_id"],
    )

    discovered_since = 0
    status_counts: dict[str, int] = {}
    if db_path.exists():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        try:
            for row in connection.execute(
                "SELECT discovered_at, status FROM candidates"
            ):
                if str(row["discovered_at"]).startswith(since_value):
                    discovered_since += 1
                    status_counts[str(row["status"])] = (
                        status_counts.get(str(row["status"]), 0) + 1
                    )
        finally:
            connection.close()

    brief_dates = sorted(
        path.name.replace("Daily_Brief_", "").replace(".md", "")
        for path in (root / BRIEFS_DIR).glob("Daily_Brief_*.md")
        if path.name.startswith("Daily_Brief_")
    )
    started = since_value
    elapsed = max(0, (date.today() - date.fromisoformat(started)).days + 1)
    channels = sorted(
        obj.object_id
        for obj in objects
        if obj.object_type == "source_channel"
        and obj.metadata.get("review_status") == "reviewed"
        and obj.metadata.get("enabled")
    )
    return {
        "since": since_value,
        "as_of": date.today().isoformat(),
        "days_elapsed": elapsed,
        "target_days": TARGET_DAYS,
        "jobs": {
            "total": len(jobs),
            "failed": len(job_failures),
            "by_name": _count_by_name(jobs),
        },
        "job_failures": job_failures,
        "candidates": {
            "discovered_since": discovered_since,
            "promoted": status_counts.get("promoted", 0),
            "dismissed": status_counts.get("dismissed", 0),
        },
        "briefs": brief_dates,
        "gate": {
            "days": elapsed,
            "promoted": status_counts.get("promoted", 0),
            "channels": len(channels),
            "duplicate_target": "duplicate rate <15% (see pipeline metrics)",
            "relevance_target": "Top-20 human relevance >=75% (manual)",
        },
    }


def _count_by_name(jobs: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for job in jobs:
        name = str(job.metadata.get("job_name") or "unknown")
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def render_pilot_status(status: dict[str, Any]) -> str:
    gate = status["gate"]
    jobs = status["jobs"]
    candidates = status["candidates"]
    brief_text = ", ".join(status["briefs"]) or "—"
    by_name_text = ", ".join(
        f"{name}={count}" for name, count in jobs["by_name"].items()
    ) or "—"
    lines = [
        f"# Pilot Status — day {gate['days']}/{status['target_days']} "
        f"(since {status['since']})",
        "",
        "## Gate progress",
        f"- Days elapsed: {gate['days']}/{status['target_days']}",
        f"- Promoted: {gate['promoted']}/{TARGET_PROMOTED}",
        f"- Reviewed+enabled channels: {gate['channels']}/{TARGET_CHANNELS}",
        f"- Duplicate rate target: {gate['duplicate_target']}",
        f"- Top-20 relevance target: {gate['relevance_target']}",
        "",
        "## Jobs",
        f"- Total: {jobs['total']} (failed {jobs['failed']})",
        f"- By name: {by_name_text}",
    ]
    if status["job_failures"]:
        lines.append("")
        lines.append("Failed jobs:")
        for failure in status["job_failures"]:
            lines.append(
                f"- {failure['job_id']} ({failure['job_name']}): "
                f"{failure['message']}"
            )
    lines += [
        "",
        "## Candidates",
        f"- Discovered since start: {candidates['discovered_since']}",
        f"- Promoted: {candidates['promoted']} / dismissed: {candidates['dismissed']}",
        "",
        "## Daily Briefs",
        f"- {brief_text}",
        "",
    ]
    return "\n".join(lines)
