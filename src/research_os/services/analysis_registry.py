"""D-005 mode registry (RCP-v03-007, Phase 4 §2).

An Analysis Mode (``MOD-ANL-<slug>-vN``) is a versioned contract. The registry
resolves modes by id/slug and enforces the status gates for running one:

- ``find_mode`` — exact id lookup;
- ``mode_versions`` / ``active_mode`` — versioned history of one slug;
- ``require_runnable`` — a mode may run a new authoritative Analysis Run only
  when it is ``active`` AND ``reviewed`` (RCP-v03-007 review point 6: mode
  activation and run review are human approvals; a ``deprecated`` or unapproved
  mode must not spawn new authoritative runs).

Pure service — no file writes. The runner (D-009) composes this with the input
resolver, prompt renderer and model adapter.
"""

from __future__ import annotations

import re
from typing import Any

from research_os.domain.models import ResearchObject

_MODE_ID_RE = re.compile(r"^MOD-ANL-(.+)-v(\d+)$")


class ModeError(ValueError):
    """Base class for registry failures."""


class UnknownMode(ModeError):
    def __init__(self, mode_id: str) -> None:
        self.mode_id = mode_id
        super().__init__(f"unknown analysis mode {mode_id!r}")


class ModeNotRunnable(ModeError):
    def __init__(self, mode_id: str, reason: str) -> None:
        self.mode_id = mode_id
        self.reason = reason
        super().__init__(f"mode {mode_id} is not runnable: {reason}")


def mode_slug(mode_id: str) -> str:
    match = _MODE_ID_RE.fullmatch(mode_id)
    if not match:
        raise ModeError(f"invalid analysis mode id {mode_id!r}")
    return match.group(1)


def mode_version(mode_id: str) -> int:
    match = _MODE_ID_RE.fullmatch(mode_id)
    if not match:
        raise ModeError(f"invalid analysis mode id {mode_id!r}")
    return int(match.group(2))


def find_mode(
    objects: list[ResearchObject],
    mode_id: str,
) -> ResearchObject | None:
    for obj in objects:
        if obj.object_type == "analysis_mode" and obj.object_id == mode_id:
            return obj
    return None


def mode_versions(
    objects: list[ResearchObject],
    slug: str,
) -> list[ResearchObject]:
    """All mode versions of one slug, oldest to newest by version number."""
    versions = [
        obj
        for obj in objects
        if obj.object_type == "analysis_mode" and mode_slug(obj.object_id) == slug
    ]
    return sorted(versions, key=lambda obj: mode_version(obj.object_id))


def active_mode(objects: list[ResearchObject], slug: str) -> ResearchObject | None:
    """The current ``active`` version of a slug, or None."""
    for obj in reversed(mode_versions(objects, slug)):
        if obj.metadata.get("status") == "active":
            return obj
    return None


def require_runnable(
    objects: list[ResearchObject],
    mode_id: str,
) -> ResearchObject:
    """Return the mode if it may produce a new authoritative run, else raise.

    Status gates: the exact version must exist, be ``active`` (a deprecated or
    merely-proposed mode cannot spawn new authoritative runs), and be
    ``reviewed`` (human approval, RCP-v03-007 point 6).
    """
    mode = find_mode(objects, mode_id)
    if mode is None:
        raise UnknownMode(mode_id)
    status = str(mode.metadata.get("status", ""))
    if status == "deprecated":
        raise ModeNotRunnable(mode_id, "mode is deprecated")
    if status != "active":
        raise ModeNotRunnable(mode_id, f"mode status is {status!r}, not active")
    if mode.metadata.get("review_status") != "reviewed":
        raise ModeNotRunnable(mode_id, "mode is not reviewed")
    return mode


def mode_metadata(mode: ResearchObject) -> dict[str, Any]:
    """Normalized field access (defaults for unset optional contract fields)."""
    meta = mode.metadata
    return {
        "id": str(meta.get("id", "")),
        "name": str(meta.get("name", "")),
        "purpose": str(meta.get("purpose", "")),
        "applicable_scopes": list(meta.get("applicable_scopes", []) or []),
        "required_input_types": list(meta.get("required_input_types", []) or []),
        "optional_input_types": list(meta.get("optional_input_types", []) or []),
        "required_questions": list(meta.get("required_questions", []) or []),
        "required_output_sections": list(
            meta.get("required_output_sections", []) or []
        ),
        "assumption_policy": str(meta.get("assumption_policy", "")),
        "evidence_policy": str(meta.get("evidence_policy", "")),
        "counterevidence_policy": str(meta.get("counterevidence_policy", "")),
        "time_horizons": list(meta.get("time_horizons", []) or []),
        "prohibited_conclusions": list(meta.get("prohibited_conclusions", []) or []),
        "prompt_template_path": str(meta.get("prompt_template_path", "")),
        "output_schema_path": str(meta.get("output_schema_path", "")),
        "evaluator_version": str(meta.get("evaluator_version", "")),
        "status": str(meta.get("status", "")),
        "valid_from": str(meta.get("valid_from", "") or ""),
        "review_status": str(meta.get("review_status", "")),
    }


def render_mode_list(objects: list[ResearchObject]) -> str:
    """D-014 ``modes list``: table of every mode with its version/status gate."""
    modes = sorted(
        (obj for obj in objects if obj.object_type == "analysis_mode"),
        key=lambda obj: obj.object_id,
    )
    if not modes:
        return "no analysis modes registered"
    header = (
        f"{'MODE':<38} {'NAME':<18} {'SCOPE':<34} {'STATUS':<10} "
        f"{'REVIEW':<10} V"
    )
    lines = [header, "-" * len(header)]
    for mode in modes:
        meta = mode_metadata(mode)
        scopes = ",".join(meta["applicable_scopes"])
        lines.append(
            f"{mode.object_id:<38} {meta['name'][:18]:<18} {scopes[:34]:<34} "
            f"{meta['status']:<10} {meta['review_status']:<10} "
            f"{mode_version(mode.object_id)}"
        )
    return "\n".join(lines)


def render_mode_detail(mode: ResearchObject, objects: list[ResearchObject]) -> str:
    """D-014 ``modes show``: the full versioned contract of one mode."""
    meta = mode_metadata(mode)
    lines = [
        f"# {mode.object_id}",
        f"name: {meta['name']}",
        f"status: {meta['status']}  (review: {meta['review_status']}, "
        f"valid_from: {meta['valid_from'] or '—'})",
        f"purpose: {meta['purpose']}",
        f"applicable_scopes: {', '.join(meta['applicable_scopes'])}",
        f"required_input_types: {', '.join(meta['required_input_types']) or '—'}",
        f"optional_input_types: {', '.join(meta['optional_input_types']) or '—'}",
        f"time_horizons: {', '.join(meta['time_horizons']) or '—'}",
        "",
        "## Required questions",
    ]
    lines.extend(f"- {q}" for q in meta["required_questions"])
    lines.append("")
    lines.append("## Required output sections")
    lines.extend(f"- {s}" for s in meta["required_output_sections"])
    lines.append("")
    lines.append("## Assumption policy")
    lines.append(meta["assumption_policy"] or "—")
    lines.append("")
    lines.append("## Evidence policy")
    lines.append(meta["evidence_policy"] or "—")
    lines.append("")
    lines.append("## Counterevidence policy")
    lines.append(meta["counterevidence_policy"] or "—")
    lines.append("")
    lines.append("## Prohibited conclusions")
    lines.extend(f"- {c}" for c in meta["prohibited_conclusions"])
    lines.append("")
    lines.append("## Prompt / output contract")
    lines.append(
        f"- prompt_template_path: {meta['prompt_template_path'] or '(default)'}"
    )
    lines.append(f"- output_schema_path: {meta['output_schema_path'] or '—'}")
    lines.append(f"- evaluator_version: {meta['evaluator_version'] or '—'}")
    lines.append("")
    versions = [o for o in mode_versions(objects, mode_slug(mode.object_id))]
    lines.append(f"## Versions of {mode_slug(mode.object_id)}")
    for version in versions:
        lines.append(
            f"- {version.object_id}  (status={version.metadata.get('status')}, "
            f"review={version.metadata.get('review_status')}, "
            f"valid_from={version.metadata.get('valid_from') or '—'})"
        )
    if mode.metadata.get("review_status") == "reviewed":
        lines.append(f"\nCurrent: runnable via `analyze run --mode {mode.object_id}`")
    else:
        lines.append(
            f"\nBlocked: review_status={mode.metadata.get('review_status')} — "
            "require_runnable refuses new authoritative runs"
        )
    return "\n".join(lines)


def render_mode_check(objects: list[ResearchObject]) -> str:
    """D-014 ``modes check``: which modes may produce a new authoritative run."""
    modes = sorted(
        (obj for obj in objects if obj.object_type == "analysis_mode"),
        key=lambda obj: obj.object_id,
    )
    lines: list[str] = []
    for mode in modes:
        try:
            require_runnable(objects, mode.object_id)
            lines.append(f"OK       {mode.object_id}")
        except ModeError as exc:
            lines.append(f"BLOCKED  {mode.object_id}  ({exc})")
    blocked = [line for line in lines if line.startswith("BLOCKED")]
    ok = len(lines) - len(blocked)
    lines.append(f"\n{ok} runnable / {len(lines)} modes")
    return "\n".join(lines)
