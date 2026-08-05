"""Typed schemas for research objects."""

from research_os.schemas.action import ActionSchema
from research_os.schemas.common import (
    ManagedObjectSchema,
    ResearchObjectSchema,
    ReviewStatus,
)
from research_os.schemas.company import CompanySchema
from research_os.schemas.event import EventSchema
from research_os.schemas.job import JobSchema
from research_os.schemas.project import ProjectSchema
from research_os.schemas.registry import validate_metadata
from research_os.schemas.report import ReportSchema
from research_os.schemas.review import ReviewSchema
from research_os.schemas.source import SourceSchema
from research_os.schemas.thesis import ThesisSchema

__all__ = [
    "CompanySchema",
    "ActionSchema",
    "EventSchema",
    "JobSchema",
    "ManagedObjectSchema",
    "ProjectSchema",
    "ReportSchema",
    "ResearchObjectSchema",
    "ReviewSchema",
    "ReviewStatus",
    "SourceSchema",
    "ThesisSchema",
    "validate_metadata",
]
