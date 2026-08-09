"""E-012 scenario workflow (Phase 5, WP-510).

Phase 4's scenario mode (MOD-ANL-scenario-v2) produces Analysis Runs whose body
carries a full three-scenario contract: Drivers and probabilities, Downside /
Base / Upside scenarios, Sensitivity and catalysts, Falsification conditions
(Phase 5 §5). This module extracts that structure deterministically so a
scenario run can back a ValuationSnapshot's ``scenario_set``, validates its
completeness, and renders a fillable worksheet template for a standalone
scenario analysis.

情景结果不能验证输入假设 — validation checks the *structure* (three scenarios,
sensitivity, falsification), never the correctness of the inputs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.services.validation import validate_repository

SCENARIO_SECTIONS = (
    "Drivers and probabilities",
    "Downside scenario",
    "Base scenario",
    "Upside scenario",
    "Sensitivity and catalysts",
    "Falsification conditions",
)

_SECTION_RE = re.compile(r"(?m)^## (.+)$")


def _extract_section(body: str, title: str) -> str:
    matches = list(_SECTION_RE.finditer(body))
    for i, match in enumerate(matches):
        if match.group(1).strip() != title:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        return body[match.end() : end].strip()
    return ""


def extract_scenario_sections(run: ResearchObject) -> dict[str, str]:
    """Extract the three-scenario contract from a scenario-mode run body.

    Returns ``{section_title: section_text}`` for the Phase 5 §5 sections.
    Missing sections are returned as empty strings — the caller decides whether
    that is a validation failure.
    """
    return {title: _extract_section(run.body, title) for title in SCENARIO_SECTIONS}


def validate_scenario_set(scenario_set: dict[str, str]) -> list[str]:
    """§5 completeness: three scenarios + sensitivity + falsification present.

    Returns a list of problems (empty = the scenario set is structurally
    complete). Structure only — it never asserts the scenarios are correct.
    """
    problems: list[str] = []
    required = [
        "Drivers and probabilities",
        "Downside scenario",
        "Base scenario",
        "Upside scenario",
        "Sensitivity and catalysts",
        "Falsification conditions",
    ]
    for section in required:
        text = (scenario_set.get(section) or "").strip()
        if len(text) < 20:
            problems.append(f"scenario section {section!r} is missing or too thin")
    return problems


def scenario_set_for_valuation(
    root: Path,
    *,
    run_id: str,
) -> dict[str, Any]:
    """Extract + validate a scenario-mode run for a ValuationSnapshot.

    Returns ``{run_id, mode_id, sections, problems}``; ``problems`` non-empty
    means the run does not satisfy the §5 completeness contract.
    """
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before extracting a scenario set"
        )
    by_id = {obj.object_id: obj for obj in objects}
    run = by_id.get(run_id)
    if run is None or run.object_type != "analysis_run":
        raise ValueError(f"unknown Analysis Run {run_id}")
    mode_id = str(run.metadata.get("mode_id", ""))
    if "scenario" not in mode_id:
        raise ValueError(f"{run_id} is not a scenario-mode run (mode_id={mode_id})")
    sections = extract_scenario_sections(run)
    return {
        "run_id": run_id,
        "mode_id": mode_id,
        "sections": sections,
        "problems": validate_scenario_set(sections),
    }


def render_scenario_template(
    *,
    company_id: str,
    as_of: str,
    question: str = "",
) -> str:
    """Render a fillable three-scenario worksheet template (Phase 5 §5).

    Each scenario records the §5 elements (drivers, probability, mechanism,
    operating/financial/valuation result, catalysts, falsifiers) plus a
    two-variable sensitivity matrix. Filled-in by a researcher, never by the
    system.
    """
    question_line = question or "TODO: state the central question being scenario-ed."
    scenario_block = (
        "## {name} scenario\n\n"
        "- 时间线 / time horizon: \n"
        "- 起点状态 / starting state: \n"
        "- 关键驱动 (3-5) / key drivers: \n"
        "- 来源或明确 Judgment / source or judgment: \n"
        "- 传导机制 / transmission mechanism: \n"
        "- 经营结果 / operating result: \n"
        "- 财务结果 / financial result: \n"
        "- 估值含义 / valuation implication: \n"
        "- 概率 / probability (若使用): \n"
        "- 催化剂 / catalysts: \n"
        "- 证伪条件 / falsifiers: \n"
        "- 对冲因素 / countervailing factors: \n"
    )
    downside = scenario_block.format(name="Downside")
    base = scenario_block.format(name="Base")
    upside = scenario_block.format(name="Upside")
    return f"""# Scenario Worksheet — {company_id}

> 填空模板：三情景 + 两变量敏感性。情景结果不能验证输入假设。

**As of**: {as_of}
**Question**: {question_line}

{downside}
{base}
{upside}
## Two-variable sensitivity matrix

| 变量 1 \\ 变量 2 | - | 0 | + |
|---|---|---|---|
| + | | | |
| 0 | | | |
| - | | | |

- 变量 1 (驱动):
- 变量 2 (驱动):
- 单元格含义 (结果变量):

## Tail risk (可选)

-

## Cross-scenario falsification

-
"""
