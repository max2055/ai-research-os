"""D-009 Analysis Run transaction (RCP-v03-007, Phase 4 §5/§10).

``prepare_run`` executes the Mode Runner pipeline (Phase 4 §5):

    require runnable mode → resolve reviewed inputs → freeze snapshot hash →
    render versioned prompt → model execution → parse structured output →
    deterministic contract validation → build pending Analysis Run

and returns a ``RunPlan``. ``apply_run`` materializes the run atomically. The
transaction rule (Phase 4 §5): a failure NEVER leaves a half-written formal
object — if the mode is unavailable, inputs are invalid, the provider times out,
or the output fails the contract, ``prepare_run`` raises ``RunError`` carrying an
``error_type`` and nothing is written. Only a contract-passing run is
materialized, as ``status=completed`` / ``review_status=pending`` (a human must
review before the run may enter a Report; RCP-v03-007 point 3).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

from research_os.adapters.model import ModelAdapter, build_adapter
from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.analysis_contract import validate_run_contract
from research_os.services.analysis_registry import (
    ModeError,
    mode_metadata,
    require_runnable,
)
from research_os.services.discovery_sandbox import validate_discovery_sandbox
from research_os.services.drafts import (
    next_object_id,
    write_new_file,
    yaml_list,
    yaml_scalar,
)
from research_os.services.input_resolver import (
    InputError,
    resolve_inputs,
)
from research_os.services.prompt_renderer import PromptError, render_prompt
from research_os.services.red_team_enforcement import validate_red_team_enforcement
from research_os.services.validation import validate_repository

_ANL_PATH = "05_Research/Analysis"

_INPUT_FIELDS = (
    "input_source_ids",
    "input_event_ids",
    "input_impact_ids",
    "input_thesis_ids",
)

# Frontmatter field order mirrors the schema; unknown keys sort after these.
_ANL_FIELD_ORDER = [
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
    "mode_id",
    "scope_ids",
    "as_of",
    "input_source_ids",
    "input_event_ids",
    "input_impact_ids",
    "input_thesis_ids",
    "input_snapshot_hash",
    "model_provider",
    "model_id",
    "model_parameters",
    "prompt_hash",
    "output_hash",
    "generation_method",
]

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", flags=re.MULTILINE)


class RunError(ValueError):
    """A run failed; ``error_type`` records the failure class (Phase 4 §5)."""

    def __init__(self, error_type: str, message: str) -> None:
        self.error_type = error_type
        super().__init__(message)


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    mode_id: str
    scope_ids: list[str]
    input_source_ids: list[str]
    input_event_ids: list[str]
    input_impact_ids: list[str]
    input_thesis_ids: list[str]
    as_of: str
    input_snapshot_hash: str
    model_provider: str
    model_id: str
    model_parameters: dict[str, str]
    prompt_hash: str
    output_hash: str
    generation_method: str
    body: str
    relative_path: Path
    content: str

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "id": self.run_id,
            "type": "analysis_run",
            "title": f"Analysis Run {self.run_id} ({self.mode_id})",
            "created_at": self.created_at,
            "updated_at": self.created_at,
            "schema_version": 2,
            "project_ids": [],
            "status": "completed",
            "review_status": "pending",
            "tags": [],
            "mode_id": self.mode_id,
            "scope_ids": self.scope_ids,
            "as_of": self.as_of,
            "input_source_ids": self.input_source_ids,
            "input_event_ids": self.input_event_ids,
            "input_impact_ids": self.input_impact_ids,
            "input_thesis_ids": self.input_thesis_ids,
            "input_snapshot_hash": self.input_snapshot_hash,
            "model_provider": self.model_provider,
            "model_id": self.model_id,
            "model_parameters": self.model_parameters,
            "prompt_hash": self.prompt_hash,
            "output_hash": self.output_hash,
            "generation_method": self.generation_method,
        }

    @property
    def created_at(self) -> str:
        match = re.fullmatch(r"ANL-(\d{8})-\d{3}", self.run_id)
        if not match:
            raise RunError("invalid-run-id", f"bad run id {self.run_id!r}")
        compact = match.group(1)
        return f"{compact[:4]}-{compact[4:6]}-{compact[6:]}"


def _body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _parse_output(raw: str, run_id: str) -> str:
    """The model output is the structured markdown body (the output contract
    validator decides whether it satisfies the required sections)."""
    body = raw.strip()
    if not body:
        raise RunError("empty-output", "model returned empty output")
    return body


def _validate_mode_output_sections(
    mode: ResearchObject,
    body: str,
) -> None:
    present = set(_SECTION_RE.findall(body))
    missing = [
        section
        for section in mode_metadata(mode)["required_output_sections"]
        if section not in present
    ]
    if missing:
        raise RunError(
            "output-contract-failed",
            "missing mode-required output sections: " + ", ".join(missing),
        )


def _contract_findings(
    run_obj: ResearchObject,
    by_id: dict[str, ResearchObject],
) -> list[str]:
    findings: list[Any] = []
    validate_run_contract(run_obj, by_id, findings)
    validate_red_team_enforcement(run_obj, by_id, findings)
    validate_discovery_sandbox(run_obj, by_id, findings)
    return [str(finding.message) for finding in findings]


def prepare_run(
    root: Path,
    *,
    mode_id: str,
    as_of: str,
    scope_ids: list[str] | None = None,
    input_source_ids: list[str] | None = None,
    input_event_ids: list[str] | None = None,
    input_impact_ids: list[str] | None = None,
    input_thesis_ids: list[str] | None = None,
    model_provider: str = "echo",
    model_id: str = "echo",
    model_parameters: dict[str, str] | None = None,
    timeout: float = 60.0,
    created_at: str | None = None,
    adapter: ModelAdapter | None = None,
) -> RunPlan:
    """Execute the Mode Runner pipeline and return a write-ready RunPlan.

    Pure — no files are written (even on success). Raises ``RunError`` on any
    failure without leaving a half-written object.
    """
    if not is_iso_date(as_of) and as_of != "unknown":
        raise RunError("invalid-as-of", f"as_of {as_of!r} is not a valid date")
    run_date = created_at or date.today().isoformat()
    if not is_iso_date(run_date):
        raise RunError("invalid-date", f"created_at {run_date!r} is not a valid date")

    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise RunError(
            "repository-invalid",
            "repository validation must pass before an analysis run",
        )
    by_id = {obj.object_id: obj for obj in objects}

    try:
        mode = require_runnable(objects, mode_id)
    except ModeError as exc:
        raise RunError("mode-unavailable", str(exc)) from exc

    try:
        resolved = resolve_inputs(
            objects,
            mode_id=mode_id,
            scope_ids=scope_ids,
            input_source_ids=input_source_ids,
            input_event_ids=input_event_ids,
            input_impact_ids=input_impact_ids,
            input_thesis_ids=input_thesis_ids,
            as_of=as_of,
        )
    except InputError as exc:
        raise RunError("input-error", str(exc)) from exc

    try:
        prompt, prompt_hash = render_prompt(
            mode, resolved, as_of=as_of, root=root
        )
    except PromptError as exc:
        raise RunError("prompt-error", str(exc)) from exc

    model = adapter or build_adapter(model_provider)
    try:
        raw = model.generate(prompt, timeout=timeout)
    except TimeoutError as exc:
        raise RunError("timeout", f"model provider timed out: {exc}") from exc
    except Exception as exc:  # provider failure boundary (Phase 4 §10)
        raise RunError("provider-failure", f"model provider failed: {exc}") from exc

    run_id = next_object_id(objects, "analysis_run", run_date)
    body = _parse_output(raw, run_id)
    _validate_mode_output_sections(mode, body)

    plan = RunPlan(
        run_id=run_id,
        mode_id=mode_id,
        scope_ids=list(scope_ids or []),
        input_source_ids=list(input_source_ids or []),
        input_event_ids=list(input_event_ids or []),
        input_impact_ids=list(input_impact_ids or []),
        input_thesis_ids=list(input_thesis_ids or []),
        as_of=as_of,
        input_snapshot_hash=resolved.input_snapshot_hash,
        model_provider=model_provider,
        model_id=model_id,
        model_parameters=dict(model_parameters or {}),
        prompt_hash=prompt_hash,
        output_hash=_body_hash(body),
        generation_method="mode-runner",
        body=body,
        relative_path=Path(_ANL_PATH) / f"{run_id}.md",
        content="",
    )
    plan = replace(plan, content=render_run_draft(plan.metadata, body))

    run_obj = ResearchObject(
        path=root / plan.relative_path,
        metadata=plan.metadata,
        body=body,
    )
    contract_problems = _contract_findings(run_obj, by_id)
    if contract_problems:
        raise RunError(
            "output-contract-failed",
            "run output failed the contract: " + "; ".join(contract_problems),
        )
    return plan


def apply_run(root: Path, plan: RunPlan) -> Path:
    """Atomically materialize the run (refuses to overwrite an existing file)."""
    return write_new_file(root, plan.relative_path, plan.content)


def run_analysis(
    root: Path,
    *,
    mode_id: str,
    as_of: str,
    scope_ids: list[str] | None = None,
    input_source_ids: list[str] | None = None,
    input_event_ids: list[str] | None = None,
    input_impact_ids: list[str] | None = None,
    input_thesis_ids: list[str] | None = None,
    model_provider: str = "echo",
    model_id: str = "echo",
    model_parameters: dict[str, str] | None = None,
    timeout: float = 60.0,
    created_at: str | None = None,
    apply: bool = False,
    adapter: ModelAdapter | None = None,
) -> str:
    """Dry-run preview (default) or materialize an Analysis Run.

    Dry-run returns the rendered run draft and writes nothing; ``apply=True``
    atomically writes the run and returns the created path. Failures raise
    ``RunError`` and never leave a half-written object.
    """
    plan = prepare_run(
        root,
        mode_id=mode_id,
        as_of=as_of,
        scope_ids=scope_ids,
        input_source_ids=input_source_ids,
        input_event_ids=input_event_ids,
        input_impact_ids=input_impact_ids,
        input_thesis_ids=input_thesis_ids,
        model_provider=model_provider,
        model_id=model_id,
        model_parameters=model_parameters,
        timeout=timeout,
        created_at=created_at,
        adapter=adapter,
    )
    if not apply:
        return (
            f"# {plan.relative_path}\n\n{plan.content}\n"
            "DRY-RUN: no files changed; rerun with --apply to write"
        )
    path = apply_run(root, plan)
    return f"CREATED: {path.relative_to(root)}"


def render_run_draft(meta: dict[str, Any], body: str) -> str:
    """Render run metadata + body into a front-matter Markdown file."""
    lines: list[str] = ["---"]
    emitted: set[str] = set()
    for key in _ANL_FIELD_ORDER:
        if key in meta and meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
            emitted.add(key)
    for key in sorted(set(meta) - emitted):
        if meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def _yaml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        if not value:
            return "{}"
        inner = ", ".join(
            f"{yaml_scalar(str(k))}: {yaml_scalar(str(v))}" for k, v in value.items()
        )
        return "{" + inner + "}"
    if isinstance(value, list):
        return yaml_list([str(item) for item in value])
    return yaml_scalar(str(value))


def render_run_detail(run: ResearchObject, by_id: dict[str, ResearchObject]) -> str:
    """D-014 ``analyze show``: frozen run detail + mode label + input listing."""
    mode = by_id.get(str(run.metadata.get("mode_id", "")))
    mode_label = (
        str(mode.metadata.get("name", "")) if mode is not None else "(unknown mode)"
    )
    lines = [
        f"# {run.object_id}",
        f"mode: {run.metadata.get('mode_id')}  ({mode_label})",
        f"as_of: {run.metadata.get('as_of')}",
        f"status: {run.metadata.get('status')}  "
        f"(review: {run.metadata.get('review_status')})",
        f"model: {run.metadata.get('model_provider')} / {run.metadata.get('model_id')}",
        f"input_snapshot_hash: {run.metadata.get('input_snapshot_hash') or '—'}",
        f"prompt_hash: {run.metadata.get('prompt_hash') or '—'}",
        f"output_hash: {run.metadata.get('output_hash') or '—'}",
        "inputs:",
    ]
    for field in _INPUT_FIELDS:
        ids = run.metadata.get(field, []) or []
        if ids:
            lines.append(f"  {field}: {', '.join(str(i) for i in ids)}")
    lines.append("")
    lines.append(run.body.rstrip())
    return "\n".join(lines)
