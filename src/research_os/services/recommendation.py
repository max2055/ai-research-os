"""E-013 recommendation renderer + completeness/freshness gate (Phase 5, WP-510).

A Recommendation (REC-*) is the highest-tier research output (RCP-v03-009,
Phase 5 §7). The v0.3 ceiling is ``investment_candidate`` — no buy/sell/position
size without a separate Portfolio & Execution RCP. This module renders a pending
REC draft from a spec and runs the §12 deterministic completeness/freshness gate
that must pass before the draft can be activated:

- references reviewed Thesis/Evidence;
- unknowns and falsification conditions are non-empty (honest hedging);
- the body carries no buy/sell/position-size language (posture ceiling);
- a referenced ValuationSnapshot is fresh against its freshness_threshold.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from research_os.domain.policies import FORBIDDEN_INVESTMENT_ACTIONS, is_iso_date
from research_os.services.drafts import (
    ensure_known_ids,
    next_object_id,
    write_new_file,
    yaml_list,
    yaml_scalar,
)
from research_os.services.validation import validate_repository
from research_os.services.valuation import valuation_freshness


def _ensure_exist(values: list[str], by_id: dict[str, Any], field: str) -> None:
    """Existence-only check for mixed-type reference lists (evidence)."""
    for value in values:
        if value not in by_id:
            raise ValueError(f"{field} references missing object {value}")

POSTURES = ("avoid", "watch", "research", "investment_candidate")
DIRECTIONS = ("positive", "neutral", "negative", "uncertain")
CONVICTIONS = ("low", "medium", "high")

_REC_FIELD_ORDER = [
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
    "company_id",
    "security_id",
    "as_of",
    "time_horizon",
    "research_posture",
    "direction",
    "conviction",
    "valuation_snapshot_id",
    "forecast_ids",
    "thesis_ids",
    "evidence_ids",
    "analysis_run_ids",
    "expected_case",
    "downside_case",
    "upside_case",
    "catalysts",
    "falsification_conditions",
    "key_risks",
    "unknowns",
    "freshness_date",
]


def prepare_recommendation_draft(
    root: Path,
    *,
    spec: dict[str, Any],
    created_at: str,
) -> tuple[Path, str]:
    """Prepare a pending Recommendation draft from a spec (dry-run, no writes).

    Enforces the §7 posture ceiling at render time: a spec whose expected/down/
    upside cases direct buy/sell/position sizing is rejected.
    """
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before creating a recommendation"
        )
    company_id = str(spec.get("company_id", "")).strip()
    as_of = str(spec.get("as_of", "")).strip()
    freshness_date = str(spec.get("freshness_date", "")).strip()
    if not is_iso_date(as_of) or not is_iso_date(freshness_date):
        raise ValueError("as_of and freshness_date must be YYYY-MM-DD")
    posture = str(spec.get("research_posture", "research")).strip()
    if posture not in POSTURES:
        raise ValueError(f"research_posture must be one of {sorted(POSTURES)}")
    body_text = " ".join(
        str(spec.get(key, "") or "")
        for key in ("expected_case", "downside_case", "upside_case")
    ) + " " + " ".join(
        str(item) for key in ("catalysts", "key_risks", "unknowns")
        for item in (spec.get(key, []) or [])
    )
    if FORBIDDEN_INVESTMENT_ACTIONS.search(body_text):
        raise ValueError(
            "recommendation body may not direct buy/sell/position sizing (§7 ceiling)"
        )
    by_id = {obj.object_id: obj for obj in objects}
    ensure_known_ids([company_id], "company", by_id, "company_id")
    security_id = str(spec.get("security_id", "")).strip() or None
    if security_id:
        ensure_known_ids([security_id], "security", by_id, "security_id")
    val_id = str(spec.get("valuation_snapshot_id", "")).strip() or None
    if val_id:
        ensure_known_ids(
            [val_id], "valuation_snapshot", by_id, "valuation_snapshot_id"
        )
    ensure_known_ids(
        [str(v) for v in spec.get("forecast_ids", [])],
        "forecast",
        by_id,
        "forecast_ids",
    )
    ensure_known_ids(
        [str(v) for v in spec.get("thesis_ids", [])], "thesis", by_id, "thesis_ids"
    )
    _ensure_exist(
        [str(v) for v in spec.get("evidence_ids", [])], by_id, "evidence_ids"
    )
    ensure_known_ids(
        [str(v) for v in spec.get("analysis_run_ids", [])],
        "analysis_run",
        by_id,
        "analysis_run_ids",
    )

    rec_id = next_object_id(objects, "recommendation", created_at)
    relative = Path("05_Research/Recommendations") / f"{rec_id}.md"
    meta = _recommendation_meta(spec, rec_id, created_at, company_id, security_id)
    return relative, render_recommendation_draft(meta, _recommendation_body(meta))


def apply_recommendation_draft(root: Path, relative: Path, content: str) -> Path:
    """Atomically write the draft (refuses to overwrite an existing file)."""
    return write_new_file(root, relative, content)


def render_recommendation_draft(meta: dict[str, Any], body: str) -> str:
    lines: list[str] = ["---"]
    emitted: set[str] = set()
    for key in _REC_FIELD_ORDER:
        if key in meta and meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
            emitted.add(key)
    for key in sorted(set(meta) - emitted):
        if meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def recommendation_gate(
    root: Path,
    *,
    spec: dict[str, Any],
    as_of: str,
) -> dict[str, list[str]]:
    """§12 deterministic completeness/freshness gate for a Recommendation spec.

    Returns ``{problems: [...]}``; problems non-empty means the spec cannot be
    activated yet. Structure/completeness only — never a correctness judgment.
    """
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    problems: list[str] = []
    thesis_ids = [str(v) for v in spec.get("thesis_ids", [])]
    evidence_ids = [str(v) for v in spec.get("evidence_ids", [])]
    unknowns = [str(v) for v in spec.get("unknowns", [])]
    falsifiers = [str(v) for v in spec.get("falsification_conditions", [])]
    if not thesis_ids:
        problems.append("thesis_ids must be non-empty (evidence-backed posture)")
    if not evidence_ids:
        problems.append("evidence_ids must be non-empty")
    if not unknowns:
        problems.append("unknowns must be non-empty (honest hedging)")
    if not falsifiers:
        problems.append("falsification_conditions must be non-empty")
    body_text = " ".join(
        str(spec.get(key, "") or "")
        for key in ("expected_case", "downside_case", "upside_case")
    )
    if FORBIDDEN_INVESTMENT_ACTIONS.search(body_text):
        problems.append("body contains buy/sell/position-size language (§7 ceiling)")
    val_id = str(spec.get("valuation_snapshot_id", "")).strip() or None
    if val_id:
        try:
            freshness = valuation_freshness(root, val_id=val_id, as_of=as_of)
            if not freshness["fresh"]:
                problems.append(
                    f"valuation {val_id} is stale "
                    f"({freshness['age_days']}d > {freshness['threshold_days']}d)"
                )
        except ValueError as exc:
            problems.append(str(exc))
    if thesis_ids:
        objects, findings = validate_repository(root)
        if any(finding.level == "error" for finding in findings):
            problems.append("repository validation failed during gate")
        else:
            by_id = {obj.object_id: obj for obj in objects}
            unreviewed = [
                tid
                for tid in thesis_ids
                if by_id.get(tid)
                and by_id[tid].metadata.get("review_status") != "reviewed"
            ]
            if unreviewed:
                problems.append(
                    "thesis_ids reference non-reviewed Thesis: "
                    + ", ".join(unreviewed)
                )
    return {"problems": problems}


def recommendation_freshness(
    root: Path,
    *,
    rec_id: str,
    as_of: str,
) -> dict[str, Any]:
    """Check a Recommendation's freshness_date against ``as_of``."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before a recommendation freshness check"
        )
    by_id = {obj.object_id: obj for obj in objects}
    rec = by_id.get(rec_id)
    if rec is None or rec.object_type != "recommendation":
        raise ValueError(f"unknown Recommendation {rec_id}")
    freshness_date = str(rec.metadata.get("freshness_date", ""))
    if not is_iso_date(freshness_date):
        raise ValueError(f"{rec_id} has no valid freshness_date")
    age_days = (date.fromisoformat(as_of) - date.fromisoformat(freshness_date)).days
    return {
        "recommendation_id": rec_id,
        "freshness_date": freshness_date,
        "check_as_of": as_of,
        "age_days": age_days,
        "fresh": age_days <= 90,  # default recommendation review window
    }


def _recommendation_meta(
    spec: dict[str, Any],
    rec_id: str,
    created_at: str,
    company_id: str,
    security_id: str | None,
) -> dict[str, Any]:
    posture = str(spec.get("research_posture", "research")).strip()
    return {
        "id": rec_id,
        "type": "recommendation",
        "title": str(spec.get("title", "")).strip()
        or f"Recommendation: {company_id}",
        "created_at": created_at,
        "updated_at": created_at,
        "schema_version": 2,
        "project_ids": [str(v) for v in spec.get("project_ids", [])],
        "status": "draft",
        "review_status": "pending",
        "tags": [str(v) for v in spec.get("tags", [])],
        "company_id": company_id,
        "security_id": security_id,
        "as_of": str(spec["as_of"]).strip(),
        "time_horizon": str(spec.get("time_horizon", "")).strip(),
        "research_posture": posture,
        "direction": str(spec.get("direction", "uncertain")).strip(),
        "conviction": str(spec.get("conviction", "low")).strip(),
        "valuation_snapshot_id": (
            str(spec.get("valuation_snapshot_id", "")).strip() or None
        ),
        "forecast_ids": [str(v) for v in spec.get("forecast_ids", [])],
        "thesis_ids": [str(v) for v in spec.get("thesis_ids", [])],
        "evidence_ids": [str(v) for v in spec.get("evidence_ids", [])],
        "analysis_run_ids": [str(v) for v in spec.get("analysis_run_ids", [])],
        "expected_case": str(spec.get("expected_case", "")).strip(),
        "downside_case": str(spec.get("downside_case", "")).strip(),
        "upside_case": str(spec.get("upside_case", "")).strip(),
        "catalysts": [str(v) for v in spec.get("catalysts", [])],
        "falsification_conditions": [
            str(v) for v in spec.get("falsification_conditions", [])
        ],
        "key_risks": [str(v) for v in spec.get("key_risks", [])],
        "unknowns": [str(v) for v in spec.get("unknowns", [])],
        "freshness_date": str(spec["freshness_date"]).strip(),
    }


def _recommendation_body(meta: dict[str, Any]) -> str:
    security = meta["security_id"] if meta["security_id"] else "—"
    horizon = meta["time_horizon"] if meta["time_horizon"] else "—"
    val_ref = meta["valuation_snapshot_id"] if meta["valuation_snapshot_id"] else "—"
    return f"""# Recommendation

## Posture

- Company: {meta['company_id']}
- Security: {security}
- As of: {meta['as_of']}
- Time horizon: {horizon}
- Research posture: {meta['research_posture']} (ceiling: investment_candidate)
- Direction: {meta['direction']}
- Conviction: {meta['conviction']}

## Cases

- Expected case: {meta['expected_case']}
- Downside case: {meta['downside_case']}
- Upside case: {meta['upside_case']}

## Catalysts

- {yaml_list(meta['catalysts'])}

## Falsification conditions

- {yaml_list(meta['falsification_conditions'])}

## Key risks

- {yaml_list(meta['key_risks'])}

## Unknowns

- {yaml_list(meta['unknowns'])}

## References

- Valuation snapshot: {val_ref}
- Forecasts: {yaml_list(meta['forecast_ids'])}
- Theses: {yaml_list(meta['thesis_ids'])}
- Evidence: {yaml_list(meta['evidence_ids'])}
- Analysis runs: {yaml_list(meta['analysis_run_ids'])}
- Freshness date: {meta['freshness_date']}

## Review

Pending — run `recommendation gate` until no problems, then review via
`review apply --targets {meta['id']} --decision approve` before activating.
"""


_SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        return yaml_list([str(item) for item in value])
    if isinstance(value, str) and _SAFE_SCALAR_RE.match(value):
        return value
    return yaml_scalar(value)
