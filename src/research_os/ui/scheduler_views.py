"""Small HTML renderers for scheduler operations."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _options(values: Sequence[tuple[str, str]], selected: str) -> str:
    return "".join(
        f'<option value="{_escape(value)}"'
        f"{' selected' if value == selected else ''}>{_escape(label)}</option>"
        for value, label in values
    )


def schedule_form(
    *,
    action: str,
    csrf_token: str,
    value: Mapping[str, Any] | None = None,
    schedule_id: str | None = None,
    target_options: Sequence[tuple[str, str]] = (),
    project_options: Sequence[tuple[str, str]] = (),
    timezone_options: Sequence[tuple[str, str]] = (),
) -> str:
    item = dict(value or {})

    def val(key: str, default: str = "") -> str:
        return _escape(item.get(key, default))

    jobs = _options(
        [
            ("validate", "Validate"),
            ("discover", "Discover"),
            ("indexes", "Indexes"),
            ("metrics", "Metrics"),
            ("source-process", "Process source"),
            ("refresh", "Refresh"),
            ("expire", "Expire candidates"),
            ("purge", "Purge candidates"),
            ("enrich", "Enrich candidates"),
            ("daily-brief", "Daily brief"),
            ("forecast-alerts", "Forecast alerts"),
            ("backup-candidate", "Candidate backup"),
            ("backup-durable", "Durable backup"),
        ],
        str(item.get("job_name", "validate")),
    )
    units = _options(
        [
            ("minutes", "分钟"),
            ("hours", "小时"),
            ("days", "天"),
            ("weeks", "周"),
        ],
        str(item.get("interval_unit", "hours")),
    )
    missed = _options(
        [("catch_up_once", "补执行一次"), ("skip_missed", "跳过")],
        str(item.get("missed_run_policy", "catch_up_once")),
    )
    targets = _options((("", "无"), *target_options), str(item.get("target", "")))
    projects = _options(
        (("", "全局"), *project_options), str(item.get("project_id", ""))
    )
    timezones = _options(timezone_options, str(item.get("timezone", "Asia/Shanghai")))
    checked = " checked" if bool(item.get("enabled")) else ""
    heading = "编辑计划" if schedule_id else "新建计划"
    return f"""<section class="panel"><h2>{heading}</h2>
<form class="mutation-form" method="post" action="{_escape(action)}">
<input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
<label>名称 <input name="name" required maxlength="120" value="{val("name")}"></label>
<label>Job <select name="job_name">{jobs}</select></label>
<label>目标 <select name="target">{targets}</select></label>
<label>项目 <select name="project_id">{projects}</select></label>
<label>间隔 <input name="interval_value" type="number" min="1" max="1000"
 required value="{val("interval_value", "1")}">
 <select name="interval_unit">{units}</select></label>
<label>时区 <select name="timezone">{timezones}</select></label>
<label>重试次数 <input name="retry_limit" type="number" min="0" max="5"
 value="{val("retry_limit", "2")}"></label>
<label>重试退避秒数 <input name="retry_backoff_seconds" type="number" min="1"
 max="3600" value="{val("retry_backoff_seconds", "30")}"></label>
<label>超时秒数 <input name="timeout_seconds" type="number" min="30" max="86400"
 value="{val("timeout_seconds", "1800")}"></label>
<label>重叠策略 <select name="overlap_policy">
<option value="skip">跳过</option></select></label>
<label>错过执行 <select name="missed_run_policy">{missed}</select></label>
<label><input type="checkbox" name="enabled" value="true"{checked}> 启用</label>
<button type="submit">预览</button></form></section>"""


def schedule_table(rows: Sequence[Any]) -> str:
    body = "".join(
        "<tr>"
        f"<td>{_escape(row.schedule_id)}</td>"
        f"<td>{_escape(row.name)}</td>"
        f"<td>{_escape(row.job_name)}</td>"
        f"<td>{row.interval_seconds}s</td>"
        f"<td>{'启用' if row.enabled else '暂停'}</td>"
        f'<td><a href="/operations/schedules/{_escape(row.schedule_id)}/edit">'
        "编辑</a> "
        f'<a href="/operations/schedules/{_escape(row.schedule_id)}/run-now">'
        "立即运行</a> "
        f'<a href="/operations/schedules/{_escape(row.schedule_id)}/'
        f'{"pause" if row.enabled else "resume"}">'
        f"{'暂停' if row.enabled else '恢复'}</a></td></tr>"
        for row in rows
    )
    if not body:
        body = '<tr><td colspan="6">暂无计划</td></tr>'
    return (
        '<div class="table-scroll"><table><thead><tr><th>ID</th><th>名称</th>'
        "<th>Job</th><th>间隔</th><th>状态</th><th>操作</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


__all__ = ["schedule_form", "schedule_table"]
