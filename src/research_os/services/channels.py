"""Channel Registry service (B-006).

Read-only list/check plus explicit --apply enable/disable. A channel is
eligible for scheduling only when reviewed and enabled (RCP-v03-005 RP-4);
enabling a non-reviewed channel is refused.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.repositories.markdown import MarkdownDocument
from research_os.services.validation import validate_repository


def _channel_rows(objects: list[ResearchObject]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for obj in objects:
        if obj.object_type != "source_channel":
            continue
        meta = obj.metadata
        rows.append(
            {
                "id": obj.object_id,
                "name": meta.get("name", ""),
                "channel_type": meta.get("channel_type", ""),
                "locator": meta.get("locator", ""),
                "license_status": meta.get("license_status", ""),
                "enabled": bool(meta.get("enabled")),
                "review_status": meta.get("review_status", ""),
            }
        )
    return sorted(rows, key=lambda row: row["id"])


def channel_rows(root: Path) -> list[dict[str, Any]]:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before channel ops")
    return _channel_rows(objects)


def render_channel_list(rows: list[dict[str, Any]]) -> str:
    header = "| ID | Name | Type | License | Review | Enabled |"
    sep = "|---|---|---|---|---|---|"
    lines = ["# Source Channels", "", header, sep]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['name']} | {row['channel_type']} | "
            f"{row['license_status']} | {row['review_status']} | "
            f"{'Y' if row['enabled'] else 'N'} |"
        )
    return "\n".join(lines) + "\n"


def render_channel_check(rows: list[dict[str, Any]]) -> str:
    header = "| ID | Review | Enabled | Schedulable |"
    sep = "|---|---|---|---|"
    lines = ["# Channel Check (schedulable = reviewed + enabled)", "", header, sep]
    for row in rows:
        schedulable = row["review_status"] == "reviewed" and row["enabled"]
        lines.append(
            f"| {row['id']} | {row['review_status']} | "
            f"{'Y' if row['enabled'] else 'N'} | "
            f"{'Y' if schedulable else 'N'} |"
        )
    return "\n".join(lines) + "\n"


def set_channel_enabled(root: Path, channel_id: str, enabled: bool) -> Path:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before channel ops")
    target = next((obj for obj in objects if obj.object_id == channel_id), None)
    if target is None or target.object_type != "source_channel":
        raise ValueError(f"unknown source_channel {channel_id}")
    if enabled and target.metadata.get("review_status") != "reviewed":
        raise ValueError(
            f"cannot enable {channel_id}: must be reviewed before scheduling "
            "(RCP-v03-005 RP-4)"
        )
    if enabled and target.metadata.get("license_status") == "restricted":
        raise ValueError(
            f"cannot enable {channel_id}: license_status is restricted "
            "(RCP-v03-005 RP-6 — register but do not schedule)"
        )
    document = MarkdownDocument.read(target.path)
    document.set_metadata("enabled", enabled)
    return target.path


def channel_id_pattern() -> re.Pattern[str]:
    return re.compile(r"^CHN-[a-z0-9]+(?:-[a-z0-9]+)*$")
