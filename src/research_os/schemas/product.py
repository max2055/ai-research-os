"""Product entity metadata schema (v0.3).

A Product is a named offering/platform owned by one or more Companies and
placed in one or more Sectors. Industry ownership migrated from flat
Taxonomy v0.1 tags (APP-/INF-/...) to Sector + Product/Technology entity
references under RCP-v03-002 (approved); v0.2 historical tags are NOT
backfilled (R1).

Permanent ID: ``PRD-<slug>``. slug is ``[a-z0-9-]`` only, matching the v0.2
Company ID grammar.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateOrUnknown, ResearchObjectSchema

ProductId = Annotated[str, StringConstraints(pattern=r"^PRD-[a-z0-9]+(?:-[a-z0-9]+)*$")]


class ProductSchema(ResearchObjectSchema):
    """A product or platform offered by one or more Companies."""

    schema_version: Literal[2]
    id: ProductId
    type: Literal["product"]

    owner_company_ids: list[str] = Field(default_factory=list)
    sector_ids: list[str] = Field(default_factory=list)
    parent_id: ProductId | None = None  # product lineage, never delete
    maturity: str = ""  # carries MAT-* via tags (Taxonomy v2 horizontal dim)
    introduced_at: DateOrUnknown = "unknown"
    retired_at: DateOrUnknown = "unknown"  # retirement, never delete
    evidence_ids: list[str] = Field(default_factory=list)

    # Reference-integrity (Company/Sector exists) enforced in WP-103, not here.