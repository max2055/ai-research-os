"""Metric Definition entity metadata schema (v0.3).

A Metric is a *definition* of a measurable quantity (e.g. ``datacenter-power-mw``,
``gpu-asp-usd``), not an observation. Observations (period, as-of, unit,
currency, Source ID) live on Source/Event records; this schema deliberately
carries no observation fields so a Metric definition cannot be silently
overwritten by a measurement (Phase 0-1 §4.5).

Permanent ID: ``MET-<slug>``. A-006 confirmed v0.2 has no ``MET-`` objects, so
``MET-`` unambiguously denotes a Metric Definition (no prefix collision with
any existing object type).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from research_os.schemas.common import ResearchObjectSchema

MetricId = Annotated[str, StringConstraints(pattern=r"^MET-[a-z0-9]+(?:-[a-z0-9]+)*$")]

# Metric scope selects which kind of owner entity a Metric Definition ties to.
# This is a closed enum so that the reference-integrity layer (WP-103) can map
# scope -> expected owner-entity prefix (sector->SEG, company->COM, ...).
MetricScope = Literal["sector", "company", "product", "technology", "security"]


class MetricSchema(ResearchObjectSchema):
    """Definition of a measurable industry/company/product metric.

    Carries no observation fields (no period/as-of/value): by construction a
    Metric is the definition; measurements live on Source/Event records. A
    future WP-103 validator forbids observation-style keys here.
    """

    schema_version: Literal[2]
    id: MetricId
    type: Literal["metric"]

    name: str
    definition: str = ""
    unit: str = ""
    frequency: str = ""  # e.g. "quarterly", "event-driven"
    scope: MetricScope
    owner_entity_ids: list[str] = Field(default_factory=list)
    preferred_source_types: list[str] = Field(default_factory=list)
    comparison_limits: str = ""  # comparability caveats (free text or future struct)

    # Reference-integrity (owner entities of `scope` exist) enforced in WP-103.