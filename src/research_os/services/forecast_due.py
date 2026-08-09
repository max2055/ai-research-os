"""E-009 due / stale Forecast queries (Phase 5, WP-501).

Read-only queries over open Forecasts for the decision workflow and for future
alerts (E-018): which forecasts are ready to resolve, which are already
overdue, and which are simply open/unresolved. Pure functions over the loaded
object list plus a rendered status report for the CLI/dashboard.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.validation import validate_repository


def _open_forecasts(objects: list[ResearchObject]) -> list[ResearchObject]:
    return sorted(
        (
            obj
            for obj in objects
            if obj.object_type == "forecast"
            and obj.metadata.get("status") == "open"
        ),
        key=lambda obj: obj.metadata.get("resolution_date", ""),
    )


def due_forecasts(
    objects: list[ResearchObject], *, as_of: str
) -> list[ResearchObject]:
    """Open Forecasts whose resolution_date is on or before ``as_of``."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    return [
        obj
        for obj in _open_forecasts(objects)
        if str(obj.metadata.get("resolution_date", "")) <= as_of
    ]


def overdue_forecasts(
    objects: list[ResearchObject], *, as_of: str
) -> list[ResearchObject]:
    """Open Forecasts past their resolution_date (subset of due)."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    return [
        obj
        for obj in _open_forecasts(objects)
        if str(obj.metadata.get("resolution_date", "")) < as_of
    ]


def unresolved_forecasts(
    objects: list[ResearchObject], *, as_of: str
) -> list[ResearchObject]:
    """All open Forecasts, regardless of due date (not yet resolved/voided)."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    return _open_forecasts(objects)


def due_within(
    objects: list[ResearchObject], *, as_of: str, days: int
) -> list[ResearchObject]:
    """Open Forecasts resolving within ``days`` of ``as_of`` (alert window)."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    if days < 0:
        raise ValueError("days must be non-negative")
    as_of_date = date.fromisoformat(as_of)
    horizon_date = as_of_date.fromordinal(as_of_date.toordinal() + days)
    return [
        obj
        for obj in _open_forecasts(objects)
        if as_of_date.toordinal() <= date.fromisoformat(
            str(obj.metadata.get("resolution_date", ""))
        ).toordinal()
        <= horizon_date.toordinal()
    ]


def forecast_status_report(root: Path, *, as_of: str) -> dict[str, Any]:
    """Aggregate open/resolved counts plus the E-009 query results."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before forecast status queries"
        )
    forecasts = [obj for obj in objects if obj.object_type == "forecast"]
    open_ = [obj for obj in _open_forecasts(forecasts)]
    resolved = [
        obj
        for obj in forecasts
        if obj.metadata.get("status") in {"resolved", "void", "superseded"}
    ]
    return {
        "total": len(forecasts),
        "open": len(open_),
        "resolved": len(resolved),
        "due": len(due_forecasts(forecasts, as_of=as_of)),
        "overdue": len(overdue_forecasts(forecasts, as_of=as_of)),
        "unresolved": len(unresolved_forecasts(forecasts, as_of=as_of)),
        "due_rows": [
            {
                "id": obj.object_id,
                "title": obj.metadata.get("title", ""),
                "resolution_date": obj.metadata.get("resolution_date", ""),
            }
            for obj in due_forecasts(forecasts, as_of=as_of)
        ],
        "overdue_rows": [
            {
                "id": obj.object_id,
                "title": obj.metadata.get("title", ""),
                "resolution_date": obj.metadata.get("resolution_date", ""),
            }
            for obj in overdue_forecasts(forecasts, as_of=as_of)
        ],
    }


def render_forecast_rows(forecasts: list[ResearchObject]) -> str:
    """Render a forecast list as a markdown table (``forecast list``)."""
    lines = [
        "| ID | Status | Review | Resolution date | Question |",
        "|---|---|---|---|---|",
    ]
    for obj in sorted(
        forecasts,
        key=lambda obj: (obj.metadata.get("status", ""), obj.object_id),
    ):
        lines.append(
            f"| {obj.object_id} | {obj.metadata.get('status', '')} | "
            f"{obj.metadata.get('review_status', '')} | "
            f"{obj.metadata.get('resolution_date', '')} | "
            f"{str(obj.metadata.get('question', ''))[:60]} |"
        )
    if not forecasts:
        lines.append("| — | No matching forecasts | — | — | — |")
    return "\n".join(lines) + "\n"


def render_forecast_status(root: Path, *, as_of: str) -> str:
    """Render the status report as a markdown table for the CLI."""
    report = forecast_status_report(root, as_of=as_of)
    lines = [
        f"# Forecast status (as of {as_of})",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Total | {report['total']} |",
        f"| Open | {report['open']} |",
        f"| Resolved / void / superseded | {report['resolved']} |",
        f"| Due (resolution_date <= as_of) | {report['due']} |",
        f"| Overdue (resolution_date < as_of) | {report['overdue']} |",
        f"| Unresolved (open) | {report['unresolved']} |",
        "",
        "## Due now",
        "",
        "| ID | Title | Resolution date |",
        "|---|---|---|",
    ]
    for row in report["due_rows"]:
        lines.append(
            f"| {row['id']} | {row['title']} | {row['resolution_date']} |"
        )
    if not report["due_rows"]:
        lines.append("| — | No forecasts due | — |")
    return "\n".join(lines) + "\n"
