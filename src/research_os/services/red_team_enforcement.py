"""D-012 Red Team enforcement (RCP-v03-007, Phase 4 §4.8/§10).

The Red Team mode exists to FIND counter-evidence, shared upstreams, timing
mismatches, value-capture risk, priced-in expectations, regulatory/execution
risk and unobservable variables. A completed red-team run that merely denies
there is any counter-evidence ("None found" / "无") has not done its job. This
validator rejects boilerplate so a red-team run cannot pass with empty
adversarial content:

- ``RT001`` counter-evidence section is a bare denial or near-empty;
- ``RT002`` alternative explanations section is a bare denial or near-empty.

Only completed runs of a mode whose slug is ``red-team`` are checked. Wired into
``validate_repository`` and the run transaction (D-009) so a boilerplate red
team run is rejected both at creation and on later repository validation.
"""

from __future__ import annotations

import re

from research_os.domain.models import Finding, ResearchObject
from research_os.services.analysis_registry import mode_slug

# Bare-denial / near-empty boilerplate (the section must be SUBSTANTIVE, not a
# refusal). Matches whole-section denials and minimal placeholders.
_BOILERPLATE_RE = re.compile(
    r"^\s*(?:无|没有|不存在|没有找到|未发现|nil|none|n/a|na|nothing|"
    r"no (?:contradicting|alternative|evidence|such|direct).*|"
    r"not (?:found|applicable)|(?:there )?(?:is|are) (?:no|none)\b.*|—|-|\.)*\s*$",
    re.IGNORECASE,
)
# CJK sentences are dense: a substantive clause is well under 30 chars, so the
# minimum is deliberately low — length only catches near-empty sections, while
# bare denials are caught by the regex.
_MIN_SUBSTANTIVE_CHARS = 15


def _add(
    findings: list[Finding],
    code: str,
    obj: ResearchObject,
    message: str,
) -> None:
    findings.append(Finding("error", code, obj.path, message))


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _is_boilerplate(section: str) -> bool:
    stripped = section.strip()
    if not stripped:
        return True
    if len(stripped) < _MIN_SUBSTANTIVE_CHARS:
        return True
    return bool(_BOILERPLATE_RE.match(stripped))


def validate_red_team_enforcement(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if obj.object_type != "analysis_run":
        return
    if obj.metadata.get("status") != "completed":
        return
    mode = by_id.get(str(obj.metadata.get("mode_id", "")))
    if mode is None or mode.object_type != "analysis_mode":
        return
    if mode_slug(mode.object_id) != "red-team":
        return

    counter = _section(obj.body, "Counter-evidence") or _section(
        obj.body, "Contradicting evidence"
    )
    if _is_boilerplate(counter):
        _add(
            findings,
            "RT001",
            obj,
            "Red Team run counter-evidence is boilerplate or empty",
        )
    alternatives = _section(obj.body, "Alternative explanations")
    if _is_boilerplate(alternatives):
        _add(
            findings,
            "RT002",
            obj,
            "Red Team run alternative explanations is boilerplate or empty",
        )
