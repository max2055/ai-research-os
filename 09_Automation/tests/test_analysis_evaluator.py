"""WP-420 (D-017): Analysis Run evaluator tests.

Pure service over synthetic mode + run objects. The scorecard must be
deterministic and honest: well-formed runs pass the §11 gate, and each
dimension (citation / outside_facts / sections / questions / counterevidence /
placeholders) is independently falsifiable.
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    from research_os.domain.models import ResearchObject
    from research_os.services.analysis_evaluator import (
        evaluate_run,
        evaluator_metrics,
        render_evaluation_packet,
        render_scorecard,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-420 tests") from exc

ROOT = Path(__file__).resolve().parents[2]

_QUESTIONS = [
    "哪个环节控制稀缺资源、入口、标准或客户关系？",
    "瓶颈和利润池正在向哪里移动？",
    "谁获得或失去议价权？",
    "传导路径与时间滞后是什么？",
    "哪个环节增长但无法保留利润？",
]


def _mode() -> ResearchObject:
    return ResearchObject(
        path=ROOT / "02_Knowledge/Modes/MOD-ANL-value-chain-v1.md",
        metadata={
            "id": "MOD-ANL-value-chain-v1",
            "type": "analysis_mode",
            "title": "value-chain",
            "name": "价值链分析",
            "purpose": "p",
            "applicable_scopes": ["sector"],
            "required_input_types": ["event"],
            "optional_input_types": [],
            "required_questions": _QUESTIONS,
            "required_output_sections": [
                "Current chain",
                "Changed chain",
                "Beneficiaries and losers",
                "Mechanism",
                "Falsification indicators",
            ],
            "assumption_policy": "a",
            "evidence_policy": "e",
            "counterevidence_policy": "c",
            "time_horizons": ["year"],
            "prohibited_conclusions": [],
            "status": "active",
            "review_status": "reviewed",
            "valid_from": "2026-08-08",
        },
        body="",
    )


def _event(object_id: str = "EVT-A") -> ResearchObject:
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


def _run(body: str, *, inputs: list[str] | None = None) -> ResearchObject:
    return ResearchObject(
        path=ROOT / "05_Research/Analysis/ANL-20260808-001.md",
        metadata={
            "id": "ANL-20260808-001",
            "type": "analysis_run",
            "mode_id": "MOD-ANL-value-chain-v1",
            "as_of": "2026-08-08",
            "input_source_ids": [],
            "input_event_ids": inputs or ["EVT-A"],
            "input_impact_ids": [],
            "input_thesis_ids": [],
            "status": "completed",
            "review_status": "reviewed",
        },
        body=body,
    )


_VALID_BODY = """\
## Facts used
EVT-A

## Inferences
议价权向稀缺产能方转移，利润池向瓶颈环节迁移。传导路径：稀缺产能→先进封装→HBM，时间滞后约两季度。

## Judgments
先进制程与 HBM 存储环节的产能瓶颈维持，环节控制稀缺资源与客户关系。

## Contradicting evidence
输入事件未提供明显反证；若二供放量则议价权判断需下调。

## Alternative explanations
需求端增速可能弱于供给约束假设。

## Unknowns
产能爬坡速度与二供进展。

## Indicators
资本开支指引。

## Mode-specific output
算力价值链全景图。

## Current chain
当前链：设备→代工→存储→设计→云。

## Changed chain
变化后链：HBM 与先进制程地位上升。

## Beneficiaries and losers
受益：先进制程代工与 HBM 存储。

## Mechanism
稀缺产能→议价权→利润池迁移。

## Falsification indicators
新增产能投产快于预期。

## Limitations
推断性分析。
"""


class EvaluatorDimensionTests(unittest.TestCase):
    def _evaluate(self, body: str, *, inputs: list[str] | None = None):
        return evaluate_run(
            [_mode(), _event(), _run(body, inputs=inputs)],
            "ANL-20260808-001",
        )

    def test_well_formed_run_passes_all_dimensions(self) -> None:
        card = self._evaluate(_VALID_BODY)
        self.assertTrue(card.gate_pass, render_scorecard(card))
        for key in (
            "citation",
            "outside_facts",
            "sections",
            "counterevidence",
            "placeholders",
        ):
            self.assertEqual(1.0, card.dimension(key).score, key)
        self.assertGreaterEqual(card.dimension("questions").score, 0.9)

    def test_unresolved_citation_lowers_score(self) -> None:
        # EVT-20260101-999 is a valid EVT id shape but does not exist
        body = _VALID_BODY.replace(
            "## Facts used\nEVT-A\n", "## Facts used\nEVT-20260101-999\n"
        )
        card = self._evaluate(body, inputs=["EVT-A"])
        self.assertLess(card.dimension("citation").score, 1.0)
        self.assertIn("EVT-20260101-999", card.dimension("citation").detail)
        self.assertFalse(card.gate_pass)

    def test_undeclared_evidence_fails_outside_facts(self) -> None:
        # run cites EVT-B (which exists) but it is NOT a declared input
        objects = [_mode(), _event("EVT-A"), _event("EVT-B")]
        body = _VALID_BODY.replace(
            "## Facts used\nEVT-A\n", "## Facts used\nEVT-B\n"
        )
        run = _run(body, inputs=["EVT-A"])
        card = evaluate_run(objects + [run], "ANL-20260808-001")
        self.assertEqual(0.0, card.dimension("outside_facts").score)
        self.assertFalse(card.gate_pass)

    def test_missing_required_section_lowers_sections(self) -> None:
        body = _VALID_BODY.replace(
            "## Current chain\n当前链：设备→代工→存储→设计→云。\n", ""
        )
        card = self._evaluate(body)
        self.assertLess(card.dimension("sections").score, 1.0)
        self.assertFalse(card.gate_pass)

    def test_placeholder_token_fails(self) -> None:
        body = _VALID_BODY.replace(
            "## Limitations\n推断性分析。\n", "## Limitations\nTODO：补充分析。\n"
        )
        card = self._evaluate(body)
        self.assertEqual(0.0, card.dimension("placeholders").score)

    def test_boilerplate_counter_evidence_fails(self) -> None:
        body = _VALID_BODY.replace(
            "## Contradicting evidence\n"
            "输入事件未提供明显反证；若二供放量则议价权判断需下调。\n",
            "## Contradicting evidence\n无。\n",
        )
        card = self._evaluate(body)
        self.assertEqual(0.0, card.dimension("counterevidence").score)

    def test_unaddressed_questions_lower_coverage(self) -> None:
        body = _VALID_BODY.replace(
            "议价权向稀缺产能方转移，利润池向瓶颈环节迁移。传导路径：稀缺产能→先进封装→HBM，时间滞后约两季度。\n",
            "议价权向稀缺产能方转移。\n",
        )
        card = self._evaluate(body)
        self.assertLess(card.dimension("questions").score, 0.9)

    def test_unknown_run_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_run([_mode()], "ANL-missing")


class EvaluatorPacketTests(unittest.TestCase):
    def test_packet_contains_deterministic_and_human_dimensions(self) -> None:
        objects = [_mode(), _event(), _run(_VALID_BODY)]
        packet = render_evaluation_packet(objects, "ANL-20260808-001")
        self.assertIn("D-017 Evaluation Packet", packet)
        self.assertIn("引用可解析", packet)
        self.assertIn("人工评分", packet)
        self.assertIn("诱发过度结论", packet)
        self.assertIn("必填问题覆盖 ≥ 90%", packet)

    def test_scorecard_render(self) -> None:
        card = evaluate_run(
            [_mode(), _event(), _run(_VALID_BODY)], "ANL-20260808-001"
        )
        text = render_scorecard(card)
        self.assertIn("ANL-20260808-001", text)
        self.assertIn("citation", text)

    def test_aggregate_metrics(self) -> None:
        objects = [_mode(), _event(), _run(_VALID_BODY)]
        card = evaluate_run(objects, "ANL-20260808-001")
        metrics = evaluator_metrics([card, card])
        self.assertEqual(2, metrics["runs"])
        self.assertEqual(2, metrics["gate_pass"])
        self.assertEqual(1.0, metrics["citation.mean"])


if __name__ == "__main__":
    unittest.main()
