"""D-006 input resolver (RCP-v03-007, Phase 4 §3/§10).

Resolves a run's declared scope + evidence inputs into concrete objects and
freezes the deterministic input snapshot hash. Enforces the evidence rules of
the analysis OS:

- every declared input/scope must resolve to a real object (``InputError``);
- evidence inputs (source/event/impact_assertion/thesis) must be ``reviewed`` —
  a run never consumes unapproved evidence (Phase 4 §10 "reviewed-only input");
- scope entities (sector/company/technology) are definitions and only need to
  exist; scope evidence (event/thesis) must be reviewed;
- as-of does not leak future evidence: an Event dated after ``as_of`` is
  rejected (Phase 4 §10);
- the scope types must be in the mode's ``applicable_scopes`` and every
  ``required_input_type`` must have at least one input (mode requirements).

The snapshot hash covers the mode id, as-of and every resolved object's content
fingerprint (metadata + body), so editing any input changes the freeze and the
run is reproducible. Pure service — no writes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.services.analysis_registry import mode_metadata

# Evidence types consumed as inputs must be human-reviewed.
_REVIEWED_INPUT_TYPES = frozenset({"source", "event", "impact_assertion", "thesis"})
# Scope entity definitions (existence suffices) vs scope evidence (reviewed).
_SCOPE_ENTITY_TYPES = frozenset({"sector", "company", "technology"})
_SCOPE_EVIDENCE_TYPES = frozenset({"event", "thesis"})


class InputError(ValueError):
    """A declared input/scope could not be resolved or violates a rule."""


@dataclass(frozen=True)
class ResolvedInputs:
    objects: list[ResearchObject] = field(default_factory=list)
    scope_ids: list[str] = field(default_factory=list)
    input_source_ids: list[str] = field(default_factory=list)
    input_event_ids: list[str] = field(default_factory=list)
    input_impact_ids: list[str] = field(default_factory=list)
    input_thesis_ids: list[str] = field(default_factory=list)
    input_snapshot_hash: str = ""

    def ids_by_type(self, object_type: str) -> list[str]:
        return [
            obj.object_id
            for obj in self.objects
            if obj.object_type == object_type
        ]


def _object_fingerprint(obj: ResearchObject) -> str:
    canonical = json.dumps(
        obj.metadata,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(
        (canonical + "\n" + obj.body).encode("utf-8")
    ).hexdigest()


def _snapshot_hash(
    mode_id: str,
    as_of: str,
    resolved: list[ResearchObject],
) -> str:
    manifest = {
        "mode_id": mode_id,
        "as_of": as_of,
        "inputs": sorted(
            (obj.object_type, obj.object_id, _object_fingerprint(obj))
            for obj in resolved
        ),
    }
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_inputs(
    objects: list[ResearchObject],
    *,
    mode_id: str,
    scope_ids: list[str] | None = None,
    input_source_ids: list[str] | None = None,
    input_event_ids: list[str] | None = None,
    input_impact_ids: list[str] | None = None,
    input_thesis_ids: list[str] | None = None,
    as_of: str,
) -> ResolvedInputs:
    mode = next(
        (
            obj
            for obj in objects
            if obj.object_type == "analysis_mode" and obj.object_id == mode_id
        ),
        None,
    )
    if mode is None:
        raise InputError(f"unknown analysis mode {mode_id!r}")
    mode_meta = mode_metadata(mode)
    by_id = {obj.object_id: obj for obj in objects}

    declared: list[tuple[str, str]] = []
    for field_, value in (
        ("scope_ids", scope_ids),
        ("input_source_ids", input_source_ids),
        ("input_event_ids", input_event_ids),
        ("input_impact_ids", input_impact_ids),
        ("input_thesis_ids", input_thesis_ids),
    ):
        for value_id in value or []:
            declared.append((field_, str(value_id)))

    resolved: list[ResearchObject] = []
    for field_, value_id in declared:
        obj = by_id.get(value_id)
        if obj is None:
            raise InputError(f"{field_} references missing object {value_id!r}")
        resolved.append(obj)

    _validate_reviewed(resolved, by_id)
    _validate_as_of(resolved, as_of)
    _validate_scope_fit(resolved, scope_ids or [], mode_meta)
    _validate_required_inputs(resolved, mode_meta)

    return ResolvedInputs(
        objects=sorted(resolved, key=lambda obj: (obj.object_type, obj.object_id)),
        scope_ids=list(scope_ids or []),
        input_source_ids=list(input_source_ids or []),
        input_event_ids=list(input_event_ids or []),
        input_impact_ids=list(input_impact_ids or []),
        input_thesis_ids=list(input_thesis_ids or []),
        input_snapshot_hash=_snapshot_hash(
            mode_id,
            as_of,
            sorted(resolved, key=lambda obj: (obj.object_type, obj.object_id)),
        ),
    )


def _validate_reviewed(
    resolved: list[ResearchObject],
    by_id: dict[str, ResearchObject],
) -> None:
    for obj in resolved:
        if obj.object_type in _REVIEWED_INPUT_TYPES:
            if obj.metadata.get("review_status") != "reviewed":
                raise InputError(
                    f"input {obj.object_id} is not reviewed "
                    f"({obj.metadata.get('review_status', 'unknown')})"
                )
        elif obj.object_type in _SCOPE_ENTITY_TYPES:
            continue
        elif obj.object_type in _SCOPE_EVIDENCE_TYPES:
            if obj.metadata.get("review_status") != "reviewed":
                raise InputError(
                    f"scope {obj.object_id} is not reviewed "
                    f"({obj.metadata.get('review_status', 'unknown')})"
                )
        else:
            raise InputError(
                f"{obj.object_id} type {obj.object_type!r} cannot be a run input"
            )


def _validate_as_of(resolved: list[ResearchObject], as_of: str) -> None:
    if as_of == "unknown":
        return
    try:
        cutoff = date.fromisoformat(as_of)
    except ValueError as exc:
        raise InputError(f"as_of {as_of!r} is not a valid date") from exc
    for obj in resolved:
        if obj.object_type != "event":
            continue
        event_date = obj.metadata.get("event_date")
        if not event_date or event_date == "unknown":
            continue
        try:
            observed = date.fromisoformat(str(event_date))
        except ValueError:
            continue
        if observed > cutoff:
            raise InputError(
                f"input {obj.object_id} is dated {event_date}, after as_of {as_of}"
            )


def _validate_scope_fit(
    resolved: list[ResearchObject],
    scope_ids: list[str],
    mode_meta: dict[str, Any],
) -> None:
    allowed = set(mode_meta["applicable_scopes"])
    if not allowed:
        return
    by_id = {obj.object_id: obj for obj in resolved}
    for scope_id in scope_ids:
        obj = by_id.get(scope_id)
        if obj is None:
            continue
        if obj.object_type not in allowed:
            raise InputError(
                f"scope {scope_id} is type {obj.object_type!r}, not applicable "
                f"to this mode (allowed: {sorted(allowed)})"
            )


def _validate_required_inputs(
    resolved: list[ResearchObject],
    mode_meta: dict[str, Any],
) -> None:
    present: dict[str, int] = {}
    for obj in resolved:
        present[obj.object_type] = present.get(obj.object_type, 0) + 1
    for required in mode_meta["required_input_types"]:
        if present.get(required, 0) == 0:
            raise InputError(
                f"mode requires input type {required!r} but none was provided"
            )
