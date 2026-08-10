"""Local, read-only FastAPI dashboard rendered directly from Markdown."""

from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)

from research_os.domain.models import ResearchObject
from research_os.llm import llm_adapter, llm_config, model_fetch, provider_catalog
from research_os.services.analysis_compare import compare_runs
from research_os.services.analysis_evaluator import (
    evaluate_run,
    render_evaluation_packet,
)
from research_os.services.analysis_registry import (
    mode_metadata,
    mode_slug,
    mode_version,
    require_runnable,
)
from research_os.services.candidate_queue import promoted_rows, queue_rows, queue_show
from research_os.services.channels import channel_rows
from research_os.services.ingestion import verify_source_assets
from research_os.services.metrics import (
    load_metrics_snapshot,
    pipeline_metrics,
    render_metrics_comparison,
    research_metrics,
)
from research_os.services.mode_metrics import mode_metrics
from research_os.services.ontology import render_impact
from research_os.services.operations_health import health_snapshot, operations_snapshot
from research_os.services.pilot import pilot_status
from research_os.services.projects import objects_for_project
from research_os.services.read_model import (
    analysis_workspace_snapshot,
    company_snapshot,
    decision_desk_snapshot,
    impact_explorer_snapshot,
    industry_home_snapshot,
    sector_snapshot,
)
from research_os.services.review_cadence import current_next_review_date
from research_os.services.validation import validate_repository

HTMX_URL = "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"

_LLM_HUMAN_ERRORS = {
    "auth": "认证失败：API Key 无效或已过期",
    "not_found": "接口不存在（404）",
    "rate_limited": "请求过于频繁，请稍后重试（429）",
    "server_error": "供应商服务暂时不可用",
    "timeout": "连接超时",
    "invalid_response": "供应商返回了无法解析的响应",
    "empty": "供应商返回为空",
}


def _llm_human(error_type: str) -> str:
    return _LLM_HUMAN_ERRORS.get(error_type, error_type)

TYPE_LABELS = {
    "source": "来源",
    "event": "事件",
    "thesis": "观点",
    "company": "公司",
    "report": "报告",
}
STATUS_LABELS = {
    "pending": "待评审",
    "reviewed": "已评审",
    "rejected": "已拒绝",
    "superseded": "已取代",
}


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
        "sector": "sectors",
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
        rows = [['<span class="empty">无记录</span>'] + ["—"] * (len(headers) - 1)]
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
<html lang="zh-CN">
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
      <span>本地 · 只读 · Markdown 驱动</span>
    </div>
    <nav aria-label="Primary">
      <a href="/home{project_query}">产业首页</a>
      <a href="/{project_query}">概览</a>
      <a href="/reviews{project_query}">评审队列</a>
      <a href="/metrics{project_query}">指标</a>
      <a href="/operations{project_query}">运营</a>
      <a href="/pipeline{project_query}">管线</a>
      <a href="/companies{project_query}">产业</a>
      <a href="/impact{project_query}">影响</a>
      <a href="/analysis{project_query}">分析</a>
      <a href="/decision{project_query}">决策</a>
      <a href="/llm{project_query}">模型</a>
      <a href="/health{project_query}">健康</a>
    </nav>
  </div>
</header>
<main class="shell">{content}</main>
<footer class="shell">
  数据由 Markdown 于 {esc(timestamp)} 实时重建。本页面不会修改任何研究数据。
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
    next_review = current_next_review_date(project)
    hero = f"""
<section class="hero">
  <div>
    <div class="eyebrow">{esc(selected)} · {esc(project.metadata.get("status"))}</div>
    <h2>{esc(project.metadata.get("title"))}</h2>
    <p>{esc(project.metadata.get("research_question"))}</p>
  </div>
  <div>
    <div class="eyebrow">下次评审</div>
    <h2>{esc(next_review)}</h2>
    <p class="muted">{esc(project.metadata.get("review_cadence"))} 节奏 · 负责人 {esc(project.metadata.get("owner"))}</p>
  </div>
</section>
<section class="metrics">
  <div class="metric"><strong>{len(by_type["source"])}</strong><span>来源</span></div>
  <div class="metric"><strong>{len(by_type["event"])}</strong><span>事件</span></div>
  <div class="metric"><strong>{len(pending)}</strong><span>待评审</span></div>
  <div class="metric"><strong>{len(open_actions)}</strong><span>未决行动</span></div>
</section>"""
    all_objects, _ = repo.all()
    all_runs = [o for o in all_objects if o.object_type == "analysis_run"]
    runs_pending = sum(
        1 for r in all_runs if r.metadata.get("review_status") == "pending"
    )
    mode_count = sum(1 for o in all_objects if o.object_type == "analysis_mode")
    phase4 = f"""
<section class="panel"><h3>分析工作区（Phase 4）</h3>
<p>{len(all_runs)} 个分析运行（{runs_pending} 待评审）· {mode_count} 个模式 ·
<a href="/analysis">进入分析工作区</a> · <a href="/llm">模型配置</a> ·
<a href="/impact">影响断言</a></p>
</section>"""
    thesis_rows = [
        [
            object_link(obj),
            esc(obj.metadata.get("confidence")),
            esc(len(obj.metadata.get("supporting_evidence", []))),
            esc(len(obj.metadata.get("contradicting_evidence", []))),
            badge(obj.metadata.get("review_status")),
            badge(
                "过期" if thesis_stale(obj) else "正常",
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
        + phase4
        + f"""
<section class="panel"><h3>产业情报</h3>
<p><a href="/companies">企业名单</a> · <a href="/sectors">板块分类</a> · <a href="/reports">研究报告</a></p>
</section>
<section class="grid">
  <div class="panel">
    <h3>观点健康</h3>
    {table(["观点", "置信度", "支持", "反对", "评审", "新鲜度"], thesis_rows)}
  </div>
  <div class="panel">
    <h3>未决行动</h3>
    {table(["行动", "负责人", "截止", "状态"], action_table)}
  </div>
  <div class="panel full">
    <h3>报告</h3>
    {table(["报告", "版本", "状态", "更新"], report_rows)}
  </div>
  <div class="panel full">
    <h3>系统信号</h3>
    <p>{len([item for item in findings if item.level == "error"])} 个错误 ·
    {len([item for item in findings if item.level == "warning"])} 个警告.
    <a href="/health?project={esc(selected)}">查看健康</a>.</p>
  </div>
</section>"""
    )
    return shell(str(project.metadata.get("title")), content, project_id=selected)


def _heat_cell(value: int, color: str = "58, 110, 165") -> str:
    if value <= 0:
        return '<span class="muted">0</span>'
    alpha = min(0.9, 0.15 + 0.12 * value)
    return (
        f'<span style="background: rgba({color}, {alpha:.2f}); '
        f'padding: 2px 8px; border-radius: 4px">{value}</span>'
    )


def _priority_text(score: Any) -> str:
    return f"{score:.3f}" if score is not None else "—"


def _industry_home(repo: DashboardRepository) -> str:
    snapshot = industry_home_snapshot(repo.root, as_of=date.today().isoformat())
    as_of = snapshot["as_of"]
    due_forecasts = len(snapshot["due_forecasts"])
    due_actions = len(snapshot["due_actions"])
    failed_runs = len(snapshot["failed_runs"])
    stale_count = len(snapshot["stale_channels"]) + len(snapshot["never_run_channels"])
    high_priority = snapshot["high_priority_candidates"]
    today_updates = len(snapshot["events_today"]) + len(snapshot["impacts_today"])

    hero = f"""
<section class="hero">
  <div>
    <div class="eyebrow">产业首页</div>
    <h2>AI 产业情报总览</h2>
    <p class="muted">as-of {esc(as_of)} · 产业级聚合（跨板块，无项目过滤）</p>
  </div>
  <div>
    <div class="eyebrow">今日待办</div>
    <h2>{due_forecasts + due_actions + failed_runs + stale_count}</h2>
    <p class="muted">{due_forecasts} 到期预测 · {due_actions} 到期行动 · {failed_runs} 抓取失败 · {stale_count} stale 通道</p>
  </div>
</section>
<section class="metrics">
  <div class="metric"><strong>{len(high_priority)}</strong><span>高优先级候选</span></div>
  <div class="metric"><strong>{today_updates}</strong><span>今日 reviewed 事件/影响</span></div>
  <div class="metric"><strong>{due_forecasts}</strong><span>到期预测</span></div>
  <div class="metric"><strong>{due_actions}</strong><span>到期行动</span></div>
  <div class="metric"><strong>{stale_count}</strong><span>stale 通道</span></div>
  <div class="metric"><strong>{failed_runs}</strong><span>抓取失败</span></div>
</section>"""

    candidate_rows = [
        [
            f'<a href="/pipeline/queue/{esc(c["candidate_id"])}">{esc(c["candidate_id"])}</a>',
            esc(c["title"]),
            esc(c.get("entity_id") or "—"),
            esc(c.get("channel_id") or "—"),
            _priority_text(c.get("priority_score")),
        ]
        for c in high_priority
    ]

    updates = [
        {"id": item["object_id"], "title": item["title"], "kind": "事件"}
        for item in snapshot["events_today"]
    ] + [
        {"id": item["object_id"], "title": item["title"], "kind": "影响"}
        for item in snapshot["impacts_today"]
    ]
    update_rows = [
        [
            f'<a href="/{("events/" if u["kind"] == "事件" else "impact/") + esc(u["id"])}">{esc(u["id"])}</a>',
            esc(u["title"]),
            badge(u["kind"]),
        ]
        for u in updates
    ]

    conflict_rows = [
        [
            f'<a href="/pipeline/queue/{esc(c["candidate_id"])}">{esc(c["candidate_id"])}</a>',
            esc(c["title"]),
        ]
        for c in snapshot["conflicts"]
    ]

    stale_company_rows = [
        [
            f'<a href="/companies/{esc(c["object_id"])}">{esc(c["object_id"])}</a>',
            esc(c["title"]),
        ]
        for c in snapshot["stale_core_companies"]
    ]
    stale_channels_text = ", ".join(snapshot["stale_channels"]) or "—"
    never_run_text = ", ".join(snapshot["never_run_channels"]) or "—"

    due_rows = (
        [
            [
                f'<a href="/decision/forecast/{esc(f["id"])}">{esc(f["id"])}</a>',
                esc(f["title"]),
                esc(f["resolution_date"]),
                badge("到期"),
            ]
            for f in snapshot["due_forecasts"]
        ]
        + [
            [
                f'<a href="/decision/forecast/{esc(f["id"])}">{esc(f["id"])}</a>',
                esc(f["title"]),
                esc(f["resolution_date"]),
                badge("逾期", danger=True),
            ]
            for f in snapshot["overdue_forecasts"]
        ]
        + [
            [
                f'<a href="/actions/{esc(a["id"])}">{esc(a["id"])}</a>',
                esc(a["title"]),
                esc(a["due_date"]),
                badge(a["status"]),
            ]
            for a in snapshot["due_actions"]
        ]
    )

    heatmap_rows = [
        [
            f'<a href="/sectors/{esc(s["sector_id"])}">{esc(s["title"])}</a>',
            _heat_cell(s["entity_count"]),
            _heat_cell(s["event_count_recent"]),
            _heat_cell(s["impact_count_reviewed"]),
            _heat_cell(s["fresh_channels"], "46, 160, 67"),
            _heat_cell(s["stale_channels"], "214, 87, 70"),
        ]
        for s in snapshot["sector_heatmap"]
    ]

    freshness = snapshot["freshness"]

    def fmt(value: Any, suffix: str = "") -> str:
        return f"{value}{suffix}" if value is not None else "—"

    freshness_panel = f"""
<section class="metrics">
  <div class="metric"><strong>{fmt(freshness.get("failure_rate"))}</strong><span>抓取失败率</span></div>
  <div class="metric"><strong>{fmt(freshness.get("median_latency_seconds"), "s")}</strong><span>中位延迟</span></div>
  <div class="metric"><strong>{fmt(freshness.get("http_errors"))}</strong><span>HTTP 错误</span></div>
  <div class="metric"><strong>{fmt(freshness.get("parse_errors"))}</strong><span>解析错误</span></div>
  <div class="metric"><strong>{fmt(freshness.get("retries"))}</strong><span>重试</span></div>
</section>"""

    failed_rows = [
        [
            esc(row["run_id"]),
            esc(row["channel_id"]),
            esc(row["started_at"]),
            esc(row["candidate_count"]),
        ]
        for row in snapshot["failed_runs"]
    ]

    content = (
        hero
        + f"""
<section class="panel"><h3>今日高优先级候选</h3>
{table(["候选", "标题", "实体", "通道", "优先级"], candidate_rows)}
</section>
<section class="panel"><h3>reviewed 事件 / 影响更新</h3>
{table(["对象", "标题", "类型"], update_rows)}
</section>
<section class="panel"><h3>反面与冲突信号</h3>
{table(["候选", "标题"], conflict_rows)}
</section>
<section class="grid">
  <div class="panel">
    <h3>stale Core 公司</h3>
    {table(["公司", "标题"], stale_company_rows)}
  </div>
  <div class="panel">
    <h3>stale / never-run 通道</h3>
    <p><strong>stale：</strong>{esc(stale_channels_text)}</p>
    <p><strong>never-run：</strong>{esc(never_run_text)}</p>
  </div>
</section>
<section class="panel"><h3>到期 Forecast / Action</h3>
{table(["对象", "标题", "日期", "状态"], due_rows)}
</section>
<section class="panel full"><h3>板块热度（原始计数，非情绪分）</h3>
{table(["板块", "实体数", "近30天事件", "reviewed 影响", "新鲜通道", "stale 通道"], heatmap_rows)}
</section>
<section class="panel"><h3>数据新鲜度</h3>
{freshness_panel}
</section>
<section class="panel"><h3>运行失败</h3>
{table(["运行", "通道", "开始", "候选数"], failed_rows)}
</section>"""
    )
    return shell("产业首页", content)



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
        f"{' selected' if object_type == value else ''}>{TYPE_LABELS.get(value, value or '全部')}</option>"
        for value in ("", "source", "event", "thesis", "company", "report")
    )
    status_options = "".join(
        f'<option value="{value}"'
        f"{' selected' if review_status == value else ''}>{STATUS_LABELS.get(value, value)}</option>"
        for value in ("pending", "reviewed", "rejected", "superseded")
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>评审队列</h2>
<p>只读队列。评审决定通过显式评审命令执行。</p>
</div><div><div class="eyebrow">{esc(STATUS_LABELS.get(review_status, review_status))}</div><h2>{len(rows)}</h2>
<p class="muted">本页不会改变任何状态。</p></div></section>
<section class="panel" style="margin-bottom:1rem">
<form method="get" action="/reviews">
<input type="hidden" name="project" value="{esc(selected)}">
<label>类型 <select name="type">{type_options}</select></label>
<label style="margin-left:1rem">状态
<select name="status">{status_options}</select></label>
<button type="submit">筛选</button>
</form></section>
<section class="panel" id="review-table"
  hx-get="/fragments/reviews?project={esc(selected)}&type={esc(object_type or "")}&status={esc(review_status)}"
  hx-trigger="refresh">
{table(["对象", "类型", "状态", "更新"], rows)}</section>"""
    return shell("评审队列", content, project_id=selected)


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
            esc("已提取" if str(path).endswith(".extracted.txt") else "已归档"),
        ]
        for index, path in enumerate(source.metadata.get("asset_paths", []))
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">来源溯源</div>
<h2>{esc(source.metadata.get("title"))}</h2>
<p>{esc(source.metadata.get("publisher"))}</p></div>
<div><div class="eyebrow">资产完整性</div>
<h2>{badge(verification.status if verification else "unknown", danger=bool(verification and verification.status not in {"ok", "registered"}))}</h2>
<p class="muted">{esc(verification.message if verification else "")}</p></div></section>
<section class="panel">{metadata_grid(source)}</section>
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>归档版本与提取</h3>
{table(["资产", "类型"], asset_rows)}</div>
<div class="panel"><h3>关联事件</h3>{table(["事件", "日期", "评审"], rows)}</div>
<div class="panel"><h3>研究笔记</h3><pre>{esc(source.body)}</pre></div>
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
        [object_link(item), badge("支持"), esc(item.metadata.get("event_date"))]
        for item in support
    ] + [
        [
            object_link(item),
            badge("反对", warning=True),
            esc(item.metadata.get("event_date")),
        ]
        for item in contradict
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">观点健康</div><h2>{esc(thesis.metadata.get("title"))}</h2>
<p>{badge("过期", warning=True) if stale else badge("正常")}</p></div>
<div><div class="eyebrow">置信度</div>
<h2>{esc(thesis.metadata.get("confidence"))}</h2>
<p class="muted">上次评审 {esc(review_date)}</p></div></section>
<section class="grid">
<div class="panel"><h3>证据平衡</h3>
{table(["事件", "关系", "日期"], evidence_rows)}</div>
<div class="panel"><h3>观点说明</h3><pre>{esc(thesis.body)}</pre></div>
</section>"""
    return shell(thesis_id, content)


def _generic_page(repo: DashboardRepository, object_id: str) -> str:
    obj = repo.one(object_id)
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(obj.object_type)}</div>
<h2>{esc(obj.metadata.get("title"))}</h2>
<p>{badge(obj.metadata.get("review_status") or obj.metadata.get("status"))}</p>
</div><div><div class="eyebrow">永久 ID</div><h2>{esc(obj.object_id)}</h2>
<p><a href="/impact/{esc(obj.object_id)}">查看关系网络</a></p>
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
    comparison = "暂无指标快照。"
    baseline_label = "none"
    if baseline_paths:
        baseline = load_metrics_snapshot(baseline_paths[-1])
        comparison = render_metrics_comparison(baseline, metrics)
        baseline_label = str(baseline.get("as_of"))
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>指标与变化</h2>
<p>当前 Markdown 状态与快照 {esc(baseline_label)} 对比。</p>
</div><div><div class="eyebrow">评审队列</div>
<h2>{esc(metrics["review_queue_total"])}</h2>
<p class="muted">实时计算，非缓存。</p></div></section>
<section class="metrics">
<div class="metric"><strong>{counts["source"]["total"]}</strong><span>来源</span></div>
<div class="metric"><strong>{counts["event"]["total"]}</strong><span>事件</span></div>
<div class="metric"><strong>{metrics["source_quality"]["archived"]}</strong><span>已归档来源</span></div>
<div class="metric"><strong>{metrics["thesis_health"]["without_contradicting"]}</strong><span>缺少反证的观点</span></div>
</section><section class="panel"><pre>{esc(comparison)}</pre></section>"""
    return shell("指标", content, project_id=selected)


def _kv_table(rows: list[list[str]]) -> str:
    return table(["指标", "数值"], rows)


def _pipeline_overview(repo: DashboardRepository) -> str:
    status = pilot_status(repo.root)
    gate = status["gate"]
    candidates = status["candidates"]
    content = f"""<section class="hero"><div>
<div class="eyebrow">管线</div><h2>机器运转中</h2>
<p>发现 → 筛选 → 入库。只读视图，决定在命令行完成。</p>
</div><div><div class="eyebrow">试点窗口</div>
<h2>{esc(gate['days'])}/{esc(status['target_days'])}</h2>
<p class="muted">自 {esc(status['since'])}</p></div></section>
<section class="metrics">
<div class="metric"><strong>{esc(candidates['discovered_since'])}</strong><span>已发现</span></div>
<div class="metric"><strong>{esc(candidates['promoted'])}</strong><span>已入库</span></div>
<div class="metric"><strong>{esc(candidates['dismissed'])}</strong><span>已驳回</span></div>
<div class="metric"><strong>{esc(gate['channels'])}</strong><span>通道就绪</span></div>
</section>
<section class="grid">
<div class="panel"><h3>候选队列</h3>
<p>等待筛选的新候选，按优先级降序。</p>
<p><a href="/pipeline/queue">打开队列 →</a></p></div>
<div class="panel"><h3>已入库来源</h3>
<p>晋升为正式来源的候选。</p>
<p><a href="/pipeline/sources">查看来源 →</a></p></div>
<div class="panel"><h3>通道与指标</h3>
<p>通道注册表与管线实时健康。</p>
<p><a href="/pipeline/channels">打开通道 →</a></p></div>
</section>
<p class="muted">候选数据为非权威、可重建；权威事实存于仓库。</p>"""
    return shell("管线", content)


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
<div class="eyebrow">管线 → 来源</div><h2>已入库来源</h2>
<p>晋升为正式来源的候选，最新优先。</p>
</div><div><div class="eyebrow">已入库</div><h2>{len(rows)}</h2>
<p class="muted">链接回其来源通道</p></div></section>
<section class="panel">{table(["来源", "通道", "发布方", "实体", "发现时间"], body_rows)}</section>"""
    return shell("管线来源", content)


def _candidate_facts(detail: dict[str, Any]) -> str:
    priority = (
        f"{detail['priority_score']:.3f}"
        if detail.get("priority_score") is not None
        else "—"
    )
    items = [
        ("状态", detail.get("status")),
        ("通道", detail.get("channel_id")),
        ("发现时间", detail.get("discovered_at")),
        ("发布时间(建议)", detail.get("published_at_proposal")),
        ("发布方", detail.get("publisher")),
        ("URL", detail.get("canonical_url")),
        ("重复簇", detail.get("duplicate_cluster_id")),
        ("优先级", priority),
        ("模型", detail.get("model_version")),
    ]
    if detail.get("existing_source_id"):
        items.append(("已是正式来源", detail["existing_source_id"]))
    if detail.get("is_representative") is False and detail.get(
        "duplicate_cluster_id"
    ):
        items.append(("簇角色", "非代表变体"))
    return '<dl class="metadata">' + "".join(
        f"<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>"
        for label, value in items
    ) + "</dl>"


def _proposal_rows(proposal: dict[str, Any]) -> list[list[str]]:
    rows = []
    for key, value in proposal.items():
        if isinstance(value, list):
            text = "、".join(str(item) for item in value)
        elif isinstance(value, dict):
            text = json.dumps(value, ensure_ascii=False)
        else:
            text = str(value)
        rows.append([esc(str(key)), esc(text)])
    return rows


def _scoring_panel(detail: dict[str, Any]) -> str:
    scoring = detail.get("scoring")
    if not scoring or not scoring.get("subscores"):
        if detail.get("model_version"):
            return (
                '<section class="panel"><h3>评分分项</h3>'
                f'<p>{badge("model version mismatch", warning=True)} · '
                f"评分版本 {esc(detail.get('model_version'))} 与当前不一致，跳过数值。</p></section>"
            )
        return ""
    subs = scoring["subscores"]
    tiles = "".join(
        f'<div class="metric"><strong>{esc(subs.get(key))}</strong>'
        f"<span>{esc(key)}</span></div>"
        for key in (
            "scope_relevance",
            "source_quality",
            "novelty",
            "materiality",
            "time_sensitivity",
            "evidence_potential",
            "duplication_penalty",
            "uncertainty_penalty",
        )
    )
    return (
        '<section class="panel"><h3>评分分项'
        f"（{esc(scoring.get('model') or 'deterministic-v1')}）</h3>"
        f'<section class="metrics">{tiles}</section></section>'
    )


def _suggestion_panel(detail: dict[str, Any]) -> str:
    hints: list[str] = []
    score = detail.get("priority_score")
    if (
        detail.get("status") == "new"
        and not detail.get("existing_source_id")
        and score is not None
        and score >= 0.6
    ):
        hints.append(badge("建议 promote"))
    if (
        not detail.get("is_representative", True)
        or detail.get("status") in {"dismissed", "expired", "failed"}
    ):
        hints.append(badge("建议 dismiss", warning=True))
    if not hints:
        return ""
    return (
        '<section class="panel"><h3>处理建议（只读）</h3>'
        f"<p>{' · '.join(hints)} · 写入请走 CLI（dry-run → --apply）</p></section>"
    )


def _reviewed_evidence(
    repo: DashboardRepository,
    entity: dict[str, Any],
    existing_source_id: str | None,
) -> str:
    links: list[str] = []
    if existing_source_id:
        links.append(
            f'<p>已有正式来源：<a href="/sources/{esc(existing_source_id)}">'
            f"{esc(existing_source_id)}</a></p>"
        )
    entity_id = entity.get("entity_id")
    event_rows: list[list[str]] = []
    if entity_id:
        objects, _ = repo.all()
        event_rows = [
            [
                f'<a href="/events/{esc(obj.object_id)}">{esc(obj.object_id)}</a>',
                esc(obj.metadata.get("event_date")),
                esc(obj.metadata.get("title")),
            ]
            for obj in objects
            if obj.object_type == "event"
            and obj.metadata.get("review_status") == "reviewed"
            and entity_id in (obj.metadata.get("companies") or [])
        ][:10]
    if not links and not event_rows:
        return '<p><span class="muted">无已评审证据关联该候选。</span></p>'
    return (
        "".join(links)
        + table(["已评审事件", "日期", "标题"], event_rows)
    )


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
<div class="eyebrow">候选 {esc(candidate_id)}</div><h2>{esc(detail.get("title"))}</h2>
<p>{badge(detail.get("status"))} · {esc(detail.get("channel_id"))}</p></div>
<div><div class="eyebrow">优先级</div><h2>{esc(priority)}</h2>
<p class="muted">{esc(detail.get("model_version")) or "启发式打分"}</p></div></section>"""
    panels = f"""<section class="panel"><h3>候选区</h3>{_candidate_facts(detail)}</section>
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>实体建议</h3>{table(["字段", "值"], _proposal_rows(entity))}</div>
<div class="panel"><h3>板块建议</h3>{table(["字段", "值"], _proposal_rows(sector))}</div>
</section>
{_scoring_panel(detail)}
{_suggestion_panel(detail)}
<section class="panel" style="border-top:2px solid var(--accent)"><h3>已评审证据区</h3>
{_reviewed_evidence(repo, entity, detail.get("existing_source_id"))}</section>
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>理由编码</h3>
{table(["编码"], reason_rows)}</div>
<div class="panel"><h3>操作历史</h3>
{table(["时间", "操作", "操作者", "原因"], action_rows_html)}</div>
</section>"""
    return shell(candidate_id, hero + panels)


def _pipeline_queue(
    repo: DashboardRepository,
    status: str,
    channel: str | None,
    entity: str | None,
    tier: str | None,
    min_priority: float | None,
    limit: int,
    offset: int,
    show_dups: bool,
) -> str:
    page_rows = queue_rows(
        repo.root,
        status=status or "new",
        channel_id=channel or None,
        entity_id=entity or None,
        tier=tier or None,
        min_priority=min_priority,
        limit=limit + 1,
        offset=offset,
        show_dups=show_dups,
    )
    has_next = len(page_rows) > limit
    rows = page_rows[:limit]

    def dup_cell(row: dict[str, Any]) -> str:
        if row.get("existing_source_id"):
            return (
                f'<a href="/sources/{esc(row["existing_source_id"])}">'
                f'已有来源 {esc(row["existing_source_id"])}</a>'
            )
        if row.get("dup_count"):
            return badge(f"+{row['dup_count']} 个变体")
        if not row.get("is_representative", True):
            return badge("变体", warning=True)
        return "—"

    def entity_cell(entity_id: Any) -> str:
        if isinstance(entity_id, str) and entity_id.startswith("COM-"):
            return f'<a href="/companies/{esc(entity_id)}">{esc(entity_id)}</a>'
        return esc(str(entity_id or "—"))

    def sector_cell(sector_ids: Any) -> str:
        if not sector_ids:
            return "—"
        return "、".join(
            f'<a href="/sectors/{esc(sid)}">{esc(sid)}</a>'
            for sid in sector_ids
        )

    body_rows = [
        [
            (
                f"{row['priority_score']:.3f}"
                if row["priority_score"] is not None
                else "—"
            ),
            badge(row["status"]),
            dup_cell(row),
            entity_cell(row.get("entity_id")),
            sector_cell(row.get("sector_ids")),
            esc(row["channel_id"]),
            esc(row.get("discovered_at") or ""),
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
    entity_value = esc(entity or "")
    min_value = esc(min_priority if min_priority is not None else "")
    dup_check = " checked" if show_dups else ""

    def page_url(page_offset: int) -> str:
        params: list[tuple[str, str]] = [("status", status or "new")]
        if channel:
            params.append(("channel", channel))
        if entity:
            params.append(("entity", entity))
        if tier:
            params.append(("tier", tier))
        if min_priority is not None:
            params.append(("min_priority", str(min_priority)))
        params.extend((("limit", str(limit)), ("offset", str(page_offset))))
        if show_dups:
            params.append(("show_dups", "true"))
        return f"/pipeline/queue?{urlencode(params)}"

    previous = (
        f'<a href="{esc(page_url(max(0, offset - limit)))}">Previous</a>'
        if offset > 0
        else '<span class="muted">Previous</span>'
    )
    next_link = (
        f'<a href="{esc(page_url(offset + limit))}">Next</a>'
        if has_next
        else '<span class="muted">Next</span>'
    )
    tier_options = "".join(
        f'<option value="{value}"'
        f"{' selected' if tier == value else ''}>{label}</option>"
        for value, label in (
            ("", "全部"),
            ("core", "core"),
            ("tracked", "tracked"),
            ("discovery", "discovery"),
        )
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">管线 → 队列</div><h2>候选队列</h2>
<p>只读筛选列表。重复簇折叠为单行代表。</p>
</div><div><div class="eyebrow">{esc(status)}</div><h2>{len(rows)}</h2>
<p class="muted">按优先级降序</p></div></section>
<section class="panel" style="margin-bottom:1rem">
<form method="get" action="/pipeline/queue">
<label>状态 <select name="status">{status_options}</select></label>
<label style="margin-left:1rem">通道 <input name="channel" value="{channel_value}"></label>
<label style="margin-left:1rem">实体 <input name="entity" value="{entity_value}"></label>
<label style="margin-left:1rem">层级 <select name="tier">{tier_options}</select></label>
<label style="margin-left:1rem">最低优先级 <input type="number" step="0.01" min="0" max="1" name="min_priority" value="{min_value}"></label>
<label style="margin-left:1rem">数量 <input type="number" min="1" max="200" name="limit" value="{esc(limit)}"></label>
<label style="margin-left:1rem"><input type="checkbox" name="show_dups" value="1"{dup_check}> 显示重复</label>
<input type="hidden" name="offset" value="0">
<button type="submit">筛选</button>
</form></section>
<section class="panel">{table(["优先级", "状态", "重复", "实体", "板块", "通道", "发现时间", "标题"], body_rows)}</section>
<nav aria-label="Candidate queue pages" style="min-height:2.5rem;display:flex;align-items:center;justify-content:space-between">{previous}<span class="muted">{offset + 1}–{offset + len(rows)}</span>{next_link}</nav>"""
    return shell("管线队列", content)


def _pipeline_channels(repo: DashboardRepository) -> str:
    channels = channel_rows(repo.root)
    channel_body = [
        [
            esc(row["id"]),
            esc(row["name"]),
            esc(row["channel_type"]),
            esc(row["license_status"]),
            badge(row["review_status"]),
            badge("启用" if row["enabled"] else "停用", warning=not row["enabled"]),
            badge(
                "是"
                if (row["review_status"] == "reviewed" and row["enabled"])
                else "否",
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
        ["运行次数", esc(discovery["runs"])],
        ["成功 / 失败", f"{esc(discovery['succeeded'])} / {esc(discovery['failed'])}"],
        ["失败率", f"{discovery['failure_rate']:.0%}"],
        ["中位延迟", esc(latency_text)],
        ["HTTP / 解析 / 重试", f"{esc(discovery['http_errors'])} / {esc(discovery['parse_errors'])} / {esc(discovery['retries'])}"],
        ["成本估算", esc(discovery["cost_estimate"])],
    ]
    duplicate_rows = [
        [
            "入队重复率(7天)",
            f"{duplicate['rate']:.0%}",
        ],
        [
            "入队窗口",
            f"{duplicate['inbound_dups']} / {duplicate['inbound_total']} 非代表",
        ],
        [
            "库内快照",
            f"{duplicate['store_rate']:.0%} "
            f"({duplicate['non_representative']} 非代表)",
        ],
        ["簇数", esc(duplicate["clusters"])],
    ]
    dismiss_text = ", ".join(
        f"{reason} ({count})" for reason, count in triage["top_dismiss_reasons"]
    ) or "—"
    triage_rows = [
        ["已处理(审计)", esc(triage["total"])],
        ["已入库 / 已驳回", f"{esc(triage['promoted'])} / {esc(triage['dismissed'])}"],
        ["入库率", f"{triage['promoted_rate']:.0%}"],
        ["驳回率", f"{triage['dismissed_rate']:.0%}"],
        ["中位入库耗时(小时)", esc(triage["median_conversion_hours"])],
        ["主要驳回原因", esc(dismiss_text)],
    ]
    coverage_rows = [
        ["已匹配实体", esc(coverage["matched_entities"])],
        ["核心已匹配", esc(coverage["core_matched"])],
        ["核心覆盖率", f"{coverage['core_rate']:.0%}"],
    ]
    stale_text = ", ".join(stale["stale"]) or "—"
    never_text = ", ".join(stale["never_run"]) or "—"
    content = f"""<section class="hero"><div>
<div class="eyebrow">管线 → 通道与指标</div><h2>通道与指标</h2>
<p>通道注册表与管线实时健康。</p>
</div><div><div class="eyebrow">截至 {esc(metrics["as_of"])}</div>
<h2>{esc(discovered["total"])}</h2>
<p class="muted">每次请求实时重算</p></div></section>
<section class="panel"><h3>通道 ({len(channels)})</h3>
{table(["ID", "名称", "类型", "许可", "评审", "启用", "可调度"], channel_body)}</section>
<section class="metrics" style="margin-top:1rem">
<div class="metric"><strong>{esc(discovered["total"])}</strong><span>累计发现</span></div>
<div class="metric"><strong>{esc(discovered["today"])}</strong><span>今日发现</span></div>
<div class="metric"><strong>{duplicate["rate"]:.0%}</strong><span>入队重复率(7天)</span></div>
<div class="metric"><strong>{discovery["failure_rate"]:.0%}</strong><span>失败率</span></div>
</section>
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>重复</h3>{_kv_table(duplicate_rows)}</div>
<div class="panel"><h3>发现</h3>{_kv_table(discovery_rows)}</div>
<div class="panel"><h3>筛选产出</h3>{_kv_table(triage_rows)}</div>
<div class="panel"><h3>核心覆盖</h3>{_kv_table(coverage_rows)}</div>
<div class="panel"><h3>通道新鲜度</h3>
<p><strong>过期:</strong> {esc(stale_text)}</p>
<p><strong>从未运行:</strong> {esc(never_text)}</p></div>
</section>"""
    return shell("管线通道", content)


def _operations_page(repo: DashboardRepository, project_id: str | None) -> str:
    _, _, selected = repo.scoped(project_id)
    snapshot = operations_snapshot(
        repo.root,
        as_of=date.today().isoformat(),
        project_id=selected,
    )
    schedule_rows = [
        [
            esc(row["channel_id"]),
            esc(row["schedule"]),
            esc(row["last_run"] or "never"),
            badge(row["status"], warning=True),
        ]
        for row in snapshot["schedules"]
    ]
    job_rows_ = [
        [
            esc(row["id"]),
            esc(row["job_name"]),
            esc(row["started_at"]),
            badge(row["status"], warning=row["status"] == "failed"),
            esc(row["message"]),
        ]
        for row in snapshot["jobs"]
    ]
    action_rows_ = [
        [
            esc(row["id"]),
            esc(row["owner"]),
            esc(row["due_date"]),
            badge(row["timing"], warning=row["timing"] == "overdue"),
        ]
        for row in snapshot["actions"]
    ]
    review_rows = [
        [
            esc(row["id"]),
            esc(row["review_cadence"]),
            esc(row["next_review_date"]),
        ]
        for row in snapshot["reviews"]
    ]
    forecast_rows = [
        [
            esc(row["id"]),
            esc(row["title"]),
            esc(row["resolution_date"]),
            badge(row["timing"], warning=True),
        ]
        for row in snapshot["forecasts"]
    ]
    recommendation_rows = [
        [
            esc(row["id"]),
            esc(row["company_id"]),
            esc(row["age_days"]),
            badge(row["freshness"], warning=True),
        ]
        for row in snapshot["recommendations"]
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>运营</h2>
<p>统一读取调度、Jobs、Actions、研究评审与决策到期项；页面不执行任务。</p>
</div><div><div class="eyebrow">待处理</div><h2>{esc(len(snapshot['schedules']) + len(snapshot['actions']) + len(snapshot['reviews']) + len(snapshot['forecasts']) + len(snapshot['recommendations']))}</h2>
<p class="muted">截至 {esc(snapshot['as_of'])}</p></div></section>
<section class="panel"><h3>调度</h3>{table(["Channel", "Schedule", "Last run", "状态"], schedule_rows)}</section>
<section class="panel"><h3>Jobs</h3>{table(["Job", "名称", "Started", "状态", "消息"], job_rows_)}</section>
<section class="panel"><h3>Actions</h3>{table(["Action", "Owner", "Due", "时点"], action_rows_)}</section>
<section class="panel"><h3>研究评审</h3>{table(["Project", "Cadence", "Next review"], review_rows)}</section>
<section class="panel"><h3>到期 Forecast</h3>{table(["Forecast", "标题", "Resolution date", "时点"], forecast_rows)}</section>
<section class="panel"><h3>过期 Recommendation</h3>{table(["Recommendation", "公司", "年龄(天)", "状态"], recommendation_rows)}</section>
<section class="panel"><h3>管线健康</h3>
<p><a href="/pipeline">打开管线看板 →</a></p>
<p class="muted">候选管线 / 通道 / 指标已移至管线页面。</p></section>
"""
    return shell("运营", content, project_id=selected)


def _health_page(repo: DashboardRepository, project_id: str | None) -> str:
    _, _, selected = repo.scoped(project_id)
    snapshot = health_snapshot(repo.root, project_id=selected)
    validation = snapshot["validation"]
    finding_rows = [
        [
            badge(
                finding["level"],
                warning=finding["level"] == "warning",
                danger=finding["level"] == "error",
            ),
            esc(finding["code"]),
            esc(finding["path"]),
            esc(finding["message"]),
        ]
        for finding in validation["findings"]
    ]
    index_rows = [[esc(path)] for path in snapshot["indexes"]["drift"]]
    asset_rows = [
        [esc(row["source_id"]), esc(row["status"]), esc(row["message"])]
        for row in snapshot["assets"]["failures"]
    ]
    db = snapshot["candidate_db"]
    channel_rows_ = [
        [
            esc(row["channel_id"]),
            badge("enabled" if row["enabled"] else "disabled"),
            badge(row["review_status"], warning=row["review_status"] != "reviewed"),
            badge(row["license_status"], warning=row["license_status"] != "reviewed"),
            esc(row["robots_checked_at"] or "—"),
        ]
        for row in snapshot["channels"]
    ]
    failed_rows = [
        [esc(row["id"]), esc(row["type"]), esc(row["status"]), esc(row["message"])]
        for row in snapshot["failed_runs"]
    ]
    config_rows = [
        [esc(key), badge(value, warning=value == "missing")]
        for key, value in snapshot["config"].items()
    ]
    backup = snapshot["backup"]
    disk = snapshot["host"]["disk"]
    model_cost = snapshot["model_cost"]
    attention = any(
        (
            validation["status"] != "ok",
            snapshot["indexes"]["status"] != "ok",
            snapshot["assets"]["status"] != "ok",
            db["status"] != "ok",
            backup["status"] != "fresh",
            disk["status"] != "ok",
            bool(snapshot["failed_runs"]),
        )
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(selected)}</div><h2>系统健康</h2>
<p>仓库、operational store、许可、备份与主机状态均在请求时只读检查。</p></div>
<div><div class="eyebrow">状态</div>
<h2>{badge("注意", warning=True) if attention else badge("健康")}</h2>
<p class="muted">{esc(len(snapshot['indexes']['drift']))} 处漂移 · {esc(len(snapshot['assets']['failures']))} 个资产失败 · {esc(len(snapshot['failed_runs']))} 个失败运行</p></div></section>
<section class="panel"><h3>仓库校验</h3>
{table(["级别", "编码", "路径", "消息"], finding_rows)}</section>
<section class="panel"><h3>索引</h3><p>scope={esc(snapshot['indexes']['scope'])} · {badge(snapshot['indexes']['status'], warning=snapshot['indexes']['status'] != 'ok')}</p>{table(["Drift"], index_rows) if index_rows else "<p class='muted'>无索引漂移。</p>"}</section>
<section class="panel"><h3>Source assets</h3>{table(["Source", "状态", "消息"], asset_rows) if asset_rows else "<p class='muted'>资产完整性通过。</p>"}</section>
<section class="panel"><h3>Candidate DB</h3>{_kv_table([["状态", badge(db['status'], warning=db['status'] != 'ok')], ["Integrity", esc(db['integrity'])], ["Schema", f"{esc(db['schema_version'])} / {esc(db['expected_schema_version'])}"], ["Size", esc(db['size_bytes'])], ["Modified", esc(db['modified_at'] or '—')]])}</section>
<section class="panel"><h3>Channels / License</h3>{table(["Channel", "Enabled", "Review", "License", "Robots checked"], channel_rows_)}</section>
<section class="panel"><h3>失败任务与失败运行</h3>{table(["ID", "Type", "状态", "消息"], failed_rows)}</section>
<section class="grid">
<div class="panel"><h3>备份</h3>{_kv_table([["状态", badge(backup['status'], warning=backup['status'] != 'fresh')], ["Age hours", esc(backup['age_hours'] if backup['age_hours'] is not None else '—')], ["Manifest", esc(backup['manifest'] or '—')]])}</div>
<div class="panel"><h3>磁盘与时区</h3>{_kv_table([["Free bytes", esc(disk['free_bytes'])], ["Disk status", badge(disk['status'], warning=disk['status'] != 'ok')], ["Timezone", esc(snapshot['host']['timezone'])]])}</div>
<div class="panel"><h3>配置存在性</h3>{table(["配置", "状态"], config_rows)}</div>
<div class="panel"><h3>模型与成本</h3>{_kv_table([["状态", esc(model_cost['status'])], ["记录数", esc(model_cost['records'])], ["预算配置", badge('present' if model_cost['budget_configured'] else 'missing', warning=not model_cost['budget_configured'])]])}</div>
</section>"""
    return shell("健康", content, project_id=selected)


def _intel_tabs(active: str) -> str:
    items = [
        ("/companies", "企业", "companies"),
        ("/sectors", "板块", "sectors"),
        ("/reports", "报告", "reports"),
    ]
    tabs = "".join(
        '<a href="{href}"{active_class}>{label}</a>'.format(
            href=href,
            label=label,
            active_class=' class="active"' if active == key else "",
        )
        for href, label, key in items
    )
    return f'<nav class="tabs">{tabs}</nav>'


def _companies_page(repo: DashboardRepository) -> str:
    objects, _ = repo.all()
    companies = [obj for obj in objects if obj.object_type == "company"]
    sectors = {
        obj.object_id: obj for obj in objects if obj.object_type == "sector"
    }
    tier_order = {"core": 0, "tracked": 1, "discovery": 2}
    companies.sort(
        key=lambda obj: (
            tier_order.get(str(obj.metadata.get("coverage_tier")), 9),
            obj.object_id,
        )
    )
    rows = []
    for company in companies:
        sector_titles = "、".join(
            sectors[sid].metadata.get("title", sid)
            for sid in company.metadata.get("sector_ids", [])
            if sid in sectors
        ) or "—"
        rows.append(
            [
                object_link(company),
                esc(company.metadata.get("legal_name")),
                esc(company.metadata.get("region_primary")),
                esc(company.metadata.get("company_stage")),
                esc(sector_titles),
                badge(company.metadata.get("coverage_tier")),
            ]
        )
    counts = {tier: 0 for tier in ("core", "tracked", "discovery")}
    for company in companies:
        tier = str(company.metadata.get("coverage_tier") or "")
        if tier in counts:
            counts[tier] += 1
    hero = f"""<section class="hero"><div>
<div class="eyebrow">产业情报 → 企业</div><h2>企业名单</h2>
<p>AI 产业链企业，按覆盖分层（core / tracked / discovery）。</p>
</div><div><div class="eyebrow">企业总数</div><h2>{len(companies)}</h2>
<p class="muted">Core {counts['core']} · Tracked {counts['tracked']} · Discovery {counts['discovery']}</p>
</div></section>"""
    content = (
        hero
        + _intel_tabs("companies")
        + '<section class="panel" style="margin-top:1rem">'
        + table(
            ["企业", "法定名称", "区域", "阶段", "板块", "分层"],
            rows,
        )
        + "</section>"
    )
    return shell("企业名单", content)


def _sectors_page(repo: DashboardRepository) -> str:
    objects, _ = repo.all()
    sectors = [obj for obj in objects if obj.object_type == "sector"]
    companies = {
        obj.object_id: obj for obj in objects if obj.object_type == "company"
    }
    rows = []
    for sector in sectors:
        core_links = "、".join(
            f'<a href="/companies/{esc(cid)}">{esc(companies[cid].metadata.get("title", cid))}</a>'
            for cid in sector.metadata.get("core_company_ids", [])
            if cid in companies
        ) or "—"
        rows.append(
            [
                object_link(sector),
                esc(sector.metadata.get("definition")),
                esc(sector.metadata.get("value_chain_position")),
                core_links,
            ]
        )
    content = f"""<section class="hero"><div>
<div class="eyebrow">产业情报 → 板块</div><h2>板块分类</h2>
<p>AI 算力基础设施价值链的板块划分与核心企业。</p>
</div><div><div class="eyebrow">板块总数</div><h2>{len(sectors)}</h2>
<p class="muted">覆盖 AI Compute Chain 各环节</p></div></section>
{_intel_tabs("sectors")}
<section class="panel" style="margin-top:1rem">{table(["板块", "定义", "价值链位置", "核心企业"], rows)}</section>"""
    return shell("板块分类", content)


def _reports_page(repo: DashboardRepository) -> str:
    objects, _ = repo.all()
    reports = [obj for obj in objects if obj.object_type == "report"]
    reports.sort(
        key=lambda obj: str(obj.metadata.get("updated_at", "")),
        reverse=True,
    )
    rows = [
        [
            object_link(report),
            esc(report.metadata.get("report_type")),
            badge(report.metadata.get("status")),
            esc(report.metadata.get("updated_at")),
        ]
        for report in reports
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">产业情报 → 报告</div><h2>研究报告</h2>
<p>基于证据库产出的正式研究报告。</p>
</div><div><div class="eyebrow">报告总数</div><h2>{len(reports)}</h2>
<p class="muted">最新优先</p></div></section>
{_intel_tabs("reports")}
<section class="panel" style="margin-top:1rem">{table(["报告", "类型", "状态", "更新"], rows)}</section>"""
    return shell("研究报告", content)


def _object_cell(obj: ResearchObject) -> str:
    return (
        f'<a href="{object_url(obj)}">{esc(obj.object_id)}</a>'
        f'<br><span class="muted">{esc(obj.metadata.get("title") or "")}</span>'
    )


def _company_detail(repo: DashboardRepository, obj: ResearchObject) -> str:
    snapshot = company_snapshot(repo.root, obj.object_id)
    identity = snapshot["identity"]
    coverage = snapshot["coverage"]
    if coverage:
        coverage_badges = (
            badge(
                "身份" if coverage.get("identity_complete") else "身份缺失",
                warning=not coverage.get("identity_complete"),
            )
            + " · "
            + badge(
                "已证据" if coverage.get("sourced") else "无证据",
                warning=not coverage.get("sourced"),
            )
            + " · "
            + badge(
                "已关联" if coverage.get("related") else "无关联",
                warning=not coverage.get("related"),
            )
        )
    else:
        coverage_badges = badge("无覆盖数据", warning=True)

    hero = f"""<section class="hero"><div>
<div class="eyebrow">企业雷达 → 公司</div><h2>{esc(identity.get("title") or obj.object_id)}</h2>
<p>{esc(identity.get("legal_name"))} · {badge(identity.get("coverage_tier"))}</p></div>
<div><div class="eyebrow">覆盖</div>{coverage_badges}
<p><a href="/impact/{esc(obj.object_id)}">查看关系网络</a></p></div></section>"""

    security_rows = [
        [
            _object_cell(security),
            esc(security.metadata.get("ticker")),
            esc(security.metadata.get("exchange")),
            esc(security.metadata.get("currency")),
            esc(security.metadata.get("instrument_type")),
            esc(security.metadata.get("active_from")),
            esc(security.metadata.get("active_to")),
        ]
        for security in snapshot["securities"]
    ]
    product_rows = [[_object_cell(p)] for p in snapshot["products"]]
    tech_rows = [[_object_cell(t)] for t in snapshot["technologies"]]
    sector_rows = [[_object_cell(s)] for s in snapshot["sectors"]]

    assertion_groups: dict[str, list[list[str]]] = {}
    for assertion in snapshot["assertions"]:
        predicate = str(assertion.metadata.get("predicate") or "")
        counterpart = (
            assertion.metadata.get("object_id")
            if assertion.metadata.get("subject_id") == obj.object_id
            else assertion.metadata.get("subject_id")
        )
        row = [
            esc(counterpart),
            esc(assertion.metadata.get("valid_from")),
            badge(assertion.metadata.get("review_status")),
        ]
        assertion_groups.setdefault(predicate, []).append(row)
    assertion_panels = "".join(
        f'<div class="panel"><h3>{esc(predicate)}</h3>'
        f'{table(["对手实体", "生效", "评审"], rows)}</div>'
        for predicate, rows in assertion_groups.items()
    ) or '<div class="panel"><h3>供应链断言</h3><p><span class="muted">无记录</span></p></div>'

    channel_rows_html = [
        [
            esc(channel["channel_id"]),
            esc(channel["title"]),
            badge(channel["freshness"], warning=channel["freshness"] != "fresh"),
        ]
        for channel in snapshot["channels"]
    ]
    metric_rows = [[_object_cell(m), esc(m.metadata.get("unit"))] for m in snapshot["metrics"]]
    event_rows = [
        [
            _object_cell(event),
            esc(event.metadata.get("event_date")),
            esc(event.metadata.get("confidence")),
        ]
        for event in snapshot["events"]
    ]
    run_rows = [
        [
            _object_cell(run),
            esc(run.metadata.get("mode_id")),
            esc(run.metadata.get("as_of")),
            badge(run.metadata.get("status")),
        ]
        for run in snapshot["analysis_runs"]
    ]
    forecast_rows = [
        [
            _object_cell(forecast),
            esc(forecast.metadata.get("resolution_date")),
            badge(forecast.metadata.get("status")),
        ]
        for forecast in snapshot["forecasts"]
    ]
    valuation_rows = [
        [
            _object_cell(valuation),
            esc(valuation.metadata.get("as_of")),
            esc(valuation.metadata.get("market_price")),
        ]
        for valuation in snapshot["valuations"]
    ]
    rec_rows = [
        [
            _object_cell(rec),
            esc(rec.metadata.get("research_posture")),
            esc(rec.metadata.get("direction")),
            esc(rec.metadata.get("conviction")),
            badge(rec.metadata.get("status")),
        ]
        for rec in snapshot["recommendations"]
    ]
    thesis_rows = [
        [
            _object_cell(thesis),
            esc(thesis.metadata.get("confidence")),
            badge(thesis.metadata.get("review_status")),
        ]
        for thesis in snapshot["theses"]
    ]

    content = (
        hero
        + _intel_tabs("companies")
        + f"""
<section class="panel" style="margin-top:1rem"><h3>主体与证券分离</h3>
{table(["证券", "代码", "交易所", "货币", "类型", "生效", "失效"], security_rows)}</section>
<section class="grid">
  <div class="panel"><h3>产品</h3>{table(["产品"], product_rows)}</div>
  <div class="panel"><h3>技术</h3>{table(["技术"], tech_rows)}</div>
  <div class="panel"><h3>板块</h3>{table(["板块"], sector_rows)}</div>
</section>
<section class="grid">{assertion_panels}</section>
<section class="panel"><h3>来源通道新鲜度</h3>
{table(["通道", "标题", "新鲜度"], channel_rows_html)}</section>
<section class="panel"><h3>指标（定义层）</h3>
{table(["指标", "单位"], metric_rows)}</section>
<section class="panel full"><h3>证据时间线</h3>
{table(["事件", "日期", "置信度"], event_rows)}</section>
<section class="panel full"><h3>分析运行</h3>
{table(["运行", "模式", "as-of", "状态"], run_rows)}</section>
<section class="grid">
  <div class="panel"><h3>预测历史</h3>{table(["预测", "到期", "状态"], forecast_rows)}</div>
  <div class="panel"><h3>估值快照历史</h3>{table(["估值", "as-of", "价格"], valuation_rows)}</div>
  <div class="panel"><h3>推荐历史</h3>{table(["推荐", "姿态", "方向", "置信", "状态"], rec_rows)}</div>
  <div class="panel"><h3>观点</h3>{table(["观点", "置信度", "评审"], thesis_rows)}</div>
</section>"""
    )
    return shell(f"{obj.object_id} · 企业雷达", content)


def _sector_detail(repo: DashboardRepository, obj: ResearchObject) -> str:
    snapshot = sector_snapshot(repo.root, obj.object_id)
    identity = snapshot["identity"]
    rollup = snapshot["coverage_rollup"]
    members = snapshot["members"]
    company_rows = [
        [
            _object_cell(company),
            esc(company.metadata.get("legal_name")),
            esc(company.metadata.get("region_primary")),
            esc(company.metadata.get("company_stage")),
            badge(company.metadata.get("coverage_tier")),
        ]
        for company in snapshot["companies"]
    ]
    product_rows = [[_object_cell(p)] for p in snapshot["products"]]
    tech_rows = [[_object_cell(t)] for t in snapshot["technologies"]]
    metric_rows = [[_object_cell(m), esc(m.metadata.get("unit"))] for m in snapshot["metrics"]]
    event_rows = [
        [_object_cell(event), esc(event.metadata.get("event_date"))]
        for event in snapshot["events"]
    ]
    impact_rows = [
        [
            f'<a href="/impact/{esc(impact.object_id)}">{esc(impact.object_id)}</a>',
            esc(impact.metadata.get("target_id")),
            esc(impact.metadata.get("impact_type")),
            badge(impact.metadata.get("direction")),
        ]
        for impact in snapshot["impacts"]
    ]
    thesis_rows = [
        [_object_cell(thesis), badge(thesis.metadata.get("review_status"))]
        for thesis in snapshot["theses"]
    ]
    forecast_rows = [
        [_object_cell(forecast), badge(forecast.metadata.get("status"))]
        for forecast in snapshot["forecasts"]
    ]
    member_flag_rows = [
        [
            f'<a href="/companies/{esc(row["company_id"])}">{esc(row["company_id"])}</a>',
            badge("身份" if row.get("identity_complete") else "缺失", warning=not row.get("identity_complete")),
            badge("已证据" if row.get("sourced") else "无", warning=not row.get("sourced")),
            badge("已关联" if row.get("related") else "无", warning=not row.get("related")),
        ]
        for row in snapshot["member_flags"]
    ]

    def rate_cell(value: float) -> str:
        return f"{value * 100:.0f}%"

    hero = f"""<section class="hero"><div>
<div class="eyebrow">板块 → {esc(obj.object_id)}</div><h2>{esc(identity.get("title") or obj.object_id)}</h2>
<p>{esc(identity.get("value_chain_position"))} · <a href="/impact/{esc(obj.object_id)}">查看关系网络</a></p></div>
<div><div class="eyebrow">覆盖</div>
<p class="muted">身份 {rate_cell(rollup["identity_rate"])} · 证据 {rate_cell(rollup["source_rate"])} · 关联 {rate_cell(rollup["relationship_rate"])}</p></div></section>
<section class="metrics">
  <div class="metric"><strong>{len(members)}</strong><span>成员企业</span></div>
  <div class="metric"><strong>{len(snapshot["events"])}</strong><span>事件</span></div>
  <div class="metric"><strong>{len(snapshot["impacts"])}</strong><span>reviewed 影响</span></div>
</section>"""

    assertion_rows = [
        [
            esc(
                assertion.metadata.get("object_id")
                if assertion.metadata.get("subject_id") == obj.object_id
                else assertion.metadata.get("subject_id")
            ),
            esc(assertion.metadata.get("predicate")),
            badge(assertion.metadata.get("review_status")),
        ]
        for assertion in snapshot["assertions"]
    ]
    definition = f"""<section class="panel"><h3>定义 / 范围 / 价值链</h3>
<p>{esc(identity.get("definition"))}</p>
<p><strong>价值链位置：</strong>{esc(identity.get("value_chain_position"))}</p>
<p><strong>范围内：</strong>{esc(identity.get("in_scope"))}</p>
<p><strong>范围外：</strong>{esc(identity.get("out_of_scope"))}</p>
<p><strong>关键输入：</strong>{esc(identity.get("key_inputs"))}</p>
<p><strong>关键输出：</strong>{esc(identity.get("key_outputs"))}</p></section>
<section class="panel"><h3>上下游断言</h3>
{table(["对端实体", "谓词", "评审"], assertion_rows)}</section>"""

    content = (
        hero
        + _intel_tabs("sectors")
        + definition
        + f"""
<section class="panel" style="margin-top:1rem"><h3>核心与追踪企业</h3>
{table(["企业", "法定名称", "区域", "阶段", "分层"], company_rows)}</section>
<section class="grid">
  <div class="panel"><h3>产品</h3>{table(["产品"], product_rows)}</div>
  <div class="panel"><h3>技术</h3>{table(["技术"], tech_rows)}</div>
  <div class="panel"><h3>指标</h3>{table(["指标", "单位"], metric_rows)}</div>
</section>
<section class="panel full"><h3>事件时间线</h3>
{table(["事件", "日期"], event_rows)}</section>
<section class="panel full"><h3>已评审影响路径</h3>
{table(["影响", "目标", "类型", "方向"], impact_rows)}</section>
<section class="grid">
  <div class="panel"><h3>活跃观点</h3>{table(["观点", "评审"], thesis_rows)}</div>
  <div class="panel"><h3>预测</h3>{table(["预测", "状态"], forecast_rows)}</div>
</section>
<section class="panel full"><h3>成员覆盖完整度</h3>
<table><thead><tr><th>企业</th><th>身份</th><th>证据</th><th>关联</th></tr></thead>
<tbody>{''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in member_flag_rows)}</tbody></table>
</section>"""
    )
    return shell(f"{obj.object_id} · 板块", content)


def _impact_page(
    repo: DashboardRepository,
    *,
    start_id: str | None = None,
    max_depth: int = 3,
) -> str:
    snapshot = impact_explorer_snapshot(
        repo.root,
        start_id=start_id,
        max_depth=max_depth,
    )
    direct_rows = [
        [
            esc(row["assertion_id"]),
            esc(row["source_id"]),
            esc(row["target_id"]),
            esc(row["predicate"] or row["impact_type"]),
            esc(row["mechanism"]),
            esc(", ".join(row["evidence_ids"]) or "—"),
            f"{esc(row['direction'])} / {esc(row['horizon'])}",
            esc(row["confidence"]),
        ]
        for row in snapshot["direct_assertions"]
    ]
    path_rows = []
    for path in snapshot["paths"]:
        hop_lines = []
        for hop in path["hops"]:
            evidence = ", ".join(hop["evidence_ids"]) or "—"
            hop_lines.append(
                "<li>"
                f"{esc(hop['source_id'])} → {esc(hop['target_id'])} · "
                f"{esc(hop['predicate'])}<br>"
                f"{esc(hop['mechanism'])}<br>Evidence: {esc(evidence)}"
                "</li>"
            )
        path_rows.append(
            [
                esc(path["trigger_event_id"]),
                esc(" → ".join(path["entity_sequence"])),
                f"<ol>{''.join(hop_lines)}</ol>",
                esc(path["weakest_confidence"]),
                esc(path["variant_count"]),
            ]
        )
    pruning_rows = [
        [esc(row.get("reason")), esc(row.get("at")), esc(row)]
        for row in snapshot["pruning_reasons"]
    ]
    conflict_rows = [
        [
            esc(row["target_id"]),
            esc(", ".join(row["directions_present"])),
            esc(", ".join(row["horizons_present"])),
            esc(", ".join(row["conflicts"])),
        ]
        for row in snapshot["conflicts"]
    ]

    def text_list(values: list[str], empty: str) -> str:
        if not values:
            return f"<p class='muted'>{esc(empty)}</p>"
        return "<ul>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"

    content = f"""<section class="hero"><div>
<div class="eyebrow">影响引擎</div><h2>Impact Explorer</h2>
<p>reviewed 直接断言与 1–3 跳解释路径分区展示；正反方向和不同 horizon 不静默合并。</p>
</div><div><div class="eyebrow">最弱环节置信度</div>
<h2>{esc(len(snapshot['paths']))}</h2><p class="muted">可解释路径</p></div></section>
<section class="metrics">
<div class="metric"><strong>{esc(snapshot['total_assertions'])}</strong><span>全部断言</span></div>
<div class="metric"><strong>{esc(snapshot['pending_assertions'])}</strong><span>pending</span></div>
<div class="metric"><strong>{esc(len(snapshot['direct_assertions']))}</strong><span>reviewed 直接断言</span></div>
<div class="metric"><strong>{esc(len(snapshot['conflicts']))}</strong><span>冲突</span></div>
</section>
<section class="panel"><h3>直接断言</h3>
{table(["ID", "触发", "Target", "谓词/类型", "机制", "Evidence", "方向/Horizon", "置信度"], direct_rows) if direct_rows else "<p class='muted'>当前无 reviewed 直接断言；pending 断言未混入。</p>"}</section>
<section class="panel"><h3>1–3 跳路径</h3>
{table(["Event", "实体序列", "每跳机制与 Evidence", "最弱环节置信度", "变体"], path_rows) if path_rows else "<p class='muted'>当前 reviewed 关系未形成可展开路径。</p>"}</section>
<section class="grid">
<div class="panel"><h3>剪枝原因</h3>{table(["原因", "位置", "详情"], pruning_rows) if pruning_rows else "<p class='muted'>无剪枝。</p>"}</div>
<div class="panel"><h3>冲突信号</h3>{table(["Target", "方向", "Horizon", "冲突"], conflict_rows) if conflict_rows else "<p class='muted'>未检测到正负或多时间跨度冲突。</p>"}</div>
<div class="panel"><h3>反向因素</h3>{text_list(snapshot['countervailing_factors'], 'reviewed 断言暂无反向因素。')}</div>
<div class="panel"><h3>替代解释</h3>{text_list(snapshot['alternative_explanations'], 'reviewed 断言暂无替代解释。')}</div>
</section>
<p class="muted">C-018 已批准；路径查询只读，不自动提升 pending Assertion。</p>"""
    return shell("影响", content)


_ANALYSIS_INPUT_FIELDS = (
    "input_source_ids",
    "input_event_ids",
    "input_impact_ids",
    "input_thesis_ids",
)


def _analysis_input_link(
    by_id: dict[str, ResearchObject], object_id: str
) -> str:
    obj = by_id.get(object_id)
    if obj is None:
        return esc(object_id)
    plural = {
        "impact_assertion": "impact",
        "analysis_run": "analysis/runs",
        "analysis_mode": "analysis/modes",
    }.get(obj.object_type, object_url(obj))
    return f'<a href="/{plural}/{obj.object_id}">{esc(obj.object_id)}</a>'


def _run_link(obj: ResearchObject) -> str:
    return f'<a href="/analysis/runs/{obj.object_id}">{esc(obj.object_id)}</a>'


def _mode_link(obj: ResearchObject) -> str:
    return f'<a href="/analysis/modes/{obj.object_id}">{esc(obj.object_id)}</a>'


def _forecast_link(obj: ResearchObject) -> str:
    return f'<a href="/decision/forecast/{obj.object_id}">{esc(obj.object_id)}</a>'


def _val_link(obj: ResearchObject) -> str:
    return f'<a href="/decision/valuation/{obj.object_id}">{esc(obj.object_id)}</a>'


def _rec_link(obj: ResearchObject) -> str:
    return f'<a href="/decision/recommendation/{obj.object_id}">{esc(obj.object_id)}</a>'


def _res_link(obj: ResearchObject) -> str:
    return f'<a href="/decision/resolution/{obj.object_id}">{esc(obj.object_id)}</a>'


def _analysis_page(
    repo: DashboardRepository,
    *,
    run_ids: list[str] | None = None,
) -> str:
    selected_ids = list(dict.fromkeys(run_ids or []))[:2]
    snapshot = analysis_workspace_snapshot(
        repo.root,
        run_ids=selected_ids if selected_ids else None,
    )
    all_snapshot = (
        analysis_workspace_snapshot(repo.root) if selected_ids else snapshot
    )
    selected = set(selected_ids)
    selector = "".join(
        "<label style='display:block'>"
        f"<input type='checkbox' name='run' value='{esc(row['run_id'])}'"
        f"{' checked' if row['run_id'] in selected else ''}> "
        f"{esc(row['run_id'])} · {esc(row['mode_id'])}</label>"
        for row in all_snapshot["runs"][:20]
    )
    run_rows = []
    evaluator_rows = []
    for row in snapshot["runs"][:10]:
        inputs = [
            object_id
            for values in row["input_ids"].values()
            for object_id in values
        ]
        run_rows.append(
            [
                f'<a href="/analysis/runs/{esc(row["run_id"])}">{esc(row["run_id"])}</a>',
                esc(", ".join(inputs) or "—"),
                esc(row["mode_id"]),
                f"mode v{esc(row['mode_version'])}<br>model {esc(row['model_version'])}<br>template {esc(row['template_version'])}",
                f"input {esc(row['input_snapshot_hash'])}<br>prompt {esc(row['prompt_hash'])}<br>output {esc(row['output_hash'])}",
                badge(row["review_status"], warning=row["review_status"] == "pending"),
            ]
        )
        scores = row["evaluator_scores"]
        evaluator_rows.append(
            [
                esc(row["run_id"]),
                f"{float(scores['overall']):.2f}",
                badge("pass" if scores["gate_pass"] else "review", warning=not scores["gate_pass"]),
                esc(
                    ", ".join(
                        f"{item['label']}={item['score']:.2f}"
                        for item in scores["dimensions"]
                    )
                ),
            ]
        )
    comparison = snapshot["comparison"] or {
        "shared_facts": [],
        "evidence_omitted": {},
        "conflicting_signals": [],
    }
    shared = ", ".join(comparison["shared_facts"]) or "—"
    omitted_rows = [
        [esc(run_id), esc(", ".join(values) or "—")]
        for run_id, values in comparison["evidence_omitted"].items()
    ]
    conflict_rows = [
        [esc(values[0]), esc(values[1]), esc(values[2]), esc(values[3])]
        for values in comparison["conflicting_signals"]
    ]
    metrics = snapshot["mode_metrics"]
    metrics_rows = [
        [
            esc(slug),
            esc(stats["run_count"]),
            esc(f"{stats['edit_distance']:.2f}"),
            esc(
                f"{stats['agreement']:.2f}"
                if stats["agreement"] is not None
                else "—"
            ),
            esc(stats["evidence_omitted"]),
        ]
        for slug, stats in metrics["modes"].items()
    ]
    metrics_panel = (
        '<section class="panel"><h3>模式指标（D-018）</h3>'
        + (
            table(
                ["模式", "运行数", "输出多样性", "一致性", "证据遗漏"],
                metrics_rows,
            )
            if metrics_rows
            else "<p class='muted'>尚无 completed 运行。</p>"
        )
        + "</section>"
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">分析工作区</div><h2>Analysis Workspace</h2>
<p>冻结输入、版本、哈希与 Evaluator 结果均来自不可变 Run；比较不自动形成 Thesis 或 Recommendation。</p>
</div><div><div class="eyebrow">Runs</div><h2>{esc(len(all_snapshot['runs']))}</h2>
<p class="muted">mode families {esc(metrics['overall']['modes'])}</p></div></section>
<section class="panel"><h3>选择 Runs 比较</h3><form method="get" action="/analysis">
{selector}<button type="submit">比较所选</button></form><p class="muted">最多比较前两个所选 Run。</p></section>
<section class="panel"><h3>冻结输入 · 版本与哈希</h3>
{table(["Run", "冻结输入", "Mode", "版本", "输入 / Prompt / Output hashes", "评审"], run_rows) if run_rows else "<p class='muted'>尚无 Analysis Run。</p>"}</section>
<section class="panel"><h3>Evaluator 分数</h3>
{table(["Run", "Overall", "Gate", "维度"], evaluator_rows) if evaluator_rows else "<p class='muted'>无可评估 Run。</p>"}</section>
{metrics_panel}
<section class="grid">
<div class="panel"><h3>共享事实</h3><p>{esc(shared)}</p></div>
<div class="panel"><h3>遗漏 Evidence</h3>{table(["Run", "其他 Run 使用但本 Run 遗漏"], omitted_rows) if omitted_rows else "<p class='muted'>选择两个 Run 后显示。</p>"}</div>
<div class="panel"><h3>冲突信号</h3>{table(["Run A", "信号", "Run B", "信号"], conflict_rows) if conflict_rows else "<p class='muted'>未检测到相反结论信号，或尚未选择比较。</p>"}</div>
</section>
<p class="muted"><a href="/analysis/runs">全部运行</a> · <a href="/analysis/modes">全部模式</a> · <a href="/analysis/compare">模式比较</a> · <a href="/analysis/metrics">模式指标</a></p>"""
    return shell("分析", content)


def _decision_page(repo: DashboardRepository) -> str:
    snapshot = decision_desk_snapshot(repo.root, as_of=date.today().isoformat())
    open_rows = [
        [
            f'<a href="/decision/forecast/{esc(row["id"])}">{esc(row["id"])}</a>',
            esc(row["question"]),
            esc(row["horizon"]),
            esc(row["resolution_date"]),
        ]
        for row in snapshot["open_forecasts"]
    ]
    due_ids = {row["id"] for row in snapshot["due_forecasts"]}
    overdue_ids = {row["id"] for row in snapshot["overdue_forecasts"]}
    due_rows = [
        [
            f'<a href="/decision/forecast/{esc(row["id"])}">{esc(row["id"])}</a>',
            esc(row["resolution_date"]),
            badge("overdue" if row["id"] in overdue_ids else "due", warning=True),
        ]
        for row in snapshot["due_forecasts"]
    ]
    valuation_rows = [
        [
            f'<a href="/decision/valuation/{esc(row["id"])}">{esc(row["id"])}</a>',
            esc(row["company_id"]),
            esc(row["age_days"]),
            esc(row["threshold_days"]),
            badge(row["freshness"], warning=row["freshness"] == "stale"),
        ]
        for row in snapshot["valuations"]
    ]
    recommendation_rows = []
    for row in snapshot["recommendations"]:
        recommendation_rows.append(
            [
                f'<a href="/decision/recommendation/{esc(row["id"])}">{esc(row["id"])}</a>',
                esc(row["company_id"]),
                esc(row["research_posture"]),
                esc(row["direction"]),
                esc("; ".join(row["catalysts"]) or "—"),
                esc("; ".join(row["falsification_conditions"]) or "—"),
                esc("; ".join(row["risks"]) or "—"),
                esc("; ".join(row["unknowns"]) or "—"),
                esc(", ".join(row["scenario_references"]) or "—"),
            ]
        )
    resolution_rows = [
        [
            f'<a href="/decision/resolution/{esc(row["id"])}">{esc(row["id"])}</a>',
            esc(row["forecast_id"]),
            esc(row["resolved_at"]),
            badge(row["decision"]),
            esc(", ".join(row["resolution_source_ids"]) or "—"),
        ]
        for row in snapshot["resolution_history"]
    ]
    calibration = snapshot["calibration"]
    calibration_label = (
        "样本不足，暂不排名"
        if calibration["status"] == "insufficient_sample"
        else "仅作描述性校准"
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">决策工作区</div><h2>Forecast &amp; Decision Desk</h2>
<p>Forecast、估值和 Recommendation 只读组合；Resolution 只记录自然到期后的真实结果。</p>
</div><div><div class="eyebrow">Open Forecast</div><h2>{esc(len(snapshot['open_forecasts']))}</h2>
<p class="muted">as of {esc(snapshot['as_of'])}</p></div></section>
<section class="metrics">
<div class="metric"><strong>{esc(len(snapshot['open_forecasts']))}</strong><span>Open Forecast</span></div>
<div class="metric"><strong>{esc(len(due_ids))}</strong><span>Due</span></div>
<div class="metric"><strong>{esc(len(overdue_ids))}</strong><span>Overdue</span></div>
<div class="metric"><strong>{esc(len(snapshot['resolution_history']))}</strong><span>Resolution</span></div>
</section>
<section class="panel"><h3>Open Forecast</h3>{table(["ID", "问题", "Horizon", "Resolution date"], open_rows)}</section>
<section class="panel"><h3>到期提醒 · Due / Overdue</h3>{table(["Forecast", "Resolution date", "状态"], due_rows) if due_rows else "<p class='muted'>当前没有到期 Forecast。</p>"}</section>
<section class="panel"><h3>校准样本</h3><p><strong>{esc(calibration_label)}</strong></p>
<p>reviewed Resolution n={esc(calibration['n_resolutions'])}；Brier/coverage/timeliness 仅在真实样本存在时解释。</p></section>
<section class="panel"><h3>估值新鲜度</h3>{table(["Valuation", "公司", "年龄(天)", "阈值(天)", "状态"], valuation_rows)}</section>
<section class="panel"><h3>催化剂与证伪条件</h3>
{table(["Recommendation", "公司", "姿态", "方向", "催化剂", "证伪条件", "风险", "未知", "Scenario 引用"], recommendation_rows)}</section>
<section class="grid">
<div class="panel"><h3>风险与未知</h3><p>风险和 unknowns 保留在每条 Recommendation 行内，不自动净额化。</p></div>
<div class="panel"><h3>Scenario 引用</h3><p>只展示已记录引用；空值显示为 —，不推断情景。</p></div>
</section>
<section class="panel"><h3>Resolution 历史</h3>
{table(["Resolution", "Forecast", "Resolved at", "Decision", "Sources"], resolution_rows) if resolution_rows else "<p class='muted'>尚无 Resolution；等待首批 Forecast 自然到期，不回填或合成 outcome。</p>"}</section>"""
    return shell("决策", content)


def _decision_detail(
    repo: DashboardRepository,
    object_id: str,
    *,
    title: str,
) -> str:
    objects, _ = repo.all()
    obj = next((o for o in objects if o.object_id == object_id), None)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"未知对象 {object_id}")
    body = html.escape(obj.body)[:6000] or "（无正文）"
    meta_lines = "".join(
        f"<tr><td>{esc(key)}</td><td>{esc(value)}</td></tr>"
        for key, value in sorted(obj.metadata.items())
        if not isinstance(value, list)
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">{esc(title)}</div><h2>{esc(object_id)}</h2>
</div></section>
<section class="panel"><h3>元数据</h3>
<table><tbody>{meta_lines}</tbody></table></section>
<section class="panel"><pre>{body}</pre></section>"""
    return shell(f"{title} · {object_id}", content)


def _analysis_metrics_panel(objects: list[ResearchObject]) -> str:
    metrics = mode_metrics(objects)
    mm_rows: list[list[str]] = []
    for slug, stats in metrics["modes"].items():
        agreement = (
            f"{stats['agreement']:.2f}" if stats["agreement"] is not None else "—"
        )
        mm_rows.append(
            [
                _mode_link(next(o for o in objects if o.object_type == "analysis_mode"
                               and mode_slug(o.object_id) == slug)),
                esc(stats["run_count"]),
                esc(f"{stats['edit_distance']:.2f}"),
                esc(agreement),
                esc(stats["evidence_omitted"]),
            ]
        )
    return (
        '<section class="panel"><h3>模式指标（D-018）</h3>'
        + (
            table(
                ["模式", "运行数", "输出多样性", "一致性", "证据遗漏"],
                mm_rows,
            )
            if mm_rows
            else "<p class='muted'>尚无 completed 运行。</p>"
        )
        + '<p class="muted">输出多样性=edit（1 完全不同/0 完全相同）；一致性=同证据 run 对信号一致率；证据遗漏=他 mode 用过而本 mode 未用的证据数。</p>'
        + "</section>"
    )


def _analysis_modes(repo: DashboardRepository) -> str:
    objects, _ = repo.all()
    modes = sorted(
        (o for o in objects if o.object_type == "analysis_mode"),
        key=lambda o: o.object_id,
    )
    rows: list[list[str]] = []
    for m in modes:
        meta = mode_metadata(m)
        try:
            require_runnable(objects, m.object_id)
            runnable = "可运行"
        except ValueError:
            runnable = "阻塞"
        rows.append(
            [
                _mode_link(m),
                esc(meta["name"]),
                esc(", ".join(meta["applicable_scopes"])),
                badge(
                    meta["status"],
                    warning=meta["status"] != "active",
                ),
                badge(
                    meta["review_status"],
                    warning=meta["review_status"] != "reviewed",
                ),
                badge(runnable),
                esc(mode_version(m.object_id)),
            ]
        )
    content = f"""<section class="hero"><div>
<div class="eyebrow">分析工作区</div><h2>分析模式</h2>
<p>版本化契约：active + reviewed 方可产生新的权威运行。</p>
</div></section>
<section class="panel">{table(["模式", "名称", "范围", "状态", "评审", "运行", "版本"], rows) if rows else "<p class='muted'>尚无模式。</p>"}</section>"""
    return shell("分析 · 模式", content)


def _analysis_mode_detail(repo: DashboardRepository, mode_id: str) -> str:
    objects, _ = repo.all()
    mode = next(
        (
            o
            for o in objects
            if o.object_type == "analysis_mode" and o.object_id == mode_id
        ),
        None,
    )
    if mode is None:
        raise KeyError(mode_id)
    meta = mode_metadata(mode)
    questions = "".join(f"<li>{esc(q)}</li>" for q in meta["required_questions"])
    sections = "".join(
        f"<li>{esc(s)}</li>" for s in meta["required_output_sections"]
    )
    banned = "".join(
        f"<li>{esc(c)}</li>" for c in meta["prohibited_conclusions"]
    )
    rows = [
        ["状态", badge(meta["status"], warning=meta["status"] != "active")],
        [
            "评审",
            badge(
                meta["review_status"],
                warning=meta["review_status"] != "reviewed",
            ),
        ],
        ["生效自", esc(meta["valid_from"] or "—")],
        ["适用范围", esc(", ".join(meta["applicable_scopes"]) or "—")],
        ["必填输入", esc(", ".join(meta["required_input_types"]) or "—")],
        ["可选输入", esc(", ".join(meta["optional_input_types"]) or "—")],
        ["时间视野", esc(", ".join(meta["time_horizons"]) or "—")],
        ["Output 契约", esc(meta["output_schema_path"] or "—")],
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">分析工作区</div><h2>{esc(mode_id)}</h2>
<p>{esc(meta["name"])}</p>
</div></section>
<section class="panel"><h3>Purpose</h3><p>{esc(meta["purpose"] or "—")}</p></section>
<section class="grid">
<div class="panel">{_kv_table(rows)}</div>
<div class="panel"><h3>必答问题</h3><ul>{questions or "<li class='muted'>—</li>"}</ul>
<h3>必输分区</h3><ul>{sections or "<li class='muted'>—</li>"}</ul></div>
<div class="panel full"><h3>政策</h3>
<table><thead><tr><th>项</th><th>内容</th></tr></thead><tbody>
<tr><td>假设</td><td>{esc(meta["assumption_policy"] or "—")}</td></tr>
<tr><td>证据</td><td>{esc(meta["evidence_policy"] or "—")}</td></tr>
<tr><td>反证</td><td>{esc(meta["counterevidence_policy"] or "—")}</td></tr>
</tbody></table></div>
<div class="panel full"><h3>禁止结论</h3><ul>{banned or "<li class='muted'>—</li>"}</ul></div>
</section>"""
    return shell(f"分析 {mode_id}", content)


def _analysis_runs(repo: DashboardRepository) -> str:
    objects, _ = repo.all()
    runs = sorted(
        (o for o in objects if o.object_type == "analysis_run"),
        key=lambda o: o.object_id,
    )
    rows = [
        [
            _run_link(o),
            esc(o.metadata.get("mode_id", "")),
            esc(o.metadata.get("as_of", "")),
            badge(o.metadata.get("status", "")),
            badge(
                o.metadata.get("review_status", ""),
                warning=o.metadata.get("review_status") == "pending",
            ),
            esc(len(o.metadata.get("input_event_ids", []) or [])),
        ]
        for o in runs
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">分析工作区</div><h2>分析运行</h2>
<p>每次运行冻结输入、模式版本、模型参数与输出哈希；失败不留半成品。</p>
</div></section>
<section class="panel">{table(["Run", "模式", "as-of", "状态", "评审", "事件数"], rows) if rows else "<p class='muted'>尚无分析运行。</p>"}</section>"""
    return shell("分析 · 运行", content)


def _analysis_run_detail(repo: DashboardRepository, run_id: str) -> str:
    objects, _ = repo.all()
    by_id = {obj.object_id: obj for obj in objects}
    run = by_id.get(run_id)
    if run is None or run.object_type != "analysis_run":
        raise KeyError(run_id)
    mode = by_id.get(str(run.metadata.get("mode_id", "")))
    mode_cell = _mode_link(mode) if mode else esc(run.metadata.get("mode_id", ""))
    inputs: list[str] = []
    for field in _ANALYSIS_INPUT_FIELDS:
        ids = run.metadata.get(field, []) or []
        if ids:
            links = " · ".join(
                _analysis_input_link(by_id, str(value)) for value in ids
            )
            inputs.append(f"<dt>{esc(field)}</dt><dd>{links}</dd>")
    input_block = "".join(inputs) or "<p class='muted'>无冻结输入</p>"
    rows = [
        ["模式", mode_cell],
        ["as-of", esc(run.metadata.get("as_of", ""))],
        ["状态", badge(run.metadata.get("status", ""))],
        [
            "评审",
            badge(
                run.metadata.get("review_status", ""),
                warning=run.metadata.get("review_status") == "pending",
            ),
        ],
        [
            "模型",
            f"{esc(run.metadata.get('model_provider', ''))} / "
            f"{esc(run.metadata.get('model_id', ''))}",
        ],
        ["输入快照", esc(run.metadata.get("input_snapshot_hash", "") or "—")],
        ["Prompt 哈希", esc(run.metadata.get("prompt_hash", "") or "—")],
        ["输出哈希", esc(run.metadata.get("output_hash", "") or "—")],
        ["生成方式", esc(run.metadata.get("generation_method", "") or "—")],
    ]
    eval_rows: list[list[str]] = []
    eval_gate = "—"
    try:
        card = evaluate_run(objects, run_id)
        eval_rows = [
            [
                esc(dimension.label),
                esc(f"{dimension.score:.2f}"),
                badge("达标" if dimension.passed else "未达标",
                      warning=not dimension.passed),
            ]
            for dimension in card.dimensions
        ]
        eval_gate = badge("PASS" if card.gate_pass else "FAIL",
                          danger=not card.gate_pass)
    except ValueError:
        pass
    eval_block = (
        table(["维度", "分数", "达标"], eval_rows)
        if eval_rows
        else "<p class='muted'>—</p>"
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">分析运行</div><h2>{esc(run_id)}</h2>
<p>{mode_cell} · as-of {esc(run.metadata.get("as_of", ""))}</p>
</div><div><div class="eyebrow">确定性 Gate</div><h2>{eval_gate}</h2>
<p class="muted"><a href="/analysis/eval?run={esc(run_id)}">人工评估包</a></p></div></section>
<section class="grid">
<div class="panel"><h3>冻结元数据</h3>{_kv_table(rows)}</div>
<div class="panel"><h3>输入引用</h3><dl>{input_block}</dl></div>
<div class="panel full"><h3>确定性评分（D-017）</h3>{eval_block}</div>
<div class="panel full"><h3>正文</h3><pre>{esc(run.body)}</pre></div>
</section>
<p class="muted"><a href="/analysis/compare?runs={esc(run_id)}">与此运行比较</a></p>"""
    return shell(f"分析 {run_id}", content)


def _analysis_compare(repo: DashboardRepository, run_ids: list[str]) -> str:
    objects, _ = repo.all()
    if not run_ids:
        run_ids = sorted(
            o.object_id
            for o in objects
            if o.object_type == "analysis_run"
        )
    by_id = {obj.object_id: obj for obj in objects}
    report = compare_runs(objects, run_ids)
    if not report.runs:
        content = (
            "<section class='panel'><p class='muted'>没有可比较的运行。"
            "用 ?runs=ANL-x,ANL-y 指定，或先产生多个运行。</p></section>"
        )
        return shell("分析 · 比较", content)
    run_rows = [
        [
            _run_link(by_id[run.run_id]),
            esc(run.mode_slug),
            esc(run.as_of),
            badge(run.review_status),
            badge(run.signal),
            esc(", ".join(run.evidence_ids)),
        ]
        for run in report.runs
    ]
    conflicts = "".join(
        f"<li><strong>{esc(a)}</strong>（{esc(sa)}）↔ "
        f"<strong>{esc(b)}</strong>（{esc(sb)}）</li>"
        for a, sa, b, sb in report.conflicting_signals
    )
    omitted = "".join(
        f"<li><strong>{esc(run_id)}</strong>: {esc(', '.join(om) or '—')}</li>"
        for run_id, om in report.evidence_omitted.items()
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">分析工作区</div><h2>模式比较</h2>
<p>浮出共享事实、证据遗漏与冲突信号；禁止多数投票，综合权重来自证据质量/机制完整性/范围适配/校准历史或人工判断。</p>
</div></section>
<section class="panel"><h3>运行</h3>
{table(["Run", "模式", "as-of", "评审", "信号", "证据"], run_rows)}</section>
<section class="grid">
<div class="panel"><h3>共享事实</h3><p>{esc(', '.join(report.shared_facts) or '—')}</p>
<h3>时间视野</h3><p>{esc(', '.join(report.time_horizons) or '—')}</p></div>
<div class="panel"><h3>证据遗漏（别 run 用了、本 run 没用）</h3><ul>{omitted or "<li class='muted'>—</li>"}</ul></div>
<div class="panel full"><h3>冲突信号（启发式，需人工复核）</h3><ul>{conflicts or "<li class='muted'>无</li>"}</ul></div>
</section>"""
    return shell("分析 · 比较", content)


def _llm_page() -> str:
    config = llm_config.load_config()
    public = llm_config.public_config(config)
    current_provider = public["provider"]
    current_model = public["model"]
    provider_options = "".join(
        f'<option value="{esc(p.id)}"{" selected" if p.id == current_provider else ""}>'
        f"{esc(p.name)}</option>"
        for p in provider_catalog.PROVIDER_CATALOG
    )
    key_hint = (
        f'<span class="muted">当前 Key：{esc(public["key_masked"])}'
        f'（{esc("已配置" if public["has_api_key"] else "未配置")}）</span>'
        if public["has_api_key"]
        else '<span class="muted">尚未配置 API Key。</span>'
    )
    model_selected = (
        f'<option value="{esc(current_model)}" selected>{esc(current_model)}</option>'
        if current_model
        else '<option value="">— 先加载模型 —</option>'
    )
    llm_provider_json = json.dumps(
        [
            {
                "id": p.id,
                "name": p.name,
                "api_key_url": p.api_key_url,
                "default_model": p.default_model,
                "recommended_models": p.recommended_models,
            }
            for p in provider_catalog.PROVIDER_CATALOG
        ],
        ensure_ascii=False,
    )
    content = f"""<section class="hero"><div>
<div class="eyebrow">LLM 配置</div><h2>模型供应商</h2>
<p>Base URL 与 API 协议由供应商预设决定，无需手填；API Key 仅保存在服务端。</p>
</div></section>
<section class="panel">
<label for="llm-provider">供应商</label>
<select id="llm-provider" name="provider">{provider_options}</select>

<label for="llm-key">API Key</label>
<div class="llm-row">
  <input id="llm-key" type="password" autocomplete="off"
         placeholder="sk-...（留空表示保留已有 Key）">
  <button type="button" id="llm-key-toggle">显示</button>
  <a id="llm-key-url" href="#" target="_blank" rel="noopener">获取 API Key</a>
</div>
<div id="llm-key-hint">{key_hint}</div>

<label for="llm-model">模型</label>
<div class="llm-row">
  <input id="llm-model-filter" type="text" placeholder="搜索模型…" disabled>
  <select id="llm-model" disabled>{model_selected}</select>
  <button type="button" id="llm-load" disabled>加载模型</button>
</div>

<div class="llm-row">
  <button type="button" id="llm-test">测试连接</button>
  <button type="button" id="llm-save">保存配置</button>
  <span id="llm-status" class="muted"></span>
</div>
</section>
<script>
(function () {{
  const $ = (id) => document.getElementById(id);
  const provider = $("llm-provider");
  const keyInput = $("llm-key");
  const keyUrl = $("llm-key-url");
  const modelFilter = $("llm-model-filter");
  const modelSelect = $("llm-model");
  const loadBtn = $("llm-load");
  const status = $("llm-status");
  const presets = {llm_provider_json};

  function setStatus(text, ok) {{
    status.textContent = text;
    status.className = ok ? "" : "badge danger";
  }}

  function preset() {{
    return presets.find((p) => p.id === provider.value) || {{}};
  }}

  function resetModels() {{
    modelSelect.innerHTML = '<option value="">— 先加载模型 —</option>';
    modelFilter.value = "";
    modelFilter.disabled = true;
    modelSelect.disabled = true;
  }}

  function providerChanged() {{
    const p = preset();
    keyUrl.href = p.api_key_url || "#";
    loadBtn.disabled = !p.id;
    resetModels();
    $("llm-key-hint").textContent = "";
  }}

  provider.addEventListener("change", () => {{
    providerChanged();
    setStatus("供应商已切换，请加载模型", false);
  }});
  $("llm-key-toggle").addEventListener("click", () => {{
    const show = keyInput.type === "password";
    keyInput.type = show ? "text" : "password";
    $("llm-key-toggle").textContent = show ? "隐藏" : "显示";
  }});
  modelFilter.addEventListener("input", () => {{
    const q = modelFilter.value.toLowerCase();
    Array.from(modelSelect.options).forEach((opt) => {{
      opt.hidden = opt.value && !opt.value.toLowerCase().includes(q);
    }});
  }});

  async function post(path, body) {{
    const response = await fetch(path, {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(body),
    }});
    return response.json();
  }}

  loadBtn.addEventListener("click", async () => {{
    setStatus("正在加载模型…", false);
    const body = {{provider: provider.value, api_key: keyInput.value.trim()}};
    const result = await post("/llm/models", body);
    if (!result.models) {{
      setStatus("加载失败：" + (result.error || "未知错误"), false);
      resetModels();
      return;
    }}
    modelSelect.innerHTML = "";
    const groups = {{}};
    result.models.forEach((m) => {{
      (groups[m.ownedBy] = groups[m.ownedBy] || []).push(m.id);
    }});
    Object.keys(groups).sort().forEach((owner) => {{
      const group = document.createElement("optgroup");
      group.label = owner;
      groups[owner].sort().forEach((id) => {{
        const option = document.createElement("option");
        option.value = option.textContent = id;
        group.appendChild(option);
      }});
      modelSelect.appendChild(group);
    }});
    modelFilter.disabled = false;
    modelSelect.disabled = false;
    setStatus("已加载 " + result.models.length + " 个模型", true);
  }});

  $("llm-test").addEventListener("click", async () => {{
    setStatus("正在测试连接…", false);
    const body = {{
      provider: provider.value,
      api_key: keyInput.value.trim(),
      model: modelSelect.value,
    }};
    const result = await post("/llm/test", body);
    setStatus(result.ok ? "✓ " + result.message + "（" + result.latency_ms + "ms）" : "✗ " + result.message, result.ok);
  }});

  $("llm-save").addEventListener("click", async () => {{
    setStatus("正在保存…", false);
    const body = {{
      provider: provider.value,
      api_key: keyInput.value.trim(),
      model: modelSelect.value,
    }};
    const result = await post("/llm/config", body);
    if (result.error) {{
      setStatus("保存失败：" + result.error, false);
      return;
    }}
    setStatus("已保存（" + result.key_masked + "）", true);
    keyInput.value = "";
  }});

  providerChanged();
  if (modelSelect.value) {{
    modelFilter.disabled = false;
    modelSelect.disabled = false;
  }}
}})();
</script>"""
    return shell("模型配置", content)


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

    @app.get("/home", response_class=HTMLResponse)
    def industry_home() -> HTMLResponse:
        try:
            return HTMLResponse(_industry_home(repo))
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

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
        entity: str | None = Query(default=None),
        tier: str | None = Query(default=None),
        min_priority: float | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        show_dups: bool = Query(default=False),
    ) -> HTMLResponse:
        return HTMLResponse(
            _pipeline_queue(
                repo,
                status,
                channel,
                entity,
                tier,
                min_priority,
                limit,
                offset,
                show_dups,
            )
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

    @app.get("/companies", response_class=HTMLResponse)
    def companies() -> HTMLResponse:
        return HTMLResponse(_companies_page(repo))

    @app.get("/sectors", response_class=HTMLResponse)
    def sectors() -> HTMLResponse:
        return HTMLResponse(_sectors_page(repo))

    @app.get("/reports", response_class=HTMLResponse)
    def reports() -> HTMLResponse:
        return HTMLResponse(_reports_page(repo))

    @app.get("/impact", response_class=HTMLResponse)
    def impact_assertions(
        project: str | None = Query(default=None),
        start: str | None = Query(default=None),
        depth: int = Query(default=3, ge=1, le=3),
    ) -> HTMLResponse:
        try:
            return HTMLResponse(
                _impact_page(repo, start_id=start, max_depth=depth)
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/analysis", response_class=HTMLResponse)
    def analysis_overview(
        project: str | None = Query(default=None),
        run: list[str] | None = None,
    ) -> HTMLResponse:
        try:
            return HTMLResponse(_analysis_page(repo, run_ids=run))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/decision", response_class=HTMLResponse)
    def decision_overview(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_decision_page(repo))

    @app.get("/decision/forecast/{object_id}", response_class=HTMLResponse)
    def decision_forecast(object_id: str) -> HTMLResponse:
        return HTMLResponse(
            _decision_detail(repo, object_id, title="Forecast")
        )

    @app.get("/decision/valuation/{object_id}", response_class=HTMLResponse)
    def decision_valuation(object_id: str) -> HTMLResponse:
        return HTMLResponse(
            _decision_detail(repo, object_id, title="Valuation")
        )

    @app.get("/decision/recommendation/{object_id}", response_class=HTMLResponse)
    def decision_recommendation(object_id: str) -> HTMLResponse:
        return HTMLResponse(
            _decision_detail(repo, object_id, title="Recommendation")
        )

    @app.get("/decision/resolution/{object_id}", response_class=HTMLResponse)
    def decision_resolution(object_id: str) -> HTMLResponse:
        return HTMLResponse(
            _decision_detail(repo, object_id, title="Resolution")
        )

    @app.get("/analysis/modes", response_class=HTMLResponse)
    def analysis_modes(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_analysis_modes(repo))

    @app.get("/analysis/runs", response_class=HTMLResponse)
    def analysis_runs(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_analysis_runs(repo))

    @app.get("/analysis/compare", response_class=HTMLResponse)
    def analysis_compare(
        runs: str = Query(default=""),
        project: str | None = Query(default=None),
    ) -> HTMLResponse:
        run_ids = [item.strip() for item in runs.split(",") if item.strip()]
        return HTMLResponse(_analysis_compare(repo, run_ids))

    @app.get("/analysis/eval", response_class=HTMLResponse)
    def analysis_eval(
        run: str = Query(default=""), project: str | None = Query(default=None)
    ) -> HTMLResponse:
        objects, _ = repo.all()
        if not run:
            content = (
                "<section class='panel'><p class='muted'>用 ?run=ANL-xxx 指定运行。</p></section>"
            )
        else:
            try:
                packet = render_evaluation_packet(objects, run)
                content = f'<section class="panel"><pre>{esc(packet)}</pre></section>'
            except ValueError as exc:
                content = f"<section class='panel'><p class='muted'>{esc(str(exc))}</p></section>"
        return HTMLResponse(shell("分析 · 评估包", content))

    @app.get("/analysis/metrics", response_class=HTMLResponse)
    def analysis_metrics(project: str | None = Query(default=None)) -> HTMLResponse:
        objects, _ = repo.all()
        metrics = mode_metrics(objects)
        mm_rows: list[list[str]] = []
        for slug, stats in metrics["modes"].items():
            agreement = (
                f"{stats['agreement']:.2f}" if stats["agreement"] is not None else "—"
            )
            omitted = ", ".join(stats["evidence_omitted_ids"][:10]) or "—"
            if stats["evidence_omitted"] > 10:
                omitted += f" … +{stats['evidence_omitted'] - 10}"
            mm_rows.append(
                [
                    esc(slug),
                    esc(stats["run_count"]),
                    esc(stats["reviewed_count"]),
                    esc(f"{stats['edit_distance']:.2f}"),
                    esc(agreement),
                    esc(stats["evidence_used"]),
                    omitted,
                ]
            )
        content = f"""<section class="hero"><div>
<div class="eyebrow">分析工作区</div><h2>模式指标</h2>
<p>edit=输出多样性（1 完全不同/0 完全相同）；一致性=同证据 run 对信号一致率；证据遗漏=他 mode 用过而本 mode 未用的证据。</p>
</div></section>
<section class="panel">{table(["模式", "运行", "已评审", "输出多样性", "一致性", "证据使用", "证据遗漏"], mm_rows) if mm_rows else "<p class='muted'>尚无 completed 运行。</p>"}</section>"""
        return HTMLResponse(shell("分析 · 模式指标", content))

    @app.get("/analysis/modes/{mode_id}", response_class=HTMLResponse)
    def analysis_mode_detail(mode_id: str) -> HTMLResponse:
        try:
            return HTMLResponse(_analysis_mode_detail(repo, mode_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=mode_id) from exc

    @app.get("/analysis/runs/{run_id}", response_class=HTMLResponse)
    def analysis_run_detail(run_id: str) -> HTMLResponse:
        try:
            return HTMLResponse(_analysis_run_detail(repo, run_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=run_id) from exc

    @app.get("/llm", response_class=HTMLResponse)
    def llm_config_page(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_llm_page())

    @app.get("/llm/config", response_class=JSONResponse)
    def llm_config_get() -> JSONResponse:
        return JSONResponse(llm_config.public_config(llm_config.load_config()))

    @app.post("/llm/config", response_class=JSONResponse)
    def llm_config_save(payload: dict[str, Any]) -> JSONResponse:
        provider_id = str(payload.get("provider", ""))
        try:
            provider_catalog.get_preset(provider_id)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)})
        try:
            saved = llm_config.save_config(
                provider=provider_id,
                api_key=str(payload.get("api_key", "") or ""),
                model=str(payload.get("model", "") or ""),
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)})
        return JSONResponse(llm_config.public_config(saved))

    @app.post("/llm/models", response_class=JSONResponse)
    def llm_models(payload: dict[str, Any]) -> JSONResponse:
        provider_id = str(payload.get("provider", ""))
        try:
            preset = provider_catalog.get_preset(provider_id)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)})
        key = str(payload.get("api_key", "") or "") or llm_config.get_api_key(
            provider=provider_id
        )
        if not key:
            return JSONResponse({"error": "请先填写 API Key"})
        try:
            models = model_fetch.fetch_models(
                base_url=preset.base_url, key=key, timeout=preset.timeout
            )
        except llm_adapter.LLMError as exc:
            return JSONResponse({"error": _llm_human(exc.error_type)})
        return JSONResponse({"models": models})

    @app.post("/llm/test", response_class=JSONResponse)
    def llm_test(payload: dict[str, Any]) -> JSONResponse:
        provider_id = str(payload.get("provider", ""))
        try:
            preset = provider_catalog.get_preset(provider_id)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)})
        key = str(payload.get("api_key", "") or "") or llm_config.get_api_key(
            provider=provider_id
        )
        model = str(payload.get("model", "") or "") or preset.default_model
        if not key:
            return JSONResponse({"error": "请先填写 API Key"})
        result = llm_adapter.test_connection(
            base_url=preset.base_url,
            api_format=preset.api_format,
            key=key,
            model=model,
            timeout=preset.timeout,
        )
        return JSONResponse(result)

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
            obj = repo.one(object_id)
            if obj.object_type == "company":
                return HTMLResponse(_company_detail(repo, obj))
            if obj.object_type == "sector":
                return HTMLResponse(_sector_detail(repo, obj))
            return HTMLResponse(_generic_page(repo, object_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=object_id) from exc

    for prefix in ("events", "companies", "sectors", "reports", "actions", "projects"):
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
        content = f'<section class="panel"><h2>影响关系图</h2><pre>{esc(body)}</pre></section>'
        return HTMLResponse(shell(f"影响 {object_id}", content))

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
