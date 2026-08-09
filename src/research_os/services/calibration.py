"""E-015 calibration engine (Phase 5, WP-511).

Computes the Phase 5 §9 calibration metrics over reviewed ForecastResolutions
(RES-*): Brier score for binary forecasts, calibration buckets, numeric interval
coverage, resolution timeliness, and void/ambiguous rate.

Honesty rules (Phase 5 §9 notes):
- small samples never rank anything — every metric reports its ``n``;
- calibration is only compared within the same outcome_type;
- a share price move is NOT treated as forecast correctness here — correctness
  comes only from the human-reviewed Resolution decision.

All functions are pure over ``(forecast, resolution)`` pairs; the pure
functions are assembled by ``calibration_report``.
"""

from __future__ import annotations

import re
import statistics
from datetime import date
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.validation import validate_repository

_BUCKET_EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0001)


def resolved_pairs(
    objects: list[ResearchObject],
) -> list[tuple[ResearchObject, ResearchObject]]:
    """[(forecast, resolution)] for reviewed ForecastResolutions only."""
    by_id = {obj.object_id: obj for obj in objects}
    pairs: list[tuple[ResearchObject, ResearchObject]] = []
    for res in objects:
        if res.object_type != "forecast_resolution":
            continue
        if res.metadata.get("review_status") != "reviewed":
            continue
        forecast = by_id.get(str(res.metadata.get("forecast_id", "")))
        if forecast is None or forecast.object_type != "forecast":
            continue
        pairs.append((forecast, res))
    return pairs


def _outcome(decision: str) -> int | None:
    if decision == "correct":
        return 1
    if decision == "incorrect":
        return 0
    return None  # partial / void / ambiguous carry no binary outcome


def brier_score(
    pairs: list[tuple[ResearchObject, ResearchObject]],
) -> dict[str, float | int | None]:
    """Mean (probability - outcome)^2 over binary forecasts with a probability."""
    scores: list[float] = []
    for forecast, res in pairs:
        if forecast.metadata.get("outcome_type") != "binary":
            continue
        probability = forecast.metadata.get("probability")
        outcome = _outcome(str(res.metadata.get("decision", "")))
        if probability is None or outcome is None:
            continue
        scores.append((float(probability) - outcome) ** 2)
    return {
        "n": len(scores),
        "brier": statistics.mean(scores) if scores else None,
    }


def calibration_buckets(
    pairs: list[tuple[ResearchObject, ResearchObject]],
) -> list[dict[str, float | int | str | None]]:
    """Per probability bucket: observed frequency of positive outcomes."""
    buckets: dict[int, list[int]] = {i: [] for i in range(5)}
    for forecast, res in pairs:
        if forecast.metadata.get("outcome_type") != "binary":
            continue
        probability = forecast.metadata.get("probability")
        outcome = _outcome(str(res.metadata.get("decision", "")))
        if probability is None or outcome is None:
            continue
        p = float(probability)
        for index in range(5):
            if _BUCKET_EDGES[index] <= p < _BUCKET_EDGES[index + 1]:
                buckets[index].append(outcome)
                break
    rows: list[dict[str, Any]] = []
    for index in range(5):
        outcomes = buckets[index]
        rows.append(
            {
                "bucket": f"{_BUCKET_EDGES[index]:.1f}-{_BUCKET_EDGES[index + 1]:.1f}",
                "n": len(outcomes),
                "observed_frequency": (
                    statistics.mean(outcomes) if outcomes else None
                ),
            }
        )
    return rows


def interval_coverage(
    pairs: list[tuple[ResearchObject, ResearchObject]],
) -> dict[str, float | int | None]:
    """Fraction of numeric_range forecasts whose observed_value fell in range."""
    covered = 0
    total = 0
    for forecast, res in pairs:
        if forecast.metadata.get("outcome_type") != "numeric_range":
            continue
        low = forecast.metadata.get("range_low")
        high = forecast.metadata.get("range_high")
        observed = res.metadata.get("observed_value")
        if low is None or high is None or observed is None:
            continue
        try:
            value = float(str(observed).replace("%", "").replace(",", ""))
        except ValueError:
            continue
        total += 1
        if float(low) <= value <= float(high):
            covered += 1
    return {
        "n": total,
        "covered": covered,
        "coverage": covered / total if total else None,
    }


def resolution_timeliness(
    pairs: list[tuple[ResearchObject, ResearchObject]],
) -> dict[str, float | int | None]:
    """Days between the forecast resolution_date and the actual resolved_at."""
    days: list[int] = []
    for forecast, res in pairs:
        resolution_date = forecast.metadata.get("resolution_date")
        resolved_at = res.metadata.get("resolved_at")
        if not is_iso_date(resolution_date) or not is_iso_date(resolved_at):
            continue
        delta = (
            date.fromisoformat(str(resolved_at))
            - date.fromisoformat(str(resolution_date))
        ).days
        days.append(delta)
    late = sum(1 for d in days if d > 0)
    result: dict[str, float | int | None] = {
        "n": len(days),
        "mean_days": statistics.mean(days) if days else None,
        "late": late,
    }
    return result


def void_ambiguous_rate(
    pairs: list[tuple[ResearchObject, ResearchObject]],
) -> dict[str, float | int | None]:
    """Void/ambiguous share of all resolutions (honesty, not dropped failures)."""
    total = len(pairs)
    void = sum(
        1 for _, res in pairs if str(res.metadata.get("decision", "")) == "void"
    )
    ambiguous = sum(
        1
        for _, res in pairs
        if str(res.metadata.get("decision", "")) == "ambiguous"
    )
    return {
        "n": total,
        "void": void,
        "ambiguous": ambiguous,
        "rate": (void + ambiguous) / total if total else None,
    }


def _forecast_modes(
    objects: list[ResearchObject],
    forecast: ResearchObject,
) -> set[str]:
    """Analysis-mode slugs a forecast's runs were produced under."""
    by_id = {obj.object_id: obj for obj in objects}
    modes: set[str] = set()
    for run_id in forecast.metadata.get("analysis_run_ids", []) or []:
        run = by_id.get(str(run_id))
        if run and run.object_type == "analysis_run":
            mode_id = str(run.metadata.get("mode_id", ""))
            match = re.fullmatch(r"MOD-ANL-(.+)-v\d+", mode_id)
            if match:
                modes.add(match.group(1))
    return modes


def _forecast_sectors(forecast: ResearchObject) -> set[str]:
    return {
        str(scope)
        for scope in forecast.metadata.get("scope_ids", []) or []
        if str(scope).startswith("SEG-")
    }


def calibration_report(
    root: Path,
    *,
    mode: str | None = None,
    sector: str | None = None,
) -> dict[str, Any]:
    """Aggregate §9 calibration metrics over reviewed resolutions.

    ``mode`` restricts to forecasts whose runs ran under that mode slug;
    ``sector`` restricts to forecasts whose scope_ids include that SEG-*.
    """
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before a calibration report"
        )
    pairs = resolved_pairs(objects)
    if mode or sector:
        filtered: list[tuple[ResearchObject, ResearchObject]] = []
        for forecast, res in pairs:
            if mode and mode not in _forecast_modes(objects, forecast):
                continue
            if sector and sector not in _forecast_sectors(forecast):
                continue
            filtered.append((forecast, res))
        pairs = filtered
    by_horizon: dict[str, list[tuple[ResearchObject, ResearchObject]]] = {}
    for forecast, res in pairs:
        horizon = str(forecast.metadata.get("horizon", "unknown")) or "unknown"
        by_horizon.setdefault(horizon, []).append((forecast, res))
    return {
        "n_resolutions": len(pairs),
        "brier": brier_score(pairs),
        "calibration_buckets": calibration_buckets(pairs),
        "interval_coverage": interval_coverage(pairs),
        "timeliness": resolution_timeliness(pairs),
        "void_ambiguous": void_ambiguous_rate(pairs),
        "by_horizon": {
            horizon: {
                "n": len(subset),
                "brier": brier_score(subset)["brier"],
                "coverage": interval_coverage(subset)["coverage"],
            }
            for horizon, subset in sorted(by_horizon.items())
        },
    }


def render_calibration_report(report: dict[str, Any]) -> str:
    lines = [
        "# Forecast calibration",
        "",
        f"- Resolved (reviewed) forecasts: {report['n_resolutions']}",
        "",
        "## Brier score (binary)",
        "",
        f"- n = {report['brier']['n']}, Brier = {_fmt(report['brier']['brier'])}",
        "",
        "## Calibration buckets (binary)",
        "",
        "| Bucket | n | Observed frequency |",
        "|---|---|---|",
    ]
    for row in report["calibration_buckets"]:
        lines.append(
            f"| {row['bucket']} | {row['n']} | {_fmt(row['observed_frequency'])} |"
        )
    coverage = report["interval_coverage"]
    lines += [
        "",
        "## Interval coverage (numeric_range)",
        "",
        f"- n = {coverage['n']}, coverage = {_fmt(coverage['coverage'])}",
        "",
        "## Resolution timeliness",
        "",
        f"- n = {report['timeliness']['n']}, mean days = "
        f"{_fmt(report['timeliness']['mean_days'])}, late = "
        f"{report['timeliness']['late']}",
        "",
        "## Void / ambiguous rate",
        "",
        f"- n = {report['void_ambiguous']['n']}, void = "
        f"{report['void_ambiguous']['void']}, ambiguous = "
        f"{report['void_ambiguous']['ambiguous']}, rate = "
        f"{_fmt(report['void_ambiguous']['rate'])}",
        "",
        "## By horizon",
        "",
    ]
    for horizon, row in sorted(report["by_horizon"].items()):
        lines.append(
            f"- {horizon}: n={row['n']}, brier={_fmt(row['brier'])}, "
            f"coverage={_fmt(row['coverage'])}"
        )
    if not report["by_horizon"]:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}" if isinstance(value, float) else str(value)
