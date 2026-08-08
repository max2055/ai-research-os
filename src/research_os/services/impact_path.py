"""C-006~C-010 impact path engine (Phase 3).

``expand_impact_paths`` expands impact paths from a reviewed Event across the
reviewed Ontology graph: hop 1 are direct targets (the event's own named
entities that are also an endpoint of a bridging assertion), hops 2+ traverse
reviewed, as-of-valid relations (forward edge + symmetric reverse) up to
``max_depth``.

Governance gate (Phase 3 §12, Backlog §6): multi-hop proposals were ACTIVE
only after the direct-impact 20-event Field Gate (C-018) passes. **C-018
APPROVED 2026-08-08** — ``max_depth`` now defaults to 3 (multi-hop active).

C-006 path expansion: max depth 3 / fan-out 10 / per-path cycle control /
pruning reasons recorded (Phase 3 §6).
C-007 temporal filter: is_valid_as_of respects valid_from/valid_to.
C-008 contradiction detector: positive+negative, or multiple horizons, for the
same target are made visible, never silently netted (§2.10/§6).
C-009 path dedup: same entity sequence + same relation sequence folds to one
representative with variant_count.
C-010 confidence policy: weakest-link (min of hop confidences); never the
product of per-hop scores; any unknown hop => overall unknown (None).

All functions are pure (no file I/O). Mechanisms are generated
deterministically and pass through validate_mechanism (C-005); hops whose
mechanism fails are pruned.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import (
    DEFAULT_IMPACT_DIRECTION,
    PRIMARY_IMPACT_TYPE,
    SYMMETRIC_PREDICATES,
)
from research_os.services.impact_proposal import (
    _build_mechanism,
    _entity_ids,
    validate_mechanism,
)


def is_valid_as_of(meta: dict[str, Any], as_of: str) -> bool:
    """C-007: true if the assertion window contains ``as_of`` (open-ended ok)."""
    valid_from = meta.get("valid_from")
    if valid_from and str(valid_from) > as_of:
        return False
    valid_to = meta.get("valid_to")
    return not (valid_to and str(valid_to) < as_of)


def expand_impact_paths(
    objects: list[ResearchObject],
    *,
    event_id: str,
    as_of: str | None = None,
    max_depth: int = 3,
    fan_out: int = 10,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """C-006: reviewed Event -> (impact paths, pruning reasons) (pure, no writes)."""
    if max_depth < 1 or max_depth > 3:
        raise ValueError("max_depth must be between 1 and 3")
    if fan_out < 1:
        raise ValueError("fan_out must be >= 1")
    event = _find_event(objects, event_id)
    if event.metadata.get("review_status") != "reviewed":
        raise ValueError(
            f"event {event_id} is not reviewed; pending events only enter sandbox"
        )
    as_of = as_of or date.today().isoformat()
    by_id = {obj.object_id: obj for obj in objects}
    event_entities = set(_entity_ids(event.metadata))

    reviewed_rels = [
        rel
        for rel in objects
        if rel.object_type == "ontology_assertion"
        and rel.metadata.get("review_status") == "reviewed"
        and is_valid_as_of(rel.metadata, as_of)
    ]
    bridging = [
        rel
        for rel in reviewed_rels
        if event_id in (rel.metadata.get("evidence_ids", []) or [])
    ]

    # Forward adjacency (+ symmetric reverse), rule-map semantics only.
    adj: dict[str, list[tuple[str, str, str, float]]] = defaultdict(list)
    pruned: list[dict[str, Any]] = []
    for rel in reviewed_rels:
        predicate = str(rel.metadata.get("predicate") or "")
        if predicate not in PRIMARY_IMPACT_TYPE:
            pruned.append({"reason": "no-rule-map-predicate", "at": rel.object_id})
            continue
        subject = str(rel.metadata.get("subject_id") or "")
        object_ = str(rel.metadata.get("object_id") or "")
        confidence = _hop_confidence(rel.metadata)
        adj[subject].append((rel.object_id, predicate, object_, confidence))
        if predicate in SYMMETRIC_PREDICATES:
            adj[object_].append((rel.object_id, predicate, subject, confidence))

    # Hop 1: direct targets from bridging assertions.
    paths: list[dict[str, Any]] = []
    for rel in bridging:
        predicate = str(rel.metadata.get("predicate") or "")
        if predicate not in PRIMARY_IMPACT_TYPE:
            pruned.append({"reason": "no-rule-map-predicate", "at": rel.object_id})
            continue
        subject = str(rel.metadata.get("subject_id") or "")
        object_ = str(rel.metadata.get("object_id") or "")
        impact_type = PRIMARY_IMPACT_TYPE[predicate]
        direction = DEFAULT_IMPACT_DIRECTION[predicate]
        for target in sorted(event_entities & {subject, object_}):
            mechanism = _build_mechanism(event, rel, by_id, impact_type, target)
            if validate_mechanism(mechanism):
                pruned.append(
                    {
                        "reason": "invalid-mechanism",
                        "at": rel.object_id,
                        "target": target,
                    }
                )
                continue
            hop = {
                "step": 1,
                "rel_id": rel.object_id,
                "predicate": predicate,
                "from_id": event_id,
                "to_id": target,
                "impact_type": impact_type,
                "direction": direction,
                "horizon": "unknown",
                "mechanism": mechanism,
                "confidence": _hop_confidence(rel.metadata),
            }
            paths.append(
                {
                    "trigger_event_id": event_id,
                    "entity_sequence": [event_id, target],
                    "hops": [hop],
                    "terminal_id": target,
                    "pruned": [],
                    "confidence": None,
                }
            )

    # Hops 2+: traverse adjacency level by level (per-path cycle control).
    # Copy `frontier` so the BFS iterates only the current level — aliasing the
    # growing `paths` list would pick up appended paths and explode past
    # max_depth (C-019 benchmark caught this on dense graphs).
    frontier = list(paths)
    for depth in range(2, max_depth + 1):
        next_frontier: list[dict[str, Any]] = []
        for path in frontier:
            terminal = path["terminal_id"]
            visited = set(path["entity_sequence"])
            neighbors = adj.get(terminal, [])
            if len(neighbors) > fan_out:
                path["pruned"].append(
                    {
                        "reason": "fan-out-capped",
                        "at": terminal,
                        "cut": len(neighbors) - fan_out,
                    }
                )
            for rel_id, predicate, neighbor, confidence in neighbors[:fan_out]:
                if neighbor in visited:
                    path["pruned"].append(
                        {"reason": "cycle", "at": rel_id, "node": neighbor}
                    )
                    continue
                impact_type = PRIMARY_IMPACT_TYPE[predicate]
                direction = DEFAULT_IMPACT_DIRECTION[predicate]
                mechanism = _hop_mechanism(by_id, rel_id, impact_type, neighbor)
                if validate_mechanism(mechanism):
                    path["pruned"].append({"reason": "invalid-mechanism", "at": rel_id})
                    continue
                hop = {
                    "step": depth,
                    "rel_id": rel_id,
                    "predicate": predicate,
                    "from_id": terminal,
                    "to_id": neighbor,
                    "impact_type": impact_type,
                    "direction": direction,
                    "horizon": "unknown",
                    "mechanism": mechanism,
                    "confidence": confidence,
                }
                next_path = {
                    "trigger_event_id": event_id,
                    "entity_sequence": path["entity_sequence"] + [neighbor],
                    "hops": list(path["hops"]) + [hop],
                    "terminal_id": neighbor,
                    "pruned": list(path["pruned"]),
                    "confidence": None,
                }
                paths.append(next_path)
                next_frontier.append(next_path)
        frontier = next_frontier
        if not frontier:
            break

    for path in paths:
        path["confidence"] = path_confidence(path)
    return paths, pruned


def dedup_paths(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """C-009: fold same entity-sequence + same relation-sequence to one rep."""
    deduped: list[dict[str, Any]] = []
    seen: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
    for path in paths:
        key = (
            tuple(path["entity_sequence"]),
            tuple(hop["rel_id"] for hop in path["hops"]),
        )
        if key in seen:
            seen[key]["variant_count"] += 1
        else:
            entry = {**path, "variant_count": 1}
            deduped.append(entry)
            seen[key] = entry
    return deduped


def detect_contradictions(
    impact_likes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """C-008: surface coexisting positive/negative or multi-horizon per target."""
    by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for imp in impact_likes:
        target = imp.get("target_id")
        if target:
            by_target[str(target)].append(imp)
    conflicts: list[dict[str, Any]] = []
    for target in sorted(by_target):
        imps = by_target[target]
        directions = sorted(
            {str(imp.get("direction")) for imp in imps if imp.get("direction")}
        )
        horizons = sorted(
            {
                str(imp.get("horizon"))
                for imp in imps
                if imp.get("horizon") not in (None, "unknown")
            }
        )
        issues: list[str] = []
        if "positive" in directions and "negative" in directions:
            issues.append("positive-and-negative-coexist")
        if len(horizons) >= 2:
            issues.append("multiple-horizons-coexist")
        if issues:
            conflicts.append(
                {
                    "target_id": target,
                    "directions_present": directions,
                    "horizons_present": horizons,
                    "conflicts": issues,
                    "assertion_count": len(imps),
                }
            )
    return conflicts


def path_confidence(path: dict[str, Any]) -> float | None:
    """C-010: weakest-link (min of hop confidences); None if any hop unknown."""
    confidences: list[float] = []
    for hop in path["hops"]:
        value = hop.get("confidence")
        if value is None:
            return None
        confidences.append(float(value))
    if not confidences:
        return None
    return min(confidences)


def _find_event(objects: list[ResearchObject], event_id: str) -> ResearchObject:
    for obj in objects:
        if obj.object_type == "event" and obj.object_id == event_id:
            return obj
    raise ValueError(f"unknown event {event_id}")


def _hop_confidence(meta: dict[str, Any]) -> float:
    value = meta.get("confidence")
    return float(value) if value is not None else 0.0


def _hop_mechanism(
    by_id: dict[str, ResearchObject],
    rel_id: str,
    impact_type: str,
    target_id: str,
) -> str:
    rel = by_id[rel_id]
    subject = _label(by_id, rel.metadata.get("subject_id", ""))
    predicate = rel.metadata.get("predicate", "")
    object_ = _label(by_id, rel.metadata.get("object_id", ""))
    target = _label(by_id, target_id)
    return (
        f"Relation {subject} {predicate} {object_} ({rel_id}) propagates the "
        f"prior step's change to {target} via {impact_type}."
    )


def _label(by_id: dict[str, ResearchObject], entity_id: str) -> str:
    obj = by_id.get(entity_id)
    if obj is not None and obj.metadata.get("title"):
        return str(obj.metadata["title"])
    return entity_id
