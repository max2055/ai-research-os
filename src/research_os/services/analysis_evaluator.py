"""D-017 Analysis Run evaluator (RCP-v03-007, Phase 4 §10/§11).

A completed run gets a DETERMINISTIC scorecard (verifiable from the frozen
run + its mode + the repository) plus a HUMAN rubric review packet for the
researcher to fill during the D-019 field gate.

Deterministic dimensions:

- ``citation`` — fraction of body-cited permanent ids that resolve to a real
  object (§11: citation/attribution 100% 可解析 → target 1.0);
- ``outside_facts`` — 1.0 iff every cited evidence-type object is a declared
  input; citing an id outside the frozen inputs breaks evidence grounding → 0.0
  (hard gate, the run transaction already refuses this via CON004);
- ``sections`` — fraction of (shared output-contract sections + mode
  required_output_sections) that are present AND non-empty;
- ``questions`` — fraction of the mode's required_questions addressed by
  distinctive CJK content tokens in the body. A conservative deterministic
  heuristic: a question is ``addressed`` iff at least one of its content
  bigrams appears in the run body. Questions whose content tokens are all
  stopwords are excluded (honestly un-checkable). §11 target ≥ 90%;
- ``counterevidence`` — 1.0 iff the Contradicting evidence section is
  substantive (not empty / not a bare denial); §11 关键反证遗漏率 < 10%;
- ``placeholders`` — 1.0 iff no placeholder token (CON003).

The packet is a markdown review card that a human scores on the 8 §11
dimensions (引用准确 / 无来源外事实 / 问题覆盖 / 反证完整 / 假设显式 /
分歧可解释 / 节省研究时间 / 过度结论风险).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import ID_PATTERNS
from research_os.services.analysis_registry import mode_metadata, mode_slug

_ID_TOKEN_RE = re.compile(r"\b[A-Z]{2,6}(?:-[A-Za-z0-9]+)+")
_PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|TBA|TBC|FIXME|PLACEHOLDER|XXX)\b"
    r"|\b(to be (determined|announced|decided|completed))\b",
    re.IGNORECASE,
)
# Bare-denial / near-empty counter-evidence (§11 反证遗漏). Mirrors the D-012
# red-team rule for any mode: an empty "Contradicting evidence" is not a
# completed job.
_BARE_DENIAL_RE = re.compile(
    r"^\s*(?:无|没有|不存在|没有找到|未发现|nil|none|n/a|na|nothing|"
    r"no (?:contradicting|alternative|evidence|such|direct).*|—|-|\.)*\s*$",
    re.IGNORECASE,
)
_MIN_SUBSTANTIVE_CHARS = 15

# §11 gate thresholds (Phase 4 §11). Citations must be fully resolvable and
# sections/question coverage meet the stated bars.
GATE = {
    "citation": 1.0,
    "outside_facts": 1.0,
    "sections": 1.0,
    "questions": 0.9,
    "counterevidence": 1.0,
    "placeholders": 1.0,
}

# CJK content-token heuristic for question coverage: drop pure particles so a
# question like "估值是否已反映该预期？" keeps "估值/反映/预期" and drops 是否/该.
_STOP_CHARS = set(
    "如何是否哪些什么多长怎么为何吗呢与或的了有是在中为对及及其一个每个该这那进行关于"
)


@dataclass(frozen=True)
class EvalDimension:
    key: str
    label: str
    score: float
    target: float
    detail: str

    @property
    def passed(self) -> bool:
        return self.score >= self.target


@dataclass(frozen=True)
class EvaluationScorecard:
    run_id: str
    mode_id: str
    mode_slug: str
    dimensions: list[EvalDimension] = field(default_factory=list)

    def dimension(self, key: str) -> EvalDimension | None:
        for dimension in self.dimensions:
            if dimension.key == key:
                return dimension
        return None

    @property
    def overall(self) -> float:
        if not self.dimensions:
            return 0.0
        return sum(dimension.score for dimension in self.dimensions) / len(
            self.dimensions
        )

    @property
    def gate_pass(self) -> bool:
        return bool(self.dimensions) and all(
            dimension.passed for dimension in self.dimensions
        )


def evaluate_run(objects: list[ResearchObject], run_id: str) -> EvaluationScorecard:
    """D-017: deterministic scorecard for a completed run (pure)."""
    by_id = {obj.object_id: obj for obj in objects}
    run = by_id.get(run_id)
    if run is None or run.object_type != "analysis_run":
        raise ValueError(f"unknown analysis run {run_id!r}")
    mode = by_id.get(str(run.metadata.get("mode_id", "")))
    if mode is None or mode.object_type != "analysis_mode":
        raise ValueError(f"run {run_id} references an unknown mode")
    meta = mode_metadata(mode)
    body = run.body

    dimensions = [
        _dimension(
            "citation",
            "引用可解析",
            _citation_score(body, by_id),
            GATE["citation"],
            _citation_detail(body, by_id),
        ),
        _dimension(
            "outside_facts",
            "无来源外事实",
            _outside_facts_score(body, by_id, run),
            GATE["outside_facts"],
            "所有被引证据对象均为声明输入",
        ),
        _dimension(
            "sections",
            "分区完整",
            _section_score(body, meta),
            GATE["sections"],
            "共享契约 + 模式必输分区均非空",
        ),
        _dimension(
            "questions",
            "问题覆盖",
            _question_score(body, meta),
            GATE["questions"],
            "必答问题的内容词在正文中出现的比例（确定性启发式）",
        ),
        _dimension(
            "counterevidence",
            "反证完整",
            _counterevidence_score(body),
            GATE["counterevidence"],
            "Contradicting evidence 非空且非裸否认",
        ),
        _dimension(
            "placeholders",
            "无占位符",
            1.0 if not _PLACEHOLDER_RE.search(body) else 0.0,
            GATE["placeholders"],
            "无 TODO/占位 token",
        ),
    ]
    return EvaluationScorecard(
        run_id=run.object_id,
        mode_id=str(run.metadata.get("mode_id", "")),
        mode_slug=mode_slug(mode.object_id),
        dimensions=dimensions,
    )


def evaluator_metrics(scorecards: list[EvaluationScorecard]) -> dict[str, Any]:
    """D-017: aggregate gate rates over a set of scorecards (D-019 readiness)."""
    if not scorecards:
        return {}
    total = len(scorecards)
    result: dict[str, Any] = {"runs": total, "gate_pass": 0, "overall": 0.0}
    for key in GATE:
        dims: list[EvalDimension] = []
        for card in scorecards:
            dimension = card.dimension(key)
            if dimension is not None:
                dims.append(dimension)
        result[f"{key}.pass"] = sum(1 for d in dims if d.passed)
        result[f"{key}.mean"] = sum(d.score for d in dims) / len(dims) if dims else 0.0
    result["gate_pass"] = sum(1 for card in scorecards if card.gate_pass)
    result["overall"] = sum(card.overall for card in scorecards) / total
    return result


def render_evaluation_packet(
    objects: list[ResearchObject],
    run_id: str,
) -> str:
    """D-017: human rubric review card for one run (§11)."""
    card = evaluate_run(objects, run_id)
    rows = "\n".join(
        f"| {dimension.label} | {_fmt(dimension.score)} | "
        f"{'✓' if dimension.passed else '✗'} | {dimension.detail} |"
        for dimension in card.dimensions
    )
    human_rows = "\n".join(f"| {label} | ⬜ |" for label in _HUMAN_DIMENSIONS)
    return f"""# D-017 Evaluation Packet — {card.run_id}

状态：`in_progress`（人工判定；阈值见 Phase 4 §11）
模式：{card.mode_id}（{card.mode_slug}）
整体：{_fmt(card.overall)} — 确定性 Gate {"PASS" if card.gate_pass else "FAIL"}

## 确定性评分

| 维度 | 分数 | 达标 | 说明 |
|---|---|---|---|
{rows}

## 人工评分（§11）

| 维度 | 评分（0-1） |
|---|---|
{human_rows}

## 阈值（§11）

- 引用/归属 100% 可解析
- 无 Source 外关键事实
- 必填问题覆盖 ≥ 90%
- 关键反证遗漏率 < 10%
- 人工认为「有增量价值」的 Run ≥ 70%
- Open Discovery 候选中至少一半可判定 investigate/reject
- 不使用多数投票产生权威结论
"""


def render_scorecard(card: EvaluationScorecard) -> str:
    """D-017: plain-text scorecard (CLI)."""
    lines = [
        f"# {card.run_id}  ({card.mode_id})",
        f"overall: {_fmt(card.overall)}  gate: {'PASS' if card.gate_pass else 'FAIL'}",
        "",
        f"{'DIMENSION':<18} {'SCORE':<8} {'TARGET':<8} STATUS  DETAIL",
        "-" * 70,
    ]
    for dimension in card.dimensions:
        lines.append(
            f"{dimension.key:<18} {_fmt(dimension.score):<8} "
            f"{_fmt(dimension.target):<8} "
            f"{'PASS' if dimension.passed else 'FAIL'}  {dimension.detail}"
        )
    return "\n".join(lines)


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


def _dimension(
    key: str,
    label: str,
    score: float,
    target: float,
    detail: str,
) -> EvalDimension:
    return EvalDimension(
        key=key, label=label, score=round(score, 3), target=target, detail=detail
    )


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _citation_score(body: str, by_id: dict[str, ResearchObject]) -> float:
    cited = {token for token in _ID_TOKEN_RE.findall(body) if _matches_pattern(token)}
    if not cited:
        return 1.0  # no citations to resolve → vacuously fine
    resolved = sum(1 for token in cited if token in by_id)
    return resolved / len(cited)


def _citation_detail(body: str, by_id: dict[str, ResearchObject]) -> str:
    cited = sorted(
        {token for token in _ID_TOKEN_RE.findall(body) if _matches_pattern(token)}
    )
    unresolved = [token for token in cited if token not in by_id]
    return (
        f"引用 {len(cited)} 个 ID，未解析 {len(unresolved)} 个: "
        f"{', '.join(unresolved) or '—'}"
    )


def _outside_facts_score(
    body: str,
    by_id: dict[str, ResearchObject],
    run: ResearchObject,
) -> float:
    declared = {
        str(value)
        for field in (
            "input_source_ids",
            "input_event_ids",
            "input_impact_ids",
            "input_thesis_ids",
            "scope_ids",
        )
        for value in run.metadata.get(field, []) or []
    }
    for token in _ID_TOKEN_RE.findall(body):
        if token == run.object_id:
            continue
        target = by_id.get(token)
        if target is None:
            continue
        if target.object_type in _EVIDENCE_TYPES and token not in declared:
            return 0.0
    return 1.0


_EVIDENCE_TYPES = {"source", "event", "impact_assertion", "thesis"}


def _section_score(body: str, meta: dict[str, Any]) -> float:
    sections = list(_SHARED_SECTIONS) + list(meta["required_output_sections"])
    present = set(re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
    ok = sum(
        1 for section in sections if section in present and _section(body, section)
    )
    return ok / len(sections) if sections else 1.0


_SHARED_SECTIONS = [
    "Facts used",
    "Inferences",
    "Judgments",
    "Contradicting evidence",
    "Alternative explanations",
    "Unknowns",
    "Indicators",
    "Mode-specific output",
    "Limitations",
]


def _question_score(body: str, meta: dict[str, Any]) -> float:
    addressed, checkable = 0, 0
    for question in meta["required_questions"]:
        tokens = _content_tokens(question)
        if not tokens:
            continue  # no distinctive content → honestly un-checkable
        checkable += 1
        if any(token in body for token in tokens):
            addressed += 1
    return addressed / checkable if checkable else 1.0


def _content_tokens(question: str) -> set[str]:
    tokens: set[str] = set()
    for run in re.findall(r"[一-鿿]+", question):
        for i in range(len(run) - 1):
            bigram = run[i : i + 2]
            if bigram[0] in _STOP_CHARS or bigram[1] in _STOP_CHARS:
                continue
            tokens.add(bigram)
    return tokens


def _counterevidence_score(body: str) -> float:
    counter = _section(body, "Contradicting evidence") or _section(
        body, "Counter-evidence"
    )
    if not counter:
        return 0.0
    if len(counter) < _MIN_SUBSTANTIVE_CHARS:
        return 0.0
    return 0.0 if _BARE_DENIAL_RE.match(counter) else 1.0


def _matches_pattern(token: str) -> bool:
    return any(pattern.fullmatch(token) for pattern in ID_PATTERNS.values())


def _fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")
