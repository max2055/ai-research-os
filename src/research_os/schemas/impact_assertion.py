"""Impact Assertion metadata schema (v0.3, Phase 3).

An Impact Assertion (IMP-YYYYMMDD-NNN) records that a reviewed Event or
subject affects a target entity/security through an explicit mechanism, with
direction, magnitude, horizon, lag, conditions, countervailing factors and
confidence (Phase 3 §3, RCP-v03-006).

Design rules implemented here:
- ``subject_id`` is usually the Event (EVT-) or the first-affected entity;
  ``target_id`` may be Sector/Company/Product/Technology/Metric/Security
  (Phase 3 §3). This reference range is WIDER than the ontology_assertion
  EntityReference (which excludes EVT/INS) — hence the separate
  ImpactEntityReference type; the ontology EntityReference is left unchanged.
- ``RELATED_TO`` is not impact (Phase 3 §2.1): every Impact Assertion must
  carry an explicit, non-empty ``mechanism``. Direction/magnitude are not
  derived from graph distance (§2.3); a supply relation does not imply revenue
  importance (§2.4) — that is enforced by the C-003 rule map, not here.
- Operating impact and security-price impact are separated (Phase 3 §2.6);
  Phase 3 does not by default generate Security/valuation price direction
  (RCP-v03-006 review point 3) — the schema keeps ``valuation`` as an enum
  value but the rule map constrains its use.
- A ``reviewed`` impact assertion must have >=1 reviewed Evidence (enforced in
  validation.py, like ontology_assertion); pending assertions may be evidence-free.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import (
    Confidence,
    DateOrUnknown,
    DateString,
    ResearchObjectSchema,
)

ImpactAssertionId = Annotated[str, StringConstraints(pattern=r"^IMP-\d{8}-\d{3}$")]

# Subject/target references. Wider than ontology_assertion.EntityReference:
# Impact subjects may be Events (EVT-) and targets may be Securities (INS-).
# Security ID format mirrors schemas/security.py (INS-<market>-<ticker>, ticker
# may contain digits/dots/hyphens). Cross-object existence is validate_refs'
# job, not the schema's.
ImpactEntityReference = Annotated[
    str,
    StringConstraints(
        pattern=r"^(EVT-\d{8}-\d{3}|"
        r"COM-[a-z0-9]+(?:-[a-z0-9]+)*|"
        r"SEG-[a-z0-9]+(?:-[a-z0-9]+)*|"
        r"TEC-[a-z0-9]+(?:-[a-z0-9]+)*|"
        r"PRD-[a-z0-9]+(?:-[a-z0-9]+)*|"
        r"MET-[a-z0-9]+(?:-[a-z0-9]+)*|"
        r"INS-[A-Z]{2,6}-[A-Z0-9][A-Z0-9.\-]*)$"
    ),
]

IMPACT_TYPES = frozenset(
    {
        "demand",
        "supply",
        "price",
        "cost",
        "revenue",
        "margin",
        "capex",
        "capacity",
        "competition",
        "technology",
        "regulation",
        "valuation",
        "other",
    }
)
DIRECTIONS = frozenset({"positive", "negative", "mixed", "uncertain"})
MAGNITUDES = frozenset({"immaterial", "low", "medium", "high", "unknown"})
HORIZONS = frozenset({"immediate", "quarter", "year", "multi_year", "unknown"})

ImpactTypeLiteral = Literal[
    "demand",
    "supply",
    "price",
    "cost",
    "revenue",
    "margin",
    "capex",
    "capacity",
    "competition",
    "technology",
    "regulation",
    "valuation",
    "other",
]
DirectionLiteral = Literal["positive", "negative", "mixed", "uncertain"]
MagnitudeLiteral = Literal["immaterial", "low", "medium", "high", "unknown"]
HorizonLiteral = Literal["immediate", "quarter", "year", "multi_year", "unknown"]


class ImpactAssertionSchema(ResearchObjectSchema):
    """An evidence-backed assertion that a subject affects a target."""

    schema_version: Literal[2]
    id: ImpactAssertionId
    type: Literal["impact_assertion"]

    trigger_event_ids: list[str] = Field(default_factory=list)
    subject_id: ImpactEntityReference
    impact_type: ImpactTypeLiteral
    target_id: ImpactEntityReference
    direction: DirectionLiteral
    magnitude: MagnitudeLiteral
    horizon: HorizonLiteral
    lag_start: DateOrUnknown | None = None
    lag_end: DateOrUnknown | None = None
    mechanism: str = Field(min_length=1)  # C-005 rejects empty/TODO at service layer
    conditions: list[str] = Field(default_factory=list)
    countervailing_factors: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = 0.5
    valid_from: DateString
    valid_to: DateString | None = None  # closed when superseded/retired, never deleted
    review_date: DateString | None = None
    generation_method: str = ""  # e.g. "direct-proposal", "path-expansion", "manual"

    # review_status inherited from ResearchObjectSchema; pending by convention.
    # A reviewed impact assertion must have >=1 reviewed Evidence (validation.py).
