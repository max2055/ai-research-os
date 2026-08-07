"""C-004 direct impact proposal + C-005 mechanism validator (Phase 3).

``propose_direct_impacts`` takes a reviewed Event and proposes pending
Impact Assertion (IMP-*) drafts: it bridges the event to the entities it
names via reviewed Ontology Assertions (REL-* that cite the event in their
evidence_ids), then applies the approved predicate->impact rule map
(IMPACT_RULE_MAP.md) to pick impact_type/direction.

Boundaries (Phase 3 §5/§6, RCP-v03-006):
- Only reviewed Events generate authoritative-flow proposals; a pending Event
  raises ValueError (it may only enter sandbox/experimental).
- Only reviewed, as-of-valid Ontology Assertions bridge.
- Targets are the event's OWN named entities (companies/technologies/products)
  that are also an endpoint of a bridging assertion — direct impact only.
  Inferred downstream entities are path expansion (C-006), not here.
- mechanism is generated deterministically and is evidence-anchored: it only
  concatenates facts present in the event title and the reviewed relation, and
  never injects facts absent from Evidence (Phase 3 §6). It must pass
  validate_mechanism (C-005) or the proposal is dropped.
- Output is a proposal dict (no file writes, no authoritative IMP). A human
  reviews and the materialization flow (C-012/C-014) assigns the IMP id via
  next_object_id.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import IMPACT_RULE_MAP

# Direction inference (C-004): the rule map's "mixed" default is overridden by a
# clear event-content valence so a volume-production event surfaces as positive
# supply, not an information-free "mixed". Only "mixed" defaults are overridden
# — an explicit rule-map direction (e.g. COMPETES_WITH->price negative) is an
# approved domain tendency and is respected. Deterministic keyword scoring.
_POSITIVE_RE = re.compile(
    r"(量产|创纪录|增长|上升|提高|大幅|率先|推出|部署|投资|commit|invest|launch|"
    r"deploy|ramp|expand|expansion|increase|increased|growth|grow|record|"
    r"volume production|mass production|mass shipments)",
    re.IGNORECASE,
)
_NEGATIVE_RE = re.compile(
    r"(下滑|下降|降低|短缺|制约|延迟|中断|放缓|亏损|削减|负增长|decline|decreased|"
    r"reduce|reduced|shortage|constraint|delay|cut|lost|loss|negative|fail|"
    r"long lead time|long lead times|backlog|contract price decline)",
    re.IGNORECASE,
)

# Horizon inference (C-004): the horizon is "unknown" by default and filled from
# temporal cues in the event title + Facts section (the evidence content, not
# risk boilerplate). Priority: multi_year > quarter > immediate > year.
_MULTI_YEAR_RE = re.compile(
    r"(multi-year|multi year|多年|through 20\d\d|至 20\d\d|over \d+ ?years?|"
    r"\d+[- ]year|长期|long[- ]term|decade|十年)",
    re.IGNORECASE,
)
_QUARTER_RE = re.compile(
    r"(\bQ[1-4]\b|[1-4]Q\s?\d{2}|\bquarter\b|quarterly|季度|财报|业绩|earnings)",
    re.IGNORECASE,
)
_IMMEDIATE_RE = re.compile(r"(immediate|即日|立即|今日|today|即起)", re.IGNORECASE)
_YEAR_RE = re.compile(
    r"(\bFY\s?\d{2,4}\b|年度|annual|yearly|全年|10-K|20-F)", re.IGNORECASE
)

# Placeholder/empty-mechanism tokens C-005 rejects. Kept deliberately narrow to
# avoid false positives on real (if terse) mechanisms.
_PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|TBA|TBC|FIXME|PLACEHOLDER|XXX)\b"
    r"|\b(to be (determined|announced|decided|completed))\b",
    re.IGNORECASE,
)
_MIN_MECHANISM_LENGTH = 15


def validate_mechanism(text: str) -> list[str]:
    """C-005: return a list of problems (empty = mechanism is acceptable)."""
    problems: list[str] = []
    stripped = text.strip()
    if not stripped:
        problems.append("mechanism is empty")
    elif len(stripped) < _MIN_MECHANISM_LENGTH:
        problems.append("mechanism too short to be meaningful")
    if _PLACEHOLDER_RE.search(text):
        problems.append("mechanism contains placeholder token(s)")
    return problems


def propose_direct_impacts(
    objects: list[ResearchObject],
    *,
    event_id: str,
) -> list[dict[str, Any]]:
    """C-004: reviewed Event -> pending IMP proposal dicts (pure, no writes)."""
    event = _find_event(objects, event_id)
    if event.metadata.get("review_status") != "reviewed":
        raise ValueError(
            f"event {event_id} is not reviewed; pending events only enter sandbox"
        )
    by_id = {obj.object_id: obj for obj in objects}
    today = date.today().isoformat()
    event_entities = set(_entity_ids(event.metadata))
    bridging = [
        rel
        for rel in objects
        if rel.object_type == "ontology_assertion"
        and event_id in (rel.metadata.get("evidence_ids", []) or [])
        and rel.metadata.get("review_status") == "reviewed"
        and _as_of_valid(rel.metadata, today)
    ]
    proposals: list[dict[str, Any]] = []
    for rel in bridging:
        predicate = rel.metadata.get("predicate")
        if predicate not in IMPACT_RULE_MAP:
            continue  # unknown predicate never generates Impact (allowlist)
        subject = rel.metadata.get("subject_id")
        target = rel.metadata.get("object_id")
        allowed = {
            impact_type: direction
            for impact_type, (direction, conditional) in IMPACT_RULE_MAP[
                predicate
            ].items()
            if not conditional  # conditional types need human/mechanism sign-off
        }
        for affected in sorted(event_entities & {subject, target}):
            for impact_type, default_direction in sorted(allowed.items()):
                direction = _infer_direction(event, default_direction)
                mechanism = _build_mechanism(event, rel, by_id, impact_type, affected)
                if validate_mechanism(mechanism):
                    continue  # defensive: never emit an invalid mechanism
                proposals.append(
                    {
                        "type": "impact_assertion",
                        "subject_id": event_id,
                        "target_id": affected,
                        "impact_type": impact_type,
                        "direction": direction,
                        "magnitude": "unknown",
                        "horizon": _infer_horizon(event),
                        "mechanism": mechanism,
                        "trigger_event_ids": [event_id],
                        "evidence_ids": [event_id],
                        "relation_id": rel.object_id,
                        "predicate": predicate,
                        "confidence": float(event.metadata.get("confidence", 0.0)),
                        "review_status": "pending",
                        "valid_from": event.metadata.get("event_date"),
                        "generation_method": "direct-proposal",
                    }
                )
    return _dedup_proposals(proposals)


def _infer_direction(event: ResearchObject, default: str) -> str:
    """Override a "mixed" default with a clear event-content valence.

    Scores the event TITLE only: research-authored titles capture the event's
    essence and are free of the boilerplate risk-factor language that pollutes
    body text (e.g. 10-K/8-K filings), which misfired direction inference on
    deployment/availability events.
    """
    if default != "mixed":
        return default
    text = str(event.metadata.get("title", ""))
    pos = len(_POSITIVE_RE.findall(text))
    neg = len(_NEGATIVE_RE.findall(text))
    if pos - neg >= 1:
        return "positive"
    if neg - pos >= 1:
        return "negative"
    return default


def _infer_horizon(event: ResearchObject) -> str:
    """Infer horizon from temporal cues in title + Facts section.

    Unlike direction, the Facts section is the right signal here (contract
    durations, report periods) and is not polluted by risk-factor boilerplate.
    """
    text = " ".join(
        [
            str(event.metadata.get("title", "")),
            _facts_section(event.body),
        ]
    )
    if _MULTI_YEAR_RE.search(text):
        return "multi_year"
    if _QUARTER_RE.search(text):
        return "quarter"
    if _IMMEDIATE_RE.search(text):
        return "immediate"
    if _YEAR_RE.search(text):
        return "year"
    return "unknown"


def _facts_section(body: str) -> str:
    """Extract the ``## Facts`` section of an Event body (evidence content)."""
    if not body:
        return ""
    lines = body.splitlines()
    in_facts = False
    parts: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Facts"):
            in_facts = True
            continue
        if stripped.startswith("##") and in_facts:
            in_facts = False
            continue
        if in_facts and stripped:
            parts.append(stripped)
    return " ".join(parts)


def _dedup_proposals(
    proposals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse same (target, impact_type); keep highest confidence, merge RELs."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for proposal in proposals:
        key = (proposal["target_id"], proposal["impact_type"])
        current = by_key.get(key)
        if current is None or proposal["confidence"] > current["confidence"]:
            by_key[key] = dict(proposal)
    for proposal in proposals:
        key = (proposal["target_id"], proposal["impact_type"])
        by_key[key]["relation_ids"] = sorted(
            {
                other["relation_id"]
                for other in proposals
                if (other["target_id"], other["impact_type"]) == key
            }
        )
    return sorted(by_key.values(), key=lambda p: (p["target_id"], p["impact_type"]))


def render_proposal(proposal: dict[str, Any]) -> str:
    return json.dumps(proposal, ensure_ascii=False, sort_keys=True)


def _find_event(objects: list[ResearchObject], event_id: str) -> ResearchObject:
    for obj in objects:
        if obj.object_type == "event" and obj.object_id == event_id:
            return obj
    raise ValueError(f"unknown event {event_id}")


def _entity_ids(meta: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for field in ("companies", "technologies", "products"):
        ids.extend(meta.get(field, []) or [])
    return [str(value) for value in ids]


def _as_of_valid(meta: dict[str, Any], today: str) -> bool:
    valid_to = meta.get("valid_to")
    return valid_to is None or str(valid_to) >= today


def _build_mechanism(
    event: ResearchObject,
    rel: ResearchObject,
    by_id: dict[str, ResearchObject],
    impact_type: str,
    target_id: str,
) -> str:
    subject = _label(by_id, rel.metadata.get("subject_id", ""))
    predicate = rel.metadata.get("predicate", "")
    object_ = _label(by_id, rel.metadata.get("object_id", ""))
    target = _label(by_id, target_id)
    return (
        f"Per {event.object_id} ({event.metadata.get('title', '')}), which "
        f"evidences the reviewed relation {subject} {predicate} {object_} "
        f"({rel.object_id}), the reported change bears on {impact_type} "
        f"impact for {target}."
    )


def _label(by_id: dict[str, ResearchObject], entity_id: str) -> str:
    obj = by_id.get(entity_id)
    if obj is not None and obj.metadata.get("title"):
        return str(obj.metadata["title"])
    return entity_id
