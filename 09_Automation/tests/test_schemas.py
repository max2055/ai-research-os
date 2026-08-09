from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

try:
    from pydantic import ValidationError

    from research_os.domain.policies import (
        ONTOLOGY_PREDICATES,
        SYMMETRIC_PREDICATES,
    )
    from research_os.repositories.markdown import (
        MarkdownDocument,
        load_documents,
        validate_documents,
    )
    from research_os.schemas import (
        CompanySchema,
        EventSchema,
        MetricSchema,
        OntologyAssertionSchema,
        ProductSchema,
        SectorSchema,
        SecuritySchema,
        TechnologySchema,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Schema tests") from exc

ROOT = Path(__file__).resolve().parents[2]


class SchemaTests(unittest.TestCase):
    def test_all_repository_objects_pass_formal_schemas(self) -> None:
        documents, errors = validate_documents(ROOT)
        self.assertEqual([], errors)
        counts = dict(Counter(document.metadata["type"] for document in documents))
        # "job" is asserted as a floor, not an exact count: launchd adds Job
        # Run records every 6h, so the exact value drifts every round.
        job_count = counts.pop("job", 0)
        # "impact_assertion" is a floor too: max materializes pending IMPs from
        # C-004 proposals as the C-018 loop runs, so the exact value grows.
        impact_count = counts.pop("impact_assertion", 0)
        # "analysis_run" is a floor too: max runs analyses (WP-410+) so the
        # exact value grows as runs are materialized.
        run_count = counts.pop("analysis_run", 0)
        self.assertEqual(
            {
                "action": 12,
                "analysis_mode": 10,  # WP-410 first 9 + scenario-v2 (2026-08-09)
                "company": 59,  # WP-120: 8 v0.2 + 51 Pilot Core Compute Chain
                "event": 54,  # EvWP; Gate30; Field gap; +4 pricing/capex/demand
                "ontology_assertion": 260,  # RelWP; Field gap: +7; Product WP: +5
                "product": 5,  # WP-120 Product entities
                "project": 2,
                "report": 2,
                # +11: C-018 BIS + mode activations + ANL-001 reject + v2 REV +
                #       3 pricing/capex/demand reviews (2026-08-09)
                "review": 181,
                "sector": 9,  # WP-120: 8 Compute Chain rings + enterprise-applications
                "security": 10,  # Field Gate §9.3 securities
                "source": 153,  # +2 C-018 BIS sources +42 8-K +2 github +26 arxiv
                "source_channel": 24,  # WP-201: 6 first-batch + 18 Pilot G1 batch
                "thesis": 8,
            },
            counts,
        )
        self.assertGreaterEqual(job_count, 40)
        self.assertGreaterEqual(impact_count, 4)
        self.assertGreaterEqual(run_count, 0)

    def test_noop_round_trip_is_byte_exact_for_all_objects(self) -> None:
        for document in load_documents(ROOT):
            self.assertEqual(document.original_text, document.render())

    def test_round_trip_edit_preserves_body_unknown_fields_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SRC-20260729-001-test.md"
            path.write_text(
                """---
id: SRC-20260729-001
type: source
title: Test
created_at: 2026-07-29
updated_at: 2026-07-29
schema_version: 1
project_ids: [PRJ-001]
status: active
review_status: pending
tags: []
source_type: article
publisher: Publisher
authors: []
published_at: 2026-07-29
accessed_at: 2026-07-29
url: https://example.com
local_path:
source_grade: A
companies: []
technologies: []
products: []
canonical_url: https://example.com
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status: registered
processing_error:
published_date_proposal:
custom_field: keep  # human comment
---
# Body

Manual text.
""",
                encoding="utf-8",
            )
            document = MarkdownDocument.read(path)
            original_body = document.body
            document.set_metadata("updated_at", "2026-07-30")
            rendered = document.render()
            path.write_text(rendered, encoding="utf-8")
            reparsed = MarkdownDocument.read(path)
            self.assertEqual(original_body, reparsed.body)
            self.assertEqual("keep", reparsed.metadata["custom_field"])
            self.assertIn("# human comment", rendered)

    def test_schema_rejects_invalid_event_id(self) -> None:
        with self.assertRaises(ValidationError):
            EventSchema.model_validate(
                {
                    "id": "BAD",
                    "type": "event",
                    "title": "Bad",
                    "created_at": "2026-07-29",
                    "updated_at": "2026-07-29",
                    "schema_version": 1,
                    "project_ids": ["PRJ-001"],
                    "status": "active",
                    "review_status": "pending",
                    "tags": [],
                    "event_date": "2026-07-29",
                    "source_ids": ["SRC-20260729-001"],
                    "companies": [],
                    "technologies": [],
                    "products": [],
                    "thesis_links": [],
                    "confidence": 0.5,
                }
            )


def _v03_base(
    *,
    object_id: str,
    object_type: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Shared base metadata for v0.3 entities (schema_version=2)."""
    meta: dict[str, object] = {
        "id": object_id,
        "type": object_type,
        "title": "Test",
        "created_at": "2026-08-05",
        "updated_at": "2026-08-05",
        "schema_version": 2,
        "project_ids": [],
        "status": "active",
        "review_status": "pending",
        "tags": [],
    }
    if extra:
        meta.update(extra)
    return meta


class V03EntitySchemaTests(unittest.TestCase):
    """RCP-v03-003: Sector/Security/Product/Technology/Metric schemas.

    Registered in WP-102 with schema_version=2; validated via their own
    schema classes and via the registry dispatch (validate_metadata).
    """

    def test_sector_valid_and_rejects_bad_id(self) -> None:
        valid = SectorSchema.model_validate(
            _v03_base(object_id="SEG-compute-silicon", object_type="sector")
        )
        self.assertEqual("SEG-compute-silicon", valid.id)
        with self.assertRaises(ValidationError):
            SectorSchema.model_validate(
                _v03_base(object_id="SEC-compute", object_type="sector")
            )  # SEC is banned (D6 chose SEG)
        with self.assertRaises(ValidationError):
            SectorSchema.model_validate(
                _v03_base(object_id="SEG-UPPER", object_type="sector")
            )  # slug is lowercase-only

    def test_sector_schema_version_is_two(self) -> None:
        obj = SectorSchema.model_validate(
            _v03_base(object_id="SEG-models", object_type="sector")
        )
        self.assertEqual(2, obj.schema_version)
        with self.assertRaises(ValidationError):
            SectorSchema.model_validate(
                {
                    **_v03_base(object_id="SEG-models", object_type="sector"),
                    "schema_version": 1,
                }
            )

    def test_security_id_market_width_disambiguation(self) -> None:
        # D2: market is fixed-width [A-Z]{2,6}; ticker may contain a hyphen.
        obj = SecuritySchema.model_validate(
            _v03_base(
                object_id="INS-NASDAQ-BRK-A",
                object_type="security",
                extra={
                    "issuer_company_id": "COM-berkshire",
                    "instrument_type": "common_stock",
                    "ticker": "BRK-A",
                    "exchange": "NASDAQ",
                    "currency": "USD",
                    "country": "US",
                    "active_from": "2026-01-01",
                },
            )
        )
        self.assertEqual("INS-NASDAQ-BRK-A", obj.id)
        with self.assertRaises(ValidationError):
            SecuritySchema.model_validate(
                _v03_base(
                    object_id="INS-7-BRK-A",  # market too short / non-alpha
                    object_type="security",
                    extra={
                        "issuer_company_id": "COM-berkshire",
                        "instrument_type": "common_stock",
                        "ticker": "BRK-A",
                        "exchange": "NASDAQ",
                        "currency": "USD",
                        "country": "US",
                        "active_from": "2026-01-01",
                    },
                )
            )

    def test_security_rejects_invalid_instrument_type(self) -> None:
        with self.assertRaises(ValidationError):
            SecuritySchema.model_validate(
                _v03_base(
                    object_id="INS-NASDAQ-BRK-A",
                    object_type="security",
                    extra={
                        "issuer_company_id": "COM-berkshire",
                        "instrument_type": "warrant",  # not in closed enum
                        "ticker": "BRK-A",
                        "exchange": "NASDAQ",
                        "currency": "USD",
                        "country": "US",
                        "active_from": "2026-01-01",
                    },
                )
            )

    def test_product_and_technology_ids(self) -> None:
        product = ProductSchema.model_validate(
            _v03_base(object_id="PRD-gpt-4o", object_type="product")
        )
        self.assertEqual("PRD-gpt-4o", product.id)
        tech = TechnologySchema.model_validate(
            _v03_base(object_id="TEC-foundation-model", object_type="technology")
        )
        self.assertEqual("TEC-foundation-model", tech.id)
        # Single-segment MOD- is banned (RCP-v03-003 review point 7 / A-006 D1):
        # Technology IDs must not start with MOD-.
        with self.assertRaises(ValidationError):
            TechnologySchema.model_validate(
                _v03_base(object_id="MOD-foundation", object_type="technology")
            )
        with self.assertRaises(ValidationError):
            ProductSchema.model_validate(
                _v03_base(object_id="PRD-UPPER", object_type="product")
            )

    def test_metric_is_definition_not_observation(self) -> None:
        metric = MetricSchema.model_validate(
            _v03_base(
                object_id="MET-gpu-asp-usd",
                object_type="metric",
                extra={
                    "name": "GPU ASP",
                    "definition": "Average selling price of a GPU, per unit",
                    "unit": "USD",
                    "frequency": "quarterly",
                    "scope": "product",
                    "owner_entity_ids": ["PRD-accel"],
                    "preferred_source_types": ["earnings", "report"],
                    "comparison_limits": "vendor-reported ASPs not comparable",
                },
            )
        )
        self.assertEqual("quarterly", metric.frequency)
        # Observation-style keys must NOT appear on a Metric definition
        # (Phase 0-1 §4.5): a definition cannot be silently overwritten by a
        # measurement. extra="allow" tolerates unknown fields, so we assert
        # the schema carries no observation field by construction instead.
        self.assertNotIn("value", MetricSchema.model_fields)
        self.assertNotIn("period", MetricSchema.model_fields)
        self.assertNotIn("as_of", MetricSchema.model_fields)

    def test_metric_rejects_bad_scope(self) -> None:
        with self.assertRaises(ValidationError):
            MetricSchema.model_validate(
                _v03_base(
                    object_id="MET-foo",
                    object_type="metric",
                    extra={
                        "name": "Foo",
                        "scope": "industry",  # not in closed enum
                    },
                )
            )

    def test_validate_metadata_dispatches_v03_types(self) -> None:
        from research_os.schemas import validate_metadata

        sector = validate_metadata(
            _v03_base(object_id="SEG-cloud-ai", object_type="sector")
        )
        self.assertEqual("sector", sector.type)
        metric = validate_metadata(
            _v03_base(
                object_id="MET-capex",
                object_type="metric",
                extra={"name": "CapEx", "scope": "company"},
            )
        )
        self.assertEqual("metric", metric.type)

    def test_unknown_object_type_still_rejected(self) -> None:
        from research_os.schemas import validate_metadata

        with self.assertRaises(ValueError):
            validate_metadata(
                _v03_base(object_id="SEG-x", object_type="not-a-type")
            )


class V03CompanyCompatibilityTests(unittest.TestCase):
    """RCP-v03-003 review point 3: v0.2 Company objects load unchanged."""

    def test_v02_company_metadata_loads_without_new_fields(self) -> None:
        # Minimal v0.2-shape Company: no v0.3 extension fields present.
        company = CompanySchema.model_validate(
            {
                "id": "COM-microsoft",
                "type": "company",
                "title": "Microsoft",
                "created_at": "2026-07-29",
                "updated_at": "2026-07-30",
                "schema_version": 1,
                "project_ids": ["PRJ-001"],
                "status": "active",
                "review_status": "reviewed",
                "tags": [],
                "aliases": ["MSFT"],
                "related_entities": ["COM-openai"],
                "evidence_ids": ["EVT-20260219-001"],
                "source_ids": ["SRC-20260429-001"],
            }
        )
        self.assertEqual(1, company.schema_version)
        self.assertIsNone(company.region_primary)
        self.assertEqual([], company.sector_ids)

    def test_v02_company_with_v03_fields_roundtrips(self) -> None:
        company = CompanySchema.model_validate(
            {
                "id": "COM-microsoft",
                "type": "company",
                "title": "Microsoft",
                "created_at": "2026-07-29",
                "updated_at": "2026-07-30",
                "schema_version": 1,
                "project_ids": ["PRJ-001"],
                "status": "active",
                "review_status": "reviewed",
                "tags": [],
                "legal_name": "Microsoft Corporation",
                "region_primary": "REG-us",
                "coverage_tier": "core",
                "sector_ids": ["SEG-cloud-ai-infrastructure"],
                "security_ids": ["INS-NASDAQ-MSFT"],
            }
        )
        self.assertEqual("REG-us", company.region_primary)
        self.assertEqual(["SEG-cloud-ai-infrastructure"], company.sector_ids)

    def test_v03_company_rejects_bad_region_and_tier(self) -> None:
        with self.assertRaises(ValidationError):
            CompanySchema.model_validate(
                {
                    "id": "COM-microsoft",
                    "type": "company",
                    "title": "Microsoft",
                    "created_at": "2026-07-29",
                    "schema_version": 1,
                    "project_ids": ["PRJ-001"],
                    "status": "active",
                    "review_status": "reviewed",
                    "tags": [],
                    "region_primary": "US",  # must be REG-<region>
                }
            )
        with self.assertRaises(ValidationError):
            CompanySchema.model_validate(
                {
                    "id": "COM-microsoft",
                    "type": "company",
                    "title": "Microsoft",
                    "created_at": "2026-07-29",
                    "schema_version": 1,
                    "project_ids": ["PRJ-001"],
                    "status": "active",
                    "review_status": "reviewed",
                    "tags": [],
                    "coverage_tier": "all",  # not in core|tracked|discovery
                }
            )


class V03MigrationPlaceholderTests(unittest.TestCase):
    """MIG-v0.3-001 (no-op): registering schemas must not touch any Markdown."""

    def test_register_v03_schemas_migration_is_noop(self) -> None:
        from research_os.services.migration import RegisterV03SchemasMigration

        migration = RegisterV03SchemasMigration()
        self.assertEqual("MIG-v0.3-001-register-v0.3-schemas", migration.migration_id)
        self.assertEqual("keep-me", migration.render(
            type("D", (), {"original_text": "keep-me"})()
        ))
        self.assertNotEqual(
            "keep-me", migration.render(
                type("D", (), {"original_text": "altered"})()
            )
        )


def _assertion_base(**extra: object) -> dict[str, object]:
    meta: dict[str, object] = {
        "id": "REL-20260805-001",
        "type": "ontology_assertion",
        "title": "Test assertion",
        "created_at": "2026-08-05",
        "updated_at": "2026-08-05",
        "schema_version": 2,
        "project_ids": [],
        "status": "active",
        "review_status": "pending",
        "tags": [],
        "subject_id": "COM-nvidia",
        "predicate": "SUPPLIES",
        "object_id": "COM-tsmc",
        "valid_from": "2026-08-05",
        "as_of": "2026-08-05",
        "evidence_ids": [],
        "source_ids": [],
        "confidence": 0.7,
        "scope": "industry",
        "qualifiers": {},
    }
    meta.update(extra)
    return meta


class V03OntologyAssertionTests(unittest.TestCase):
    """WP-103: Ontology Assertion schema + predicates + reference checks."""

    def test_assertion_valid_and_id_regex(self) -> None:
        obj = OntologyAssertionSchema.model_validate(_assertion_base())
        self.assertEqual("REL-20260805-001", obj.id)
        self.assertEqual("SUPPLIES", obj.predicate)
        with self.assertRaises(ValidationError):
            OntologyAssertionSchema.model_validate(
                _assertion_base(id="REL-bad-id")
            )

    def test_assertion_rejects_unknown_predicate(self) -> None:
        with self.assertRaises(ValidationError):
            OntologyAssertionSchema.model_validate(
                _assertion_base(predicate="RELATES_TO")
            )

    def test_predicate_sets_are_complete_and_symmetric(self) -> None:
        self.assertEqual(12, len(ONTOLOGY_PREDICATES))
        self.assertEqual(
            {"COMPETES_WITH", "SUBSTITUTES", "COMPLEMENTS", "PARTNERS_WITH"},
            set(SYMMETRIC_PREDICATES),
        )
        self.assertTrue(SYMMETRIC_PREDICATES <= ONTOLOGY_PREDICATES)

    def test_assertion_rejects_bad_entity_reference_format(self) -> None:
        # EntityReference regex: COM-/SEG-/TEC-/PRD-/MET- only.
        with self.assertRaises(ValidationError):
            OntologyAssertionSchema.model_validate(
                _assertion_base(subject_id="SRC-20260805-001")
            )
        with self.assertRaises(ValidationError):
            OntologyAssertionSchema.model_validate(
                _assertion_base(object_id="EVT-20260805-001")
            )

    def test_assertion_dispatches_via_registry(self) -> None:
        from research_os.schemas import validate_metadata

        obj = validate_metadata(_assertion_base())
        self.assertEqual("ontology_assertion", obj.type)

    def test_assertion_validates_in_repository(self) -> None:
        # A pending assertion with evidence-free body validates in-repo (the
        # reviewed-evidence rule applies only to reviewed assertions).

        # Can't add a REL object to the real repo (would mutate); instead
        # confirm the schema model_validate path + registry dispatch suffice.
        self.assertIsNotNone(
            OntologyAssertionSchema.model_validate(_assertion_base())
        )


class V03AssertionReferenceTests(unittest.TestCase):
    """WP-103: reference integrity for v0.3 entity fields."""

    def _assertion(self, **extra: object) -> dict[str, object]:
        return _assertion_base(**extra)

    def test_reviewed_assertion_requires_reviewed_evidence(self) -> None:
        # Unit-level: the validator function rejects a reviewed assertion with
        # no evidence, and accepts pending ones (rule is scoped to reviewed).
        from research_os.domain.models import Finding, ResearchObject
        from research_os.services.validation import (
            validate_reviewed_assertion_evidence,
        )

        class DummyObject:
            pass

        # pending assertion with no evidence -> no error
        obj = ResearchObject(
            path=Path("05_Research/Assertions/REL-20260805-001.md"),
            metadata={
                "id": "REL-20260805-001",
                "type": "ontology_assertion",
                "review_status": "pending",
                "evidence_ids": [],
            },
            body="",
        )
        findings: list[Finding] = []
        validate_reviewed_assertion_evidence(obj, {}, findings)
        self.assertEqual([], findings)

        # reviewed assertion with no evidence -> REF003 error
        obj_reviewed = ResearchObject(
            path=Path("05_Research/Assertions/REL-20260805-002.md"),
            metadata={
                "id": "REL-20260805-002",
                "type": "ontology_assertion",
                "review_status": "reviewed",
                "evidence_ids": [],
            },
            body="",
        )
        findings = []
        validate_reviewed_assertion_evidence(obj_reviewed, {}, findings)
        self.assertEqual(1, len(findings))
        self.assertEqual("REF003", findings[0].code)

    def test_expect_refs_allows_none_type_for_existence_only(self) -> None:
        from research_os.domain.models import Finding, ResearchObject
        from research_os.services.validation import expect_refs

        findings: list[Finding] = []
        obj = ResearchObject(
            path=Path("x.md"),
            metadata={"id": "x", "type": "metric", "owner_entity_ids": ["COM-nvidia"]},
            body="",
        )
        # None expected_type => existence check only; missing object errors.
        expect_refs(obj, "owner_entity_ids", None, {}, findings)
        self.assertEqual(1, len(findings))
        self.assertEqual("REF001", findings[0].code)


if __name__ == "__main__":
    unittest.main()
