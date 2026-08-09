"""D-019 10-case field gate review packet (RCP-v03-007, Phase 4 §11).

Aggregates a case x mode -> run matrix into a human review packet: per-run
D-017 deterministic scorecards, per-case multi-mode comparison (D-011), the
§11 human rubric table and the gate thresholds. No majority voting anywhere —
convergence weight must come from evidence quality / mechanism completeness /
scope fit / calibration history / explicit researcher judgment (§6).

The matrix maps a case label to {mode_slug: run_id}; a run whose mode_id does
not match the slot is reported as a mismatch (defensive, never silently
coerced).
"""

from __future__ import annotations

from typing import Any

from research_os.domain.models import ResearchObject
from research_os.services.analysis_compare import compare_runs, render_compare_report
from research_os.services.analysis_evaluator import (
    EvaluationScorecard,
    evaluate_run,
    render_scorecard,
)

_HUMAN_DIMENSIONS = (
    "引用准确",
    "没有 Source 外事实",
    "模式问题覆盖",
    "反证完整",
    "假设显式",
    "分歧可解释",
    "输出节省研究时间",
    "诱发过度结论（反向计分）",
)


def field_gate_packet(
    objects: list[ResearchObject],
    matrix: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Build the deterministic part of the D-019 packet (pure, read-only)."""
    by_id = {obj.object_id: obj for obj in objects}
    cases: dict[str, Any] = {}
    all_scorecards: list[EvaluationScorecard] = []
    mismatches: list[str] = []
    for case_id in sorted(matrix):
        slots = matrix[case_id]
        scorecards: dict[str, EvaluationScorecard] = {}
        for mode_slug, run_id in slots.items():
            run = by_id.get(run_id)
            if run is None or run.object_type != "analysis_run":
                mismatches.append(f"{case_id}/{mode_slug}: {run_id} missing")
                continue
            try:
                card = evaluate_run(objects, run_id)
            except ValueError as exc:
                mismatches.append(f"{case_id}/{mode_slug}: {exc}")
                continue
            if card.mode_slug != mode_slug:
                mismatches.append(
                    f"{case_id}/{mode_slug}: {run_id} is {card.mode_slug}, "
                    f"slot expects {mode_slug}"
                )
                continue
            scorecards[mode_slug] = card
            all_scorecards.append(card)
        compare = None
        run_ids = [slots[s] for s in slots if s in scorecards]
        if len(run_ids) >= 2:
            compare = compare_runs(objects, run_ids)
        cases[case_id] = {
            "event": _case_event(objects, slots),
            "scorecards": scorecards,
            "compare": compare,
        }
    return {
        "cases": cases,
        "runs": len(all_scorecards),
        "gate_pass": sum(1 for card in all_scorecards if card.gate_pass),
        "overall": (
            sum(card.overall for card in all_scorecards) / len(all_scorecards)
            if all_scorecards
            else 0.0
        ),
        "mismatches": mismatches,
    }


def _case_event(objects: list[ResearchObject], slots: dict[str, str]) -> str:
    """The shared input event of a case's runs (or —)."""
    by_id = {obj.object_id: obj for obj in objects}
    for run_id in slots.values():
        run = by_id.get(run_id)
        if run is None:
            continue
        events = run.metadata.get("input_event_ids", []) or []
        if events:
            return str(events[0])
    return "—"


def render_field_gate_packet(
    objects: list[ResearchObject],
    matrix: dict[str, dict[str, str]],
) -> str:
    """Render the D-019 human review packet (markdown)."""
    packet = field_gate_packet(objects, matrix)
    lines = [
        "# D-019 Field Gate — 10-case 多模式真实比较核验包",
        "",
        "状态：`in_progress`（max 判定；阈值见 Phase 4 §11）",
        "批次：2026-08-09（第一批 3 Sector case × 4 modes，"
        "DeepSeek deepseek-v4-flash）",
        "",
        f"运行 {packet['runs']} 个；确定性 Gate 通过 "
        f"{packet['gate_pass']}/{packet['runs']}；整体均分 {packet['overall']:.3f}",
    ]
    if packet["mismatches"]:
        lines.append("")
        lines.append("## 不匹配告警")
        for mismatch in packet["mismatches"]:
            lines.append(f"- {mismatch}")
    for case_id in sorted(packet["cases"]):
        case = packet["cases"][case_id]
        lines.append("")
        lines.append(f"## Case: {case_id}（事件 {case['event']}）")
        rows = []
        for mode_slug, card in sorted(case["scorecards"].items()):
            dims = {d.key: d.score for d in card.dimensions}
            detail = (
                f"cite {dims.get('citation', 0):.2f} / "
                f"out {dims.get('outside_facts', 0):.0f} / "
                f"sec {dims.get('sections', 0):.2f} / "
                f"q {dims.get('questions', 0):.2f} / "
                f"ce {dims.get('counterevidence', 0):.0f} / "
                f"ph {dims.get('placeholders', 0):.0f}"
            )
            rows.append(
                f"| {card.run_id} | {mode_slug} | {card.overall:.2f} | "
                f"{'PASS' if card.gate_pass else 'FAIL'} | {detail} |"
            )
        header = (
            "| Run | 模式 | 均分 | Gate | "
            "citation/outside/sections/questions/counterev/placeholders |"
        )
        lines.append(header)
        lines.append("|---|---|---|---|---|")
        lines.extend(rows)
        if case["compare"] is not None:
            lines.append("")
            lines.append("多模式比较（D-011）：")
            lines.append(render_compare_report(case["compare"]))
    lines.append("")
    lines.append("## 人工评分表（§11 八维，0-1）")
    lines.append(
        "| Case | Run | 引用准确 | 无外事实 | 问题覆盖 | 反证完整 | "
        "假设显式 | 分歧可解释 | 节省时间 | 过度结论 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for case_id in sorted(packet["cases"]):
        for mode_slug, card in sorted(
            packet["cases"][case_id]["scorecards"].items()
        ):
            cells = " | ".join("⬜" for _ in _HUMAN_DIMENSIONS)
            lines.append(f"| {case_id} | {card.run_id}（{mode_slug}） | {cells} |")
    lines.append("")
    lines.append("## 阈值（§11）")
    lines.append("- 引用/归属 100% 可解析")
    lines.append("- 无 Source 外关键事实")
    lines.append("- 必填问题覆盖 ≥ 90%")
    lines.append("- 关键反证遗漏率 < 10%")
    lines.append("- 人工认为「有增量价值」的 Run ≥ 70%")
    lines.append("- Open Discovery 候选中至少一半可判定 investigate/reject")
    lines.append("- 不使用多数投票产生权威结论")
    return "\n".join(lines)


def render_field_gate_scorecards(
    objects: list[ResearchObject],
    matrix: dict[str, dict[str, str]],
) -> str:
    """Plain-text per-run scorecards (CLI)."""
    packet = field_gate_packet(objects, matrix)
    parts = [f"# D-019 scorecards — {packet['runs']} runs, "
             f"gate {packet['gate_pass']}/{packet['runs']}, "
             f"overall {packet['overall']:.3f}"]
    for case_id in sorted(packet["cases"]):
        for _, card in sorted(packet["cases"][case_id]["scorecards"].items()):
            parts.append("\n" + render_scorecard(card))
    return "\n".join(parts)
