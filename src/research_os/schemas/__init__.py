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
from research_os.schemas.metric import MetricSchema
from research_os.schemas.ontology_assertion import (
    ONTOLOGY_PREDICATES,
    SYMMETRIC_PREDICATES,
    OntologyAssertionSchema,
)
from research_os.schemas.product import ProductSchema
from research_os.schemas.project import ProjectSchema
from research_os.schemas.registry import validate_metadata
from research_os.schemas.report import ReportSchema
from research_os.schemas.review import ReviewSchema
from research_os.schemas.sector import SectorSchema
from research_os.schemas.security import SecuritySchema
from research_os.schemas.source import SourceSchema
from research_os.schemas.technology import TechnologySchema
from research_os.schemas.thesis import ThesisSchema

__all__ = [
    "ActionSchema",
    "CompanySchema",
    "EventSchema",
    "JobSchema",
    "ManagedObjectSchema",
    "MetricSchema",
    "ONTOLOGY_PREDICATES",
    "OntologyAssertionSchema",
    "ProductSchema",
    "ProjectSchema",
    "ReportSchema",
    "ResearchObjectSchema",
    "ReviewSchema",
    "ReviewStatus",
    "SYMMETRIC_PREDICATES",
    "SectorSchema",
    "SecuritySchema",
    "SourceSchema",
    "TechnologySchema",
    "ThesisSchema",
    "validate_metadata",
]
