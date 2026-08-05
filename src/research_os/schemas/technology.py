"""Technology entity metadata schema (v0.3).

A Technology is a stable technology entity (e.g. a foundation model, an
accelerator architecture, a packaging technology). Under RCP-v03-002 the
v0.1 ``MOD-*`` model-type tags are ``map``-decided: their semantics are
carried by Technology entities here (e.g. ``MOD-FOUNDATION`` ->
``TEC-foundation-model`` rather than as tags). v0.2 historical tags are NOT
backfilled (R1); only new objects reference Technology entities.

Permanent ID: ``TEC-<slug>``. slug is ``[a-z0-9-]`` only.

Note (A-006 D1): the ``MOD-ANL-`` double-segment prefix reserved for Analysis
Mode (``MOD-ANL-<slug>-vN``) is NOT a Technology ID. The ``TEC-`` prefix is
distinct; single-segment ``MOD-`` is banned as a Model prefix (RCP-v03-003
review point 7) precisely so it cannot be confused with ``MOD-ANL-``. No
Technology ID therefore begins with ``MOD-``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateOrUnknown, ResearchObjectSchema

TechnologyId = Annotated[
    str, StringConstraints(pattern=r"^TEC-[a-z0-9]+(?:-[a-z0-9]+)*$")
]


class TechnologySchema(ResearchObjectSchema):
    """A stable technology entity in the AI value chain."""

    schema_version: Literal[2]
    id: TechnologyId
    type: Literal["technology"]

    owner_company_ids: list[str] = Field(default_factory=list)
    sector_ids: list[str] = Field(default_factory=list)
    parent_id: TechnologyId | None = None  # technology lineage, never delete
    maturity: str = ""  # carries MAT-* via tags (Taxonomy v2 horizontal dim)
    introduced_at: DateOrUnknown = "unknown"
    retired_at: DateOrUnknown = "unknown"  # retirement, never delete
    evidence_ids: list[str] = Field(default_factory=list)

    # Reference-integrity (Company/Sector exists) enforced in WP-103, not here.