"""Ontology Assertion metadata schema (v0.3).

An Ontology Assertion (REL-YYYYMMDD-NNN) records a typed, evidence-backed
relation between two stable entities. It is the authoritative replacement
for stuffing all relationships into ``related_entities``: relations now carry
a predicate, validity window, evidence and confidence (Phase 0-1 §5).

Design rules implemented here:
- subject/object IDs are format-validated (cross-object existence is enforced
  by validate_refs, WP-103); direction is explicit in the schema.
- symmetric predicates (COMPETES_WITH/SUBSTITUTES/COMPLEMENTS/PARTNERS_WITH)
  are written once by the user; the export layer derives the reverse edge
  deterministically (no duplicate authoritative objects).
- time changes create a new assertion or close an old one (valid_to) — never
  overwrite history; retired assertions are not deleted.
- a ``reviewed`` assertion must have at least one reviewed Evidence (enforced
  in validation.py); pending assertions may be evidence-free.
- relation existence is separate from impact strength (impact is Phase 3).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import Confidence, DateString, ResearchObjectSchema

AssertionId = Annotated[str, StringConstraints(pattern=r"^REL-\d{8}-\d{3}$")]

# Subject/object entity ID formats (RCP-v03-003 permanent IDs). Any of the
# entity prefixes is acceptable; cross-object existence and type checks are
# validate_refs' job, not the schema's.
EntityReference = Annotated[
    str,
    StringConstraints(
        pattern=r"^(COM-[a-z0-9]+(?:-[a-z0-9]+)*|SEG-[a-z0-9]+(?:-[a-z0-9]+)*|"
        r"TEC-[a-z0-9]+(?:-[a-z0-9]+)*|PRD-[a-z0-9]+(?:-[a-z0-9]+)*|"
        r"MET-[a-z0-9]+(?:-[a-z0-9]+)*)$"
    ),
]

# Directional predicates (from Phase 0-1 §5). The symmetric set is derived
# deterministically in the export layer, never duplicated as authoritative
# objects.
ONTOLOGY_PREDICATES = frozenset(
    {
        "SUPPLIES",
        "CUSTOMER_OF",
        "COMPETES_WITH",
        "SUBSTITUTES",
        "COMPLEMENTS",
        "DEPENDS_ON",
        "ENABLES",
        "CONSTRAINS",
        "OWNS",
        "PARTNERS_WITH",
        "PRODUCES",
        "USES",
    }
)
SYMMETRIC_PREDICATES = frozenset(
    {"COMPETES_WITH", "SUBSTITUTES", "COMPLEMENTS", "PARTNERS_WITH"}
)

PredicateLiteral = Literal[
    "SUPPLIES",
    "CUSTOMER_OF",
    "COMPETES_WITH",
    "SUBSTITUTES",
    "COMPLEMENTS",
    "DEPENDS_ON",
    "ENABLES",
    "CONSTRAINS",
    "OWNS",
    "PARTNERS_WITH",
    "PRODUCES",
    "USES",
]


class OntologyAssertionSchema(ResearchObjectSchema):
    """A typed, evidence-backed relation between two stable entities."""

    schema_version: Literal[2]
    id: AssertionId
    type: Literal["ontology_assertion"]

    subject_id: EntityReference
    predicate: PredicateLiteral
    object_id: EntityReference

    valid_from: DateString
    valid_to: DateString | None = None  # closed when superseded/retired, never deleted
    as_of: DateString
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = 0.5
    scope: str = ""  # e.g. "industry", "company", "product"; free-form for now
    qualifiers: dict[str, str] = Field(default_factory=dict)

    # review_status inherited from ResearchObjectSchema; pending by default.
    # A reviewed assertion must have >=1 reviewed Evidence (validation.py).
