"""Valuation Snapshot metadata schema (v0.3, Phase 5).

A ValuationSnapshot (VAL-YYYYMMDD-NNN) freezes a dated, sourced market-price
observation for a company/security so matched-period multiples are computed
deterministically (RCP-v03-009, Phase 5 §6). Equity Value and Enterprise Value
are derived from the snapshot inputs; external consensus is recorded with
provider, access date, range, fiscal period, definition and license.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import DateString, ResearchObjectSchema

ValuationId = Annotated[str, StringConstraints(pattern=r"^VAL-\d{8}-\d{3}$")]
CompanyRef = Annotated[
    str, StringConstraints(pattern=r"^COM-[a-z0-9]+(?:-[a-z0-9]+)*$")
]
SecurityRef = Annotated[
    str,
    StringConstraints(pattern=r"^INS-[A-Z]{2,6}-[A-Z0-9][A-Z0-9.\-]*$"),
]
SourceRef = Annotated[str, StringConstraints(pattern=r"^SRC-\d{8}-\d{3}$")]
EventRef = Annotated[str, StringConstraints(pattern=r"^EVT-\d{8}-\d{3}$")]


class ValuationSnapshotSchema(ResearchObjectSchema):
    """A dated, sourced valuation observation for one company/security."""

    schema_version: Literal[2]
    id: ValuationId
    type: Literal["valuation_snapshot"]

    company_id: CompanyRef
    security_id: SecurityRef | None = None
    as_of: DateString
    market_price: float
    currency: str = ""
    shares: float | None = None
    debt: float | None = None
    cash: float | None = None
    other_adjustments: float | None = None
    valuation_identity: str = ""  # e.g. "ev/ebitda", "pe", "ps", "manual"
    denominator_period: str = ""  # matched period for the multiple
    source_ids: list[SourceRef] = Field(default_factory=list)
    event_ids: list[EventRef] = Field(default_factory=list)
    scenario_set: str = ""  # reference to a scenario analysis run/name
    freshness_threshold: str = ""  # e.g. "7d"

    # review_status inherited; reviewed snapshots require reviewed sources.
