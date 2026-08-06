"""Schema dispatch for current research object types."""

from collections.abc import Mapping
from datetime import date
from typing import Any

from research_os.schemas.action import ActionSchema
from research_os.schemas.common import ManagedObjectSchema
from research_os.schemas.company import CompanySchema
from research_os.schemas.event import EventSchema
from research_os.schemas.job import JobSchema
from research_os.schemas.metric import MetricSchema
from research_os.schemas.ontology_assertion import OntologyAssertionSchema
from research_os.schemas.product import ProductSchema
from research_os.schemas.project import ProjectSchema
from research_os.schemas.report import ReportSchema
from research_os.schemas.review import ReviewSchema
from research_os.schemas.sector import SectorSchema
from research_os.schemas.security import SecuritySchema
from research_os.schemas.source import SourceSchema
from research_os.schemas.source_channel import SourceChannelSchema
from research_os.schemas.technology import TechnologySchema
from research_os.schemas.thesis import ThesisSchema

type SchemaType = type[ManagedObjectSchema]

# v0.3 entities (Sector/Security/Product/Technology/Metric, RCP-v03-003) are
# registered here so validate_metadata can dispatch on `type`. No v0.3 entities
# exist on disk yet (created in WP-120); registering the schemas only — no
# object is created, no markdown touched (R1). count_by_type will enumerate
# these types once entities exist.
SCHEMAS: dict[str, SchemaType] = {
    "source": SourceSchema,
    "event": EventSchema,
    "thesis": ThesisSchema,
    "company": CompanySchema,
    "report": ReportSchema,
    "project": ProjectSchema,
    "review": ReviewSchema,
    "action": ActionSchema,
    "job": JobSchema,
    "sector": SectorSchema,
    "security": SecuritySchema,
    "product": ProductSchema,
    "technology": TechnologySchema,
    "metric": MetricSchema,
    "source_channel": SourceChannelSchema,
    "ontology_assertion": OntologyAssertionSchema,
}


def schema_for_metadata(metadata: Mapping[str, Any]) -> SchemaType:
    object_type = metadata.get("type")
    if not isinstance(object_type, str) or object_type not in SCHEMAS:
        raise ValueError(f"unsupported research object type: {object_type!r}")
    return SCHEMAS[object_type]


def validate_metadata(metadata: Mapping[str, Any]) -> ManagedObjectSchema:
    normalized = {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in metadata.items()
    }
    return schema_for_metadata(normalized).model_validate(normalized)
