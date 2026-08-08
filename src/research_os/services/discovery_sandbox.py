"""D-013 discovery sandbox (RCP-v03-007, Phase 4 §4.9).

Open Discovery is a boundary, not a free-for-all: it only produces candidate
Hypotheses and must never assert authoritative research conclusions. A completed
open-discovery run must be hypothesis-candidate-shaped and must not smuggle in a
Thesis/Recommendation:

- ``OD001`` the run body has no ``Hypothesis proposal`` section — without a
  candidate the sandbox produced nothing;
- ``OD002`` the run body asserts an authoritative conclusion (a
  ``Recommendation``/``Thesis``/``Investment implication`` section, or explicit
  buy/sell phrasing) — sandbox leakage.

``extract_hypotheses`` returns the candidate proposals from an open-discovery
run as a plain list (never authoritative; a human investigates or rejects them).

Wired into ``validate_repository`` and the run transaction (D-009) so
open-discovery output is confined to the sandbox both at creation and later.
"""

from __future__ import annotations

import re

from research_os.domain.models import Finding, ResearchObject
from research_os.services.analysis_registry import mode_slug

# Sections/lemmas that assert an authoritative conclusion — sandbox leakage.
_AUTHORITATIVE_RE = re.compile(
    r"(?:^|\n)##\s*(?:Recommendation|Thesis|Investment implication|"
    r"Investment implications|Buy rating|Sell rating)\s*\n"
    r"|(?:建议买入|建议卖出|强烈推荐买入|强烈推荐卖出|recommend\s+(?:buy|sell|hold)|"
    r"strong\s+(?:buy|sell))",
    re.IGNORECASE,
)
_HYPOTHESIS_SECTION = "Hypothesis proposal"


def _add(
    findings: list[Finding],
    code: str,
    obj: ResearchObject,
    message: str,
) -> None:
    findings.append(Finding("error", code, obj.path, message))


def _open_discovery_run(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
) -> ResearchObject | None:
    if obj.object_type != "analysis_run":
        return None
    if obj.metadata.get("status") != "completed":
        return None
    mode = by_id.get(str(obj.metadata.get("mode_id", "")))
    if mode is None or mode.object_type != "analysis_mode":
        return None
    if mode_slug(mode.object_id) != "open-discovery":
        return None
    return mode


def validate_discovery_sandbox(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if _open_discovery_run(obj, by_id) is None:
        return
    headings = set(re.findall(r"^##\s+(.+?)\s*$", obj.body, flags=re.MULTILINE))
    if _HYPOTHESIS_SECTION not in headings:
        _add(
            findings,
            "OD001",
            obj,
            "Open Discovery run has no Hypothesis proposal section",
        )
    if _AUTHORITATIVE_RE.search(obj.body):
        _add(
            findings,
            "OD002",
            obj,
            "Open Discovery run asserts an authoritative conclusion "
            "(Thesis/Recommendation) — sandbox leakage",
        )


def extract_hypotheses(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
) -> list[str]:
    """The candidate hypotheses of an open-discovery run (sandbox output).

    Each block under ``Hypothesis proposal`` is a candidate; they are NOT
    authoritative and a human decides whether to investigate or reject them
    (Phase 4 §4.9). Returns [] for non-open-discovery or non-completed runs.
    """
    if _open_discovery_run(obj, by_id) is None:
        return []
    section = ""
    for match in re.finditer(
        r"(?ms)^## (.*?)\s*\n(.*?)(?=^## |\Z)", obj.body
    ):
        if match.group(1).strip() == _HYPOTHESIS_SECTION:
            section = match.group(2)
            break
    blocks = [block.strip() for block in section.split("\n\n") if block.strip()]
    return [block for block in blocks if not block.startswith("##")]
