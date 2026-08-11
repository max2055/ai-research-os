"""Strict schema for the pending Impact Assertion Agent audit packet."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AuditRecommendation = Literal[
    "ready_for_human_review", "edit_required", "reject_recommended"
]
AuditCheck = Literal["pass", "fail", "unknown", "not_applicable"]

_FORBIDDEN_REVIEW_FIELDS = frozenset({"reviewer", "decision", "reviewed_at"})


def _forbidden_field(value: Any, path: str = "packet") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in _FORBIDDEN_REVIEW_FIELDS:
                return child_path
            found = _forbidden_field(child, child_path)
            if found:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            found = _forbidden_field(child, f"{path}[{index}]")
            if found:
                return found
    return None


class _StrictAuditModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def reject_human_review_fields(cls, value: Any) -> Any:
        found = _forbidden_field(value)
        if found:
            raise ValueError(f"forbidden human review field at {found}")
        return value


class ImpactAuditEntry(_StrictAuditModel):
    assertion_id: Annotated[str, Field(pattern=r"^IMP-\d{8}-\d{3}$")]
    path: Annotated[str, Field(min_length=1)]
    before_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    after_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    recommendation: AuditRecommendation
    rationale: Annotated[str, Field(min_length=1)]
    event: dict[str, Any]
    sources: Annotated[tuple[dict[str, Any], ...], Field(min_length=1)]
    subject: dict[str, str]
    target: dict[str, str]
    declared_relation: dict[str, str]
    relevant_relations: tuple[dict[str, str], ...]
    rule_check: dict[str, Any]
    checks: dict[str, AuditCheck]
    issues: tuple[str, ...]
    changes: tuple[dict[str, Any], ...]
    preserved_note_fragments: Annotated[tuple[str, ...], Field(min_length=1)]
    human_review_required: Literal[True]


class ImpactAuditPacket(_StrictAuditModel):
    schema_version: Literal[1]
    audit_id: Annotated[str, Field(min_length=1)]
    audit_date: str
    baseline_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    scope: dict[str, Any]
    guardrails: tuple[str, ...]
    summary: dict[str, int]
    assertions: tuple[ImpactAuditEntry, ...]

    @field_validator("audit_date")
    @classmethod
    def validate_audit_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value
