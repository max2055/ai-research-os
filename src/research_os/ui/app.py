"""Local, read-only FastAPI dashboard rendered directly from Markdown."""

from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)

from research_os.domain.models import ResearchObject
from research_os.services.actions import action_rows
from research_os.services.candidate_queue import promoted_rows, queue_rows, queue_show
from research_os.services.channels import channel_rows
from research_os.services.indexing import (
    index_drift,
    render_project_indexes,
)
from research_os.services.ingestion import verify_source_assets
from research_os.services.metrics import (
    load_metrics_snapshot,
    pipeline_metrics,
    render_metrics_comparison,
    research_metrics,
)
from research_os.services.ontology import render_impact
from research_os.services.pilot import pilot_status
from research_os.services.projects import objects_for_project
from research_os.services.validation import validate_repository

HTMX_URL = "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"


def esc(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return html.escape(", ".join(str(item) for item in value)) or "—"
    return html.escape(str(value))


def object_url(obj: ResearchObject) -> str:
    plural = {
        "source": "sources",
        "event": "events",
        "thesis": "theses",
        "company": "companies",
        "report": "reports",
        "action": "actions",
        "project": "projects",
    }.get(obj.object_type, "objects")
    return f"/{plural}/{obj.object_id}"


def object_link(obj: ResearchObject) -> str:
    return (
        f'<a href="{object_url(obj)}">{esc(obj.object_id)}</a>'
        f'<br><span class="muted">{esc(obj.metadata.get("title"))}</span>'
    )


def badge(value: Any, *, warning: bool = False, danger: bool = False) -> str:
    classes = "badge"
    if warning:
        classes += " warn"
    if danger:
        classes += " danger"
    return f'<span class="{classes}">{esc(value)}</span>'


def thesis_stale(obj: ResearchObject, *, as_of: date | None = None) -> bool:
    review_date = obj.metadata.get("review_date") or obj.metadata.get("updated_at")
    if not isinstance(review_date, str):
        return True
    try:
        parsed = date.fromisoformat(review_date)
    except ValueError:
        return True
    return parsed < (as_of or date.today()) - timedelta(days=90)


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(header)}</th>" for header in headers)
    if not rows:
        rows = [['<span class="empty">No records</span>'] + ["—"] * (len(headers) - 1)]
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def metadata_grid(obj: ResearchObject) -> str:
    hidden = {"title"}
    items = [(key, value) for key, value in obj.metadata.items() if key not in hidden]
    return (
        '<dl class="metadata">'
        + "".join(
            f"<div><dt>{esc(key)}</dt><dd>{esc(value)}</dd></div>"
            for key, value in items
        )
        + "</dl>"
    )


def shell(title: str, content: str, *, project_id: str | None = None) -> str:
    project_query = f"?project={project_id}" if project_id else ""
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>{esc(title)} · AI Research OS</title>
  <link rel="stylesheet" href="/static/styles.css">
  <script src="{HTMX_URL}" defer></script>
</head>
<body>
<header>
  <div class="shell">
    <div class="brand">
      <h1><a href="/" style="color:inherit;text-decoration:none">AI Research OS</a></h1>
      <span>Local · Read-only · Markdown-backed</span>
    </div>
    <nav aria-label="Primary">
      <a href="/{project_query}">Overview</a>
      <a href="/reviews{project_query}">Review queue</a>
      <a href="/metrics{project_query}">Metrics</a>
      <a href="/operations{project_query}">Operations</a>
      <a href="/pipeline{project_query}">Pipeline</a>
      <a href="/health{project_query}">Health</a>
    </nav>
  </div>
</header>
<main class="shell">{content}</main>
<footer class="shell">
  Live rebuild from Markdown at {esc(timestamp)}. No dashboard page edits research data.
</footer>
</body>
</html>"""


class DashboardRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def all(self) -> tuple[list[ResearchObject], list[Any]]:
        return validate_repository(self.root)

    def scoped(
        self,
        project_id: str | None,
    ) -> tuple[list[ResearchObject], list[Any], str]:
        objects, findings = self.all()
        projects = sorted(
            (obj for obj in objects if obj.object_type == "project"),
            key=lambda obj: obj.object_id,
        )
        selected = project_id or next(
            (
                obj.object_id
                for obj in projects
                if obj.metadata.get("status") == "active"
            ),
            projects[0].object_id if projects else "",
        )
        if not selected:
            raise ValueError("repository has no Project")
        scoped = objects_for_project(objects, selected)
        paths = {obj.path for obj in scoped}
        scoped_findings = [finding for finding in findings if finding.path in paths]
        return scoped, scoped_findings, selected

    def one(self, object_id: str) -> ResearchObject:
        objects, _ = self.all()
        item = next((obj for obj in objects if obj.object_id == object_id), None)
        if item is None:
            raise KeyError(object_id)
        return item


def _project_overview(repo: DashboardRepository, project_id: str | None) -> str:
    objects, findings, selected = repo.scoped(project_id)
    by_type = {
        object_type: [obj for obj in objects if obj.object_type == object_type]
        for object_type in ("source", "event", "thesis", "report", "action")
    }
    project = next(obj for obj in objects if obj.object_id == selected)
    pending = [obj for obj in objects if obj.metadata.get("review_status") == "pending"]
    open_actions = [
        obj
        for obj in by_type["action"]
        if obj.metadata.get("status") in {"open", "in_progress"}
    ]
    reports = sorted(
        by_type["report"],
        key=lambda obj: str(obj.metadata.get("updated_at", "")),
        reverse=True,
    )
    hero = f"""
<section class="hero">
  <div>
    <div class="eyebrow">{esc(selected)} · {esc(project.metadata.get("status"))}</div>
    <h2>{esc(project.metadata.get("title"))}</h2>
    <p>{esc(project.metadata.get("research_question"))}</p>
  </div>
  <div>
    <div class="eyebrow">Next review</div>
    <h2>{esc(project.metadata.get("next_review_date"))}</h2>
    <p class="muted">{esc(project.metadata.get("review_cadence"))} cadence · owner {esc(project.metadata.get("owner"))}</p>
  </div>
</section>
<section class="metrics">
  <div class="metric"><strong>{len(by_type["source"])}</strong><span>Sources</span></div>
  <div class="metric"><strong>{len(by_type["event"])}</strong><span>Events</span></div>
  <div class="metric"><strong>{len(pending)}</strong><span>Pending reviews</span></div>
  <div class="metric"><strong>{len(open_actions)}</strong><span>Open actions</span></div>
</section>"""
    thesis_rows = [
        [
            object_link(obj),
            esc(obj.metadata.get("confidence")),
            esc(len(obj.metadata.get("supporting_evidence", []))),
            esc(len(obj.metadata.get("contradicting_evidence", []))),
            badge(obj.metadata.get("review_status")),
            badge(
                "stale" if thesis_stale(obj) else "current",
                warning=thesis_stale(obj),
            ),
        ]
        for obj in by_type["thesis"]
    ]
    action_table = [
        [
            object_link(obj),
            esc(obj.metadata.get("owner")),
            esc(obj.metadata.get("due_date")),
            badge(
                obj.metadata.get("status"),
                warning=str(obj.metadata.get("due_date")) < date.today().isoformat(),
            ),
        ]
        for obj in open_actions
    ]
    report_rows = [
        [
            object_link(obj),
            esc(obj.metadata.get("version")),
            badge(obj.metadata.get("status")),
            esc(obj.metadata.get("updated_at")),
        ]
        for obj in reports[:8]
    ]
    content = (
        hero
        + f"""
<section class="grid">
  <div class="panel">
    <h3>Thesis health</h3>
    {table(["Thesis", "Confidence", "Support", "Contradict", "Review", "Freshness"], thesis_rows)}
  </div>
  <div class="panel">
    <h3>Open actions</h3>
    {table(["Action", "Owner", "Due", "Status"], action_table)}
  </div>
  <div class="panel full">
    <h3>Reports</h3>
    {table(["Report", "Version", "Status", "Updated"], report_rows)}
  </div>
  <div class="panel full">
    <h3>System signal</h3>
    <p>{len([item for item in findings if item.level == "error"])} errors ·
    {len([item for item in findings if item.level == "warning"])} warnings.
    <a href="/health?project={esc(selected)}">Inspect health</a>.</p>
  </div>
</section>"""
    )
    return shell(str(project.metadata.get("title")), content, project_id=selected)


def _review_rows(
    repo: DashboardRepository,
    project_id: str | None,
    object_type: str | None,
    review_status: str,
) -> tuple[list[list[str]], str]:
    objects, _, selected = repo.scoped(project_id)
    rows = [
        [
            object_link(obj),
            esc(obj.object_type),
            badge(obj.metadata.get("review_status"), warning=True),
            esc(obj.metadata.get("updated_at")),
        ]
        for obj in sorted(
            (
                item
                for item in objects
                if item.metadata.get("review_status") == review_status
                and (object_type is None or item.object_type == object_type)
            ),
            key=lambda item: (item.object_type, item.object_id),
        )
    ]
    return rows, selected


def _review_queue(
    repo: DashboardRepository,
    project_id: str | None,
    object_type: str | None,
    review_status: str,
) -> str:
    rows, selected = _review_rows(
        repo,
        project_id,
        object_type,
        review_status,
    )
    type_options = "".join(
        f'<option value="{value}"'
        f"{' selected' if object_type == value else ''}>{value or 'all'}</option>"
        for value in ("", "source", "event", "thesis", "company", "report")
    )
    status_options = "".join(
        f'<option value="{value}"'
        f"{' selected' if review_status == value else ''}>{value}</option>"
        for value in ("pending", "reviewed", "rejected", "superseded")
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>Review queue</h2>
<p>Read-only queue. Apply decisions through the explicit review command.</p>
</div><div><div class="eyebrow">{esc(review_status)}</div><h2>{len(rows)}</h2>
<p class="muted">No state is changed from this page.</p></div></section>
<section class="panel" style="margin-bottom:1rem">
<form method="get" action="/reviews">
<input type="hidden" name="project" value="{esc(selected)}">
<label>Type <select name="type">{type_options}</select></label>
<label style="margin-left:1rem">Status
<select name="status">{status_options}</select></label>
<button type="submit">Filter</button>
</form></section>
<section class="panel" id="review-table"
  hx-get="/fragments/reviews?project={esc(selected)}&type={esc(object_type or "")}&status={esc(review_status)}"
  hx-trigger="refresh">
{table(["Object", "Type", "Status", "Updated"], rows)}</section>"""
    return shell("Review queue", content, project_id=selected)


def _source_page(repo: DashboardRepository, source_id: str) -> str:
    source = repo.one(source_id)
    if source.object_type != "source":
        raise KeyError(source_id)
    objects, _ = repo.all()
    events = [
        obj
        for obj in objects
        if obj.object_type == "event"
        and source_id in obj.metadata.get("source_ids", [])
    ]
    verification = next(
        (
            result
            for result in verify_source_assets(repo.root)
            if result.source_id == source_id
        ),
        None,
    )
    rows = [
        [
            object_link(event),
            esc(event.metadata.get("event_date")),
            badge(event.metadata.get("review_status")),
        ]
        for event in events
    ]
    asset_rows = [
        [
            f'<a href="/source-assets/{esc(source_id)}/{index}">{esc(path)}</a>',
            esc("extracted" if str(path).endswith(".extracted.txt") else "archived"),
        ]
        for index, path in enumerate(source.metadata.get("asset_paths", []))
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">Source provenance</div>
<h2>{esc(source.metadata.get("title"))}</h2>
<p>{esc(source.metadata.get("publisher"))}</p></div>
<div><div class="eyebrow">Asset integrity</div>
<h2>{badge(verification.status if verification else "unknown", danger=bool(verification and verification.status not in {"ok", "registered"}))}</h2>
<p class="muted">{esc(verification.message if verification else "")}</p></div></section>
<section class="panel">{metadata_grid(source)}</section>
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>Archived versions & extracts</h3>
{table(["Asset", "Kind"], asset_rows)}</div>
<div class="panel"><h3>Linked Events</h3>{table(["Event", "Date", "Review"], rows)}</div>
<div class="panel"><h3>Research note</h3><pre>{esc(source.body)}</pre></div>
</section>"""
    return shell(source_id, content)


def _thesis_page(repo: DashboardRepository, thesis_id: str) -> str:
    thesis = repo.one(thesis_id)
    if thesis.object_type != "thesis":
        raise KeyError(thesis_id)
    objects, _ = repo.all()
    by_id = {obj.object_id: obj for obj in objects}
    support = [
        by_id[str(value)]
        for value in thesis.metadata.get("supporting_evidence", [])
        if str(value) in by_id
    ]
    contradict = [
        by_id[str(value)]
        for value in thesis.metadata.get("contradicting_evidence", [])
        if str(value) in by_id
    ]
    review_date = thesis.metadata.get("review_date") or thesis.metadata.get(
        "updated_at"
    )
    stale = thesis_stale(thesis)
    evidence_rows = [
        [object_link(item), badge("supporting"), esc(item.metadata.get("event_date"))]
        for item in support
    ] + [
        [
            object_link(item),
            badge("contradicting", warning=True),
            esc(item.metadata.get("event_date")),
        ]
        for item in contradict
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">Thesis health</div><h2>{esc(thesis.metadata.get("title"))}</h2>
<p>{badge("stale", warning=True) if stale else badge("current")}</p></div>
<div><div class="eyebrow">Confidence</div>
<h2>{esc(thesis.metadata.get("confidence"))}</h2>
<p class="muted">Last review {esc(review_date)}</p></div></section>
<section class="grid">
<div class="panel"><h3>Evidence balance</h3>
{table(["Event", "Relationship", "Date"], evidence_rows)}</div>
<div class="panel"><h3>Thesis note</h3><pre>{esc(thesis.body)}</pre></div>
</section>"""
    return shell(thesis_id, content)


def _generic_page(repo: DashboardRepository, object_id: str) -> str:
    obj = repo.one(object_id)
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(obj.object_type)}</div>
<h2>{esc(obj.metadata.get("title"))}</h2>
<p>{badge(obj.metadata.get("review_status") or obj.metadata.get("status"))}</p>
</div><div><div class="eyebrow">Permanent ID</div><h2>{esc(obj.object_id)}</h2>
<p><a href="/impact/{esc(obj.object_id)}">Explore relationships</a></p>
</div></section><section class="panel">{metadata_grid(obj)}
<pre>{esc(obj.body)}</pre></section>"""
    return shell(object_id, content)


def _metrics_page(repo: DashboardRepository, project_id: str | None) -> str:
    _, _, selected = repo.scoped(project_id)
    metrics = research_metrics(repo.root, date.today().isoformat(), selected)
    counts = metrics["object_counts"]
    baseline_paths = sorted(
        (repo.root / "05_Research" / "Reviews" / "Snapshots").glob(
            f"METRICS-{selected}-*.json"
        )
    )
    if not baseline_paths:
        baseline_paths = sorted(
            (repo.root / "05_Research" / "Reviews" / "Snapshots").glob("METRICS-*.json")
        )
    comparison = "No metrics snapshot is available."
    baseline_label = "none"
    if baseline_paths:
        baseline = load_metrics_snapshot(baseline_paths[-1])
        comparison = render_metrics_comparison(baseline, metrics)
        baseline_label = str(baseline.get("as_of"))
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>Metrics & change</h2>
<p>Current Markdown state compared with snapshot {esc(baseline_label)}.</p>
</div><div><div class="eyebrow">Review queue</div>
<h2>{esc(metrics["review_queue_total"])}</h2>
<p class="muted">Current, not cached.</p></div></section>
<section class="metrics">
<div class="metric"><strong>{counts["source"]["total"]}</strong><span>Sources</span></div>
<div class="metric"><strong>{counts["event"]["total"]}</strong><span>Events</span></div>
<div class="metric"><strong>{metrics["source_quality"]["archived"]}</strong><span>Archived Sources</span></div>
<div class="metric"><strong>{metrics["thesis_health"]["without_contradicting"]}</strong><span>Theses lacking counterevidence</span></div>
</section><section class="panel"><pre>{esc(comparison)}</pre></section>"""
    return shell("Metrics", content, project_id=selected)


def _kv_table(rows: list[list[str]]) -> str:
    return table(["Metric", "Value"], rows)


def _pipeline_overview(repo: DashboardRepository) -> str:
    status = pilot_status(repo.root)
    gate = status["gate"]
    candidates = status["candidates"]
    content = f"""<section class="hero"><div>
<div class="eyebrow">Pipeline</div><h2>Machine in motion</h2>
<p>Discovery → triage → Sources. Read-only view; decisions stay in the CLI.</p>
</div><div><div class="eyebrow">Pilot window</div>
<h2>{esc(gate['days'])}/{esc(status['target_days'])}</h2>
<p class="muted">since {esc(status['since'])}</p></div></section>
<section class="metrics">
<div class="metric"><strong>{esc(candidates['discovered_since'])}</strong><span>Discovered</span></div>
<div class="metric"><strong>{esc(candidates['promoted'])}</strong><span>Promoted</span></div>
<div class="metric"><strong>{esc(candidates['dismissed'])}</strong><span>Dismissed</span></div>
<div class="metric"><strong>{esc(gate['channels'])}</strong><span>Channels ready</span></div>
</section>
<section class="grid">
<div class="panel"><h3>Candidate queue</h3>
<p>New candidates awaiting triage, highest priority first.</p>
<p><a href="/pipeline/queue">Open queue →</a></p></div>
<div class="panel"><h3>Promoted Sources</h3>
<p>Candidates that became authoritative Sources.</p>
<p><a href="/pipeline/sources">View sources →</a></p></div>
<div class="panel"><h3>Channels & metrics</h3>
<p>Channel registry and live pipeline health.</p>
<p><a href="/pipeline/channels">Open channels →</a></p></div>
</section>
<p class="muted">Candidate data is non-authoritative and rebuildable; authoritative facts live in the repository.</p>"""
    return shell("Pipeline", content)


def _pipeline_sources(repo: DashboardRepository) -> str:
    rows = promoted_rows(repo.root)
    body_rows = [
        [
            f'<a href="/sources/{esc(row["promoted_source_id"])}">{esc(row["promoted_source_id"])}</a>'
            f'<br><span class="muted">{esc(row["title"])}</span>',
            esc(row["channel_id"]),
            esc(row["publisher"]) or "—",
            esc(row["entity_id"]) or "—",
            esc(row["discovered_at"]),
        ]
        for row in rows
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">Pipeline → Sources</div><h2>Promoted Sources</h2>
<p>Candidates that became authoritative Sources, newest first.</p>
</div><div><div class="eyebrow">Promoted</div><h2>{len(rows)}</h2>
<p class="muted">linking back to their originating channel</p></div></section>
<section class="panel">{table(["Source", "Channel", "Publisher", "Entity", "Discovered"], body_rows)}</section>"""
    return shell("Pipeline Sources", content)


def _candidate_facts(detail: dict[str, Any]) -> str:
    priority = (
        f"{detail['priority_score']:.3f}"
        if detail.get("priority_score") is not None
        else "—"
    )
    items = [
        ("Status", detail.get("status")),
        ("Channel", detail.get("channel_id")),
        ("Discovered", detail.get("discovered_at")),
        ("Published (proposal)", detail.get("published_at_proposal")),
        ("Publisher", detail.get("publisher")),
        ("URL", detail.get("canonical_url")),
        ("Duplicate cluster", detail.get("duplicate_cluster_id")),
        ("Priority", priority),
        ("Model", detail.get("model_version")),
    ]
    return '<dl class="metadata">' + "".join(
        f"<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>"
        for label, value in items
    ) + "</dl>"


def _pipeline_candidate(repo: DashboardRepository, candidate_id: str) -> str:
    detail = queue_show(repo.root, candidate_id)
    if detail is None:
        raise KeyError(candidate_id)
    entity = detail.get("entity_proposals") or {}
    sector = detail.get("sector_proposals") or {}
    reasons = detail.get("reason_codes") or []
    actions = detail.get("actions") or []
    reason_rows = [[esc(code)] for code in reasons] if reasons else []
    action_rows_html = [
        [
            esc(action.get("acted_at")),
            badge(action.get("action")),
            esc(action.get("actor")),
            esc(action.get("reason")),
        ]
        for action in actions
    ]
    priority = (
        f"{detail['priority_score']:.3f}"
        if detail.get("priority_score") is not None
        else "—"
    )
    hero = f"""<section class="hero"><div>
<div class="eyebrow">Candidate {esc(candidate_id)}</div><h2>{esc(detail.get("title"))}</h2>
<p>{badge(detail.get("status"))} · {esc(detail.get("channel_id"))}</p></div>
<div><div class="eyebrow">Priority</div><h2>{esc(priority)}</h2>
<p class="muted">{esc(detail.get("model_version")) or "heuristic"}</p></div></section>"""
    panels = f"""{_candidate_facts(detail)}
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>Entity proposal</h3><pre>{esc(json.dumps(entity, ensure_ascii=False, indent=2))}</pre></div>
<div class="panel"><h3>Sector proposal</h3><pre>{esc(json.dumps(sector, ensure_ascii=False, indent=2))}</pre></div>
</section>
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>Reason codes</h3>
{table(["Code"], reason_rows)}</div>
<div class="panel"><h3>Action history</h3>
{table(["Acted at", "Action", "Actor", "Reason"], action_rows_html)}</div>
</section>"""
    return shell(candidate_id, hero + panels)


def _pipeline_queue(
    repo: DashboardRepository,
    status: str,
    channel: str | None,
    min_priority: float | None,
    limit: int,
) -> str:
    rows = queue_rows(
        repo.root,
        status=status or "new",
        channel_id=channel or None,
        min_priority=min_priority,
        limit=limit,
    )
    body_rows = [
        [
            (
                f"{row['priority_score']:.3f}"
                if row["priority_score"] is not None
                else "—"
            ),
            badge(row["status"]),
            esc(row["entity_id"] or row["entity_status"]),
            esc(len(row["sector_ids"])),
            esc(row["channel_id"]),
            f'<a href="/pipeline/queue/{esc(row["candidate_id"])}">{esc(row["title"])}</a>',
        ]
        for row in rows
    ]
    status_options = "".join(
        f'<option value="{value}"'
        f"{' selected' if status == value else ''}>{value}</option>"
        for value in ("new", "triaged", "promoted", "dismissed", "expired", "failed")
    )
    channel_value = esc(channel or "")
    min_value = esc(min_priority if min_priority is not None else "")
    content = f"""<section class="hero"><div>
<div class="eyebrow">Pipeline → Queue</div><h2>Candidate queue</h2>
<p>Read-only triage list. Decisions stay in the CLI.</p>
</div><div><div class="eyebrow">{esc(status)}</div><h2>{len(rows)}</h2>
<p class="muted">highest priority first</p></div></section>
<section class="panel" style="margin-bottom:1rem">
<form method="get" action="/pipeline/queue">
<label>Status <select name="status">{status_options}</select></label>
<label style="margin-left:1rem">Channel <input name="channel" value="{channel_value}"></label>
<label style="margin-left:1rem">Min priority <input type="number" step="0.01" min="0" max="1" name="min_priority" value="{min_value}"></label>
<label style="margin-left:1rem">Limit <input type="number" min="1" max="200" name="limit" value="{esc(limit)}"></label>
<button type="submit">Filter</button>
</form></section>
<section class="panel">{table(["Priority", "Status", "Entity", "Sectors", "Channel", "Title"], body_rows)}</section>"""
    return shell("Pipeline Queue", content)


def _pipeline_channels(repo: DashboardRepository) -> str:
    channels = channel_rows(repo.root)
    channel_body = [
        [
            esc(row["id"]),
            esc(row["name"]),
            esc(row["channel_type"]),
            esc(row["license_status"]),
            badge(row["review_status"]),
            badge("enabled" if row["enabled"] else "disabled", warning=not row["enabled"]),
            badge(
                "yes"
                if (row["review_status"] == "reviewed" and row["enabled"])
                else "no",
                warning=not (row["review_status"] == "reviewed" and row["enabled"]),
            ),
        ]
        for row in channels
    ]
    metrics = pipeline_metrics(repo.root)
    discovered = metrics["discovered"]
    duplicate = metrics["duplicate"]
    discovery = metrics["discovery"]
    triage = metrics["triage"]
    coverage = metrics["coverage"]
    stale = metrics["stale_channels"]
    latency = discovery["median_latency_seconds"]
    latency_text = f"{latency}s" if latency is not None else "—"
    discovery_rows = [
        ["Runs", esc(discovery["runs"])],
        ["Succeeded / failed", f"{esc(discovery['succeeded'])} / {esc(discovery['failed'])}"],
        ["Failure rate", f"{discovery['failure_rate']:.0%}"],
        ["Median latency", esc(latency_text)],
        ["HTTP / parse / retries", f"{esc(discovery['http_errors'])} / {esc(discovery['parse_errors'])} / {esc(discovery['retries'])}"],
        ["Cost estimate", esc(discovery["cost_estimate"])],
    ]
    dismiss_text = ", ".join(
        f"{reason} ({count})" for reason, count in triage["top_dismiss_reasons"]
    ) or "—"
    triage_rows = [
        ["Total discovered", esc(triage["total"])],
        ["Promoted / dismissed", f"{esc(triage['promoted'])} / {esc(triage['dismissed'])}"],
        ["Promoted rate", f"{triage['promoted_rate']:.0%}"],
        ["Dismissed rate", f"{triage['dismissed_rate']:.0%}"],
        ["Median conversion hours", esc(triage["median_conversion_hours"])],
        ["Top dismiss reasons", esc(dismiss_text)],
    ]
    coverage_rows = [
        ["Matched entities", esc(coverage["matched_entities"])],
        ["Core matched", esc(coverage["core_matched"])],
        ["Core rate", f"{coverage['core_rate']:.0%}"],
    ]
    stale_text = ", ".join(stale["stale"]) or "—"
    never_text = ", ".join(stale["never_run"]) or "—"
    content = f"""<section class="hero"><div>
<div class="eyebrow">Pipeline → Channels & metrics</div><h2>Channels & metrics</h2>
<p>Channel registry and live pipeline health.</p>
</div><div><div class="eyebrow">As of {esc(metrics["as_of"])}</div>
<h2>{esc(discovered["total"])}</h2>
<p class="muted">recomputed on every request</p></div></section>
<section class="panel"><h3>Channels ({len(channels)})</h3>
{table(["ID", "Name", "Type", "License", "Review", "Enabled", "Schedulable"], channel_body)}</section>
<section class="metrics" style="margin-top:1rem">
<div class="metric"><strong>{esc(discovered["total"])}</strong><span>Discovered total</span></div>
<div class="metric"><strong>{esc(discovered["today"])}</strong><span>Discovered today</span></div>
<div class="metric"><strong>{duplicate["rate"]:.0%}</strong><span>Duplicate rate</span></div>
<div class="metric"><strong>{discovery["failure_rate"]:.0%}</strong><span>Failure rate</span></div>
</section>
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>Discovery</h3>{_kv_table(discovery_rows)}</div>
<div class="panel"><h3>Triage yield</h3>{_kv_table(triage_rows)}</div>
<div class="panel"><h3>Core coverage</h3>{_kv_table(coverage_rows)}</div>
<div class="panel"><h3>Channel freshness</h3>
<p><strong>Stale:</strong> {esc(stale_text)}</p>
<p><strong>Never run:</strong> {esc(never_text)}</p></div>
</section>"""
    return shell("Pipeline Channels", content)


def _operations_page(repo: DashboardRepository, project_id: str | None) -> str:
    objects, _, selected = repo.scoped(project_id)
    overdue = action_rows(
        repo.root,
        project_id=selected,
        overdue_as_of=date.today().isoformat(),
    )
    due_projects = [
        obj
        for obj in objects
        if obj.object_type == "project"
        and str(obj.metadata.get("next_review_date")) <= date.today().isoformat()
    ]
    open_rows = [
        [
            object_link(obj),
            esc(obj.metadata.get("owner")),
            esc(obj.metadata.get("due_date")),
            badge(obj.metadata.get("status"), warning=True),
        ]
        for obj in overdue
    ]
    due_rows = [
        [
            object_link(obj),
            esc(obj.metadata.get("review_cadence")),
            esc(obj.metadata.get("next_review_date")),
        ]
        for obj in due_projects
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>Operations</h2>
<p>Overdue actions and due research reviews from structured metadata.</p>
</div><div><div class="eyebrow">Overdue actions</div><h2>{len(overdue)}</h2>
<p class="muted">As of {date.today().isoformat()}</p></div></section>
<section class="grid">
<div class="panel"><h3>Pipeline health</h3>
<p><a href="/pipeline">Open Pipeline dashboard →</a></p>
<p class="muted">Candidate pipeline / channels / metrics now live on the Pipeline page.</p></div>
<div class="panel"><h3>Overdue actions</h3>
{table(["Action", "Owner", "Due", "Status"], open_rows)}</div>
<div class="panel"><h3>Review due</h3>
{table(["Project", "Cadence", "Next review"], due_rows)}</div>
</section>"""
    return shell("Operations", content, project_id=selected)


def _health_page(repo: DashboardRepository, project_id: str | None) -> str:
    objects, findings, selected = repo.scoped(project_id)
    rendered = render_project_indexes(objects, selected)
    drift = index_drift(repo.root, rendered)
    asset_failures = [
        result
        for result in verify_source_assets(repo.root)
        if result.status in {"missing", "invalid", "hash_mismatch"}
    ]
    job_failures = [
        obj
        for obj in objects
        if obj.object_type == "job" and obj.metadata.get("status") == "failed"
    ]
    finding_rows = [
        [
            badge(
                finding.level,
                warning=finding.level == "warning",
                danger=finding.level == "error",
            ),
            esc(finding.code),
            esc(finding.path.relative_to(repo.root)),
            esc(finding.message),
        ]
        for finding in findings
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>System health</h2>
<p>Every value is rebuilt from repository files on request.</p></div>
<div><div class="eyebrow">Status</div>
<h2>{badge("healthy") if not drift and not asset_failures and not job_failures else badge("attention", warning=True)}</h2>
<p class="muted">{len(drift)} drift · {len(asset_failures)} asset failures ·
{len(job_failures)} failed jobs</p></div></section>
<section class="panel"><h3>Validation findings</h3>
{table(["Level", "Code", "Path", "Message"], finding_rows)}</section>
<section class="panel" style="margin-top:1rem"><h3>Failed jobs</h3>
{table(["Job", "Name", "Message"], [[object_link(job), esc(job.metadata.get("job_name")), esc(job.metadata.get("message"))] for job in job_failures])}
</section>"""
    return shell("Health", content, project_id=selected)


def create_app(root: Path) -> FastAPI:
    repo = DashboardRepository(root)
    app = FastAPI(
        title="AI Research OS",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/static/styles.css", response_class=PlainTextResponse)
    def styles() -> PlainTextResponse:
        content = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
        return PlainTextResponse(content, media_type="text/css")

    @app.get("/", response_class=HTMLResponse)
    def overview(project: str | None = Query(default=None)) -> HTMLResponse:
        try:
            return HTMLResponse(_project_overview(repo, project))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/reviews", response_class=HTMLResponse)
    def reviews(
        project: str | None = Query(default=None),
        object_type: str | None = Query(default=None, alias="type"),
        review_status: str = Query(default="pending", alias="status"),
    ) -> HTMLResponse:
        return HTMLResponse(
            _review_queue(
                repo,
                project,
                object_type or None,
                review_status,
            )
        )

    @app.get("/fragments/reviews", response_class=HTMLResponse)
    def review_fragment(
        project: str | None = Query(default=None),
        object_type: str | None = Query(default=None, alias="type"),
        review_status: str = Query(default="pending", alias="status"),
    ) -> HTMLResponse:
        rows, _ = _review_rows(
            repo,
            project,
            object_type or None,
            review_status,
        )
        return HTMLResponse(table(["Object", "Type", "Status", "Updated"], rows))

    @app.get("/metrics", response_class=HTMLResponse)
    def metrics(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_metrics_page(repo, project))

    @app.get("/operations", response_class=HTMLResponse)
    def operations(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_operations_page(repo, project))

    @app.get("/pipeline", response_class=HTMLResponse)
    def pipeline() -> HTMLResponse:
        return HTMLResponse(_pipeline_overview(repo))

    @app.get("/pipeline/sources", response_class=HTMLResponse)
    def pipeline_sources() -> HTMLResponse:
        return HTMLResponse(_pipeline_sources(repo))

    @app.get("/pipeline/queue", response_class=HTMLResponse)
    def pipeline_queue(
        status: str = Query(default="new"),
        channel: str | None = Query(default=None),
        min_priority: float | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> HTMLResponse:
        return HTMLResponse(
            _pipeline_queue(repo, status, channel, min_priority, limit)
        )

    @app.get("/pipeline/queue/{candidate_id}", response_class=HTMLResponse)
    def pipeline_candidate(candidate_id: str) -> HTMLResponse:
        try:
            return HTMLResponse(_pipeline_candidate(repo, candidate_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=candidate_id) from exc

    @app.get("/pipeline/channels", response_class=HTMLResponse)
    def pipeline_channels() -> HTMLResponse:
        return HTMLResponse(_pipeline_channels(repo))

    @app.get("/health", response_class=HTMLResponse)
    def health(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_health_page(repo, project))

    @app.get("/sources/{source_id}", response_class=HTMLResponse)
    def source(source_id: str) -> HTMLResponse:
        try:
            return HTMLResponse(_source_page(repo, source_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=source_id) from exc

    @app.get("/source-assets/{source_id}/{asset_index}")
    def source_asset(source_id: str, asset_index: int) -> FileResponse:
        try:
            source_obj = repo.one(source_id)
            if source_obj.object_type != "source":
                raise KeyError(source_id)
            paths = [
                Path(str(value)) for value in source_obj.metadata.get("asset_paths", [])
            ]
            relative = paths[asset_index]
            target = (repo.root / relative).resolve()
            if not target.is_relative_to(repo.root) or not target.is_file():
                raise KeyError(str(relative))
            return FileResponse(target, filename=target.name)
        except (IndexError, KeyError) as exc:
            raise HTTPException(status_code=404, detail="asset not found") from exc

    @app.get("/theses/{thesis_id}", response_class=HTMLResponse)
    def thesis(thesis_id: str) -> HTMLResponse:
        try:
            return HTMLResponse(_thesis_page(repo, thesis_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=thesis_id) from exc

    def generic_detail(object_id: str) -> HTMLResponse:
        try:
            return HTMLResponse(_generic_page(repo, object_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=object_id) from exc

    for prefix in ("events", "companies", "reports", "actions", "projects"):
        app.add_api_route(
            f"/{prefix}/{{object_id}}",
            generic_detail,
            methods=["GET"],
            response_class=HTMLResponse,
            name=f"{prefix}-detail",
        )

    @app.get("/impact/{object_id}", response_class=HTMLResponse)
    def impact(
        object_id: str, depth: int = Query(default=2, ge=1, le=3)
    ) -> HTMLResponse:
        try:
            body = render_impact(repo.root, object_id, depth)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        content = f'<section class="panel"><h2>Impact graph</h2><pre>{esc(body)}</pre></section>'
        return HTMLResponse(shell(f"Impact {object_id}", content))

    @app.get("/api/state", response_class=JSONResponse)
    def state(project: str | None = Query(default=None)) -> JSONResponse:
        objects, findings, selected = repo.scoped(project)
        return JSONResponse(
            {
                "project_id": selected,
                "objects": [
                    {
                        "id": obj.object_id,
                        "type": obj.object_type,
                        "title": obj.metadata.get("title"),
                        "review_status": obj.metadata.get("review_status"),
                    }
                    for obj in objects
                ],
                "findings": [
                    {"level": item.level, "code": item.code, "message": item.message}
                    for item in findings
                ],
            }
        )

    return app


def run_ui(
    root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Dashboard v1 only binds to a loopback host")
    import uvicorn

    uvicorn.run(
        create_app(root),
        host=host,
        port=port,
        log_level="info",
    )
