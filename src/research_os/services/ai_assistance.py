"""Small, human-reviewed AI assistance read models for the web UI.

These helpers intentionally produce suggestions only. They do not change
repository files, candidate state, review status, or scoring decisions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_os.adapters.model import build_adapter
from research_os.domain.models import ResearchObject
from research_os.llm import llm_adapter
from research_os.services.drafts import split_values
from research_os.services.validation import validate_repository

MAX_REVIEW_ASSISTANCE_TARGETS = 10
_REVIEW_TYPES = {"source", "event", "impact_assertion"}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def _review_item(obj: ResearchObject) -> dict[str, Any]:
    meta = obj.metadata
    required_fields = {
        "source": (
            ("publisher", "发布方"),
            ("published_at", "发布日期"),
            ("source_grade", "来源等级"),
            ("canonical_url", "规范 URL"),
        ),
        "event": (
            ("event_date", "事件日期"),
            ("source_ids", "来源 ID"),
            ("confidence", "置信度"),
        ),
        "impact_assertion": (
            ("target_id", "影响对象"),
            ("mechanism", "作用机制"),
            ("evidence_ids", "Evidence ID"),
        ),
    }
    missing = [
        label
        for key, label in required_fields.get(obj.object_type, ())
        if not _string_list(meta.get(key)) and not str(meta.get(key) or "").strip()
    ]
    source_ids = _string_list(meta.get("source_ids"))
    evidence_ids = _string_list(meta.get("evidence_ids"))
    basis = [f"对象类型：{obj.object_type}"]
    if source_ids:
        basis.append("来源：" + ", ".join(source_ids))
    if evidence_ids:
        basis.append("Evidence：" + ", ".join(evidence_ids))
    if missing:
        recommendation = "信息不足"
        reason = "先补齐缺失字段，再由研究者决定是否进入人工评审。"
    elif obj.metadata.get("review_status") == "reviewed":
        recommendation = "保持"
        reason = "对象已完成人工评审，建议仅作为复核提示。"
    else:
        recommendation = "建议人工核验"
        reason = "基础字段和关联依据可供研究者进行人工评审。"
    return {
        "object_id": obj.object_id,
        "object_type": obj.object_type,
        "title": str(meta.get("title") or obj.object_id),
        "review_status": str(meta.get("review_status") or "unknown"),
        "recommendation": recommendation,
        "reason": reason,
        "basis": basis,
        "missing_fields": missing,
    }


def _review_prompt(items: list[dict[str, Any]]) -> str:
    lines = [
        "你是研究者的评审辅助，不得自动批准、拒绝或修改任何文件。",
        "请仅根据下面对象给出简短建议；区分事实、推断和未知，"
        "不能补写来源未提供的事实。",
        "对每个对象输出：对象 ID、建议（批准/要求修改/拒绝/信息不足）、"
        "依据、主要不确定性。",
    ]
    for item in items:
        lines.append(
            f"- {item['object_id']} ({item['object_type']}): "
            f"标题={item['title']}; 当前状态={item['review_status']}; "
            f"规则建议={item['recommendation']}; "
            f"依据={'；'.join(item['basis']) or '无'}; "
            f"缺失={','.join(item['missing_fields']) or '无'}"
        )
    return "\n".join(lines)


def prepare_review_assistance(
    root: Path,
    target_ids: str,
    *,
    provider: str = "",
    model: str = "",
) -> dict[str, Any]:
    """Build a read-only review suggestion packet with a graceful LLM fallback."""
    targets = split_values(target_ids)
    if not targets:
        raise ValueError("请至少选择一个对象")
    if len(targets) > MAX_REVIEW_ASSISTANCE_TARGETS:
        raise ValueError(f"一次最多生成 {MAX_REVIEW_ASSISTANCE_TARGETS} 个对象的建议")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before AI assistance")
    by_id = {obj.object_id: obj for obj in objects}
    unknown = [target_id for target_id in targets if target_id not in by_id]
    if unknown:
        raise ValueError("unknown review target: " + ", ".join(unknown))
    items = [_review_item(by_id[target_id]) for target_id in targets]
    unsupported = [
        item["object_id"] for item in items if item["object_type"] not in _REVIEW_TYPES
    ]
    supported_items = [item for item in items if item["object_type"] in _REVIEW_TYPES]
    result: dict[str, Any] = {
        "mode": "rule_precheck",
        "provider": provider or "未配置",
        "model": model or "未配置",
        "items": items,
        "model_status": "未调用模型：未配置真实供应商，使用规则预检查。",
        "model_output": "",
        "uncertainties": [
            "规则建议不等于事实核验，也不会改变评审状态。",
            "研究者仍需检查原始来源、证据锚点和反面证据。",
        ],
    }
    if unsupported:
        result["uncertainties"].append(
            "以下对象类型暂不提供模型辅助：" + ", ".join(unsupported)
        )
    if provider and provider != "echo" and supported_items:
        try:
            adapter = build_adapter(
                provider, config_path=root / "00_System" / "llm.local.json"
            )
            output = adapter.generate(
                _review_prompt(supported_items),
                timeout=30,
                model_id=model or None,
                # DeepSeek expects numeric sampling parameters in JSON.
                model_parameters={"temperature": 0.2},
            ).strip()
            if output:
                result["mode"] = "llm_plus_rule_precheck"
                result["model_status"] = "已生成模型建议；请人工核验后再评审。"
                result["model_output"] = output
            else:
                result["model_status"] = "模型返回为空，已降级为规则预检查。"
        except llm_adapter.LLMError as exc:
            result["model_status"] = (
                f"模型调用失败（{exc.error_type}）：{exc}；"
                "已降级为规则预检查，仍可继续人工评审。"
            )
        except Exception as exc:  # noqa: BLE001 — assistance must not block review
            result["model_status"] = (
                f"模型调用失败（{type(exc).__name__}），已降级为规则预检查；"
                "仍可继续人工评审。"
            )
    return {"target_ids": targets, **result}


def _source_suggestion(source: ResearchObject) -> dict[str, Any]:
    meta = source.metadata
    missing = [
        label
        for key, label in (
            ("publisher", "发布方"),
            ("published_at", "发布日期"),
            ("source_grade", "来源等级"),
            ("canonical_url", "规范 URL"),
        )
        if not str(meta.get(key) or "").strip()
    ]
    asset_paths = meta.get("asset_paths") or []
    processing = str(meta.get("processing_status") or "")
    review = str(meta.get("review_status") or "")
    if missing or not asset_paths:
        recommendation = "修改"
        reason = "补齐来源出处、等级或原始资产后再进行人工评审。"
    elif review == "reviewed":
        recommendation = "保持"
        reason = "Source 已完成人工评审；建议仅作为复核提示。"
    else:
        recommendation = "建议评审"
        reason = "基础 provenance 字段和资产已存在，可进入人工核验。"
    return {
        "kind": "source_review",
        "mode": "deterministic_precheck",
        "recommendation": recommendation,
        "reason": reason,
        "missing_fields": missing,
        "asset_count": len(asset_paths) if isinstance(asset_paths, list) else 0,
        "processing_status": processing or "unknown",
        "review_status": review or "unknown",
        "uncertainties": [
            "来源等级建议不能替代原始出处核验。",
            "该建议不会提交评审，也不会改变 Source 状态。",
        ],
    }


def source_review_assistance(root: Path, source_id: str) -> dict[str, Any]:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before AI assistance")
    source = next(
        (
            obj
            for obj in objects
            if obj.object_type == "source" and obj.object_id == source_id
        ),
        None,
    )
    if source is None:
        raise KeyError(source_id)
    return {"source_id": source_id, **_source_suggestion(source)}


def candidate_match_explanation(detail: dict[str, Any]) -> dict[str, Any]:
    """Explain the existing deterministic match without inventing IDs."""
    entity = detail.get("entity_proposals") or []
    sectors = detail.get("sector_proposals") or []
    reasons = detail.get("reason_codes") or []
    return {
        "kind": "candidate_match",
        "mode": "deterministic_explanation",
        "entity_candidates": entity,
        "sector_candidates": sectors,
        "reason_codes": reasons,
        "uncertainties": [
            "候选 ID 仅来自 Universe 注册表，仍需人工选择。",
            "重新评分应在人工确认匹配后执行。",
        ],
    }
