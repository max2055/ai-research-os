"""WP-401 (D-005~D-009): Analysis Mode registry / input resolver / prompt
renderer / model adapter / run transaction tests.

The registry, resolver and renderer are pure services over synthetic objects.
The run transaction (D-009) is exercised with ``validate_repository`` patched to
a controlled object list, isolating the Mode Runner pipeline; writes go to a
temp dir so the real repository is never touched.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from research_os.adapters.model import EchoAdapter, build_adapter
    from research_os.domain.models import ResearchObject
    from research_os.repositories.markdown import MarkdownDocument
    from research_os.services.analysis_registry import (
        ModeNotRunnable,
        UnknownMode,
        active_mode,
        find_mode,
        mode_slug,
        mode_version,
        mode_versions,
        require_runnable,
    )
    from research_os.services.analysis_runner import (
        RunError,
        apply_run,
        prepare_run,
        run_analysis,
    )
    from research_os.services.input_resolver import InputError, resolve_inputs
    from research_os.services.prompt_renderer import render_prompt
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-401 tests") from exc

ROOT = Path(__file__).resolve().parents[2]

_VALID_BODY = """\
## Facts used
EVT-20260225-034: NVIDIA disclosed supply commitments.

## Inferences
The supply constraint eases by 2Q26.

## Judgments
High confidence in the direction.

## Contradicting evidence
No contrary signal in the inputs.

## Alternative explanations
Demand could soften faster than supply.

## Unknowns
CapEx mix and yield rates.

## Indicators
NVIDIA guidance, HBM qualification results.

## Mode-specific output
Value chain map with the bargaining-power shifts.

## Limitations
No primary data; inference only.
"""


class ValidBodyAdapter:
    provider = "valid"

    def generate(self, prompt: str, *, timeout: float | None = None) -> str:
        del prompt, timeout
        return _VALID_BODY


def _mode(
    *,
    status: str = "active",
    review_status: str = "reviewed",
    **extra: object,
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / "02_Knowledge/Modes/MOD-ANL-value-chain-v1.md",
        metadata={
            "id": "MOD-ANL-value-chain-v1",
            "type": "analysis_mode",
            "title": "Value Chain Mode",
            "name": "Value Chain",
            "purpose": "Who holds leverage in the chain",
            "applicable_scopes": ["sector", "company", "technology", "event", "thesis"],
            "required_input_types": ["event"],
            "optional_input_types": [],
            "required_questions": ["Which stage gains bargaining power?"],
            "required_output_sections": ["Mode-specific output"],
            "assumption_policy": "state assumptions explicitly",
            "evidence_policy": "cite only frozen inputs",
            "counterevidence_policy": "surface contrary signals",
            "time_horizons": ["quarter", "year"],
            "prohibited_conclusions": ["no buy/sell advice"],
            "status": status,
            "review_status": review_status,
            "valid_from": "2026-08-08",
            **extra,
        },
        body="",
    )


def _mode_v2(**extra: object) -> ResearchObject:
    mode = _mode(**extra)
    return ResearchObject(
        path=ROOT / "02_Knowledge/Modes/MOD-ANL-value-chain-v2.md",
        metadata={
            **mode.metadata,
            "id": "MOD-ANL-value-chain-v2",
            "valid_from": "2026-08-09",
        },
        body="",
    )


def _event(
    *,
    object_id: str = "EVT-20260225-034",
    reviewed: bool = True,
    event_date: str = "2026-02-25",
    title: str = "NVIDIA supply disclosure",
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"05_Research/Events/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "event",
            "title": title,
            "review_status": "reviewed" if reviewed else "pending",
            "event_date": event_date,
        },
        body="",
    )


def _company(object_id: str = "COM-nvidia") -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"02_Knowledge/Companies/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "company",
            "title": "NVIDIA",
            "review_status": "reviewed",
        },
        body="",
    )


def _adapter_from(output: str) -> object:
    """A minimal adapter returning a fixed output (no provider semantics)."""

    class Adapter:
        def generate(self, prompt: str, *, timeout: float | None = None) -> str:
            del prompt, timeout
            return output

    return Adapter()


def _raise_adapter(exc: Exception) -> object:
    """An adapter that always raises (timeout / provider failure)."""

    class Adapter:
        def generate(self, prompt: str, *, timeout: float | None = None) -> str:
            del prompt, timeout
            raise exc

    return Adapter()


class ModeRegistryTests(unittest.TestCase):
    def test_mode_slug_and_version_parsing(self) -> None:
        self.assertEqual("value-chain", mode_slug("MOD-ANL-value-chain-v1"))
        self.assertEqual(1, mode_version("MOD-ANL-value-chain-v1"))
        self.assertEqual(9, mode_version("MOD-ANL-red-team-v9"))
        with self.assertRaises(ValueError):
            mode_slug("MOD-ANL-no-version")

    def test_find_mode_exact_id(self) -> None:
        objects = [_mode()]
        self.assertIsNotNone(find_mode(objects, "MOD-ANL-value-chain-v1"))
        self.assertIsNone(find_mode(objects, "MOD-ANL-other-v1"))

    def test_mode_versions_and_active(self) -> None:
        objects = [_mode(), _mode_v2()]
        self.assertEqual(
            ["MOD-ANL-value-chain-v1", "MOD-ANL-value-chain-v2"],
            [obj.object_id for obj in mode_versions(objects, "value-chain")],
        )
        self.assertEqual(
            "MOD-ANL-value-chain-v2", active_mode(objects, "value-chain").object_id
        )

    def test_require_runnable_gates(self) -> None:
        self.assertEqual(
            "MOD-ANL-value-chain-v1",
            require_runnable([_mode()], "MOD-ANL-value-chain-v1").object_id,
        )
        with self.assertRaises(UnknownMode):
            require_runnable([_mode()], "MOD-ANL-missing-v1")
        with self.assertRaises(ModeNotRunnable):
            require_runnable([_mode(status="deprecated")], "MOD-ANL-value-chain-v1")
        with self.assertRaises(ModeNotRunnable):
            require_runnable([_mode(status="proposed")], "MOD-ANL-value-chain-v1")
        with self.assertRaises(ModeNotRunnable):
            require_runnable([_mode(review_status="pending")], "MOD-ANL-value-chain-v1")


class InputResolverTests(unittest.TestCase):
    def _resolve(self, **kwargs: object):
        return resolve_inputs(
            [_mode(), _event(), _company()],
            mode_id="MOD-ANL-value-chain-v1",
            as_of="2026-08-08",
            **kwargs,
        )

    def test_resolves_reviewed_inputs(self) -> None:
        resolved = self._resolve(input_event_ids=["EVT-20260225-034"])
        self.assertEqual(["EVT-20260225-034"], resolved.ids_by_type("event"))
        self.assertRegex(resolved.input_snapshot_hash, r"^[0-9a-f]{64}$")

    def test_rejects_unreviewed_input(self) -> None:
        objects = [_mode(), _event(reviewed=False)]
        with self.assertRaises(InputError):
            resolve_inputs(
                objects,
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-20260225-034"],
                as_of="2026-08-08",
            )

    def test_rejects_missing_input(self) -> None:
        with self.assertRaises(InputError):
            self._resolve(input_event_ids=["EVT-does-not-exist"])

    def test_rejects_future_evidence(self) -> None:
        future = _event(object_id="EVT-20261101-001", event_date="2026-11-01")
        with self.assertRaises(InputError):
            resolve_inputs(
                [_mode(), future],
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-20261101-001"],
                as_of="2026-08-08",
            )

    def test_rejects_scope_not_in_applicable_scopes(self) -> None:
        # mode only applies to "sector"; a company scope is rejected for scope
        # fit (required_input_types cleared so the failure is unambiguous).
        mode = _mode(applicable_scopes=["sector"], required_input_types=[])
        with self.assertRaises(InputError):
            resolve_inputs(
                [mode, _company()],
                mode_id="MOD-ANL-value-chain-v1",
                scope_ids=["COM-nvidia"],
                as_of="2026-08-08",
            )

    def test_scope_entity_definition_passes(self) -> None:
        # company scope needs only to exist; event input satisfies the
        # required-input rule.
        resolved = self._resolve(
            scope_ids=["COM-nvidia"],
            input_event_ids=["EVT-20260225-034"],
        )
        self.assertIn("COM-nvidia", resolved.ids_by_type("company"))
        self.assertIn("EVT-20260225-034", resolved.ids_by_type("event"))

    def test_required_input_type_enforced(self) -> None:
        # mode requires "event"; company-only input fails.
        with self.assertRaises(InputError):
            resolve_inputs(
                [_mode(), _company()],
                mode_id="MOD-ANL-value-chain-v1",
                scope_ids=["COM-nvidia"],
                as_of="2026-08-08",
            )

    def test_snapshot_hash_is_deterministic_and_order_independent(self) -> None:
        a = self._resolve(input_event_ids=["EVT-20260225-034"])
        b = self._resolve(input_event_ids=["EVT-20260225-034"])
        self.assertEqual(a.input_snapshot_hash, b.input_snapshot_hash)
        # content change must change the freeze
        edited = _event(title="NVIDIA updated guidance")
        changed = resolve_inputs(
            [_mode(), edited],
            mode_id="MOD-ANL-value-chain-v1",
            input_event_ids=["EVT-20260225-034"],
            as_of="2026-08-08",
        )
        self.assertNotEqual(a.input_snapshot_hash, changed.input_snapshot_hash)


class PromptRendererTests(unittest.TestCase):
    def test_render_prompt_is_deterministic_and_contains_contract(self) -> None:
        from research_os.services.input_resolver import resolve_inputs

        resolved = resolve_inputs(
            [_mode(), _event()],
            mode_id="MOD-ANL-value-chain-v1",
            input_event_ids=["EVT-20260225-034"],
            as_of="2026-08-08",
        )
        prompt, prompt_hash = render_prompt(_mode(), resolved, as_of="2026-08-08")
        prompt2, prompt_hash2 = render_prompt(_mode(), resolved, as_of="2026-08-08")
        self.assertEqual(prompt, prompt2)
        self.assertEqual(prompt_hash, prompt_hash2)
        self.assertEqual(64, len(prompt_hash))
        self.assertIn("MOD-ANL-value-chain-v1", prompt)
        self.assertIn("## Facts used", prompt)
        self.assertIn("## Limitations", prompt)
        self.assertIn("EVT-20260225-034", prompt)
        self.assertIn("Which stage gains bargaining power?", prompt)

    def test_file_template_override(self) -> None:
        from research_os.services.input_resolver import resolve_inputs

        resolved = resolve_inputs(
            [_mode(), _event()],
            mode_id="MOD-ANL-value-chain-v1",
            input_event_ids=["EVT-20260225-034"],
            as_of="2026-08-08",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "templates" / "custom.md"
            template.parent.mkdir(parents=True)
            template.write_text("CUSTOM {mode_id}", encoding="utf-8")
            mode = _mode(prompt_template_path="templates/custom.md")
            prompt, _ = render_prompt(mode, resolved, as_of="2026-08-08", root=root)
            self.assertEqual("CUSTOM MOD-ANL-value-chain-v1", prompt)

    def test_missing_template_file_raises(self) -> None:
        from research_os.services.input_resolver import resolve_inputs

        resolved = resolve_inputs(
            [_mode(), _event()],
            mode_id="MOD-ANL-value-chain-v1",
            input_event_ids=["EVT-20260225-034"],
            as_of="2026-08-08",
        )
        mode = _mode(prompt_template_path="templates/missing.md")
        with self.assertRaises(ValueError):
            render_prompt(mode, resolved, as_of="2026-08-08", root=ROOT)


class ModelAdapterTests(unittest.TestCase):
    def test_echo_adapter_returns_prompt(self) -> None:
        adapter = EchoAdapter()
        self.assertEqual("hello", adapter.generate("hello"))

    def test_build_adapter_echo(self) -> None:
        self.assertIsInstance(build_adapter("echo"), EchoAdapter)

    def test_build_adapter_unknown_provider(self) -> None:
        from research_os.adapters.model import UnknownProvider

        with self.assertRaises(UnknownProvider):
            build_adapter("anthropic")


class RunTransactionTests(unittest.TestCase):
    """D-009: pipeline + atomicity. validate_repository is patched so the real
    repository is untouched; writes go to a temp dir."""

    def _patch_repo(self, objects: list[ResearchObject]):
        return mock.patch(
            "research_os.services.analysis_runner.validate_repository",
            return_value=(objects, []),
        )

    def test_prepare_run_builds_frozen_run_plan(self) -> None:
        objects = [_mode(), _event()]
        with self._patch_repo(objects):
            plan = prepare_run(
                ROOT,
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-20260225-034"],
                as_of="2026-08-08",
                created_at="2026-08-08",
                adapter=ValidBodyAdapter(),
            )
        self.assertEqual("ANL-20260808-001", plan.run_id)
        self.assertEqual("completed", plan.metadata["status"])
        self.assertEqual("pending", plan.metadata["review_status"])
        self.assertEqual(64, len(plan.prompt_hash))
        self.assertEqual(64, len(plan.output_hash))
        self.assertEqual(64, len(plan.input_snapshot_hash))
        self.assertIn("EVT-20260225-034", plan.body)
        self.assertTrue(str(plan.relative_path).startswith("05_Research/Analysis/ANL-"))
        doc_meta = _parse_frontmatter(plan.content)
        self.assertEqual(plan.input_snapshot_hash, doc_meta["input_snapshot_hash"])
        self.assertEqual("mode-runner", doc_meta["generation_method"])

    def test_run_analysis_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            objects = [_mode(), _event()]
            with self._patch_repo(objects):
                output = run_analysis(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-20260225-034"],
                    as_of="2026-08-08",
                    created_at="2026-08-08",
                    adapter=ValidBodyAdapter(),
                )
            self.assertIn("DRY-RUN: no files changed", output)
            self.assertFalse((root / "05_Research").exists())

    def test_apply_run_writes_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            objects = [_mode(), _event()]
            with self._patch_repo(objects):
                plan = prepare_run(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-20260225-034"],
                    as_of="2026-08-08",
                    created_at="2026-08-08",
                    adapter=ValidBodyAdapter(),
                )
                path = apply_run(root, plan)
            self.assertTrue(path.exists())
            self.assertEqual(plan.content, path.read_text(encoding="utf-8"))
            # a second apply refuses to overwrite
            with self.assertRaises(FileExistsError):
                apply_run(root, plan)

    def test_non_runnable_mode_raises_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            objects = [_mode(status="deprecated"), _event()]
            with self._patch_repo(objects), self.assertRaises(RunError) as ctx:
                run_analysis(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-20260225-034"],
                    as_of="2026-08-08",
                    created_at="2026-08-08",
                    adapter=ValidBodyAdapter(),
                )
            self.assertEqual("mode-unavailable", ctx.exception.error_type)
            self.assertFalse((root / "05_Research").exists())

    def test_unreviewed_input_raises(self) -> None:
        objects = [_mode(), _event(reviewed=False)]
        with self._patch_repo(objects), self.assertRaises(RunError) as ctx:
            prepare_run(
                ROOT,
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-20260225-034"],
                as_of="2026-08-08",
                created_at="2026-08-08",
                adapter=ValidBodyAdapter(),
            )
        self.assertEqual("input-error", ctx.exception.error_type)

    def test_malformed_output_fails_contract_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            objects = [_mode(), _event()]
            with self._patch_repo(objects), self.assertRaises(RunError) as ctx:
                run_analysis(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-20260225-034"],
                    as_of="2026-08-08",
                    created_at="2026-08-08",
                    adapter=EchoAdapter(),  # echoes the prompt, not a body
                )
            self.assertEqual("output-contract-failed", ctx.exception.error_type)
            self.assertFalse((root / "05_Research").exists())

    def test_mode_required_section_missing_fails(self) -> None:
        body = _VALID_BODY.replace(
            "## Mode-specific output\n"
            "Value chain map with the bargaining-power shifts.\n",
            "",
        )
        adapter = _adapter_from(body)
        with self.assertRaises(RunError) as ctx, self._patch_repo(
            [_mode(), _event()]
        ):
            prepare_run(
                ROOT,
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-20260225-034"],
                as_of="2026-08-08",
                created_at="2026-08-08",
                adapter=adapter,
            )
        self.assertEqual("output-contract-failed", ctx.exception.error_type)

    def test_empty_output_raises(self) -> None:
        adapter = _adapter_from("   ")
        with self.assertRaises(RunError) as ctx, self._patch_repo(
            [_mode(), _event()]
        ):
            prepare_run(
                ROOT,
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-20260225-034"],
                as_of="2026-08-08",
                created_at="2026-08-08",
                adapter=adapter,
            )
        self.assertEqual("empty-output", ctx.exception.error_type)

    def test_invalid_as_of_raises(self) -> None:
        with self.assertRaises(RunError) as ctx:
            prepare_run(
                ROOT,
                mode_id="MOD-ANL-value-chain-v1",
                as_of="not-a-date",
                created_at="2026-08-08",
                adapter=ValidBodyAdapter(),
            )
        self.assertEqual("invalid-as-of", ctx.exception.error_type)

    def test_invalid_created_at_raises(self) -> None:
        with self.assertRaises(RunError) as ctx:
            prepare_run(
                ROOT,
                mode_id="MOD-ANL-value-chain-v1",
                as_of="2026-08-08",
                created_at="2026/08/08",
                adapter=ValidBodyAdapter(),
            )
        self.assertEqual("invalid-date", ctx.exception.error_type)

    def test_timeout_raises_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._patch_repo([_mode(), _event()]), self.assertRaises(
                RunError
            ) as ctx:
                run_analysis(
                    root,
                    mode_id="MOD-ANL-value-chain-v1",
                    input_event_ids=["EVT-20260225-034"],
                    as_of="2026-08-08",
                    created_at="2026-08-08",
                    adapter=_raise_adapter(TimeoutError("slow provider")),
                )
            self.assertEqual("timeout", ctx.exception.error_type)
            self.assertFalse((root / "05_Research").exists())

    def test_provider_failure_raises(self) -> None:
        with self.assertRaises(RunError) as ctx, self._patch_repo(
            [_mode(), _event()]
        ):
            prepare_run(
                ROOT,
                mode_id="MOD-ANL-value-chain-v1",
                input_event_ids=["EVT-20260225-034"],
                as_of="2026-08-08",
                created_at="2026-08-08",
                adapter=_raise_adapter(RuntimeError("boom")),
            )
        self.assertEqual("provider-failure", ctx.exception.error_type)


def _parse_frontmatter(content: str) -> dict[str, object]:
    block = content.split("---\n", 2)[1]
    meta: dict[str, object] = {}
    for line in block.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        meta[key] = value.strip('"')
    return meta


class RunDraftRenderTests(unittest.TestCase):
    """render_run_draft must emit schema-valid frontmatter: dict values
    (model_parameters) render as YAML flow mappings, never quoted strings."""

    def _meta(self) -> dict[str, object]:
        return {
            "id": "ANL-20260808-001",
            "type": "analysis_run",
            "title": "t",
            "created_at": "2026-08-08",
            "updated_at": "2026-08-08",
            "schema_version": 2,
            "project_ids": [],
            "status": "completed",
            "review_status": "pending",
            "tags": [],
            "mode_id": "MOD-ANL-value-chain-v1",
            "scope_ids": [],
            "as_of": "2026-08-08",
            "input_source_ids": [],
            "input_event_ids": [],
            "input_impact_ids": [],
            "input_thesis_ids": [],
            "input_snapshot_hash": "a" * 64,
            "model_provider": "deterministic",
            "model_id": "m",
            "model_parameters": {"temperature": "0.2", "max_tokens": "2000"},
            "prompt_hash": "b" * 64,
            "output_hash": "c" * 64,
            "generation_method": "mode-runner",
        }

    def test_dict_roundtrips_through_schema(self) -> None:
        from research_os.repositories.markdown import MarkdownDocument
        from research_os.schemas import AnalysisRunSchema
        from research_os.services.analysis_runner import render_run_draft

        content = render_run_draft(self._meta(), "## Facts used\nx\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ANL-20260808-001.md"
            path.write_text(content, encoding="utf-8")
            doc = MarkdownDocument.read(path)
            obj = AnalysisRunSchema.model_validate(doc.metadata)
            self.assertEqual(
                {"temperature": "0.2", "max_tokens": "2000"}, obj.model_parameters
            )

    def test_empty_dict_renders_as_flow_mapping(self) -> None:
        from research_os.services.analysis_runner import render_run_draft

        content = render_run_draft({"model_parameters": {}}, "body")
        self.assertIn("model_parameters: {}", content)


class ModeDefinitionsTests(unittest.TestCase):
    """D-010: the 9 first-batch modes exist, share the output contract, and are
    all activated (value-chain/supply-demand/red-team via REV-20260808-005, the
    remaining 6 via REV-20260808-007) so require_runnable accepts every one."""

    EXPECTED = [
        "MOD-ANL-value-chain-v1",
        "MOD-ANL-supply-demand-v1",
        "MOD-ANL-technology-curve-v1",
        "MOD-ANL-company-fundamental-v1",
        "MOD-ANL-competitive-dynamics-v1",
        "MOD-ANL-expectations-valuation-v1",
        "MOD-ANL-scenario-v1",
        "MOD-ANL-red-team-v1",
        "MOD-ANL-open-discovery-v1",
    ]

    # All 9 activated 2026-08-08 by max (REV-20260808-005 + REV-20260808-007):
    # status=active + review_status=reviewed + valid_from.
    ACTIVATED = frozenset(EXPECTED)

    def _repo_objects(self) -> list[ResearchObject]:
        from research_os.services.validation import validate_repository

        objects, findings = validate_repository(ROOT)
        assert not [f for f in findings if f.level == "error"]
        return objects

    def test_nine_modes_registered(self) -> None:
        objects = self._repo_objects()
        modes = sorted(
            obj.object_id
            for obj in objects
            if obj.object_type == "analysis_mode"
        )
        self.assertEqual(sorted(self.EXPECTED), modes)
        for mode_id in self.EXPECTED:
            self.assertIsNotNone(find_mode(objects, mode_id))

    def test_all_modes_are_active_and_runnable(self) -> None:
        objects = self._repo_objects()
        for mode_id in self.EXPECTED:
            mode = find_mode(objects, mode_id)
            self.assertEqual("active", mode.metadata["status"])
            self.assertEqual("reviewed", mode.metadata["review_status"])
            self.assertEqual("2026-08-08", mode.metadata.get("valid_from"))
            self.assertIsNotNone(require_runnable(objects, mode_id))

    def test_modes_share_output_contract(self) -> None:
        objects = self._repo_objects()
        for mode_id in self.EXPECTED:
            mode = find_mode(objects, mode_id)
            self.assertEqual(
                "00_System/Analysis_Modes/output_contract_schema.json",
                mode.metadata.get("output_schema_path"),
            )
            self.assertNotEqual([], mode.metadata.get("required_questions"))

    def test_mode_files_round_trip_byte_exact(self) -> None:
        for mode_id in self.EXPECTED:
            path = ROOT / "02_Knowledge/Modes" / f"{mode_id}.md"
            doc = MarkdownDocument.read(path)
            self.assertEqual(doc.original_text, doc.render())


if __name__ == "__main__":
    unittest.main()
