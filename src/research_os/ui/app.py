"""Local, read-only FastAPI dashboard rendered directly from Markdown."""

from __future__ import annotations

import html
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
from research_os.services.indexing import (
    index_drift,
    render_project_indexes,
)
from research_os.services.ingestion import verify_source_assets
from research_os.services.metrics import (
    load_metrics_snapshot,
    render_metrics_comparison,
    research_metrics,
)
from research_os.services.ontology import render_impact
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
