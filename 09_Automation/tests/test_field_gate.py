"""WP-430 (D-019): field-gate review packet tests.

Pure service over synthetic mode + run objects: builds per-run D-017
scorecards, per-case D-011 comparison and the §11 human rubric table; reports
missing / mode-mismatched runs instead of silently coercing.
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    from research_os.domain.models import ResearchObject
    from research_os.services.field_gate import (
        field_gate_packet,
        render_field_gate_packet,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-430 tests") from exc

ROOT = Path(__file__).resolve().parents[2]


def _mode(*, slug: str) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"02_Knowledge/Modes/MOD-ANL-{slug}-v1.md",
        metadata={
            "id": f"MOD-ANL-{slug}-v1",
            "type": "analysis_mode",
            "title": slug,
            "name": slug,
            "purpose": "p",
            "applicable_scopes": ["event"],
            "required_input_types": ["event"],
            "optional_input_types": [],
            "required_questions": ["产能与供给弹性如何变化？", "库存与需求匹配吗？"],
            "required_output_sections": ["Supply-demand balance"],
            "assumption_policy": "a",
            "evidence_policy": "e",
            "counterevidence_policy": "c",
            "time_horizons": ["quarter"],
            "prohibited_conclusions": [],
            "status": "active",
            "review_status": "reviewed",
            "valid_from": "2026-08-08",
        },
        body="",
    )


def _run(
    *, object_id: str, mode_id: str, inputs: list[str], body: str
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"05_Research/Analysis/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "analysis_run",
            "mode_id": mode_id,
            "as_of": "2026-08-09",
            "input_source_ids": [],
            "input_event_ids": inputs,
            "input_impact_ids": [],
            "input_thesis_ids": [],
            "status": "completed",
            "review_status": "pending",
        },
        body=body,
    )


def _event(object_id: str) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"04_Evidence/Events/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "event",
            "title": object_id,
            "review_status": "reviewed",
        },
        body="",
    )


_BODY = """\
## Facts used
EVT-A

## Inferences
产能供给弹性变化，库存与需求匹配。

## Judgments
产能约束紧张。

## Contradicting evidence
输入事件未提供明显反证；若二供放量则判断需下调。

## Alternative explanations
需求端增速可能弱于供给约束假设。

## Unknowns
产能爬坡速度。

## Indicators
资本开支指引。

## Mode-specific output
o。

## Supply-demand balance
紧平衡。

## Limitations
推断性分析。
"""


def _objects() -> list[ResearchObject]:
    return [
        _mode(slug="value-chain"),
        _mode(slug="supply-demand"),
        _event("EVT-A"),
        _run(
            object_id="ANL-1",
            mode_id="MOD-ANL-value-chain-v1",
            inputs=["EVT-A"],
            body=_BODY,
        ),
        _run(
            object_id="ANL-2",
            mode_id="MOD-ANL-supply-demand-v1",
            inputs=["EVT-A"],
            body=_BODY,
        ),
    ]


class FieldGatePacketTests(unittest.TestCase):
    def test_packet_counts_and_scorecards(self) -> None:
        objects = _objects()
        matrix = {
            "case-x": {
                "value-chain": "ANL-1",
                "supply-demand": "ANL-2",
            }
        }
        packet = field_gate_packet(objects, matrix)
        self.assertEqual(2, packet["runs"])
        self.assertEqual(2, packet["gate_pass"])
        self.assertEqual(1.0, packet["overall"])
        self.assertEqual([], packet["mismatches"])
        scorecards = packet["cases"]["case-x"]["scorecards"]
        self.assertEqual("ANL-1", scorecards["value-chain"].run_id)
        self.assertEqual("ANL-2", scorecards["supply-demand"].run_id)

    def test_packet_reports_missing_and_mismatched_runs(self) -> None:
        objects = _objects()
        matrix = {
            "case-x": {
                "value-chain": "ANL-1",
                "supply-demand": "ANL-missing",  # does not exist
                "scenario": "ANL-2",  # exists but is supply-demand
            }
        }
        packet = field_gate_packet(objects, matrix)
        self.assertEqual(1, packet["runs"])  # only ANL-1 resolves correctly
        self.assertEqual(2, len(packet["mismatches"]))

    def test_render_includes_cases_and_human_rubric(self) -> None:
        objects = _objects()
        matrix = {"case-x": {"value-chain": "ANL-1", "supply-demand": "ANL-2"}}
        rendered = render_field_gate_packet(objects, matrix)
        self.assertIn("D-019 Field Gate", rendered)
        self.assertIn("case-x", rendered)
        self.assertIn("人工评分表", rendered)
        self.assertIn("阈值（§11）", rendered)
        self.assertIn("不使用多数投票", rendered)


if __name__ == "__main__":
    unittest.main()
