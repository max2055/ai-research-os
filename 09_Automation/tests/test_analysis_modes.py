"""WP-400 (D-002~D-004): Analysis Mode / Run contract tests.

Covers the mode definition contract (version/status/path), the run immutable
fingerprint, the D-004 output contract validator (required sections / TODO /
citations) and the ANL- id generator. Mirrors the Phase 4 §10 test intent.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    from pydantic import ValidationError

    from research_os.domain.models import Finding, ResearchObject
    from research_os.schemas import AnalysisModeSchema, AnalysisRunSchema
    from research_os.services.analysis_contract import (
        CONTRACT_SCHEMA_PATH,
        REQUIRED_SECTIONS,
        validate_run_contract,
    )
    from research_os.services.drafts import next_object_id
    from research_os.services.validation import (
        validate_analysis_mode_semantics,
        validate_analysis_run_fingerprint,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Mode tests") from exc

ROOT = Path(__file__).resolve().parents[2]


def _meta(
    *,
    object_id: str,
    object_type: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    meta: dict[str, object] = {
        "id": object_id,
        "type": object_type,
        "title": "Test",
        "created_at": "2026-08-08",
        "updated_at": "2026-08-08",
        "schema_version": 2,
        "project_ids": [],
        "status": "active",
        "review_status": "pending",
        "tags": [],
    }
    if extra:
        meta.update(extra)
    return meta


class AnalysisModeSchemaTests(unittest.TestCase):
    def test_valid_mode_validates(self) -> None:
        mode = AnalysisModeSchema.model_validate(
            _meta(
                object_id="MOD-ANL-value-chain-v1",
                object_type="analysis_mode",
                extra={
                    "name": "Value Chain",
                    "status": "proposed",
                    "purpose": "Who holds leverage",
                },
            )
        )
        self.assertEqual("MOD-ANL-value-chain-v1", mode.id)

    def test_mode_id_rejects_bad_version(self) -> None:
        with self.assertRaises(ValidationError):
            AnalysisModeSchema.model_validate(
                _meta(object_id="MOD-ANL-value-chain", object_type="analysis_mode")
            )  # missing -vN
        with self.assertRaises(ValidationError):
            AnalysisModeSchema.model_validate(
                _meta(
                    object_id="MOD-ANL-VALUE-CHAIN-v1",
                    object_type="analysis_mode",
                    extra={"name": "x"},
                )
            )  # slug must be lowercase

    def test_mode_dispatches_via_registry(self) -> None:
        from research_os.schemas import validate_metadata

        obj = validate_metadata(
            _meta(
                object_id="MOD-ANL-scenario-v2",
                object_type="analysis_mode",
                extra={
                    "name": "Scenario",
                    "purpose": "What outcomes are priced",
                    "status": "active",
                },
            )
        )
        self.assertEqual("analysis_mode", obj.type)


class AnalysisRunSchemaTests(unittest.TestCase):
    def test_valid_run_validates(self) -> None:
        run = AnalysisRunSchema.model_validate(
            _meta(
                object_id="ANL-20260808-001",
                object_type="analysis_run",
                extra={
                    "mode_id": "MOD-ANL-value-chain-v1",
                    "as_of": "2026-08-08",
                    "status": "draft",
                },
            )
        )
        self.assertEqual("ANL-20260808-001", run.id)

    def test_run_id_rejects_bad_date(self) -> None:
        with self.assertRaises(ValidationError):
            AnalysisRunSchema.model_validate(
                _meta(object_id="ANL-2026-001", object_type="analysis_run")
            )


def _run_object(
    *,
    object_id: str,
    status: str,
    meta: dict[str, object] | None = None,
    body: str = "",
) -> ResearchObject:
    return ResearchObject(
        path=ROOT / f"05_Research/Analysis/{object_id}.md",
        metadata={
            "id": object_id,
            "type": "analysis_run",
            "status": status,
            **({} if meta is None else meta),
        },
        body=body,
    )


class ModeContractValidationTests(unittest.TestCase):
    def _mode(self, **meta: object) -> ResearchObject:
        return ResearchObject(
            path=Path("02_Knowledge/Modes/MOD-ANL-value-chain-v1.md"),
            metadata={
                "id": "MOD-ANL-value-chain-v1",
                "type": "analysis_mode",
                **meta,
            },
            body="",
        )

    def test_active_requires_reviewed_and_valid_from(self) -> None:
        # active is a governance state: it needs human approval (reviewed) and
        # an effective date, so an active-but-pending mode fails both rules.
        findings: list[Finding] = []
        validate_analysis_mode_semantics(
            ROOT,
            self._mode(status="active", review_status="pending"),
            findings,
        )
        self.assertEqual(["MOD001", "MOD002"], [f.code for f in findings])

    def test_active_requires_valid_from(self) -> None:
        findings: list[Finding] = []
        validate_analysis_mode_semantics(
            ROOT,
            self._mode(status="active", review_status="reviewed"),
            findings,
        )
        self.assertEqual(["MOD002"], [f.code for f in findings])

    def test_active_mode_fully_valid(self) -> None:
        findings: list[Finding] = []
        validate_analysis_mode_semantics(
            ROOT,
            self._mode(
                status="active",
                review_status="reviewed",
                valid_from="2026-08-08",
            ),
            findings,
        )
        self.assertEqual([], findings)

    def test_proposed_mode_has_no_status_rules(self) -> None:
        findings: list[Finding] = []
        validate_analysis_mode_semantics(
            ROOT,
            self._mode(status="proposed", review_status="pending"),
            findings,
        )
        self.assertEqual([], findings)

    def test_path_escaping_repository(self) -> None:
        findings: list[Finding] = []
        validate_analysis_mode_semantics(
            ROOT,
            self._mode(
                status="active",
                review_status="reviewed",
                valid_from="2026-08-08",
                prompt_template_path="/etc/passwd",
            ),
            findings,
        )
        self.assertEqual(["MOD003"], [f.code for f in findings])

    def test_path_missing_inside_repository(self) -> None:
        findings: list[Finding] = []
        validate_analysis_mode_semantics(
            ROOT,
            self._mode(
                status="active",
                review_status="reviewed",
                valid_from="2026-08-08",
                output_schema_path="00_System/Analysis_Modes/nope.yaml",
            ),
            findings,
        )
        self.assertEqual(["MOD004"], [f.code for f in findings])

    def test_existing_path_accepts(self) -> None:
        findings: list[Finding] = []
        validate_analysis_mode_semantics(
            ROOT,
            self._mode(
                status="active",
                review_status="reviewed",
                valid_from="2026-08-08",
                prompt_template_path=CONTRACT_SCHEMA_PATH,
            ),
            findings,
        )
        self.assertEqual([], findings)


class RunFingerprintValidationTests(unittest.TestCase):
    def test_completed_requires_full_fingerprint(self) -> None:
        findings: list[Finding] = []
        validate_analysis_run_fingerprint(
            _run_object(object_id="ANL-20260808-001", status="completed"),
            findings,
        )
        self.assertEqual(["RUN001"], [f.code for f in findings])

    def test_completed_with_fingerprint_passes(self) -> None:
        findings: list[Finding] = []
        validate_analysis_run_fingerprint(
            _run_object(
                object_id="ANL-20260808-001",
                status="completed",
                meta={
                    "input_snapshot_hash": "a" * 64,
                    "prompt_hash": "b" * 64,
                    "output_hash": "c" * 64,
                    "model_provider": "anthropic",
                    "model_id": "claude-5-sonnet",
                    "generation_method": "mode-runner",
                },
            ),
            findings,
        )
        self.assertEqual([], findings)

    def test_superseded_retains_fingerprint_requirement(self) -> None:
        findings: list[Finding] = []
        validate_analysis_run_fingerprint(
            _run_object(
                object_id="ANL-20260808-002",
                status="superseded",
                meta={"output_hash": "c" * 64},
            ),
            findings,
        )
        self.assertEqual(["RUN001"], [f.code for f in findings])

    def test_draft_must_not_have_output_hash(self) -> None:
        findings: list[Finding] = []
        validate_analysis_run_fingerprint(
            _run_object(
                object_id="ANL-20260808-003",
                status="draft",
                meta={"output_hash": "c" * 64},
            ),
            findings,
        )
        self.assertEqual(["RUN002"], [f.code for f in findings])

    def test_failed_must_not_have_output_hash(self) -> None:
        findings: list[Finding] = []
        validate_analysis_run_fingerprint(
            _run_object(
                object_id="ANL-20260808-004",
                status="failed",
                meta={"output_hash": "c" * 64},
            ),
            findings,
        )
        self.assertEqual(["RUN002"], [f.code for f in findings])

    def test_failed_without_output_hash_passes(self) -> None:
        findings: list[Finding] = []
        validate_analysis_run_fingerprint(
            _run_object(object_id="ANL-20260808-004", status="failed"),
            findings,
        )
        self.assertEqual([], findings)


_COMPLETE_BODY = (
    "## Facts used\nEVT-20260225-034: SK hynix HBM ramp.\n"
    "## Inferences\nThe supply constraint eases by 2Q26.\n"
    "## Judgments\nHigh confidence in the direction.\n"
    "## Contradicting evidence\nMicron guides flat.\n"
    "## Alternative explanations\nDemand may soften.\n"
    "## Unknowns\nCapEx mix.\n"
    "## Indicators\nNVIDIA guidance.\n"
    "## Mode-specific output\nValue chain map.\n"
    "## Limitations\nNo primary data.\n"
)


class RunContractValidationTests(unittest.TestCase):
    def _by_id(self) -> dict[str, ResearchObject]:
        evt = ResearchObject(
            path=ROOT / "05_Research/Events/EVT-20260225-034.md",
            metadata={"id": "EVT-20260225-034", "type": "event"},
            body="",
        )
        return {"EVT-20260225-034": evt}

    def test_clean_completed_run_passes(self) -> None:
        run = _run_object(
            object_id="ANL-20260808-001",
            status="completed",
            meta={"input_event_ids": ["EVT-20260225-034"]},
            body=_COMPLETE_BODY,
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual([], findings)

    def test_draft_run_is_not_contract_checked(self) -> None:
        run = _run_object(
            object_id="ANL-20260808-002",
            status="draft",
            body="## Facts used\nTODO\n",
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual([], findings)

    def test_missing_section(self) -> None:
        body = _COMPLETE_BODY.replace("## Limitations\nNo primary data.\n", "")
        run = _run_object(
            object_id="ANL-20260808-003",
            status="completed",
            meta={"input_event_ids": ["EVT-20260225-034"]},
            body=body,
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual(["CON001"], [f.code for f in findings])

    def test_empty_section(self) -> None:
        body = _COMPLETE_BODY.replace("## Unknowns\nCapEx mix.\n", "## Unknowns\n")
        run = _run_object(
            object_id="ANL-20260808-004",
            status="completed",
            meta={"input_event_ids": ["EVT-20260225-034"]},
            body=body,
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual(["CON002"], [f.code for f in findings])

    def test_placeholder_token(self) -> None:
        run = _run_object(
            object_id="ANL-20260808-005",
            status="completed",
            meta={"input_event_ids": ["EVT-20260225-034"]},
            body=_COMPLETE_BODY.replace(
                "## Limitations\nNo primary data.\n",
                "## Limitations\nTBD by next week.\n",
            ),
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual(["CON003"], [f.code for f in findings])

    def test_undeclared_evidence_citation(self) -> None:
        run = _run_object(
            object_id="ANL-20260808-006",
            status="completed",
            meta={"input_event_ids": []},
            body=_COMPLETE_BODY,
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual(["CON004"], [f.code for f in findings])

    def test_scope_declared_citation_passes(self) -> None:
        run = _run_object(
            object_id="ANL-20260808-007",
            status="completed",
            meta={"scope_ids": ["EVT-20260225-034"]},
            body=_COMPLETE_BODY,
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual([], findings)

    def test_unknown_object_citation(self) -> None:
        run = _run_object(
            object_id="ANL-20260808-008",
            status="completed",
            body=_COMPLETE_BODY.replace(
                "EVT-20260225-034",
                "EVT-20260101-999",
            ),
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual(["CON004"], [f.code for f in findings])

    def test_own_run_id_in_body_is_not_a_citation(self) -> None:
        run = _run_object(
            object_id="ANL-20260808-009",
            status="completed",
            meta={"input_event_ids": ["EVT-20260225-034"]},
            body=_COMPLETE_BODY.replace(
                "## Mode-specific output\nValue chain map.\n",
                "## Mode-specific output\n"
                "Value chain map (supersedes ANL-20260808-009).\n",
            ),
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual([], findings)

    def test_natural_text_token_is_ignored(self) -> None:
        # "GPU-design" is not a registered id shape; it must not be treated as a
        # fabricated citation.
        run = _run_object(
            object_id="ANL-20260808-010",
            status="completed",
            meta={"input_event_ids": ["EVT-20260225-034"]},
            body=_COMPLETE_BODY.replace(
                "## Inferences\nThe supply constraint eases by 2Q26.\n",
                "## Inferences\nThe GPU-design bottleneck eases by 2Q26.\n",
            ),
        )
        findings: list[Finding] = []
        validate_run_contract(run, self._by_id(), findings)
        self.assertEqual([], findings)

    def test_non_run_object_skipped(self) -> None:
        event = ResearchObject(
            path=ROOT / "05_Research/Events/EVT-20260225-034.md",
            metadata={
                "id": "EVT-20260225-034",
                "type": "event",
                "status": "active",
            },
            body="## Facts\nx\n",
        )
        findings: list[Finding] = []
        validate_run_contract(event, self._by_id(), findings)
        self.assertEqual([], findings)


class OutputContractSchemaArtifactTests(unittest.TestCase):
    def test_json_schema_is_valid_and_synced(self) -> None:
        path = ROOT / CONTRACT_SCHEMA_PATH
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(REQUIRED_SECTIONS, schema["required"])

    def test_required_sections_match_phase_doc(self) -> None:
        # Phase 4 §3 body sections; a new mode must not invent incompatible
        # Facts/Inference fields (Phase 4 §7).
        self.assertEqual(9, len(REQUIRED_SECTIONS))
        self.assertIn("Mode-specific output", REQUIRED_SECTIONS)


class NextObjectIdAnalysisRunTests(unittest.TestCase):
    def test_next_anl_id_sequences(self) -> None:
        existing = [
            ResearchObject(
                path=ROOT / "05_Research/Analysis/ANL-20260808-001.md",
                metadata={"id": "ANL-20260808-001", "type": "analysis_run"},
                body="",
            ),
            ResearchObject(
                path=ROOT / "05_Research/Analysis/ANL-20260808-007.md",
                metadata={"id": "ANL-20260808-007", "type": "analysis_run"},
                body="",
            ),
        ]
        self.assertEqual(
            "ANL-20260808-008",
            next_object_id(existing, "analysis_run", "2026-08-08"),
        )

    def test_next_anl_id_rejects_bad_date(self) -> None:
        with self.assertRaises(ValueError):
            next_object_id([], "analysis_run", "not-a-date")


if __name__ == "__main__":
    unittest.main()
