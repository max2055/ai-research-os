"""D-011 mode compare (RCP-v03-007, Phase 4 §6).

Compares multiple Analysis Runs produced by different modes over (possibly)
shared evidence. The output is DESCRIPTIVE — it lists shared facts, evidence
each mode omitted, time horizons, modes and questions, plus a heuristic signal
for conflicting conclusions. It never synthesizes a verdict and never uses
majority voting (Phase 4 §6): synthesis weight may only come from evidence
quality/independence, mechanism completeness, mode scope fit, calibration
history or explicit researcher judgment, all human decisions surfaced by this
report.

The deterministic basis for "facts" is each run's declared inputs
(input_source/event/impact/thesis ids), which the D-004 contract enforces as the
only citable evidence. Pure service — no writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from research_os.domain.models import ResearchObject
from research_os.services.analysis_registry import mode_metadata, mode_slug

# Signals for the conflicting-conclusion heuristic (Phase 4 §6: differing
# conclusions are flagged for human review, never auto-resolved). Scored over
# the run's Judgments + Inferences prose; keyword heuristic, clearly labeled.
_POSITIVE_RE = re.compile(
    r"(受益|增长|上升|提高|改善|利好|走强|支撑|有利|positive|benefit|gain|"
    r"improve|upside|bullish|strengthen|support)",
    re.IGNORECASE,
)
_NEGATIVE_RE = re.compile(
    r"(受损|下降|下滑|降低|恶化|利空|走弱|承压|风险|压力|萎缩|negative|decline|"
    r"weaken|downside|bearish|deteriorate|risk|pressure)",
    re.IGNORECASE,
)

_INPUT_FIELDS = (
    "input_source_ids",
    "input_event_ids",
    "input_impact_ids",
    "input_thesis_ids",
)


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    mode_id: str
    mode_slug: str
    as_of: str
    review_status: str
    evidence_ids: list[str]
    time_horizons: list[str]
    questions: list[str]
    signal: str

    @property
    def evidence_set(self) -> frozenset[str]:
        return frozenset(self.evidence_ids)


@dataclass(frozen=True)
class CompareReport:
    runs: list[RunSummary] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)
    time_horizons: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    shared_facts: list[str] = field(default_factory=list)
    evidence_omitted: dict[str, list[str]] = field(default_factory=dict)
    conflicting_signals: list[tuple[str, str, str, str]] = field(default_factory=list)

    @property
    def run_ids(self) -> list[str]:
        return [run.run_id for run in self.runs]


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _signal(body: str) -> str:
    parts = [f"{_section(body, 'Inferences')}\n{_section(body, 'Judgments')}"]
    text = " ".join(parts)
    positive = len(_POSITIVE_RE.findall(text))
    negative = len(_NEGATIVE_RE.findall(text))
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    if positive or negative:
        return "mixed"
    return "neutral"


def _summary(
    run: ResearchObject,
    by_id: dict[str, ResearchObject],
) -> RunSummary | None:
    mode = by_id.get(str(run.metadata.get("mode_id", "")))
    if mode is None or mode.object_type != "analysis_mode":
        return None
    evidence: list[str] = []
    for field_ in _INPUT_FIELDS:
        evidence.extend(str(value) for value in run.metadata.get(field_, []) or [])
    meta = mode_metadata(mode)
    return RunSummary(
        run_id=run.object_id,
        mode_id=str(run.metadata.get("mode_id", "")),
        mode_slug=mode_slug(mode.object_id),
        as_of=str(run.metadata.get("as_of", "")),
        review_status=str(run.metadata.get("review_status", "")),
        evidence_ids=sorted(set(evidence)),
        time_horizons=meta["time_horizons"],
        questions=meta["required_questions"],
        signal=_signal(run.body),
    )


def compare_runs(
    objects: list[ResearchObject],
    run_ids: list[str],
) -> CompareReport:
    by_id = {obj.object_id: obj for obj in objects}
    runs: list[RunSummary] = []
    for run_id in run_ids:
        run = by_id.get(run_id)
        if run is None or run.object_type != "analysis_run":
            continue
        summary = _summary(run, by_id)
        if summary is not None:
            runs.append(summary)
    if not runs:
        return CompareReport()

    return CompareReport(
        runs=runs,
        modes=sorted({run.mode_id for run in runs}),
        time_horizons=sorted(
            {horizon for run in runs for horizon in run.time_horizons}
        ),
        questions=sorted({q for run in runs for q in run.questions}),
        shared_facts=_shared_facts(runs),
        evidence_omitted=_evidence_omitted(runs),
        conflicting_signals=_conflicting_signals(runs),
    )


def _shared_facts(runs: list[RunSummary]) -> list[str]:
    if not runs:
        return []
    common = runs[0].evidence_set
    for run in runs[1:]:
        common &= run.evidence_set
    return sorted(common)


def _evidence_omitted(runs: list[RunSummary]) -> dict[str, list[str]]:
    """Per run: evidence used by OTHER runs but not this one (coverage gap)."""
    all_used = {fact for run in runs for fact in run.evidence_ids}
    return {run.run_id: sorted(all_used - run.evidence_set) for run in runs}


def _conflicting_signals(
    runs: list[RunSummary],
) -> list[tuple[str, str, str, str]]:
    """Pairs of runs whose Judgments/Inferences valence points opposite ways.
    Heuristic only — surfaced for human review, never resolved here."""
    conflicts: list[tuple[str, str, str, str]] = []
    for i, run_a in enumerate(runs):
        for run_b in runs[i + 1 :]:
            if _opposing(run_a.signal, run_b.signal):
                conflicts.append(
                    (run_a.run_id, run_a.signal, run_b.run_id, run_b.signal)
                )
    return conflicts


def _opposing(a: str, b: str) -> bool:
    return (a, b) in {("positive", "negative"), ("negative", "positive")}


def render_compare_report(report: CompareReport) -> str:
    """D-014 ``analyze compare``: human-readable comparison (no majority vote)."""
    lines = ["# Mode comparison"]
    if not report.runs:
        return "# Mode comparison\n\n(no comparable runs)"
    lines.append("\n## Runs")
    for run in report.runs:
        lines.append(
            f"- {run.run_id}  [{run.mode_slug}]  as_of={run.as_of}  "
            f"review={run.review_status}  signal={run.signal}"
        )
    lines.append(f"\n## Shared facts\n{', '.join(report.shared_facts) or '—'}")
    lines.append(f"\n## Distinct modes\n{', '.join(report.modes) or '—'}")
    lines.append(f"\n## Distinct horizons\n{', '.join(report.time_horizons) or '—'}")
    lines.append("\n## Questions")
    for question in report.questions:
        lines.append(f"- {question}")
    lines.append("\n## Evidence omitted by each run (used by another, not itself)")
    for run_id, omitted in report.evidence_omitted.items():
        lines.append(f"- {run_id}: {', '.join(omitted) or '—'}")
    lines.append("\n## Conflicting signals (heuristic — human review required)")
    if not report.conflicting_signals:
        lines.append("- none")
    for a, signal_a, b, signal_b in report.conflicting_signals:
        lines.append(f"- {a} ({signal_a}) vs {b} ({signal_b})")
    lines.append(
        "\nNo majority voting: convergence weight must come from evidence quality, "
        "mechanism completeness, scope fit, calibration history or explicit "
        "researcher judgment (Phase 4 §6)."
    )
    return "\n".join(lines)
