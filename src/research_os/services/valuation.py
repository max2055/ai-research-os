"""E-011 deterministic valuation service (Phase 5, WP-510).

A ValuationSnapshot (VAL-*) freezes dated, sourced market inputs so that
Equity Value, Enterprise Value and a matched-period multiple are computed
deterministically (RCP-v03-009, Phase 5 §6). The derived figures are NEVER
stored as authoritative inputs — they are recomputed from the frozen inputs on
every render, so the record cannot drift.

``compute_valuation`` is a pure function; ``prepare_valuation_draft`` validates
the spec against the repository and renders a pending VAL object (status draft /
review pending); ``apply_valuation_draft`` is an atomic write that refuses to
overwrite; ``valuation_freshness`` checks a snapshot against its
freshness_threshold (``"7d"`` / ``"30d"``) for the E-013 recommendation gate.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.drafts import (
    ensure_known_ids,
    next_object_id,
    write_new_file,
    yaml_list,
    yaml_scalar,
)
from research_os.services.validation import validate_repository

VALUATION_IDENTITIES = (
    "ev/ebitda",
    "ev/ebit",
    "ev/sales",
    "ev/fcf",
    "pe",
    "ps",
    "manual",
)

_VAL_FIELD_ORDER = [
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
    "market_price",
    "currency",
    "shares",
    "debt",
    "cash",
    "other_adjustments",
    "valuation_identity",
    "denominator_period",
    "denominator_value",
    "source_ids",
    "event_ids",
    "scenario_set",
    "freshness_threshold",
    "data_license",
]


def compute_valuation(
    *,
    market_price: float,
    shares: float,
    debt: float = 0.0,
    cash: float = 0.0,
    other_adjustments: float = 0.0,
    valuation_identity: str = "",
    denominator: float | None = None,
) -> dict[str, float | None]:
    """Deterministic Equity/Enterprise Value + matched-period multiple.

    Pure — no I/O. Units follow the inputs: if ``market_price`` is per-share
    in a currency and ``shares`` is in the same scale, ``equity_value`` and
    ``enterprise_value`` are in that currency. Raises ValueError on impossible
    inputs (negative price, non-positive shares).
    """
    if market_price < 0:
        raise ValueError("market_price must be non-negative")
    if shares <= 0:
        raise ValueError("shares must be positive")
    equity_value = market_price * shares
    enterprise_value = (
        equity_value + (debt or 0.0) - (cash or 0.0) + (other_adjustments or 0.0)
    )
    multiple: float | None = None
    identity = valuation_identity.strip().lower()
    if identity not in VALUATION_IDENTITIES:
        raise ValueError(
            f"valuation_identity must be one of {sorted(VALUATION_IDENTITIES)}"
        )
    if identity != "manual":
        if denominator is None:
            raise ValueError(
                f"valuation_identity {identity!r} requires a denominator_value"
            )
        if denominator <= 0:
            raise ValueError("denominator_value must be positive")
        if identity.startswith("ev/"):
            multiple = enterprise_value / denominator
        else:  # pe / ps use the equity value
            multiple = equity_value / denominator
    return {
        "equity_value": equity_value,
        "enterprise_value": enterprise_value,
        "multiple": multiple,
    }


def _parse_threshold(raw: str) -> int:
    match = re.fullmatch(r"(\d+)\s*d(?:ays?)?", str(raw).strip().lower())
    if not match:
        raise ValueError(f"freshness_threshold must be like '7d' or '30d', got {raw!r}")
    return int(match.group(1))


def prepare_valuation_draft(
    root: Path,
    *,
    spec: dict[str, Any],
    created_at: str,
) -> tuple[Path, str]:
    """Prepare a pending ValuationSnapshot draft from a spec (dry-run)."""
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before creating a valuation snapshot"
        )
    company_id = str(spec.get("company_id", "")).strip()
    as_of = str(spec.get("as_of", "")).strip()
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    market_price = spec.get("market_price")
    shares = spec.get("shares")
    if market_price is None or shares is None:
        raise ValueError("market_price and shares are required")
    # run the deterministic compute so impossible inputs fail at draft time
    compute_valuation(
        market_price=float(market_price),
        shares=float(shares),
        debt=float(spec.get("debt", 0.0) or 0.0),
        cash=float(spec.get("cash", 0.0) or 0.0),
        other_adjustments=float(spec.get("other_adjustments", 0.0) or 0.0),
        valuation_identity=str(spec.get("valuation_identity", "manual")),
        denominator=(
            float(spec["denominator_value"])
            if spec.get("denominator_value") is not None
            else None
        ),
    )
    if spec.get("freshness_threshold"):
        _parse_threshold(str(spec["freshness_threshold"]))
    by_id = {obj.object_id: obj for obj in objects}
    ensure_known_ids([company_id], "company", by_id, "company_id")
    security_id = str(spec.get("security_id", "")).strip() or None
    if security_id:
        ensure_known_ids([security_id], "security", by_id, "security_id")
    ensure_known_ids(
        [str(v) for v in spec.get("source_ids", [])], "source", by_id, "source_ids"
    )
    ensure_known_ids(
        [str(v) for v in spec.get("event_ids", [])], "event", by_id, "event_ids"
    )

    val_id = next_object_id(objects, "valuation_snapshot", created_at)
    relative = Path("05_Research/Valuations") / f"{val_id}.md"
    meta = _valuation_meta(spec, val_id, created_at, company_id, security_id)
    return relative, render_valuation_draft(meta, _valuation_body(meta))


def apply_valuation_draft(root: Path, relative: Path, content: str) -> Path:
    """Atomically write the draft (refuses to overwrite an existing file)."""
    return write_new_file(root, relative, content)


def render_valuation_draft(meta: dict[str, Any], body: str) -> str:
    lines: list[str] = ["---"]
    emitted: set[str] = set()
    for key in _VAL_FIELD_ORDER:
        if key in meta and meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
            emitted.add(key)
    for key in sorted(set(meta) - emitted):
        if meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def render_valuation_rows(snapshots: list[ResearchObject]) -> str:
    """Render a valuation list as a markdown table (``valuation list``)."""
    lines = [
        "| ID | Company | As of | Price | Identity | Status |",
        "|---|---|---|---|---|---|",
    ]
    for obj in sorted(snapshots, key=lambda obj: obj.object_id):
        lines.append(
            f"| {obj.object_id} | {obj.metadata.get('company_id', '')} | "
            f"{obj.metadata.get('as_of', '')} | "
            f"{obj.metadata.get('market_price', '')} | "
            f"{obj.metadata.get('valuation_identity', '')} | "
            f"{obj.metadata.get('status', '')} |"
        )
    if not snapshots:
        lines.append("| — | No valuation snapshots | — | — | — | — |")
    return "\n".join(lines) + "\n"


def valuation_freshness(
    root: Path,
    *,
    val_id: str,
    as_of: str,
) -> dict[str, Any]:
    """Check a ValuationSnapshot against its freshness_threshold (E-013 gate)."""
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before a valuation freshness check"
        )
    by_id = {obj.object_id: obj for obj in objects}
    val = by_id.get(val_id)
    if val is None or val.object_type != "valuation_snapshot":
        raise ValueError(f"unknown ValuationSnapshot {val_id}")
    snapshot_as_of = str(val.metadata.get("as_of", ""))
    if not is_iso_date(snapshot_as_of):
        raise ValueError(f"{val_id} has no valid as_of")
    threshold = str(val.metadata.get("freshness_threshold", "")).strip()
    if not threshold:
        threshold = "7d"  # default freshness window
    days = _parse_threshold(threshold)
    age_days = (date.fromisoformat(as_of) - date.fromisoformat(snapshot_as_of)).days
    return {
        "valuation_id": val_id,
        "snapshot_as_of": snapshot_as_of,
        "check_as_of": as_of,
        "age_days": age_days,
        "threshold_days": days,
        "fresh": age_days <= days,
    }


def _valuation_meta(
    spec: dict[str, Any],
    val_id: str,
    created_at: str,
    company_id: str,
    security_id: str | None,
) -> dict[str, Any]:
    valuation_identity = str(spec.get("valuation_identity", "manual")).strip()
    return {
        "id": val_id,
        "type": "valuation_snapshot",
        "title": str(spec.get("title", "")).strip() or f"Valuation: {company_id}",
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
        "market_price": spec["market_price"],
        "currency": str(spec.get("currency", "")).strip(),
        "shares": spec["shares"],
        "debt": spec.get("debt"),
        "cash": spec.get("cash"),
        "other_adjustments": spec.get("other_adjustments"),
        "valuation_identity": valuation_identity,
        "denominator_period": str(spec.get("denominator_period", "")).strip(),
        "denominator_value": spec.get("denominator_value"),
        "source_ids": [str(v) for v in spec.get("source_ids", [])],
        "event_ids": [str(v) for v in spec.get("event_ids", [])],
        "scenario_set": str(spec.get("scenario_set", "")).strip(),
        "freshness_threshold": str(spec.get("freshness_threshold", "7d")).strip(),
        "data_license": str(spec.get("data_license", "")).strip(),
    }


def _valuation_body(meta: dict[str, Any]) -> str:
    debt = meta["debt"] if meta["debt"] is not None else 0.0
    cash = meta["cash"] if meta["cash"] is not None else 0.0
    adj = meta["other_adjustments"] if meta["other_adjustments"] is not None else 0.0
    identity = meta["valuation_identity"]
    denominator = meta.get("denominator_value")
    computed = compute_valuation(
        market_price=float(meta["market_price"]),
        shares=float(meta["shares"]),
        debt=float(debt),
        cash=float(cash),
        other_adjustments=float(adj),
        valuation_identity=identity or "manual",
        denominator=float(denominator) if denominator is not None else None,
    )
    multiple = (
        f"{computed['multiple']:.2f}" if computed["multiple"] is not None else "—"
    )
    unit = meta["currency"] if meta["currency"] else "currency units"
    period = meta["denominator_period"] if meta["denominator_period"] else "—"
    return f"""# Valuation Snapshot

## Inputs

- Company: {meta['company_id']}
- Security: {meta['security_id'] if meta['security_id'] else '—'}
- As of: {meta['as_of']}
- Market price: {meta['market_price']} {meta['currency']}
- Shares: {meta['shares']}
- Debt: {debt} / Cash: {cash} / Other adjustments: {adj}
- Valuation identity: {identity}
- Denominator period: {period}

## Derived valuation (deterministic from inputs)

- Equity Value = price × shares = {computed['equity_value']:.2f}
- Enterprise Value = equity + debt − cash + adjustments
  = {computed['enterprise_value']:.2f}
- Multiple ({identity}, {period}): {multiple}
- Units: {unit}

## Scenario set

- {meta['scenario_set'] if meta['scenario_set'] else '—'}

## Sources

- {yaml_list(meta['source_ids'])}

## Review

Pending — review via `review apply --targets {meta['id']} --decision approve`.
"""


_SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        return yaml_list([str(item) for item in value])
    if isinstance(value, str) and _SAFE_SCALAR_RE.match(value):
        return value
    return yaml_scalar(value)
