"""Sector entity metadata schema (v0.3).

A Sector is a stable industry segment. Industry ownership migrated from
flat tags (Taxonomy v0.1 INF-/APP-/...) to Sector entity references under
RCP-v03-002 (approved). Sectors are cross-project Universe primitives; their
``project_ids`` may be empty (public Universe) and are not required to belong
to a single Project. See ``00_System/Metadata_Schema_v0.3_Proposal.md`` §3.

Permanent ID: ``SEG-<slug>`` (RCP-v03-003 decision D6: chose ``SEG`` over
``SEC`` to avoid collision with the US SEC disclosure adapter). slug is
``[a-z0-9-]`` only, matching the v0.2 Company ID grammar.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import ResearchObjectSchema

SectorId = Annotated[str, StringConstraints(pattern=r"^SEG-[a-z0-9]+(?:-[a-z0-9]+)*$")]


class SectorSchema(ResearchObjectSchema):
    """A vertical industry segment in the AI value chain.

    One of the 13 L1 sectors defined by Taxonomy v2 (Compute Silicon,
    Memory & Storage, ...). Sectors reference Companies (Core/Tracked tiers)
    and Metrics; Core seats prioritise CN/US firms per the region-scope
    constraint (D-REGION-SCOPE).
    """

    # v0.3 entities use schema_version=2; v0.2 objects (schema_version=1)
    # remain readable unchanged (RCP-v03-003 review point 1).
    schema_version: Literal[2]
    id: SectorId
    type: Literal["sector"]

    # Self-describing Universe fields. All optional: a freshly proposed
    # sector may carry only an id/title/definition; reviewers fill the rest.
    parent_id: SectorId | None = None
    definition: str = ""
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    value_chain_position: str = ""
    key_inputs: list[str] = Field(default_factory=list)
    key_outputs: list[str] = Field(default_factory=list)
    key_metrics: list[str] = Field(default_factory=list)
    core_company_ids: list[str] = Field(default_factory=list)
    tracked_company_ids: list[str] = Field(default_factory=list)
    source_channel_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    # Reference-integrity (Company/Security exists) is enforced in WP-103
    # (Ontology assertion + relation validation), not at the schema layer;
    # empty Universe phase must not force every Company to fail. WP-102 only
    # validates ID format via Annotated regex on the referenced-id *types*,
    # not cross-object existence.
