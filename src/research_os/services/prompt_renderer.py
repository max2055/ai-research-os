"""D-007 prompt renderer (RCP-v03-007, Phase 4 §3/§5).

Renders a deterministic, versioned prompt for one Analysis Run from the mode
contract + the frozen resolved inputs. ``render_prompt`` returns
``(prompt, prompt_hash)``; the hash is sha256 of the prompt string, so identical
mode + inputs + as-of + template yield an identical prompt hash (Phase 4 §10:
"prompt/input/output hash").

The default template forces the shared output contract (the nine body sections
of Phase 4 §3) and injects the mode's required questions and policies. A mode
may override the template via ``prompt_template_path`` (a file inside the
repository); placeholders use the ``{field}`` syntax below. Pure service — no
writes.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.services.analysis_registry import mode_metadata
from research_os.services.input_resolver import ResolvedInputs

DEFAULT_TEMPLATE = """\
You are performing an Analysis Run for the research-OS {mode_id} mode.

# Mode contract
- Purpose: {purpose}
- Required questions:
{required_questions}
- Assumption policy: {assumption_policy}
- Evidence policy: {evidence_policy}
- Counterevidence policy: {counterevidence_policy}
- Time horizons: {time_horizons}
- Prohibited conclusions: {prohibited_conclusions}

# Frozen inputs (as-of {as_of})
{inputs}

# Output contract
Produce a markdown analysis body with exactly these sections, in order:
## Facts used
## Inferences
## Judgments
## Contradicting evidence
## Alternative explanations
## Unknowns
## Indicators
## Mode-specific output
## Limitations

Rules:
- Facts used may cite ONLY the frozen inputs above, by permanent id.
- Separate Facts (what the inputs state) from Inferences (what follows) from
  Judgments (your assessment). Never blend them.
- Contradicting evidence and Alternative explanations must be non-empty; if the
  inputs contain no contrary signal, say so explicitly.
- Do not reach any prohibited conclusion.
- Do not leave placeholder text.
"""


class PromptError(ValueError):
    """The prompt could not be rendered."""


def _fmt_list(values: list[str]) -> str:
    if not values:
        return "(none)"
    return "\n".join(f"- {value}" for value in values)


def _fmt_inputs(inputs: ResolvedInputs) -> str:
    if not inputs.objects:
        return "(no inputs)"
    blocks: list[str] = []
    for obj in inputs.objects:
        title = obj.metadata.get("title", "")
        blocks.append(f"### {obj.object_id} ({obj.object_type}) — {title}")
        if obj.body.strip():
            blocks.append(obj.body.strip())
    return "\n\n".join(blocks)


def _placeholder_value(
    key: str,
    mode: ResearchObject,
    inputs: ResolvedInputs,
    as_of: str,
) -> str:
    meta = mode_metadata(mode)
    values: dict[str, str] = {
        "mode_id": meta["id"],
        "purpose": meta["purpose"] or "(not specified)",
        "required_questions": _fmt_list(meta["required_questions"]),
        "assumption_policy": meta["assumption_policy"] or "(not specified)",
        "evidence_policy": meta["evidence_policy"] or "(not specified)",
        "counterevidence_policy": meta["counterevidence_policy"] or "(not specified)",
        "time_horizons": _fmt_list(meta["time_horizons"]),
        "prohibited_conclusions": _fmt_list(meta["prohibited_conclusions"]),
        "as_of": as_of,
        "inputs": _fmt_inputs(inputs),
    }
    return values[key]


def _apply_template(
    template: str,
    mode: ResearchObject,
    inputs: ResolvedInputs,
    as_of: str,
) -> str:
    def replace(match: Any) -> str:
        return _placeholder_value(match.group(1), mode, inputs, as_of)

    return re.sub(r"\{([a-z_]+)\}", replace, template)


def render_prompt(
    mode: ResearchObject,
    inputs: ResolvedInputs,
    *,
    as_of: str,
    root: Path | None = None,
) -> tuple[str, str]:
    """Return ``(prompt, prompt_hash)`` deterministically.

    ``root`` is only needed when the mode's ``prompt_template_path`` points at a
    repository file; the default embedded template is used otherwise.
    """
    meta = mode_metadata(mode)
    template = DEFAULT_TEMPLATE
    template_path = meta["prompt_template_path"]
    if template_path:
        if root is None:
            raise PromptError(
                "mode has prompt_template_path but no root was provided"
            )
        path = root / template_path
        try:
            template = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PromptError(
                f"cannot read prompt template {template_path!r}: {exc}"
            ) from exc
    prompt = _apply_template(template, mode, inputs, as_of)
    return prompt, hashlib.sha256(prompt.encode("utf-8")).hexdigest()
