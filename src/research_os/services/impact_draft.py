"""C-011 impact assertion materialization (Phase 3).

Turns a C-004 direct-impact proposal dict into a pending ``IMP-YYYYMMDD-NNN``
Markdown object on disk. Mirrors the ontology-assertion draft flow
(``prepare_assertion_draft``/``write_new_file``): prepare is a pure dry-run
preview, apply is an atomic write that refuses to overwrite.

Materialized IMPs are ``review_status: pending``. The generic review flow
(reviews.py ``apply_review``) flips them to reviewed + writes a REV-* Decision
— no review-system changes needed (impact_assertion is in REVIEWABLE_TYPES).

Traceability: the proposal's ``relation_id``/``predicate`` (the bridging REL
that produced the impact) are kept as extra front-matter fields. The
ImpactAssertionSchema allows extra fields (ConfigDict extra="allow").
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_os.domain.policies import is_iso_date
from research_os.services.drafts import (
    next_object_id,
    write_new_file,
    yaml_list,
    yaml_scalar,
)
from research_os.services.impact_proposal import propose_direct_impacts
from research_os.services.validation import validate_repository

_IMPACT_FIELD_ORDER = [
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
    "trigger_event_ids",
    "subject_id",
    "impact_type",
    "target_id",
    "direction",
    "magnitude",
    "horizon",
    "lag_start",
    "lag_end",
    "mechanism",
    "conditions",
    "countervailing_factors",
    "alternative_explanations",
    "evidence_ids",
    "confidence",
    "valid_from",
    "valid_to",
    "review_date",
    "generation_method",
    "relation_id",
    "predicate",
]


def prepare_impact_draft(
    root: Path,
    *,
    proposal: dict[str, Any],
    created_at: str,
) -> tuple[Path, str]:
    """Prepare a pending Impact Assertion draft from a C-004 proposal.

    Returns (relative_path, markdown_content). Pure — no file writes.
    """
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before creating an impact assertion"
        )
    subject_id = str(proposal["subject_id"])
    by_id = {obj.object_id: obj for obj in objects}
    if subject_id not in by_id:
        raise ValueError(f"subject event {subject_id!r} does not exist")
    imp_id = next_object_id(objects, "impact_assertion", created_at)
    meta = _proposal_meta(proposal, imp_id, created_at)
    relative = Path("05_Research/Assertions") / f"{imp_id}.md"
    return relative, render_impact_draft(meta, _impact_body(meta))


def apply_impact_draft(root: Path, relative: Path, content: str) -> Path:
    """Atomically write the draft (refuses to overwrite an existing file)."""
    return write_new_file(root, relative, content)


def prepare_impact_batch(
    root: Path,
    *,
    event_id: str,
    created_at: str,
    apply: bool = False,
) -> str:
    """C-014 flow: propose direct impacts for an Event and draft/materialize.

    Dry-run (default) previews each pending IMP draft and writes nothing;
    ``apply=True`` materializes them via write_new_file (refusing overwrite).
    """
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before impact proposals")
    proposals = propose_direct_impacts(objects, event_id=event_id)
    if not proposals:
        return f"no direct-impact proposals for {event_id}"
    if not apply:
        preview = []
        for proposal in proposals:
            relative, content = prepare_impact_draft(
                root, proposal=proposal, created_at=created_at
            )
            preview.append(f"# {relative}\n\n{content}")
        return (
            "\n\n".join(preview)
            + "\nDRY-RUN: no files changed; rerun with --apply to write"
        )
    # Prepare + apply per proposal so next_object_id sees prior writes (each
    # prepare_impact_draft re-validates and scans the current disk state).
    created: list[Path] = []
    skipped: list[str] = []
    for proposal in proposals:
        relative, content = prepare_impact_draft(
            root, proposal=proposal, created_at=created_at
        )
        try:
            created.append(apply_impact_draft(root, relative, content))
        except FileExistsError:
            skipped.append(str(relative))
    lines = [f"- {path}" for path in created]
    if skipped:
        lines.append(f"skipped (already exist): {', '.join(skipped)}")
    return "CREATED:\n" + "\n".join(lines)


def render_impact_draft(meta: dict[str, Any], body: str) -> str:
    """Render a meta dict + body into a comment-preserving front-matter file."""
    lines: list[str] = ["---"]
    emitted: set[str] = set()
    for key in _IMPACT_FIELD_ORDER:
        if key in meta and meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
            emitted.add(key)
    for key in sorted(set(meta) - emitted):
        if meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def _proposal_meta(
    proposal: dict[str, Any], imp_id: str, created_at: str
) -> dict[str, Any]:
    subject_id = str(proposal["subject_id"])
    target_id = str(proposal["target_id"])
    impact_type = str(proposal["impact_type"])
    return {
        "id": imp_id,
        "type": "impact_assertion",
        "title": f"{subject_id} {impact_type} impact on {target_id}",
        "created_at": created_at,
        "updated_at": created_at,
        "schema_version": 2,
        "project_ids": list(proposal.get("project_ids", [])),
        "status": "active",
        "review_status": "pending",
        "tags": [],
        "trigger_event_ids": list(proposal.get("trigger_event_ids", [])),
        "subject_id": subject_id,
        "impact_type": impact_type,
        "target_id": target_id,
        "direction": str(proposal["direction"]),
        "magnitude": str(proposal["magnitude"]),
        "horizon": str(proposal["horizon"]),
        "mechanism": str(proposal["mechanism"]),
        "conditions": list(proposal.get("conditions", [])),
        "countervailing_factors": list(proposal.get("countervailing_factors", [])),
        "alternative_explanations": list(proposal.get("alternative_explanations", [])),
        "evidence_ids": list(proposal.get("evidence_ids", [])),
        "confidence": proposal.get("confidence", 0.0),
        "valid_from": proposal.get("valid_from"),
        "generation_method": "direct-proposal",
        "relation_id": str(proposal.get("relation_id", "")),
        "predicate": str(proposal.get("predicate", "")),
    }


def _impact_body(meta: dict[str, Any]) -> str:
    return f"""# Impact Assertion

## Assertion

- Trigger Event: {meta['subject_id']}
- Subject: {meta['subject_id']}
- Target: {meta['target_id']}
- Impact type: {meta['impact_type']}
- Direction: {meta['direction']}
- Magnitude: {meta['magnitude']}
- Horizon: {meta['horizon']}
- Confidence: {meta['confidence']}
- Mechanism: {meta['mechanism']}

## Evidence

- {yaml_list(meta['evidence_ids'])}

## Review

Pending — review via `review apply --targets {meta['id']} --decision approve`.

## Notes

- Generated by C-004 direct impact proposal from {meta['subject_id']} via
  {meta['relation_id']} ({meta['predicate']}).
- Mechanism is a deterministic, evidence-anchored draft; refine at review.
"""


_SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        return yaml_list([str(item) for item in value])
    # Emit enum/ID/date tokens unquoted (matches repo front-matter style); quote
    # free text that would otherwise be ambiguous YAML.
    if isinstance(value, str) and _SAFE_SCALAR_RE.match(value):
        return value
    return yaml_scalar(value)
