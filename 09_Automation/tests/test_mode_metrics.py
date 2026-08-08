"""WP-420 (D-018): mode metrics tests.

Pure service over synthetic mode + run objects. Verifies the three per-mode
signals: edit (output diversity), agreement (signal consistency on shared
evidence), and evidence omission (coverage gap vs other modes).
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    from research_os.domain.models import ResearchObject
    from research_os.services.mode_metrics import mode_metrics, render_mode_metrics
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-420 tests") from exc

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
            "applicable_scopes": ["sector"],
            "required_input_types": [],
            "optional_input_types": [],
            "required_questions": [],
            "required_output_sections": [],
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


def _run(
    *,
    object_id: str,
    mode_id: str,
    inputs: list[str],
    body: str,
    status: str = "completed",
    review_status: str = "reviewed",
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
            "status": status,
            "review_status": review_status,
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


_POSITIVE = """\
## Facts used
EVT-A

## Inferences
议价权上升，利润池迁移。

## Judgments
改善确定，正面。

## Contradicting evidence
无显著反证。

## Alternative explanations
需求或放缓。

## Unknowns
产能爬坡。

## Indicators
资本开支。

## Mode-specific output
o。

## Limitations
l。
"""

_NEGATIVE = """\
## Facts used
EVT-A

## Inferences
需求下滑，供给过剩压力上升。

## Judgments
恶化风险，负面。

## Contradicting evidence
无显著反证。

## Alternative explanations
供给或收缩。

## Unknowns
库存。

## Indicators
价格。

## Mode-specific output
o。

## Limitations
l。
"""

_DIFFERENT = """\
## Facts used
EVT-Z

## Inferences
监管收紧，出口管制扩大，先进制程设备交付周期延长。

## Judgments
政策不确定性上升。

## Contradicting evidence
无显著反证。

## Alternative explanations
管制或放松。

## Unknowns
许可证审批节奏。

## Indicators
联邦公报。

## Mode-specific output
o。

## Limitations
l。
"""


class ModeMetricsTests(unittest.TestCase):
    def test_edit_distance_between_identical_and_different_bodies(self) -> None:
        objects = [
            _mode(slug="value-chain"),
            _event("EVT-A"),
            _event("EVT-Z"),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
            ),
            _run(
                object_id="ANL-2",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,  # identical body → distance 0
            ),
            _run(
                object_id="ANL-3",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-Z"],
                body=_DIFFERENT,
            ),
        ]
        metrics = mode_metrics(objects)
        stats = metrics["modes"]["value-chain"]
        self.assertEqual(3, stats["run_count"])
        self.assertEqual(3, stats["pairs"])
        # identical pair pulls the mean below a fully-different baseline
        self.assertLess(stats["edit_distance"], 1.0)
        self.assertGreater(stats["edit_distance"], 0.0)

    def test_agreement_on_shared_evidence(self) -> None:
        objects = [
            _mode(slug="supply-demand"),
            _event("EVT-A"),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-supply-demand-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
            ),
            _run(
                object_id="ANL-2",
                mode_id="MOD-ANL-supply-demand-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
            ),
        ]
        stats = mode_metrics(objects)["modes"]["supply-demand"]
        self.assertEqual(1, stats["agreement_pairs"])
        self.assertEqual(1.0, stats["agreement"])

    def test_agreement_zero_on_opposing_signals(self) -> None:
        objects = [
            _mode(slug="supply-demand"),
            _event("EVT-A"),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-supply-demand-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
            ),
            _run(
                object_id="ANL-2",
                mode_id="MOD-ANL-supply-demand-v1",
                inputs=["EVT-A"],
                body=_NEGATIVE,
            ),
        ]
        stats = mode_metrics(objects)["modes"]["supply-demand"]
        self.assertEqual(1, stats["agreement_pairs"])
        self.assertEqual(0.0, stats["agreement"])

    def test_evidence_omission_is_cross_mode_gap(self) -> None:
        objects = [
            _mode(slug="value-chain"),
            _mode(slug="supply-demand"),
            _event("EVT-A"),
            _event("EVT-B"),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
            ),
            _run(
                object_id="ANL-2",
                mode_id="MOD-ANL-supply-demand-v1",
                inputs=["EVT-B"],
                body=_POSITIVE,
            ),
        ]
        metrics = mode_metrics(objects)
        vc = metrics["modes"]["value-chain"]
        sd = metrics["modes"]["supply-demand"]
        self.assertEqual(["EVT-B"], vc["evidence_omitted_ids"])
        self.assertEqual(["EVT-A"], sd["evidence_omitted_ids"])
        self.assertEqual(1, vc["evidence_omitted"])

    def test_non_completed_runs_excluded(self) -> None:
        objects = [
            _mode(slug="value-chain"),
            _event("EVT-A"),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
            ),
            _run(
                object_id="ANL-2",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
                status="failed",
            ),
        ]
        stats = mode_metrics(objects)["modes"]["value-chain"]
        self.assertEqual(1, stats["run_count"])
        self.assertEqual(0, stats["pairs"])

    def test_render_mode_metrics(self) -> None:
        objects = [
            _mode(slug="value-chain"),
            _event("EVT-A"),
            _run(
                object_id="ANL-1",
                mode_id="MOD-ANL-value-chain-v1",
                inputs=["EVT-A"],
                body=_POSITIVE,
            ),
        ]
        text = render_mode_metrics(mode_metrics(objects))
        self.assertIn("Mode metrics", text)
        self.assertIn("value-chain", text)
        self.assertIn("edit=", text)


if __name__ == "__main__":
    unittest.main()
