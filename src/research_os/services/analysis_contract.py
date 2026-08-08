"""D-004 output contract for Analysis Runs (RCP-v03-007, Phase 4 §3/§7).

Every completed Analysis Run (ANL-*) body must satisfy ONE shared contract so
modes stay comparable without inventing incompatible Facts/Inference fields
(Phase 4 §7). The contract is declared in
``00_System/Analysis_Modes/output_contract_schema.json`` and enforced here:

- ``CON001`` a required section is missing;
- ``CON002`` a required section is present but empty;
- ``CON003`` a completed run body contains a placeholder token;
- ``CON004`` the body cites an object id that is not a declared input (or does
  not resolve to a real object) — "no facts outside the run's inputs".

Only a *frozen* run (status ``completed``) is checked; draft/failed runs are
work-in-progress and are covered by the fingerprint rules (RUN002).
"""

from __future__ import annotations

import re

from research_os.domain.models import Finding, ResearchObject
from research_os.domain.policies import ID_PATTERNS

# Shared output contract (Phase 4 §3). Keep in sync with the JSON Schema
# artifact 00_System/Analysis_Modes/output_contract_schema.json.
REQUIRED_SECTIONS = [
    "Facts used",
    "Inferences",
    "Judgments",
    "Contradicting evidence",
    "Alternative explanations",
    "Unknowns",
    "Indicators",
    "Mode-specific output",
    "Limitations",
]

CONTRACT_SCHEMA_PATH = "00_System/Analysis_Modes/output_contract_schema.json"


def _add(
    findings: list[Finding],
    level: str,
    code: str,
    obj: ResearchObject,
    message: str,
) -> None:
    findings.append(Finding(level, code, obj.path, message))


_PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|TBA|TBC|FIXME|PLACEHOLDER|XXX)\b"
    r"|\b(to be (determined|announced|decided|completed))\b",
    re.IGNORECASE,
)

# Evidence-citing id types map 1:1 to a run input field; a citation of one of
# these must be a declared input. Other registered id types are checked for
# existence only (a fabricated id is still a citation failure).
_EVIDENCE_INPUT_FIELDS = {
    "source": "input_source_ids",
    "event": "input_event_ids",
    "impact_assertion": "input_impact_ids",
    "thesis": "input_thesis_ids",
}

_ID_TOKEN_RE = re.compile(r"\b[A-Z]{2,6}(?:-[A-Za-z0-9]+)+")


def validate_run_contract(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if obj.object_type != "analysis_run":
        return
    if obj.metadata.get("status") != "completed":
        return
    body = obj.body
    present = set(re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
    for section in REQUIRED_SECTIONS:
        if section not in present:
            _add(
                findings,
                "error",
                "CON001",
                obj,
                f"missing required output section: {section}",
            )
        elif not _section(body, section):
            _add(
                findings,
                "error",
                "CON002",
                obj,
                f"empty output section: {section}",
            )
    if _PLACEHOLDER_RE.search(body):
        _add(
            findings,
            "error",
            "CON003",
            obj,
            "completed Analysis Run body contains placeholder token(s)",
        )
    _validate_citations(obj, by_id, findings)


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def _validate_citations(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    declared = {
        str(value)
        for field in (
            "input_source_ids",
            "input_event_ids",
            "input_impact_ids",
            "input_thesis_ids",
            "scope_ids",
        )
        for value in obj.metadata.get(field, []) or []
    }
    for token in _ID_TOKEN_RE.findall(obj.body):
        if token == obj.object_id:
            continue
        target = by_id.get(token)
        if target is None:
            if _matches_any_pattern(token):
                _add(
                    findings,
                    "error",
                    "CON004",
                    obj,
                    f"body cites unknown object {token!r}",
                )
            continue
        field = _EVIDENCE_INPUT_FIELDS.get(target.object_type)
        if field is not None and token not in declared:
            _add(
                findings,
                "error",
                "CON004",
                obj,
                f"body cites {token} not declared in {field}",
            )


def _matches_any_pattern(token: str) -> bool:
    return any(pattern.fullmatch(token) for pattern in ID_PATTERNS.values())
