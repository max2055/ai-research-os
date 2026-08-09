"""E-018 decision alerts (Phase 5, WP-512).

A scheduled alert over the decision workflow: which open Forecasts are due /
overdue for resolution, and which active Recommendations are stale or monitor
catalysts/falsifiers. Deterministic, read-only; the Catalyst/falsifier monitor
is evidence heuristics over referenced Forecasts and freshness — it never
claims a catalyst happened without a reviewed Event (that needs the future
event-matching work).

The ``forecast-alerts`` job (jobs.py) runs this and records the alert report as
a JOB Run audit record.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_os.domain.policies import is_iso_date
from research_os.services.forecast_due import due_forecasts, overdue_forecasts
from research_os.services.validation import validate_repository


def decision_alerts(root: Path, *, as_of: str) -> dict[str, Any]:
    """Collect due/overdue forecasts and active-recommendation alerts."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before decision alerts")
    forecasts = [o for o in objects if o.object_type == "forecast"]
    recs = [o for o in objects if o.object_type == "recommendation"]

    due = due_forecasts(forecasts, as_of=as_of)
    overdue_ids = {o.object_id for o in overdue_forecasts(forecasts, as_of=as_of)}
    active_recs = [o for o in recs if o.metadata.get("status") == "active"]

    rec_rows: list[dict[str, Any]] = []
    for rec in active_recs:
        freshness_date = str(rec.metadata.get("freshness_date", ""))
        fresh = True
        if is_iso_date(freshness_date):
            from datetime import date

            age = (date.fromisoformat(as_of) - date.fromisoformat(freshness_date)).days
            fresh = age <= 90
        rec_rows.append(
            {
                "id": rec.object_id,
                "company_id": rec.metadata.get("company_id", ""),
                "posture": rec.metadata.get("research_posture", ""),
                "freshness_date": freshness_date,
                "fresh": fresh,
                "catalysts": list(rec.metadata.get("catalysts", []) or []),
                "falsifiers": list(
                    rec.metadata.get("falsification_conditions", []) or []
                ),
            }
        )

    alerts: list[str] = []
    for forecast in due:
        label = "逾期" if forecast.object_id in overdue_ids else "到期"
        alerts.append(
            f"{forecast.object_id} {label} "
            f"({forecast.metadata.get('resolution_date')}) — 需 Resolution 解析"
        )
    for row in rec_rows:
        if not row["fresh"]:
            alerts.append(
                f"{row['id']} 已过期（freshness {row['freshness_date']}）— 需复核或关闭"
            )
    for row in rec_rows:
        if row["catalysts"] or row["falsifiers"]:
            alerts.append(
                f"{row['id']} 催化剂/证伪条件待监控："
                f"{len(row['catalysts'])} 催化剂 · {len(row['falsifiers'])} 证伪"
            )
    if not alerts:
        alerts.append("无到期 Forecast / 无过期 Recommendation 告警。")

    return {
        "as_of": as_of,
        "due_count": len(due),
        "overdue_count": len(overdue_ids),
        "active_recommendations": len(rec_rows),
        "due_rows": [
            {
                "id": o.object_id,
                "title": o.metadata.get("title", ""),
                "resolution_date": o.metadata.get("resolution_date", ""),
                "overdue": o.object_id in overdue_ids,
            }
            for o in due
        ],
        "recommendation_rows": rec_rows,
        "alerts": alerts,
    }


def render_decision_alerts(report: dict[str, Any]) -> str:
    lines = [
        f"# Decision alerts (as of {report['as_of']})",
        "",
        f"- Due forecasts: {report['due_count']}",
        f"- Overdue forecasts: {report['overdue_count']}",
        f"- Active recommendations: {report['active_recommendations']}",
        "",
        "## Alerts",
        "",
    ]
    for alert in report["alerts"]:
        lines.append(f"- {alert}")
    lines += ["", "## Due forecasts", ""]
    for row in report["due_rows"]:
        mark = "OVERDUE" if row["overdue"] else "due"
        lines.append(
            f"- {row['id']} [{mark}] {row['title']} "
            f"(resolution {row['resolution_date']})"
        )
    if not report["due_rows"]:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"
