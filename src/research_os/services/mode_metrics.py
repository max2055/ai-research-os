"""D-018 mode metrics (RCP-v03-007, Phase 4 §6/§10).

Per-mode aggregates over completed Analysis Runs, the three signals the mode
table asks for:

- ``edit`` — output diversity: mean pairwise normalized body distance between a
  mode's completed runs (1 - difflib ratio). A mode whose runs are near-identical
  across DIFFERENT inputs is not discriminating its evidence (boilerplate risk);
- ``agreement`` — reproducibility: for every pair of a mode's runs that SHARE at
  at least one evidence id, the fraction whose Judgments/Inferences valence
  signal matches. Low agreement on the same evidence is a divergence a human
  should look at (surfaced, never auto-resolved — no majority voting, §6);
- ``evidence omission`` — coverage gap: evidence ids used by OTHER modes' runs
  but by none of this mode's runs (aggregate of D-011's per-run omitted set).

All read-only, heuristic, and honest about being a proxy: ``edit`` is lexical
distance not semantic novelty, ``agreement`` is valence-signal agreement not
conclusion identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.services.analysis_compare import _signal
from research_os.services.analysis_registry import mode_slug

_INPUT_FIELDS = (
    "input_source_ids",
    "input_event_ids",
    "input_impact_ids",
    "input_thesis_ids",
)


@dataclass(frozen=True)
class ModeMetrics:
    mode_id: str
    run_count: int
    reviewed_count: int
    edit_distance: float
    pairs: int
    signal_counts: dict[str, int] = field(default_factory=dict)
    agreement: float | None = None
    agreement_pairs: int = 0
    evidence_used: int = 0
    evidence_omitted: int = 0
    evidence_omitted_ids: list[str] = field(default_factory=list)


def mode_metrics(objects: list[ResearchObject]) -> dict[str, Any]:
    """D-018: per-mode aggregates over completed runs (pure, read-only)."""
    by_id = {obj.object_id: obj for obj in objects}
    runs = [obj for obj in objects if obj.object_type == "analysis_run"]
    # slug -> list of (run, signal, evidence set)
    per_mode: dict[str, list[tuple[ResearchObject, str, frozenset[str]]]] = {}
    for run in runs:
        mode = by_id.get(str(run.metadata.get("mode_id", "")))
        if mode is None or mode.object_type != "analysis_mode":
            continue
        slug = mode_slug(mode.object_id)
        if run.metadata.get("status") != "completed":
            continue
        evidence = {
            str(value)
            for field in _INPUT_FIELDS
            for value in (run.metadata.get(field, []) or [])
        }
        per_mode.setdefault(slug, []).append(
            (run, _signal(run.body), frozenset(evidence))
        )

    all_evidence = {
        evidence_id
        for entries in per_mode.values()
        for _, _, evidence in entries
        for evidence_id in evidence
    }

    result: dict[str, Any] = {}
    for slug in sorted(per_mode):
        entries = per_mode[slug]
        bodies = [run.body for run, _, _ in entries]
        pairs = 0
        distance_sum = 0.0
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                pairs += 1
                distance_sum += (
                    1.0 - SequenceMatcher(None, bodies[i], bodies[j]).ratio()
                )
        edit_distance = distance_sum / pairs if pairs else 0.0

        signal_counts: dict[str, int] = {}
        agreement_sum = 0
        agreement_pairs = 0
        for i in range(len(entries)):
            _, signal_a, evidence_a = entries[i]
            signal_counts[signal_a] = signal_counts.get(signal_a, 0) + 1
            for j in range(i + 1, len(entries)):
                _, signal_b, evidence_b = entries[j]
                if evidence_a & evidence_b:
                    agreement_pairs += 1
                    if signal_a == signal_b:
                        agreement_sum += 1

        used = {e for _, _, evidence in entries for e in evidence}
        omitted_ids = sorted(all_evidence - used)

        result[slug] = {
            "mode_id": slug,
            "run_count": len(entries),
            "reviewed_count": sum(
                1
                for run, _, _ in entries
                if run.metadata.get("review_status") == "reviewed"
            ),
            "edit_distance": round(edit_distance, 3),
            "pairs": pairs,
            "signal_counts": signal_counts,
            "agreement": (
                round(agreement_sum / agreement_pairs, 3) if agreement_pairs else None
            ),
            "agreement_pairs": agreement_pairs,
            "evidence_used": len(used),
            "evidence_omitted": len(omitted_ids),
            "evidence_omitted_ids": omitted_ids,
        }

    return {
        "modes": result,
        "overall": {
            "modes": len(result),
            "runs": sum(entry["run_count"] for entry in result.values()),
        },
    }


def render_mode_metrics(metrics: dict[str, Any]) -> str:
    """D-018: human-readable mode metrics table (CLI / dashboard)."""
    lines = ["# Mode metrics", ""]
    header = (
        f"{'MODE':<22} {'RUNS':<5} {'REV':<5} {'EDIT':<7} "
        f"{'AGREE':<7} {'PAIRS':<6} {'EV-USE':<7} {'EV-OMIT':<7}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for slug, stats in metrics["modes"].items():
        agreement = (
            f"{stats['agreement']:.3f}" if stats["agreement"] is not None else "—"
        )
        lines.append(
            f"{slug:<22} {stats['run_count']:<5} {stats['reviewed_count']:<5} "
            f"{stats['edit_distance']:<7} {agreement:<7} {stats['agreement_pairs']:<6} "
            f"{stats['evidence_used']:<7} {stats['evidence_omitted']:<7}"
        )
    lines.append("")
    lines.append(
        "edit=mean pairwise body distance（1=完全不同/0=完全相同）; "
        "agree=同证据 run 对信号一致率; ev-omit=他 mode 用过而本 mode 未用的证据数"
    )
    for slug, stats in metrics["modes"].items():
        if stats["evidence_omitted"]:
            lines.append(
                f"\n{slug} evidence omitted: "
                + ", ".join(stats["evidence_omitted_ids"][:20])
            )
            if stats["evidence_omitted"] > 20:
                lines.append(f"  … +{stats['evidence_omitted'] - 20} more")
    return "\n".join(lines)
