"""E-010 forecast resolution workflow (Phase 5, WP-501).

An open Forecast can only be closed by a ForecastResolution (RES-*) — the
original Forecast is never retro-edited (E-010 acceptance, RCP-v03-008
Phase 5 §4). This module prepares a pending ``RES-YYYYMMDD-NNN`` draft and, on
apply, atomically writes the Resolution and flips the Forecast's status to
``resolved`` (or ``void`` when the decision voids it) in one transaction.

Only the status/audit fields of the Forecast change: the question, outcome
definition, probability, and resolution criteria are untouched.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_os.domain.policies import is_iso_date
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.services.drafts import (
    ensure_known_ids,
    next_object_id,
    yaml_list,
    yaml_scalar,
)
from research_os.services.validation import validate_repository

RESOLUTION_DECISIONS = ("correct", "incorrect", "partial", "void", "ambiguous")
SCORING_METHODS = ("brier", "log_score", "interval_coverage", "manual", "none")

_RESOLUTION_FIELD_ORDER = [
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
    "forecast_id",
    "resolved_at",
    "outcome",
    "observed_value",
    "source_ids",
    "decision",
    "resolution_reason",
    "scoring_method",
    "score",
    "reviewer",
]


def prepare_resolution_draft(
    root: Path,
    *,
    spec: dict[str, Any],
    created_at: str,
) -> tuple[Path, str]:
    """Prepare a pending ForecastResolution draft (dry-run, no writes).

    Requires the referenced Forecast to be ``open`` (only open Forecasts can
    be resolved) and cites at least one existing Source. ``ambiguous``/``void``
    must carry a reason — they are never used to silently drop a forecast.
    """
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before creating a resolution")
    forecast_id = str(spec.get("forecast_id", "")).strip()
    by_id = {obj.object_id: obj for obj in objects}
    forecast = by_id.get(forecast_id)
    if forecast is None or forecast.object_type != "forecast":
        raise ValueError(f"unknown Forecast {forecast_id}")
    if forecast.metadata.get("status") != "open":
        raise ValueError(
            f"cannot resolve {forecast_id}: status must be open, "
            f"is {forecast.metadata.get('status')!r}"
        )
    resolved_at = str(spec.get("resolved_at", "")).strip()
    if not is_iso_date(resolved_at):
        raise ValueError("resolved_at must be YYYY-MM-DD")
    forecast_as_of = str(forecast.metadata.get("forecast_as_of", ""))
    if resolved_at < forecast_as_of:
        raise ValueError(
            f"resolved_at must not be before forecast_as_of {forecast_as_of}"
        )
    decision = str(spec.get("decision", "")).strip()
    if decision not in RESOLUTION_DECISIONS:
        raise ValueError(f"decision must be one of {sorted(RESOLUTION_DECISIONS)}")
    resolution_reason = str(spec.get("resolution_reason", "")).strip()
    if not resolution_reason:
        raise ValueError("resolution_reason is required")
    source_ids = [str(v) for v in spec.get("source_ids", [])]
    if not source_ids:
        raise ValueError("at least one source_id is required")
    ensure_known_ids(source_ids, "source", by_id, "source_ids")
    scoring_method = str(spec.get("scoring_method", "manual")).strip()
    if scoring_method not in SCORING_METHODS:
        raise ValueError(f"scoring_method must be one of {sorted(SCORING_METHODS)}")

    resolution_id = next_object_id(objects, "forecast_resolution", created_at)
    relative = Path("05_Research/Resolutions") / f"{resolution_id}.md"
    meta = _resolution_meta(spec, resolution_id, created_at, source_ids)
    return relative, render_resolution_draft(meta, _resolution_body(meta, forecast_id))


def apply_resolution(
    root: Path,
    *,
    spec: dict[str, Any],
    created_at: str,
) -> list[Path]:
    """Atomically write the Resolution AND close the Forecast in one commit.

    The Forecast is edited only in status/audit fields: ``resolved`` for a
    normal decision, ``void`` when the resolution voids it.
    """
    root = root.resolve()
    relative, content = prepare_resolution_draft(root, spec=spec, created_at=created_at)
    forecast_id = str(spec["forecast_id"])
    forecast_status = "void" if str(spec.get("decision")) == "void" else "resolved"
    objects, _ = validate_repository(root)
    by_id = {obj.object_id: obj for obj in objects}
    forecast = by_id[forecast_id]
    document = MarkdownDocument.read(forecast.path)
    document.set_metadata("status", forecast_status)
    document.set_metadata("updated_at", created_at)
    document.set_metadata("resolved_at", str(spec["resolved_at"]))
    document.set_metadata("resolved_by", str(spec.get("reviewer", "")))

    transaction = FileTransaction(root)
    transaction.stage_create(relative, content)
    transaction.stage_replace(forecast.path, document.render())
    return transaction.commit()


def render_resolution_draft(meta: dict[str, Any], body: str) -> str:
    """Render a meta dict + body into a comment-preserving front-matter file."""
    lines: list[str] = ["---"]
    emitted: set[str] = set()
    for key in _RESOLUTION_FIELD_ORDER:
        if key in meta and meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
            emitted.add(key)
    for key in sorted(set(meta) - emitted):
        if meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def _resolution_meta(
    spec: dict[str, Any],
    resolution_id: str,
    created_at: str,
    source_ids: list[str],
) -> dict[str, Any]:
    forecast_id = str(spec["forecast_id"])
    decision = str(spec["decision"])
    title = str(spec.get("title", "")).strip() or f"Resolution: {forecast_id}"
    return {
        "id": resolution_id,
        "type": "forecast_resolution",
        "title": title,
        "created_at": created_at,
        "updated_at": created_at,
        "schema_version": 2,
        "project_ids": [str(v) for v in spec.get("project_ids", [])],
        "status": "applied",
        "review_status": "pending",
        "tags": [str(v) for v in spec.get("tags", [])],
        "forecast_id": forecast_id,
        "resolved_at": str(spec["resolved_at"]).strip(),
        "outcome": str(spec.get("outcome", "")).strip(),
        "observed_value": spec.get("observed_value"),
        "source_ids": source_ids,
        "decision": decision,
        "resolution_reason": str(spec.get("resolution_reason", "")).strip(),
        "scoring_method": str(spec.get("scoring_method", "manual")).strip(),
        "score": spec.get("score"),
        "reviewer": str(spec.get("reviewer", "")).strip(),
    }


def _resolution_body(meta: dict[str, Any], forecast_id: str) -> str:
    return f"""# Forecast Resolution

## Resolution

- Forecast: {forecast_id}
- Resolved at: {meta["resolved_at"]}
- Decision: {meta["decision"]}
- Scoring method: {meta["scoring_method"]}
- Score: {meta["score"] if meta["score"] is not None else "—"}
- Reviewer: {meta["reviewer"]}

## Outcome

- Observed outcome: {meta["outcome"]}
- Observed value: {meta["observed_value"] if meta["observed_value"] else "—"}

## Sources

- {yaml_list(meta["source_ids"])}

## Reason

{meta["resolution_reason"]}

## Review

Pending — review via `review apply --targets {meta["id"]} --decision approve`.
The referenced Forecast is never retro-edited; only its status closes.
"""


_SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        return yaml_list([str(item) for item in value])
    if isinstance(value, str) and _SAFE_SCALAR_RE.match(value):
        return value
    return yaml_scalar(value)
