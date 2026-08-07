from __future__ import annotations

import unittest
from pathlib import Path

try:
    from research_os.domain.policies import (
        DEFAULT_IMPACT_DIRECTION,
        ONTOLOGY_PREDICATES,
        PRIMARY_IMPACT_TYPE,
    )
    from research_os.schemas.impact_assertion import DIRECTIONS, IMPACT_TYPES
    from research_os.services.impact_proposal import (
        propose_direct_impacts,
        render_proposal,
        validate_mechanism,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Schema tests") from exc

ROOT = Path(__file__).resolve().parents[2]


class _Fake:
    def __init__(self, object_id: str, object_type: str, metadata: dict,
                 body: str = "") -> None:
        self.object_id = object_id
        self.object_type = object_type
        self.metadata = metadata
        self.body = body


def _event(**extra: object) -> _Fake:
    body = str(extra.pop("body", ""))
    meta: dict[str, object] = {
        "id": "EVT-1",
        "type": "event",
        "title": "ASML EUV platform ramp",
        "review_status": "reviewed",
        "companies": ["COM-asml", "COM-tsmc"],
        "technologies": [],
        "products": [],
        "confidence": 0.7,
        "event_date": "2026-08-01",
    }
    meta.update(extra)
    return _Fake("EVT-1", "event", meta, body=body)


def _rel(rel_id: str = "REL-1", **extra: object) -> _Fake:
    meta: dict[str, object] = {
        "id": rel_id,
        "type": "ontology_assertion",
        "subject_id": "COM-asml",
        "predicate": "SUPPLIES",
        "object_id": "COM-tsmc",
        "evidence_ids": ["EVT-1"],
        "review_status": "reviewed",
        "valid_to": None,
    }
    meta.update(extra)
    return _Fake(rel_id, "ontology_assertion", meta)


def _entities() -> list[_Fake]:
    return [
        _Fake("COM-asml", "company", {"title": "ASML"}),
        _Fake("COM-tsmc", "company", {"title": "TSMC"}),
    ]


class MechanismValidatorTests(unittest.TestCase):
    """C-005: reject empty / placeholder / too-short mechanisms."""

    def test_accepts_substantive_mechanism(self) -> None:
        text = "HBM supply constraint reduces GPU module availability for NVIDIA."
        self.assertEqual([], validate_mechanism(text))

    def test_rejects_empty_and_whitespace(self) -> None:
        self.assertEqual(["mechanism is empty"], validate_mechanism(""))
        self.assertEqual(["mechanism is empty"], validate_mechanism("   \n  "))

    def test_rejects_placeholder_tokens(self) -> None:
        for token in ("TODO", "TBD", "FIXME", "to be determined", "XXX"):
            problems = validate_mechanism(f"Impact via {token} and nothing else yet.")
            self.assertIn("mechanism contains placeholder token(s)", problems)

    def test_rejects_too_short(self) -> None:
        problems = validate_mechanism("impact")
        self.assertIn("mechanism too short to be meaningful", problems)


class DirectImpactProposalTests(unittest.TestCase):
    """C-004: reviewed Event -> pending IMP proposals via bridging REL + rule map."""

    def _objects(self) -> list[_Fake]:
        return [_event(), _rel(), *_entities()]

    def test_rejects_pending_event(self) -> None:
        objects = [_event(review_status="pending"), _rel(), *_entities()]
        with self.assertRaises(ValueError):
            propose_direct_impacts(objects, event_id="EVT-1")

    def test_rejects_unknown_event(self) -> None:
        with self.assertRaises(ValueError):
            propose_direct_impacts(self._objects(), event_id="EVT-missing")

    def test_proposes_both_event_named_endpoints(self) -> None:
        proposals = propose_direct_impacts(self._objects(), event_id="EVT-1")
        targets = sorted({p["target_id"] for p in proposals})
        self.assertEqual(["COM-asml", "COM-tsmc"], targets)
        for proposal in proposals:
            # SUPPLIES allows supply/capacity/cost/price (non-conditional).
            self.assertIn(
                proposal["impact_type"], {"supply", "capacity", "cost", "price"}
            )
            # "ramp" in the event title -> positive valence overrides "mixed".
            self.assertEqual("positive", proposal["direction"])
            self.assertEqual("unknown", proposal["magnitude"])
            self.assertEqual("unknown", proposal["horizon"])
            self.assertEqual("pending", proposal["review_status"])
            self.assertEqual("direct-proposal", proposal["generation_method"])
            self.assertEqual("EVT-1", proposal["subject_id"])
            self.assertEqual(["EVT-1"], proposal["trigger_event_ids"])
            self.assertEqual(["EVT-1"], proposal["evidence_ids"])
            self.assertEqual("SUPPLIES", proposal["predicate"])
            self.assertEqual(0.7, proposal["confidence"])
            self.assertEqual("2026-08-01", proposal["valid_from"])
            self.assertEqual([], validate_mechanism(proposal["mechanism"]))

    def test_proposes_all_non_conditional_allowed_types(self) -> None:
        proposals = propose_direct_impacts(self._objects(), event_id="EVT-1")
        types = {p["impact_type"] for p in proposals}
        self.assertEqual({"supply", "capacity", "cost", "price"}, types)

    def test_dedup_collapses_same_target_type_and_merges_rels(self) -> None:
        objects = [
            _event(),
            _rel("REL-1"),  # COM-a SUPPLIES COM-b
            _rel("REL-2"),  # COM-a SUPPLIES COM-b (duplicate relation)
            *_entities(),
        ]
        proposals = propose_direct_impacts(objects, event_id="EVT-1")
        supply = [p for p in proposals if p["impact_type"] == "supply"]
        self.assertTrue(supply)
        for proposal in supply:
            self.assertEqual(["REL-1", "REL-2"], proposal["relation_ids"])

    def test_direction_stays_mixed_without_content_signal(self) -> None:
        objects = [
            _event(title="Quarterly report", body=""),  # no valence keywords
            _rel("REL-1"),
            *_entities(),
        ]
        proposals = propose_direct_impacts(objects, event_id="EVT-1")
        by_type = {p["impact_type"]: p["direction"] for p in proposals}
        # Content-neutral event: mixed defaults stay mixed; explicit rule-map
        # defaults (capacity positive) are respected.
        self.assertEqual("mixed", by_type["supply"])
        self.assertEqual("mixed", by_type["cost"])
        self.assertEqual("mixed", by_type["price"])
        self.assertEqual("positive", by_type["capacity"])

    def test_horizon_inferred_quarter_for_earnings(self) -> None:
        objects = [
            _event(title="NVIDIA FY27 Q1 record revenue"),
            _rel("REL-1"),
            *_entities(),
        ]
        proposals = propose_direct_impacts(objects, event_id="EVT-1")
        self.assertTrue(proposals)
        for proposal in proposals:
            self.assertEqual("quarter", proposal["horizon"])

    def test_horizon_multi_year_for_long_commitments(self) -> None:
        objects = [
            _event(title="AWS expands commitment by $100B over 8 years"),
            _rel("REL-1"),
            *_entities(),
        ]
        proposals = propose_direct_impacts(objects, event_id="EVT-1")
        for proposal in proposals:
            self.assertEqual("multi_year", proposal["horizon"])

    def test_skips_pending_relation(self) -> None:
        objects = [_event(), _rel(review_status="pending"), *_entities()]
        self.assertEqual([], propose_direct_impacts(objects, event_id="EVT-1"))

    def test_skips_relation_not_citing_event(self) -> None:
        objects = [_event(), _rel(evidence_ids=["EVT-other"]), *_entities()]
        self.assertEqual([], propose_direct_impacts(objects, event_id="EVT-1"))

    def test_skips_closed_relation(self) -> None:
        objects = [_event(), _rel(valid_to="2026-01-01"), *_entities()]
        self.assertEqual([], propose_direct_impacts(objects, event_id="EVT-1"))

    def test_skips_unknown_predicate(self) -> None:
        objects = [_event(), _rel(predicate="RELATES_TO"), *_entities()]
        self.assertEqual([], propose_direct_impacts(objects, event_id="EVT-1"))

    def test_no_target_when_event_entity_not_a_rel_endpoint(self) -> None:
        # Event names a company that is not an endpoint of the bridging REL.
        objects = [
            _event(companies=["COM-other"], technologies=[], products=[]),
            _rel(),
            _Fake("COM-other", "company", {"title": "Other"}),
            *_entities(),
        ]
        self.assertEqual([], propose_direct_impacts(objects, event_id="EVT-1"))

    def test_skips_event_with_no_bridging_relation(self) -> None:
        objects = [_event(companies=["COM-other"]), *_entities()]
        self.assertEqual([], propose_direct_impacts(objects, event_id="EVT-1"))

    def test_drops_proposal_whose_mechanism_fails_validation(self) -> None:
        # A title carrying a placeholder token leaks into the template mechanism
        # and is dropped by C-005 (defensive).
        objects = [
            _event(title="TBD"),  # placeholder in title -> mechanism fails C-005
            _rel(),
            *_entities(),
        ]
        self.assertEqual([], propose_direct_impacts(objects, event_id="EVT-1"))

    def test_render_proposal_is_json(self) -> None:
        proposals = propose_direct_impacts(self._objects(), event_id="EVT-1")
        self.assertTrue(proposals)
        self.assertIn('"target_id"', render_proposal(proposals[0]))


class RuleMapProjectionTests(unittest.TestCase):
    """The code projection matches the approved rule map and the schema enums."""

    def test_every_predicate_has_primary_type_and_direction(self) -> None:
        self.assertEqual(set(ONTOLOGY_PREDICATES), set(PRIMARY_IMPACT_TYPE))
        self.assertEqual(set(ONTOLOGY_PREDICATES), set(DEFAULT_IMPACT_DIRECTION))

    def test_projection_values_are_valid_enum_members(self) -> None:
        self.assertTrue(set(PRIMARY_IMPACT_TYPE.values()) <= IMPACT_TYPES)
        self.assertTrue(set(DEFAULT_IMPACT_DIRECTION.values()) <= DIRECTIONS)


class RealRepositorySmokeTests(unittest.TestCase):
    """Real data: EVT-20260225-034 is reviewed and bridged by REL-20260805-002."""

    def test_real_event_produces_grounded_proposals(self) -> None:
        from research_os.services.validation import load_objects

        objects, findings = load_objects(ROOT)
        self.assertEqual([], findings)
        proposals = propose_direct_impacts(objects, event_id="EVT-20260225-034")
        self.assertTrue(proposals)
        for proposal in proposals:
            self.assertIn(proposal["target_id"], {"COM-asml", "COM-tsmc"})
            self.assertEqual([], validate_mechanism(proposal["mechanism"]))
            self.assertIn(proposal["predicate"], ONTOLOGY_PREDICATES)


if __name__ == "__main__":
    unittest.main()
