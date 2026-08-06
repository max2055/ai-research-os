"""Source Channel entity metadata schema (v0.3, Phase 2).

A Source Channel is a configured, bounded capture source for candidate
discovery. Channels are reviewed before scheduling: the scheduler only calls
channels with ``review_status: reviewed`` and ``enabled: true``
(RCP-v03-005 review point 4). Permanent ID ``CHN-<slug>`` completes the
``CHN-`` placeholder reserved in RCP-v03-003.

See ``03_Phase_2_Intelligence_Ingestion.md`` §3.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import ResearchObjectSchema

ChannelId = Annotated[str, StringConstraints(pattern=r"^CHN-[a-z0-9]+(?:-[a-z0-9]+)*$")]

ChannelType = Literal[
    "rss", "web_page", "github_release", "arxiv", "sec", "journal", "api", "manual"
]
LicenseStatus = Literal["reviewed", "pending", "restricted"]


class SourceChannelSchema(ResearchObjectSchema):
    """A configured, reviewed capture source for candidate discovery."""

    schema_version: Literal[2]
    id: ChannelId
    type: Literal["source_channel"]

    name: str = ""
    channel_type: ChannelType = "web_page"
    locator: str = ""
    allow_hosts: list[str] = Field(default_factory=list)
    publisher: str = ""
    source_grade_proposal: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    sector_ids: list[str] = Field(default_factory=list)
    query: str = ""
    schedule: str = ""
    timezone: str = "Asia/Shanghai"
    max_candidates_per_run: int = 20
    rate_limit: str = ""
    retention_days: int = 30
    license_status: LicenseStatus = "pending"
    license_notes: str = ""
    robots_checked_at: str = ""
    enabled: bool = False
