"""WP-412 (D-016): promote insight workflow tests.

``prepare_thesis_proposal`` is a pure service: ``validate_repository`` is patched
so the real repository is untouched and synthetic run objects are injected;
writes (apply) go to a temp dir. A proposal is a pending document — the service
must never create a ``THS-*`` object (RCP-v03-007 points 3/6).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from research_os.domain.models import ResearchObject
    from research_os.services.insight_proposal import (
        apply_thesis_proposal,
        prepare_thesis_proposal,
        propose_thesis,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-412 tests") from exc

ROOT = Path(__file__).resolve().parents[2]


def _propose(
    root: Path = ROOT, *, run_id: str = "ANL-20260808-001"
) -> tuple[Path, str]:
    return prepare_thesis_proposal(root, run_id=run_id, created_at="2026-08-08")


def _mode(*, slug: str = "value-chain") -> ResearchObject:
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
            "required_questions": ["q"],
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
    object_id: str = "ANL-20260808-001",
    mode_id: str = "MOD-ANL-value-chain-v1",
    status: str = "completed",
    review_status: str = "reviewed",
    inputs: list[str] | None = None,
    body: str | None = None,
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"05_Research/Analysis/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "analysis_run",
            "mode_id": mode_id,
            "as_of": "2026-08-08",
            "input_source_ids": [],
            "input_event_ids": inputs or [],
            "input_impact_ids": [],
            "input_thesis_ids": [],
            "input_snapshot_hash": "a" * 64,
            "status": status,
            "review_status": review_status,
        },
        body=body or _VALUE_CHAIN_BODY,
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


_VALUE_CHAIN_BODY = """\
## Facts used
EVT-A

## Inferences
议价权向稀缺产能方转移。

## Judgments
先进制程与 HBM 存储环节的产能瓶颈维持，利润池向瓶颈迁移。

## Contradicting evidence
输入事件未提供明显反证。

## Alternative explanations
需求端增速可能弱于供给约束假设。

## Unknowns
产能爬坡速度与二供进展。

## Indicators
资本开支指引。

## Mode-specific output
算力价值链全景图。

## Limitations
推断性分析。
"""

_RED_TEAM_BODY = """\
## Facts used
EVT-A

## Counter-evidence
历史表明新产能投产快于指引，且二供已在客户端验证，议价权判断可能被证伪。

## Alternative explanations
共同上游约束导致所有环节同步承压。

## Inferences
待检验。

## Judgments
存在证伪风险。

## Contradicting evidence
无。

## Unknowns
x。

## Indicators
y。

## Mode-specific output
红队报告。

## Limitations
l。
"""

_DISCOVERY_BODY = """\
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
COM-tsmc, COM-nvidia。

## Inferences
x。

## Judgments
y。

## Contradicting evidence
无。

## Alternative explanations
需求或放缓。

## Unknowns
u。

## Indicators
i。

## Mode-specific output
o。

## Limitations
候选假设，未权威化。
"""


def _patch_repo(objects: list[ResearchObject]):
    return mock.patch(
        "research_os.services.insight_proposal.validate_repository",
        return_value=(objects, []),
    )


class ThesisProposalGateTests(unittest.TestCase):
    def test_reviewed_completed_run_prepares_proposal(self) -> None:
        objects = [_mode(), _event(), _run(inputs=["EVT-A"])]
        with _patch_repo(objects):
            relative, content = prepare_thesis_proposal(
                ROOT, run_id="ANL-20260808-001", created_at="2026-08-08"
            )
        self.assertTrue(
            str(relative).startswith(
                "05_Research/Analysis_Proposals/Thesis_Proposal_ANL-20260808-001.md"
            )
        )
        self.assertIn("## Proposed Thesis", content)
        self.assertIn("## Evidence used", content)
        self.assertIn("EVT-A", content)
        self.assertIn("这是 Proposal，不是权威 Thesis", content)
        self.assertNotIn("type: analysis_run", content)

    def test_rejected_run_refused(self) -> None:
        objects = [_mode(), _event(), _run(review_status="rejected")]
        with _patch_repo(objects), self.assertRaises(ValueError) as ctx:
            _propose()
        self.assertIn("only reviewed runs", str(ctx.exception))

    def test_pending_run_refused(self) -> None:
        objects = [_mode(), _event(), _run(review_status="pending")]
        with _patch_repo(objects), self.assertRaises(ValueError) as ctx:
            _propose()
        self.assertIn("only reviewed runs", str(ctx.exception))

    def test_non_completed_run_refused(self) -> None:
        objects = [_mode(), _event(), _run(status="failed")]
        with _patch_repo(objects), self.assertRaises(ValueError) as ctx:
            _propose()
        self.assertIn("not completed", str(ctx.exception))

    def test_unknown_run_refused(self) -> None:
        objects = [_mode(), _event()]
        with _patch_repo(objects), self.assertRaises(ValueError) as ctx:
            _propose(run_id="ANL-missing")
        self.assertIn("unknown analysis run", str(ctx.exception))

    def test_unknown_mode_refused(self) -> None:
        objects = [_event(), _run(mode_id="MOD-ANL-missing-v1")]
        with _patch_repo(objects), self.assertRaises(ValueError) as ctx:
            _propose()
        self.assertIn("unknown mode", str(ctx.exception))

    def test_never_writes_a_thesis_object(self) -> None:
        objects = [_mode(), _event(), _run(inputs=["EVT-A"])]
        with _patch_repo(objects):
            _, content = prepare_thesis_proposal(
                ROOT, run_id="ANL-20260808-001", created_at="2026-08-08"
            )
        frontmatter = content.split("---", 2)[1]
        self.assertNotIn("THS-", frontmatter)
        self.assertNotIn("type: thesis\n", frontmatter)


class ThesisProposalEnforcementTests(unittest.TestCase):
    def test_red_team_boilerplate_refused(self) -> None:
        boilerplate = _RED_TEAM_BODY.replace(
            "## Counter-evidence\n"
            "历史表明新产能投产快于指引，且二供已在客户端验证，议价权判断可能被证伪。\n",
            "## Counter-evidence\nNone found.\n",
        ).replace(
            "## Alternative explanations\n共同上游约束导致所有环节同步承压。\n",
            "## Alternative explanations\n无。\n",
        )
        run = _run(
            mode_id="MOD-ANL-red-team-v1",
            body=boilerplate,
        )
        objects = [_mode(slug="red-team"), _event(), run]
        with _patch_repo(objects), self.assertRaises(ValueError) as ctx:
            _propose()
        self.assertIn("RT001", str(ctx.exception))
        self.assertIn("RT002", str(ctx.exception))

    def test_red_team_substantive_prepares_proposal(self) -> None:
        run = _run(mode_id="MOD-ANL-red-team-v1", body=_RED_TEAM_BODY)
        objects = [_mode(slug="red-team"), _event(), run]
        with _patch_repo(objects):
            _, content = prepare_thesis_proposal(
                ROOT, run_id="ANL-20260808-001", created_at="2026-08-08"
            )
        self.assertIn("## Proposed Thesis", content)

    def test_open_discovery_renders_hypotheses_not_thesis(self) -> None:
        run = _run(
            mode_id="MOD-ANL-open-discovery-v1",
            body=_DISCOVERY_BODY,
        )
        objects = [_mode(slug="open-discovery"), _event(), run]
        with _patch_repo(objects):
            _, content = prepare_thesis_proposal(
                ROOT, run_id="ANL-20260808-001", created_at="2026-08-08"
            )
        self.assertIn("## Hypothesis candidates", content)
        self.assertIn("H1: 存储环节的议价权转移快于市场预期。", content)
        self.assertNotIn("## Proposed Thesis", content)
        self.assertIn("候选 Hypothesis", content)


class ThesisProposalWriteTests(unittest.TestCase):
    def test_dry_run_writes_nothing(self) -> None:
        objects = [_mode(), _event(), _run(inputs=["EVT-A"])]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch_repo(objects):
                output = propose_thesis(
                    root, run_id="ANL-20260808-001", created_at="2026-08-08"
                )
            self.assertIn("DRY-RUN: no files changed", output)
            self.assertFalse((root / "05_Research").exists())

    def test_apply_writes_atomically_and_refuses_overwrite(self) -> None:
        objects = [_mode(), _event(), _run(inputs=["EVT-A"])]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch_repo(objects):
                relative, content = prepare_thesis_proposal(
                    root, run_id="ANL-20260808-001", created_at="2026-08-08"
                )
                path = apply_thesis_proposal(root, relative, content)
            self.assertTrue(path.exists())
            self.assertEqual(content, path.read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                apply_thesis_proposal(root, relative, content)

    def test_apply_output_reports_created_path(self) -> None:
        objects = [_mode(), _event(), _run(inputs=["EVT-A"])]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch_repo(objects):
                output = propose_thesis(
                    root,
                    run_id="ANL-20260808-001",
                    created_at="2026-08-08",
                    apply=True,
                )
            self.assertIn("CREATED: 05_Research/Analysis_Proposals/", output)


if __name__ == "__main__":
    unittest.main()
