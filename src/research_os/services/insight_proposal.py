"""D-016 promote insight workflow (RCP-v03-007, Phase 4 §3/§5/§9).

Turns a reviewed Analysis Run into a pending Thesis PROPOSAL document under
``05_Research/Analysis_Proposals/``. The proposal is NOT an authoritative
Thesis: this service never creates or modifies a ``THS-*`` object and never
changes Thesis confidence (RCP-v03-007 points 3/6). A human reviews the
proposal and decides whether to promote it into a real Thesis via the normal
Thesis flow.

Gates (proposals are cheap, but they must come from a run a human already
endorsed and that did its mode's job):

- The run must exist, be ``completed``, and be ``reviewed`` — a pending or
  rejected run cannot propose an insight.
- The run's mode must resolve.
- Red-team runs must have done their adversarial job (D-012 RT001/RT002 absent):
  a boilerplate red-team run proposing an insight would leak an unchallenged
  conclusion.
- Open-discovery runs stay in the sandbox (D-013): the proposal renders its
  ``extract_hypotheses`` candidates as a Hypothesis proposal and is explicitly
  NOT a Thesis.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.services.analysis_registry import mode_metadata, mode_slug
from research_os.services.discovery_sandbox import (
    extract_hypotheses,
    validate_discovery_sandbox,
)
from research_os.services.drafts import write_new_file, yaml_list, yaml_scalar
from research_os.services.red_team_enforcement import validate_red_team_enforcement
from research_os.services.validation import validate_repository

_PROPOSALS_PATH = "05_Research/Analysis_Proposals"

_INPUT_FIELDS = (
    "input_source_ids",
    "input_event_ids",
    "input_impact_ids",
    "input_thesis_ids",
)


def prepare_thesis_proposal(
    root: Path,
    *,
    run_id: str,
    created_at: str,
) -> tuple[Path, str]:
    """Prepare a pending Thesis proposal from a reviewed Analysis Run.

    Returns ``(relative_path, markdown_content)``. Pure — no file writes.
    Raises ``ValueError`` on any gate failure. The proposal is not an
    authoritative Thesis and never creates a ``THS-*`` object.
    """
    if not is_iso_date(created_at):
        raise ValueError("created_at must be YYYY-MM-DD")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError("repository validation must pass before proposing an insight")
    by_id = {obj.object_id: obj for obj in objects}
    run = by_id.get(run_id)
    if run is None or run.object_type != "analysis_run":
        raise ValueError(f"unknown analysis run {run_id!r}")

    status = str(run.metadata.get("status", ""))
    if status != "completed":
        raise ValueError(
            f"run {run_id} is {status!r}, not completed; "
            "only completed runs may propose an insight"
        )
    review_status = str(run.metadata.get("review_status", ""))
    if review_status != "reviewed":
        raise ValueError(
            f"run {run_id} is review_status={review_status!r}; "
            "only reviewed runs may propose an insight"
        )
    mode = by_id.get(str(run.metadata.get("mode_id", "")))
    if mode is None or mode.object_type != "analysis_mode":
        raise ValueError(f"run {run_id} references an unknown mode")

    # Reuse D-012/D-013 validators: any finding means the run failed its mode's
    # enforcement and cannot be proposed.
    enforcement: list[Any] = []
    validate_red_team_enforcement(run, by_id, enforcement)
    validate_discovery_sandbox(run, by_id, enforcement)
    if enforcement:
        codes = ", ".join(sorted({f.code for f in enforcement}))
        raise ValueError(
            f"run {run_id} fails enforcement ({codes}); cannot propose an insight"
        )

    is_discovery = mode_slug(mode.object_id) == "open-discovery"
    relative = Path(_PROPOSALS_PATH) / f"Thesis_Proposal_{run_id}.md"
    meta = _proposal_meta(run, mode, created_at)
    body = _proposal_body(run, mode, by_id, meta, is_discovery)
    return relative, render_proposal_draft(meta, body)


def apply_thesis_proposal(root: Path, relative: Path, content: str) -> Path:
    """Atomically write the proposal (refuses to overwrite an existing file)."""
    return write_new_file(root, relative, content)


def propose_thesis(
    root: Path,
    *,
    run_id: str,
    created_at: str,
    apply: bool = False,
) -> str:
    """D-016 flow: reviewed run -> pending Thesis proposal.

    Dry-run (default) previews the proposal and writes nothing; ``apply=True``
    materializes it (refusing overwrite).
    """
    relative, content = prepare_thesis_proposal(
        root, run_id=run_id, created_at=created_at
    )
    if not apply:
        return (
            f"# {relative}\n\n{content}\n"
            "DRY-RUN: no files changed; rerun with --apply to write"
        )
    path = apply_thesis_proposal(root, relative, content)
    return f"CREATED: {path.relative_to(root.resolve())}"


def render_proposal_draft(meta: dict[str, Any], body: str) -> str:
    """Render proposal metadata + body into a lightweight front-matter file."""
    lines: list[str] = ["---"]
    for key in _FIELD_ORDER:
        if key in meta and meta[key] is not None:
            lines.append(f"{key}: {_yaml_value(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


_FIELD_ORDER = [
    "type",
    "status",
    "source_run",
    "mode_id",
    "mode_name",
    "as_of",
    "created_at",
    "input_snapshot_hash",
]


def _proposal_meta(
    run: ResearchObject,
    mode: ResearchObject,
    created_at: str,
) -> dict[str, Any]:
    meta = mode_metadata(mode)
    return {
        "type": "thesis_proposal",
        "status": "pending",
        "source_run": run.object_id,
        "mode_id": run.metadata.get("mode_id"),
        "mode_name": meta["name"],
        "as_of": run.metadata.get("as_of"),
        "created_at": created_at,
        "input_snapshot_hash": run.metadata.get("input_snapshot_hash"),
    }


def _proposal_body(
    run: ResearchObject,
    mode: ResearchObject,
    by_id: dict[str, ResearchObject],
    meta: dict[str, Any],
    is_discovery: bool,
) -> str:
    parts: list[str] = []
    if is_discovery:
        hypotheses = extract_hypotheses(run, by_id)
        if hypotheses:
            bullets = "\n".join(f"- {h}" for h in hypotheses)
        else:
            bullets = "- （无候选假设）"
        parts.append(f"## Hypothesis candidates\n\n{bullets}\n")
        for title in (
            "Why surprising",
            "Minimum evidence needed",
            "Disconfirming search plan",
            "Related entities",
            "Spurious-correlation risk",
        ):
            section = _section(run.body, title)
            if section:
                parts.append(f"## {title}\n\n{section}\n")
    else:
        thesis = _section(run.body, "Judgments") or "—"
        reasoning = _section(run.body, "Inferences") or "—"
        counter = _section(run.body, "Contradicting evidence") or "—"
        alternatives = _section(run.body, "Alternative explanations") or "—"
        parts.append(f"## Proposed Thesis\n\n{thesis}\n")
        parts.append(f"## Reasoning\n\n{reasoning}\n")
        parts.append(f"## Contradicting evidence\n\n{counter}\n")
        parts.append(f"## Alternative explanations\n\n{alternatives}\n")
    parts.append(f"## Unknowns\n\n{_section(run.body, 'Unknowns') or '—'}\n")
    evidence = [
        str(value)
        for field in _INPUT_FIELDS
        for value in (run.metadata.get(field, []) or [])
    ]
    if evidence:
        bullets = "\n".join(f"- {e}" for e in evidence)
        parts.append(f"## Evidence used\n\n{bullets}\n")
    else:
        parts.append("## Evidence used\n\n（无冻结输入）\n")
    parts.append(
        "## Review path\n\n"
        "这是 Proposal，不是权威 Thesis。来源为 reviewed run "
        f"{meta['source_run']}（{meta['mode_id']}）；"
        "由人工复核后按 Thesis 流程创建 THS-* 对象，本文件不直接改写任何 Thesis "
        "（RCP-v03-007 points 3/6）。"
        + (
            "\n\nOpen Discovery 边界（D-013）：以上为候选 Hypothesis，"
            "不构成权威研究结论。"
            if is_discovery
            else ""
        )
    )
    return "\n".join(parts)


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        return yaml_list([str(item) for item in value])
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", value):
        return value
    return yaml_scalar(value)
