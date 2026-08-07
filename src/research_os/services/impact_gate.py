"""C-018 20-event field gate tooling (Phase 3).

Selects a balanced sample of reviewed Events with direct-impact proposals,
renders a human-review packet, and computes the §11 precision metrics from
recorded judgments.

Sample composition (Phase 3 §11): supply/capacity 5, pricing 3,
product/technology 3, customer/demand 3, financial/capex 2, competition 2,
regulation/other 2. Events are bucketed by the impact_type of their C-004
proposals; shortfalls are reported honestly rather than padded.

The gate is a human judgment: ``render_gate_packet`` produces the review
artifact, max records per-event judgments, and ``gate_metrics`` computes the
thresholds. ``gate_metrics_from_reviews`` derives an approve-rate proxy from
review outcomes automatically.

Pure functions — no file I/O; the packet is returned as a string for the
caller (CLI/docs) to persist.
"""

from __future__ import annotations

from typing import Any

from research_os.domain.models import ResearchObject
from research_os.services.impact_proposal import propose_direct_impacts

# impact_type -> §11 bucket (from IMPACT_RULE_MAP / Phase 3 §11 sample list).
BUCKET_BY_IMPACT: dict[str, str] = {
    "supply": "supply-capacity",
    "capacity": "supply-capacity",
    "price": "pricing",
    "technology": "product-technology",
    "demand": "customer-demand",
    "capex": "financial-capex",
    "competition": "competition",
    "regulation": "regulation-other",
    "other": "regulation-other",
}
QUOTA: dict[str, int] = {
    "supply-capacity": 5,
    "pricing": 3,
    "product-technology": 3,
    "customer-demand": 3,
    "financial-capex": 2,
    "competition": 2,
    "regulation-other": 2,
}

# §11 thresholds.
DIRECT_PRECISION_MIN = 0.85
MECHANISM_BACKED_MIN = 0.95


def gate_sample(
    objects: list[ResearchObject],
    *,
    target: int = 20,
) -> tuple[dict[str, str], list[str]]:
    """Pick a §11-balanced sample of reviewed Events with proposals.

    Returns ({event_id: bucket}, shortfall_report). Greedy: each event is
    assigned to the least-filled bucket it can satisfy. Events whose proposals
    carry no §11 impact_type (or that have no proposals) are skipped.
    """
    scale = target / sum(QUOTA.values())
    quotas = {bucket: round(count * scale) for bucket, count in QUOTA.items()}
    counts = {bucket: 0 for bucket in quotas}
    assigned: dict[str, str] = {}
    events = [
        obj
        for obj in objects
        if obj.object_type == "event"
        and obj.metadata.get("review_status") == "reviewed"
    ]
    for event in sorted(events, key=lambda obj: obj.object_id):
        proposals = propose_direct_impacts(objects, event_id=event.object_id)
        buckets = {
            BUCKET_BY_IMPACT[proposal["impact_type"]]
            for proposal in proposals
            if proposal["impact_type"] in BUCKET_BY_IMPACT
        }
        if not buckets:
            continue
        best = min(buckets, key=lambda bucket: counts[bucket])
        if counts[best] < quotas[best]:
            assigned[event.object_id] = best
            counts[best] += 1
    shortfalls = [
        f"{bucket}: {counts[bucket]}/{quotas[bucket]}"
        for bucket in quotas
        if counts[bucket] < quotas[bucket]
    ]
    return assigned, shortfalls


def render_gate_packet(
    objects: list[ResearchObject],
    *,
    bucket_map: dict[str, str],
) -> str:
    """Render the C-018 review packet for the sample (human review artifact)."""
    by_id = {obj.object_id: obj for obj in objects}
    rows: list[str] = []
    for event_id in sorted(bucket_map):
        event = by_id.get(event_id)
        proposals = propose_direct_impacts(objects, event_id=event_id)
        impact_summary = "; ".join(
            f"{p['target_id']} {p['impact_type']} ({p['direction']})"
            for p in sorted(proposals, key=lambda p: p["target_id"])
        ) or "—"
        title = event.metadata.get("title", "") if event else ""
        rows.append(
            f"| {event_id} | {bucket_map[event_id]} | {title} | "
            f"{impact_summary} | ⬜ |"
        )
    counts = {bucket: 0 for bucket in QUOTA}
    for bucket in bucket_map.values():
        if bucket in counts:
            counts[bucket] += 1
    composition = "\n".join(
        f"| {bucket} | {QUOTA[bucket]} | {counts.get(bucket, 0)} |"
        for bucket in QUOTA
    )
    return f"""# C-018 Field Gate — 20 真实事件人工影响路径核验包

状态：`in_progress`（max 判定；阈值见 Phase 3 §11）
日期：2026-08-07
范围：Phase 3 C-018「20 个真实事件的人工影响路径 Gate」

## 样本组成（§11）

| 桶 | 配额 | 已分配 |
|---|---|---|
{composition}

## 事件审核表

每事件逐项审计五列：target 精度 / mechanism 支撑 / direction 合理 / horizon 合理 /
重大反面路径遗漏。

| Event | 桶 | 事件 | 建议 direct impact（C-004 提案）| Decision |
|---|---|---|---|---|
{chr(10).join(rows)}

## 阈值（§11）

- 直接影响 precision ≥ {DIRECT_PRECISION_MIN:.0%}
- mechanism 无来源外事实 ≥ {MECHANISM_BACKED_MIN:.0%}
- 二跳路径人工保留率 ≥ 60%
- 三跳只作探索，不设高权威阈值
- 所有重大反面路径遗漏必须修复后通过
- 未知项不得被强制赋方向或强度

## 批量审核快捷方式

- 回复「**全部 approve**」：20 事件全部 target/mechanism/direction/horizon 通过。
- 逐项指出修改项（如 `EVT-xxx target 改 ...`）。
"""


def gate_metrics(judgments: list[dict[str, Any]]) -> dict[str, float | bool | int]:
    """C-018: precision metrics from recorded per-event judgments.

    Each judgment: {event_id, direct_precision, mechanism_backed, direction_ok,
    horizon_ok, contrary_omitted} (booleans). Returns rates + pass/fail vs §11.
    """
    total = len(judgments)
    if total == 0:
        return {}

    def rate(key: str) -> float:
        return sum(1 for judgment in judgments if judgment.get(key)) / total

    direct = rate("direct_precision")
    mechanism = rate("mechanism_backed")
    contrary_omissions = sum(
        1 for judgment in judgments if judgment.get("contrary_omitted")
    )
    return {
        "n": total,
        "direct_precision": direct,
        "mechanism_backed": mechanism,
        "direction_ok": rate("direction_ok"),
        "horizon_ok": rate("horizon_ok"),
        "contrary_omissions": contrary_omissions,
        "gate_direct_precision": direct >= DIRECT_PRECISION_MIN,
        "gate_mechanism_backing": mechanism >= MECHANISM_BACKED_MIN,
        "gate_contrary_omissions": contrary_omissions == 0,
    }


def gate_metrics_from_reviews(objects: list[ResearchObject]) -> dict[str, Any]:
    """Approve-rate proxy from review outcomes on materialized IMPs."""
    impacts = [
        obj for obj in objects if obj.object_type == "impact_assertion"
    ]
    if not impacts:
        return {}
    approved = sum(
        1 for obj in impacts if obj.metadata.get("review_status") == "reviewed"
    )
    rejected = sum(
        1 for obj in impacts if obj.metadata.get("review_status") == "rejected"
    )
    return {
        "total": len(impacts),
        "approved": approved,
        "rejected": rejected,
        "approve_rate": approved / len(impacts),
    }
