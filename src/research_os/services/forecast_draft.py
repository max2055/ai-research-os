"""E-007 forecast draft materialization (Phase 5, WP-501).

Turns a Forecast spec dict into a pending ``FCT-YYYYMMDD-NNN`` Markdown object
on disk (RCP-v03-008, Phase 5 §3). Mirrors the impact-draft flow
(``impact_draft.prepare_impact_draft``): prepare is a pure dry-run preview,
apply is an atomic write that refuses to overwrite.

Materialized Forecasts are ``status: draft`` / ``review_status: pending``.
Opening them is a separate lifecycle step (E-008, ``forecast_lifecycle``) that
requires ``review_status=reviewed``; the resolution criteria (outcome_definition
/ resolution_date / resolution_source_requirements) are immutable after open.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_os.domain.policies import is_iso_date
from research_os.services.drafts import (
    ensure_known_ids,
    next_object_id,
    write_new_file,
    yaml_list,
    yaml_scalar,
)
from research_os.services.validation import validate_repository


def _ensure_exist(values: list[str], by_id: dict[str, Any], field: str) -> None:
    """Existence-only check for mixed-type reference lists (scope/evidence)."""
    for value in values:
        if value not in by_id:
            raise ValueError(f"{field} references missing object {value}")


OUTCOME_TYPES = ("binary", "categorical", "numeric_range")

_FORECAST_FIELD_ORDER = [
    "id",
    "type",
    "title",
    "created_at",
    "updated_at",
    "schema_version",
    "project_ids",
    "status",
    "review_status",
    "tags",
    "scope_ids",
    "question",
    "outcome_type",
    "outcome_definition",
    "base_rate",
    "probability",
    "range_low",
    "range_high",
    "unit",
    "forecast_as_of",
    "horizon",
    "resolution_date",
    "resolution_source_requirements",
    "evidence_ids",
    "analysis_run_ids",
    "assumptions",
    "alternative_outcomes",
    "falsification_conditions",
]


def prepare_forecast_draft(
    root: Path,
    *,
    spec: dict[str, Any],
    created_at: str,
) -> tuple[Path, str]:
    """Prepare a pending Forecast draft from a spec dict (dry-run, no writes).

    The spec maps to ForecastSchema fields; unknown keys are dropped. Enforces
    the Phase 5 §3 invariants that the schema itself cannot express:
    - resolution_date must be strictly after forecast_as_of;
    - a numeric_range forecast needs a bounded range and a unit;
    - binary probability must be in [0, 1] when supplied.
    """
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating a forecast")
    question = str(spec.get("question", "")).strip()
    if not question:
        raise ValueError("question is required")
    outcome_type = str(spec.get("outcome_type", "")).strip()
    if outcome_type not in OUTCOME_TYPES:
        raise ValueError(f"outcome_type must be one of {sorted(OUTCOME_TYPES)}")
    outcome_definition = str(spec.get("outcome_definition", "")).strip()
    if not outcome_definition:
        raise ValueError("outcome_definition is required")
    forecast_as_of = str(spec.get("forecast_as_of", "")).strip()
    resolution_date = str(spec.get("resolution_date", "")).strip()
    if not is_iso_date(forecast_as_of) or not is_iso_date(resolution_date):
        raise ValueError("forecast_as_of and resolution_date must be YYYY-MM-DD")
    if resolution_date <= forecast_as_of:
        raise ValueError("resolution_date must be after forecast_as_of")
    if outcome_type == "numeric_range":
        range_low = spec.get("range_low")
        range_high = spec.get("range_high")
        unit = str(spec.get("unit", "")).strip()
        if range_low is None or range_high is None:
            raise ValueError("numeric_range requires range_low and range_high")
        if float(range_low) > float(range_high):
            raise ValueError("range_low must not exceed range_high")
        if not unit:
            raise ValueError("numeric_range requires a unit")
    probability = spec.get("probability")
    if probability is not None and not (0.0 <= float(probability) <= 1.0):
        raise ValueError("probability must be between 0 and 1")

    by_id = {obj.object_id: obj for obj in objects}
    project_ids = [str(v) for v in spec.get("project_ids", [])]
    ensure_known_ids(project_ids, "project", by_id, "project_ids")
    _ensure_exist([str(v) for v in spec.get("scope_ids", [])], by_id, "scope_ids")
    _ensure_exist([str(v) for v in spec.get("evidence_ids", [])], by_id, "evidence_ids")
    ensure_known_ids(
        [str(v) for v in spec.get("analysis_run_ids", [])],
        "analysis_run",
        by_id,
        "analysis_run_ids",
    )

    forecast_id = next_object_id(objects, "forecast", created_at)
    relative = Path("05_Research/Forecasts") / f"{forecast_id}.md"
    meta = _forecast_meta(spec, forecast_id, created_at, project_ids)
    return relative, render_forecast_draft(meta, _forecast_body(meta))


def apply_forecast_draft(root: Path, relative: Path, content: str) -> Path:
    """Atomically write the draft (refuses to overwrite an existing file)."""
    return write_new_file(root, relative, content)


def render_forecast_draft(meta: dict[str, Any], body: str) -> str:
    """Render a meta dict + body into a comment-preserving front-matter file."""
    lines: list[str] = ["---"]
    emitted: set[str] = set()
    for key in _FORECAST_FIELD_ORDER:
        if key in meta and meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
            emitted.add(key)
    for key in sorted(set(meta) - emitted):
        if meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def _forecast_meta(
    spec: dict[str, Any],
    forecast_id: str,
    created_at: str,
    project_ids: list[str],
) -> dict[str, Any]:
    title = str(spec.get("title", "")).strip() or (
        f"Forecast: {spec.get('question', '')[:80]}"
    )
    outcome_type = str(spec["outcome_type"])
    probability = spec.get("probability")
    if outcome_type != "binary":
        probability = None  # probability applies only to well-defined outcomes
    unit = str(spec.get("unit", "")).strip()
    meta: dict[str, Any] = {
        "id": forecast_id,
        "type": "forecast",
        "title": title,
        "created_at": created_at,
        "updated_at": created_at,
        "schema_version": 2,
        "project_ids": project_ids,
        "status": "draft",
        "review_status": "pending",
        "tags": [str(v) for v in spec.get("tags", [])],
        "scope_ids": [str(v) for v in spec.get("scope_ids", [])],
        "question": str(spec["question"]).strip(),
        "outcome_type": outcome_type,
        "outcome_definition": str(spec["outcome_definition"]).strip(),
        "base_rate": str(spec.get("base_rate", "unknown")).strip() or "unknown",
        "probability": probability,
        "range_low": spec.get("range_low"),
        "range_high": spec.get("range_high"),
        "forecast_as_of": str(spec["forecast_as_of"]).strip(),
        "horizon": str(spec.get("horizon", "")).strip(),
        "resolution_date": str(spec["resolution_date"]).strip(),
        "resolution_source_requirements": [
            str(v) for v in spec.get("resolution_source_requirements", [])
        ],
        "evidence_ids": [str(v) for v in spec.get("evidence_ids", [])],
        "analysis_run_ids": [str(v) for v in spec.get("analysis_run_ids", [])],
        "assumptions": [str(v) for v in spec.get("assumptions", [])],
        "alternative_outcomes": [str(v) for v in spec.get("alternative_outcomes", [])],
        "falsification_conditions": [
            str(v) for v in spec.get("falsification_conditions", [])
        ],
    }
    if unit:
        meta["unit"] = unit
    return meta


def _forecast_body(meta: dict[str, Any]) -> str:
    probability = meta["probability"]
    probability_line = (
        f"{probability:.2f}" if isinstance(probability, (int, float)) else "N/A"
    )
    range_line = ""
    if meta["outcome_type"] == "numeric_range":
        unit = meta.get("unit", "")
        range_line = f"- Range: {meta['range_low']} – {meta['range_high']} {unit}"
    return f"""# Forecast

## Question

{meta["question"]}

## Outcome

- Type: {meta["outcome_type"]}
- Definition: {meta["outcome_definition"]}
- Base rate: {meta["base_rate"]}
- Probability: {probability_line}
{range_line}
- Unit: {meta.get("unit", "") if meta.get("unit", "") else "—"}

## Horizon

- Forecast as of: {meta["forecast_as_of"]}
- Horizon: {meta["horizon"] if meta["horizon"] else "—"}
- Resolution date: {meta["resolution_date"]}
- Resolution source requirements: {yaml_list(meta["resolution_source_requirements"])}

## Assumptions

- {yaml_list(meta["assumptions"])}

## Alternative outcomes

- {yaml_list(meta["alternative_outcomes"])}

## Falsification conditions

- {yaml_list(meta["falsification_conditions"])}

## Evidence

- {yaml_list(meta["evidence_ids"])}

## Review

Pending — review via `review apply --targets {meta["id"]} --decision approve`;
then open via `forecast open --id {meta["id"]}`. Resolution criteria are
immutable after open.
"""


_SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        return yaml_list([str(item) for item in value])
    if isinstance(value, str) and _SAFE_SCALAR_RE.match(value):
        return value
    return yaml_scalar(value)
