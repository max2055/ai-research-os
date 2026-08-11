"""WP-411 (D-011~D-013): mode compare / red-team enforcement / discovery
sandbox tests.

D-011 compare is a pure service over synthetic run objects. D-012/D-013 are
validators over completed runs of the red-team / open-discovery modes; the mode
must resolve through ``by_id``.
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    from research_os.domain.models import Finding, ResearchObject
    from research_os.services.analysis_compare import compare_runs
    from research_os.services.discovery_sandbox import (
        extract_hypotheses,
        validate_discovery_sandbox,
    )
    from research_os.services.red_team_enforcement import (
        validate_red_team_enforcement,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-411 tests") from exc

ROOT = Path(__file__).resolve().parents[2]


def _mode(
    *,
    slug: str,
    questions: list[str],
    horizons: list[str],
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"02_Knowledge/Modes/MOD-ANL-{slug}-v1.md",
        metadata={
            "id": f"MOD-ANL-{slug}-v1",
            "type": "analysis_mode",
            "title": slug,
            "name": slug,
            "purpose": "p",
            "applicable_scopes": ["sector", "company", "technology", "event", "thesis"],
            "required_input_types": [],
            "optional_input_types": [],
            "required_questions": questions,
            "required_output_sections": [],
            "assumption_policy": "a",
            "evidence_policy": "e",
            "counterevidence_policy": "c",
            "time_horizons": horizons,
            "prohibited_conclusions": [],
            "status": "active",
            "review_status": "reviewed",
            "valid_from": "2026-08-08",
        },
        body="",
    )


def _event(object_id: str) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"05_Research/Events/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "event",
            "title": object_id,
            "review_status": "reviewed",
        },
        body="",
    )


def _run(
    *,
    object_id: str,
    mode_id: str,
    inputs: list[str],
    body: str,
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"05_Research/Analysis/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "analysis_run",
            "mode_id": mode_id,
            "as_of": "2026-08-08",
            "input_source_ids": [],
            "input_event_ids": inputs,
            "input_impact_ids": [],
            "input_thesis_ids": [],
            "status": "completed",
            "review_status": "pending",
        },
        body=body,
    )


POSITIVE_BODY = """\
## Facts used
EVT-A, EVT-B

## Inferences
链上受益环节议价权上升，支撑利润池向瓶颈迁移。

## Judgments
改善确定，正面。

## Contradicting evidence
无。

## Alternative explanations
需求或放缓。

## Unknowns
产能爬坡。

## Indicators
资本开支。

## Mode-specific output
价值链条。
"""

NEGATIVE_BODY = """\
## Facts used
EVT-A, EVT-C

## Inferences
需求端下滑，供给过剩压力上升。

## Judgments
恶化风险，负面。

## Contradicting evidence
无。

## Alternative explanations
供给或收缩。

## Unknowns
库存。

## Indicators
价格。

## Mode-specific output
供需表。
"""


class ModeCompareTests(unittest.TestCase):
    def test_compare_reports_shared_and_omitted_evidence(self) -> None:
        objects = [
            _mode(
                slug="value-chain",
                questions=["Q1 链上谁受益？"],
                horizons=["quarter", "year"],
            ),
            _mode(
                slug="supply-demand",
                questions=["Q2 供需平衡？"],
                horizons=["quarter", "year"],
            ),
            _event("EVT-A"),
            _event("EVT-B"),
            _event("EVT-C"),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A", "EVT-B"],
                body=POSITIVE_BODY,
            ),
            _run(
                object_id="ANL-2",
                mode_id="MOD-ANL-supply-demand-v1",
                inputs=["EVT-A", "EVT-C"],
                body=NEGATIVE_BODY,
            ),
        ]
        report = compare_runs(objects, ["ANL-1", "ANL-2"])
        self.assertEqual(["ANL-1", "ANL-2"], report.run_ids)
        self.assertEqual(["EVT-A"], report.shared_facts)  # cited by both
        self.assertEqual(["EVT-C"], report.evidence_omitted["ANL-1"])
        self.assertEqual(["EVT-B"], report.evidence_omitted["ANL-2"])
        self.assertEqual(
            ["MOD-ANL-supply-demand-v1", "MOD-ANL-value-chain-v1"], report.modes
        )
        self.assertEqual(["quarter", "year"], report.time_horizons)
        self.assertEqual(["Q1 链上谁受益？", "Q2 供需平衡？"], report.questions)
        # ANL-1 positive vs ANL-2 negative -> flagged for human review
        self.assertEqual(
            [("ANL-1", "positive", "ANL-2", "negative")],
            report.conflicting_signals,
        )

    def test_compare_skips_unknown_or_non_run(self) -> None:
        objects = [
            _mode(slug="value-chain", questions=["q"], horizons=["year"]),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A"],
                body=POSITIVE_BODY,
            ),
            _event("EVT-A"),
        ]
        # unknown run id ignored; run with unresolvable mode ignored
        report = compare_runs(objects, ["ANL-1", "ANL-missing"])
        self.assertEqual(["ANL-1"], report.run_ids)
        empty = compare_runs(objects, [])
        self.assertEqual([], empty.run_ids)


class RedTeamEnforcementTests(unittest.TestCase):
    def _red_team_run(self, body: str) -> ResearchObject:
        return _run(
            object_id="ANL-RT-1",
            mode_id="MOD-ANL-red-team-v1",
            inputs=["EVT-A"],
            body=body,
        )

    def _by_id(self, run: ResearchObject) -> dict[str, ResearchObject]:
        return {
            "MOD-ANL-red-team-v1": _mode(
                slug="red-team", questions=["q"], horizons=["year"]
            ),
            run.object_id: run,
        }

    def test_boilerplate_counter_evidence_rejected(self) -> None:
        run = self._red_team_run(
            POSITIVE_BODY.replace(
                "## Judgments\n改善确定，正面。\n",
                "## Counter-evidence\nNone found.\n## Judgments\n改善确定，正面。\n",
            )
        )
        findings: list[Finding] = []
        validate_red_team_enforcement(run, self._by_id(run), findings)
        self.assertIn("RT001", [f.code for f in findings])
        self.assertIn("RT002", [f.code for f in findings])

    def test_substantive_counter_evidence_passes(self) -> None:
        body = """\
## Facts used
EVT-A

## Counter-evidence
历史表明新产能投产快于指引，且二供已在客户端验证，议价权判断可能被证伪。

## Alternative explanations
共同上游约束导致所有环节同步承压，而非本环节独有问题。

## Unobservable variables
客户私下议价条款不可观测。

## Judgments
存在证伪风险。

## Inferences
待检验。

## Contradicting evidence
无。

## Unknowns
x。

## Indicators
y。

## Mode-specific output
红队报告。
"""
        run = self._red_team_run(body)
        findings: list[Finding] = []
        validate_red_team_enforcement(run, self._by_id(run), findings)
        self.assertEqual([], findings)

    def test_non_red_team_mode_skipped(self) -> None:
        run = _run(
            object_id="ANL-X",
            mode_id="MOD-ANL-value-chain-v1",
            inputs=["EVT-A"],
            body=POSITIVE_BODY,
        )
        findings: list[Finding] = []
        validate_red_team_enforcement(
            run,
            {
                "MOD-ANL-value-chain-v1": _mode(
                    slug="value-chain", questions=["q"], horizons=["year"]
                )
            },
            findings,
        )
        self.assertEqual([], findings)


class DiscoverySandboxTests(unittest.TestCase):
    DISCOVERY_BODY = """\
## Facts used
EVT-A

## Hypothesis proposal

H1: 存储环节的议价权转移快于市场预期。

H2: 先进封装产能是比制程更紧的瓶颈。

## Why surprising
现有叙事聚焦制程，忽略封装。

## Minimum evidence needed
两家以上客户合同或资本开支指引。

## Disconfirming search plan
跟踪二供扩产公告与良率数据。

## Related entities
SEG-compute-silicon, COM-tsmc。

## Spurious-correlation risk
样本期短，可能混淆季节性与结构性。

## Limitations
候选假设，未权威化。
"""

    def _open_run(self, body: str) -> ResearchObject:
        return _run(
            object_id="ANL-OD-1",
            mode_id="MOD-ANL-open-discovery-v1",
            inputs=["EVT-A"],
            body=body,
        )

    def _by_id(self, run: ResearchObject) -> dict[str, ResearchObject]:
        return {
            "MOD-ANL-open-discovery-v1": _mode(
                slug="open-discovery", questions=["q"], horizons=["year"]
            ),
            run.object_id: run,
        }

    def test_candidate_hypothesis_run_passes(self) -> None:
        run = self._open_run(self.DISCOVERY_BODY)
        findings: list[Finding] = []
        validate_discovery_sandbox(run, self._by_id(run), findings)
        self.assertEqual([], findings)

    def test_extract_hypotheses_returns_candidates(self) -> None:
        run = self._open_run(self.DISCOVERY_BODY)
        hypotheses = extract_hypotheses(run, self._by_id(run))
        self.assertEqual(2, len(hypotheses))
        self.assertIn("H1: 存储环节的议价权转移快于市场预期。", hypotheses)

    def test_missing_hypothesis_section(self) -> None:
        body = self.DISCOVERY_BODY.replace(
            "## Hypothesis proposal\n\n"
            "H1: 存储环节的议价权转移快于市场预期。\n\n"
            "H2: 先进封装产能是比制程更紧的瓶颈。\n\n",
            "",
        )
        run = self._open_run(body)
        findings: list[Finding] = []
        validate_discovery_sandbox(run, self._by_id(run), findings)
        self.assertEqual(["OD001"], [f.code for f in findings])

    def test_authoritative_conclusion_leakage(self) -> None:
        body = self.DISCOVERY_BODY + "\n## Recommendation\n建议买入。\n"
        run = self._open_run(body)
        findings: list[Finding] = []
        validate_discovery_sandbox(run, self._by_id(run), findings)
        self.assertEqual(["OD002"], [f.code for f in findings])

    def test_non_discovery_mode_skipped(self) -> None:
        run = _run(
            object_id="ANL-X",
            mode_id="MOD-ANL-value-chain-v1",
            inputs=["EVT-A"],
            body=POSITIVE_BODY,
        )
        findings: list[Finding] = []
        validate_discovery_sandbox(
            run,
            {
                "MOD-ANL-value-chain-v1": _mode(
                    slug="value-chain", questions=["q"], horizons=["year"]
                )
            },
            findings,
        )
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
