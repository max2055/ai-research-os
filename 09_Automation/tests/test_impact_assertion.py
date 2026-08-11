from __future__ import annotations

import unittest
from pathlib import Path

try:
    from pydantic import ValidationError

    from research_os.domain.models import ResearchObject
    from research_os.domain.policies import ID_PATTERNS
    from research_os.schemas import validate_metadata
    from research_os.schemas.impact_assertion import (
        DIRECTIONS,
        HORIZONS,
        IMPACT_TYPES,
        MAGNITUDES,
        ImpactAssertionSchema,
    )
    from research_os.services.drafts import next_object_id
    from research_os.services.validation import (
        expect_refs,
        validate_reviewed_assertion_evidence,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Schema tests") from exc


def _impact_base(**extra: object) -> dict[str, object]:
    meta: dict[str, object] = {
        "id": "IMP-20260807-001",
        "type": "impact_assertion",
        "title": "HBM supply shock affects NVIDIA",
        "created_at": "2026-08-07",
        "updated_at": "2026-08-07",
        "schema_version": 2,
        "project_ids": [],
        "status": "pending",
        "review_status": "pending",
        "tags": [],
        "trigger_event_ids": ["EVT-20260716-037"],
        "subject_id": "EVT-20260716-037",
        "impact_type": "supply",
        "target_id": "COM-nvidia",
        "direction": "negative",
        "magnitude": "medium",
        "horizon": "quarter",
        "mechanism": "HBM supply constraint reduces GPU module availability.",
        "conditions": [],
        "countervailing_factors": [],
        "alternative_explanations": [],
        "evidence_ids": [],
        "confidence": 0.6,
        "valid_from": "2026-08-07",
        "generation_method": "manual",
    }
    meta.update(extra)
    return meta


class ImpactAssertionSchemaTests(unittest.TestCase):
    """WP-300 C-002: schema round-trip and enum/ID/reference validation."""

    def test_valid_impact_assertion_roundtrip(self) -> None:
        obj = ImpactAssertionSchema.model_validate(_impact_base())
        self.assertEqual("IMP-20260807-001", obj.id)
        self.assertEqual("impact_assertion", obj.type)
        self.assertEqual("supply", obj.impact_type)
        self.assertEqual("COM-nvidia", obj.target_id)
        self.assertEqual("pending", obj.review_status)

    def test_rejects_bad_id(self) -> None:
        with self.assertRaises(ValidationError):
            ImpactAssertionSchema.model_validate(_impact_base(id="IMP-bad-id"))

    def test_accepts_event_subject_and_ins_security_target(self) -> None:
        # ImpactEntityReference is wider than ontology_assertion's: EVT subjects
        # and INS targets are valid (Phase 3 §3).
        obj = ImpactAssertionSchema.model_validate(
            _impact_base(subject_id="EVT-20260716-037", target_id="INS-NASDAQ-NVDA")
        )
        self.assertEqual("EVT-20260716-037", obj.subject_id)
        self.assertEqual("INS-NASDAQ-NVDA", obj.target_id)

    def test_accepts_ins_ticker_with_digits(self) -> None:
        obj = ImpactAssertionSchema.model_validate(
            _impact_base(target_id="INS-KRX-000660")
        )
        self.assertEqual("INS-KRX-000660", obj.target_id)

    def test_rejects_non_entity_reference_format(self) -> None:
        # SRC- is not a valid ImpactEntityReference prefix.
        with self.assertRaises(ValidationError):
            ImpactAssertionSchema.model_validate(
                _impact_base(target_id="SRC-20260807-001")
            )

    def test_rejects_unknown_impact_type(self) -> None:
        with self.assertRaises(ValidationError):
            ImpactAssertionSchema.model_validate(_impact_base(impact_type="bogus"))

    def test_all_13_impact_types_validate(self) -> None:
        for impact_type in IMPACT_TYPES:
            ImpactAssertionSchema.model_validate(_impact_base(impact_type=impact_type))

    def test_rejects_bad_direction_magnitude_horizon(self) -> None:
        for field, bad in [
            ("direction", "bogus"),
            ("magnitude", "huge"),
            ("horizon", "soon"),
        ]:
            with self.assertRaises(ValidationError):
                ImpactAssertionSchema.model_validate(_impact_base(**{field: bad}))

    def test_rejects_empty_mechanism(self) -> None:
        # RELATED_TO is not impact: a non-empty mechanism is mandatory (Phase 3 §2.2).
        with self.assertRaises(ValidationError):
            ImpactAssertionSchema.model_validate(_impact_base(mechanism=""))

    def test_dispatch_via_registry(self) -> None:
        obj = validate_metadata(_impact_base())
        self.assertEqual("impact_assertion", obj.type)

    def test_id_pattern_registered_in_policies(self) -> None:
        self.assertIn("impact_assertion", ID_PATTERNS)
        self.assertIsNotNone(
            ID_PATTERNS["impact_assertion"].fullmatch("IMP-20260807-001")
        )

    def test_enum_sets_are_complete(self) -> None:
        self.assertEqual(13, len(IMPACT_TYPES))
        self.assertEqual(4, len(DIRECTIONS))
        self.assertEqual(5, len(MAGNITUDES))
        self.assertEqual(5, len(HORIZONS))


class ImpactAssertionValidationTests(unittest.TestCase):
    """WP-300 C-002: reviewed-evidence rule and reference integrity."""

    def _obj(self, id_: str, review_status: str, **meta: object) -> ResearchObject:
        metadata = {
            "id": id_,
            "type": "impact_assertion",
            "review_status": review_status,
            "evidence_ids": [],
            **meta,
        }
        return ResearchObject(
            path=Path(f"05_Research/Assertions/{id_}.md"),
            metadata=metadata,
            body="",
        )

    def test_pending_impact_without_evidence_passes(self) -> None:
        obj = self._obj("IMP-20260807-001", "pending")
        findings = []
        validate_reviewed_assertion_evidence(obj, {}, findings)
        self.assertEqual([], findings)

    def test_reviewed_impact_without_evidence_errors(self) -> None:
        obj = self._obj("IMP-20260807-002", "reviewed")
        findings = []
        validate_reviewed_assertion_evidence(obj, {}, findings)
        self.assertEqual(1, len(findings))
        self.assertEqual("REF003", findings[0].code)

    def test_reviewed_impact_with_reviewed_evidence_passes(self) -> None:
        evidence = ResearchObject(
            path=Path("04_Evidence/Events/EVT-20260716-037.md"),
            metadata={
                "id": "EVT-20260716-037",
                "type": "event",
                "review_status": "reviewed",
            },
            body="",
        )
        obj = self._obj(
            "IMP-20260807-003",
            "reviewed",
            evidence_ids=["EVT-20260716-037"],
        )
        findings = []
        validate_reviewed_assertion_evidence(
            obj, {evidence.object_id: evidence}, findings
        )
        self.assertEqual([], findings)

    def test_trigger_events_must_exist_and_be_events(self) -> None:
        event = ResearchObject(
            path=Path("04_Evidence/Events/EVT-20260716-037.md"),
            metadata={
                "id": "EVT-20260716-037",
                "type": "event",
                "review_status": "reviewed",
            },
            body="",
        )
        findings: list[object] = []
        obj = self._obj(
            "IMP-20260807-004",
            "pending",
            trigger_event_ids=["EVT-20260716-037", "EVT-missing"],
        )
        # expects event type; missing id -> REF001
        expect_refs(
            obj,
            "trigger_event_ids",
            "event",
            {event.object_id: event},
            findings,
        )
        self.assertEqual(1, len(findings))
        self.assertEqual("REF001", findings[0].code)

    def test_subject_target_existence_only(self) -> None:
        from research_os.services.validation import expect_ref

        company = ResearchObject(
            path=Path("02_Knowledge/Companies/COM-nvidia.md"),
            metadata={
                "id": "COM-nvidia",
                "type": "company",
                "review_status": "reviewed",
            },
            body="",
        )
        findings: list[object] = []
        obj = self._obj(
            "IMP-20260807-005",
            "pending",
            subject_id="EVT-20260716-037",
            target_id="COM-nvidia",
        )
        by_id = {company.object_id: company}
        # subject/target are existence checks (expected_type=None) in validate_refs:
        # a present target resolves, a missing subject errors.
        expect_ref(obj, "subject_id", None, by_id, findings)
        expect_ref(obj, "target_id", None, by_id, findings)
        self.assertEqual(1, len(findings))
        self.assertEqual("REF001", findings[0].code)

    def test_next_object_id_generates_imp_prefix(self) -> None:
        objects = [
            ResearchObject(
                path=Path("05_Research/Assertions/IMP-20260807-001.md"),
                metadata={"id": "IMP-20260807-001", "type": "impact_assertion"},
                body="",
            )
        ]
        next_id = next_object_id(objects, "impact_assertion", "2026-08-07")
        self.assertEqual("IMP-20260807-002", next_id)


if __name__ == "__main__":
    unittest.main()
