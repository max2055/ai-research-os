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
from research_os.llm import llm_adapter, llm_config, model_fetch, provider_catalog
from research_os.services.actions import action_rows
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
from research_os.services.mode_metrics import mode_metrics
from research_os.services.ontology import render_impact
from research_os.services.pilot import pilot_status
from research_os.services.projects import objects_for_project
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
      <a href="/{project_query}">概览</a>
      <a href="/reviews{project_query}">评审队列</a>
      <a href="/metrics{project_query}">指标</a>
      <a href="/operations{project_query}">运营</a>
      <a href="/pipeline{project_query}">管线</a>
      <a href="/companies{project_query}">产业</a>
      <a href="/impact{project_query}">影响</a>
      <a href="/analysis{project_query}">分析</a>
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
    hero = f"""
<section class="hero">
  <div>
    <div class="eyebrow">{esc(selected)} · {esc(project.metadata.get("status"))}</div>
    <h2>{esc(project.metadata.get("title"))}</h2>
    <p>{esc(project.metadata.get("research_question"))}</p>
  </div>
  <div>
    <div class="eyebrow">下次评审</div>
    <h2>{esc(project.metadata.get("next_review_date"))}</h2>
    <p class="muted">{esc(project.metadata.get("review_cadence"))} 节奏 · 负责人 {esc(project.metadata.get("owner"))}</p>
  </div>
</section>
<section class="metrics">
  <div class="metric"><strong>{len(by_type["source"])}</strong><span>来源</span></div>
  <div class="metric"><strong>{len(by_type["event"])}</strong><span>事件</span></div>
  <div class="metric"><strong>{len(pending)}</strong><span>待评审</span></div>
  <div class="metric"><strong>{len(open_actions)}</strong><span>未决行动</span></div>
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
    panels = f"""{_candidate_facts(detail)}
<section class="grid" style="margin-top:1rem">
<div class="panel"><h3>实体建议</h3><pre>{esc(json.dumps(entity, ensure_ascii=False, indent=2))}</pre></div>
<div class="panel"><h3>板块建议</h3><pre>{esc(json.dumps(sector, ensure_ascii=False, indent=2))}</pre></div>
</section>
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
    min_priority: float | None,
    limit: int,
    show_dups: bool,
) -> str:
    rows = queue_rows(
        repo.root,
        status=status or "new",
        channel_id=channel or None,
        min_priority=min_priority,
        limit=limit,
        show_dups=show_dups,
    )

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

    body_rows = [
        [
            (
                f"{row['priority_score']:.3f}"
                if row["priority_score"] is not None
                else "—"
            ),
            badge(row["status"]),
            dup_cell(row),
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
    dup_check = " checked" if show_dups else ""
    content = f"""<section class="hero"><div>
<div class="eyebrow">管线 → 队列</div><h2>候选队列</h2>
<p>只读筛选列表。重复簇折叠为单行代表。</p>
</div><div><div class="eyebrow">{esc(status)}</div><h2>{len(rows)}</h2>
<p class="muted">按优先级降序</p></div></section>
<section class="panel" style="margin-bottom:1rem">
<form method="get" action="/pipeline/queue">
<label>状态 <select name="status">{status_options}</select></label>
<label style="margin-left:1rem">通道 <input name="channel" value="{channel_value}"></label>
<label style="margin-left:1rem">最低优先级 <input type="number" step="0.01" min="0" max="1" name="min_priority" value="{min_value}"></label>
<label style="margin-left:1rem">数量 <input type="number" min="1" max="200" name="limit" value="{esc(limit)}"></label>
<label style="margin-left:1rem"><input type="checkbox" name="show_dups" value="1"{dup_check}> 显示重复</label>
<button type="submit">筛选</button>
</form></section>
<section class="panel">{table(["优先级", "状态", "重复", "实体", "板块", "通道", "标题"], body_rows)}</section>"""
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
<div class="eyebrow">{esc(selected)}</div><h2>运营</h2>
<p>从结构化元数据读取逾期行动与到期的研究评审。</p>
</div><div><div class="eyebrow">逾期行动</div><h2>{len(overdue)}</h2>
<p class="muted">截至 {date.today().isoformat()}</p></div></section>
<section class="grid">
<div class="panel"><h3>管线健康</h3>
<p><a href="/pipeline">打开管线看板 →</a></p>
<p class="muted">候选管线 / 通道 / 指标已移至管线页面。</p></div>
<div class="panel"><h3>逾期行动</h3>
{table(["行动", "负责人", "截止", "状态"], open_rows)}</div>
<div class="panel"><h3>到期评审</h3>
{table(["项目", "节奏", "下次评审"], due_rows)}</div>
</section>"""
    return shell("运营", content, project_id=selected)


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
<div class="eyebrow">{esc(selected)}</div><h2>系统健康</h2>
<p>所有值均在请求时从仓库文件重建。</p></div>
<div><div class="eyebrow">状态</div>
<h2>{badge("健康") if not drift and not asset_failures and not job_failures else badge("注意", warning=True)}</h2>
<p class="muted">{len(drift)} 处漂移 · {len(asset_failures)} 个资产失败 ·
{len(job_failures)} 个失败任务</p></div></section>
<section class="panel"><h3>校验发现</h3>
{table(["级别", "编码", "路径", "消息"], finding_rows)}</section>
<section class="panel" style="margin-top:1rem"><h3>失败任务</h3>
{table(["任务", "名称", "消息"], [[object_link(job), esc(job.metadata.get("job_name")), esc(job.metadata.get("message"))] for job in job_failures])}
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


def _impact_page(repo: DashboardRepository) -> str:
    objects, _ = repo.all()
    impacts = sorted(
        (obj for obj in objects if obj.object_type == "impact_assertion"),
        key=lambda obj: obj.object_id,
    )
    pending = sum(1 for o in impacts if o.metadata.get("review_status") == "pending")
    reviewed = sum(1 for o in impacts if o.metadata.get("review_status") == "reviewed")
    events_covered = len({o.metadata.get("subject_id") for o in impacts})
    rows = [
        [
            f"{esc(o.object_id)}<br><span class='muted'>{esc(o.metadata.get('title', ''))}</span>",
            esc(o.metadata.get("subject_id", "")),
            esc(o.metadata.get("target_id", "")),
            esc(o.metadata.get("impact_type", "")),
            badge(o.metadata.get("direction", "")),
            esc(o.metadata.get("horizon", "")),
            esc(o.metadata.get("confidence", "")),
            badge(o.metadata.get("review_status", ""),
                  warning=o.metadata.get("review_status") == "pending"),
        ]
        for o in impacts
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">影响引擎</div><h2>事件 → 影响断言</h2>
<p>仅 reviewed Event 生成；提案默认 pending，人工 review 后转 reviewed。多跳待 C-018 通过后激活。</p>
</div><div><div class="eyebrow">Gate 样本</div>
<h2>{esc(events_covered)}</h2>
<p class="muted">事件覆盖</p></div></section>
<section class="metrics">
<div class="metric"><strong>{esc(len(impacts))}</strong><span>影响断言</span></div>
<div class="metric"><strong>{esc(pending)}</strong><span>待审</span></div>
<div class="metric"><strong>{esc(reviewed)}</strong><span>已审</span></div>
</section>
<section class="panel">{table(["Impact ID", "触发 Event", "Target", "类型", "方向", "Horizon", "置信度", "状态"], rows) if rows else "<p class='muted'>尚无影响断言。</p>"}</section>
<p class="muted"><a href="/reports" style="display:none"></a>C-018 评估包见 <code>05_Research/Reviews/Field_Gate_20_Impact_Packet.md</code>。</p>"""
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


def _analysis_page(repo: DashboardRepository) -> str:
    objects, _ = repo.all()
    modes = [o for o in objects if o.object_type == "analysis_mode"]
    runs = [o for o in objects if o.object_type == "analysis_run"]
    by_status: dict[str, int] = {}
    for run in runs:
        key = str(run.metadata.get("review_status", "")) or "—"
        by_status[key] = by_status.get(key, 0) + 1
    active = sum(1 for m in modes if m.metadata.get("status") == "active")
    latest = sorted(runs, key=lambda o: o.object_id, reverse=True)[:10]
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
        ]
        for o in latest
    ]
    content = f"""<section class="hero"><div>
<div class="eyebrow">分析工作区</div><h2>同一证据 · 多视角复现</h2>
<p>版本化契约模式 + 冻结分析运行；Run ≠ Thesis，仅 reviewed run 可进入报告。</p>
</div><div><div class="eyebrow">模式</div>
<h2>{esc(len(modes))}</h2>
<p class="muted">active {esc(active)} · <a href="/analysis/modes">全部</a></p>
</div></section>
<section class="metrics">
<div class="metric"><strong>{esc(len(runs))}</strong><span>分析运行</span></div>
<div class="metric"><strong>{esc(by_status.get('pending', 0))}</strong><span>待评审</span></div>
<div class="metric"><strong>{esc(by_status.get('reviewed', 0))}</strong><span>已评审</span></div>
<div class="metric"><strong>{esc(by_status.get('rejected', 0))}</strong><span>已拒绝</span></div>
</section>
{_analysis_metrics_panel(objects)}
<section class="panel"><h3>最新运行</h3>
{table(["Run", "模式", "as-of", "状态", "评审"], rows) if rows else "<p class='muted'>尚无分析运行。</p>"}
<p class="muted"><a href="/analysis/runs">全部运行</a> · <a href="/analysis/modes">全部模式</a> · <a href="/analysis/compare">模式比较</a> · <a href="/analysis/metrics">模式指标</a></p>
</section>"""
    return shell("分析", content)


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
        show_dups: bool = Query(default=False),
    ) -> HTMLResponse:
        return HTMLResponse(
            _pipeline_queue(
                repo, status, channel, min_priority, limit, show_dups
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
    def impact_assertions(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_impact_page(repo))

    @app.get("/analysis", response_class=HTMLResponse)
    def analysis_overview(project: str | None = Query(default=None)) -> HTMLResponse:
        return HTMLResponse(_analysis_page(repo))

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
