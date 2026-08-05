"""Company knowledge metadata schema."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import ResearchObjectSchema

CompanyId = Annotated[
    str,
    StringConstraints(pattern=r"^COM-[a-z0-9]+(?:-[a-z0-9]+)*$"),
]

# v0.3 extension (RCP-v03-003, review point 2). Closed vocabularies so typos
# surface at validate time; "other" keeps the set open-ended.
CompanyStage = Literal["public", "private", "subsidiary", "state_owned", "other"]
CoverageTier = Literal["core", "tracked", "discovery"]

# Region primary (D-REGION-SCOPE): Universe prioritises CN/US AI firms, other
# regions covered as key-node补充 per value-chain distinctiveness. REG- prefix
# is ratified by RCP-v03-002. Any REG-<region> form is accepted here (format
# check only); a closed country list is not enforced at the schema layer so
# the registry can grow without a schema change per new region.
RegionPrimary = Annotated[
    str,
    StringConstraints(pattern=r"^REG-[a-z0-9]+(?:-[a-z0-9]+)*$"),
]


class CompanySchema(ResearchObjectSchema):
    id: CompanyId
    type: Literal["company"]
    aliases: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)

    # v0.3 extension (RCP-v03-003 review points 2/3). All fields optional with
    # defaults: existing v0.2 Company objects (schema_version=1) load
    # unchanged. No backfill (R1) — these are populated per-object by humans
    # during WP-120, never auto-assigned by a migration.
    legal_name: str | None = None
    company_stage: CompanyStage | None = None
    headquarters: str | None = None
    region_primary: RegionPrimary | None = None
    sector_ids: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    technology_ids: list[str] = Field(default_factory=list)
    security_ids: list[str] = Field(default_factory=list)
    coverage_tier: CoverageTier | None = None
    source_channel_ids: list[str] = Field(default_factory=list)
    key_metric_ids: list[str] = Field(default_factory=list)

    # NOTE: schema_version stays Literal[1] on Company. The v0.2 baseline
    # contract requires Company to remain schema_version=1; v0.3 entity types
    # (Sector/Security/Product/Technology/Metric) use Literal[2]. A Company is
    # upgraded to schema_version=2 only by an explicit human-approved MIG-v0.3-002
    # step (per-object), never by WP-102.
