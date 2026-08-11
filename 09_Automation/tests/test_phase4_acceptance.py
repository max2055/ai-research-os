"""D-020 Phase 4 acceptance (replay / hash-rebuild) tests.

Phase 4 §10/§12 acceptance: a frozen run must be auditable — its
input_snapshot_hash / prompt_hash / output_hash are reproducible from the
frozen inputs + mode + body, replay creates a NEW run id and never overwrites,
and a failed provider leaves no half-written object.

Most atomicity/hash tests live in test_analysis_runner; this file adds the
D-020-specific guarantees: replay-new-id (re-running a run's frozen inputs
yields a fresh run, old one intact) and hash-rebuild (recompute == stored).
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from research_os.adapters.model import EchoAdapter
    from research_os.domain.models import ResearchObject
    from research_os.services.analysis_runner import (
        RunError,
        apply_run,
        prepare_run,
    )
    from research_os.services.input_resolver import resolve_inputs
    from research_os.services.prompt_renderer import render_prompt
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run D-020 tests") from exc

ROOT = Path(__file__).resolve().parents[2]

_BODY = """\
## Facts used
EVT-A

## Inferences
议价权向稀缺产能方转移。

## Judgments
先进制程与 HBM 存储环节的产能瓶颈维持。

## Contradicting evidence
输入事件未提供明显反证；若二供放量则判断需下调。

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


def _mode() -> ResearchObject:
    return ResearchObject(
        path=ROOT / "02_Knowledge/Modes/MOD-ANL-value-chain-v1.md",
        metadata={
            "id": "MOD-ANL-value-chain-v1",
            "type": "analysis_mode",
            "title": "value-chain",
            "name": "价值链分析",
            "purpose": "p",
            "applicable_scopes": ["event"],
            "required_input_types": ["event"],
            "optional_input_types": [],
            "required_questions": [
                "传导路径与时间滞后是什么？",
                "瓶颈和利润池正在向哪里移动？",
            ],
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


class _ValidBodyAdapter:
    provider = "valid"

    def generate(self, prompt, *, timeout=None, model_id=None, model_parameters=None):
        del prompt, timeout, model_id, model_parameters
        return _BODY


def _patch_repo(objects):
    """Patch validate_repository to mirror the REAL disk scan: after a run is
    applied under root/05_Research/Analysis, subsequent prepare_run sees it
    (so a replay yields a fresh id, exactly like the real repo)."""
    from research_os.repositories.markdown import MarkdownDocument

    def fake(root_path: Path):
        found = list(objects)
        anl = root_path / "05_Research" / "Analysis"
        if anl.exists():
            for path in sorted(anl.glob("ANL-*.md")):
                doc = MarkdownDocument.read(path)
                found.append(
                    ResearchObject(
                        path=path, metadata=dict(doc.metadata), body=doc.body
                    )
                )
        return found, []

    return mock.patch(
        "research_os.services.analysis_runner.validate_repository",
        side_effect=fake,
    )


class ReplayCreatesNewIdTests(unittest.TestCase):
    """Re-running a run's frozen inputs must yield a NEW run id; the old run
    stays byte-identical (§10 replay 创建新 ID, §12 不覆盖历史)."""

    def test_replay_same_inputs_new_id_no_overwrite(self) -> None:
        objects = [_mode(), _event()]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with _patch_repo(objects):
                first = prepare_run(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-A"],
                    as_of="2026-08-09",
                    created_at="2026-08-09",
                    adapter=_ValidBodyAdapter(),
                )
                path_a = apply_run(root, first)
                first_content = path_a.read_text(encoding="utf-8")

                # replay: same frozen inputs -> a fresh, DIFFERENT run id
                second = prepare_run(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-A"],
                    as_of="2026-08-09",
                    created_at="2026-08-09",
                    adapter=_ValidBodyAdapter(),
                )
                self.assertNotEqual(first.run_id, second.run_id)
                path_b = apply_run(root, second)
                self.assertNotEqual(path_a, path_b)
                # old run unchanged; inputs frozen identically
                self.assertEqual(first_content, path_a.read_text(encoding="utf-8"))
                self.assertEqual(first.input_snapshot_hash, second.input_snapshot_hash)

    def test_replay_cannot_overwrite_existing(self) -> None:
        objects = [_mode(), _event()]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with _patch_repo(objects):
                plan = prepare_run(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-A"],
                    as_of="2026-08-09",
                    created_at="2026-08-09",
                    adapter=_ValidBodyAdapter(),
                )
                apply_run(root, plan)
                with self.assertRaises(FileExistsError):
                    apply_run(root, plan)


class HashRebuildTests(unittest.TestCase):
    """A frozen run's hashes are reproducible from its frozen inputs (§10:
    prompt/input/output hash; §12 确定性输入 manifest)."""

    def test_stored_hashes_match_recomputation(self) -> None:
        objects = [_mode(), _event()]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with _patch_repo(objects):
                plan = prepare_run(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-A"],
                    as_of="2026-08-09",
                    created_at="2026-08-09",
                    adapter=_ValidBodyAdapter(),
                )
            # input snapshot hash: re-resolving the same inputs reproduces it
            resolved = resolve_inputs(
                objects,
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-A"],
                as_of="2026-08-09",
            )
            self.assertEqual(plan.input_snapshot_hash, resolved.input_snapshot_hash)
            # prompt hash: re-rendering the same prompt reproduces it
            prompt, prompt_hash = render_prompt(
                _mode(), resolved, as_of="2026-08-09", root=root
            )
            self.assertEqual(plan.prompt_hash, prompt_hash)
            self.assertEqual(
                plan.prompt_hash,
                hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            )
            # output hash: sha256 of the frozen body
            self.assertEqual(
                plan.output_hash,
                hashlib.sha256(plan.body.encode("utf-8")).hexdigest(),
            )

    def test_failed_replay_leaves_no_half_object(self) -> None:
        objects = [_mode(), _event()]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with _patch_repo(objects), self.assertRaises(RunError) as ctx:
                prepare_run(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-A"],
                    as_of="2026-08-09",
                    created_at="2026-08-09",
                    adapter=EchoAdapter(),
                )
            self.assertEqual("output-contract-failed", ctx.exception.error_type)
            self.assertFalse((root / "05_Research").exists())


if __name__ == "__main__":
    unittest.main()
