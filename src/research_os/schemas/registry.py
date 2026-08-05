"""Schema dispatch for current research object types."""

from collections.abc import Mapping
from datetime import date
from typing import Any

from research_os.schemas.action import ActionSchema
from research_os.schemas.common import ManagedObjectSchema
from research_os.schemas.company import CompanySchema
from research_os.schemas.event import EventSchema
from research_os.schemas.job import JobSchema
from research_os.schemas.project import ProjectSchema
from research_os.schemas.report import ReportSchema
from research_os.schemas.review import ReviewSchema
from research_os.schemas.source import SourceSchema
from research_os.schemas.thesis import ThesisSchema

type SchemaType = type[ManagedObjectSchema]

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
