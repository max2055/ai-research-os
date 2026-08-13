"""Web adapters for the Forecast, Valuation and Recommendation workbench."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_os.repositories.markdown import MarkdownDocument
from research_os.services.forecast_draft import prepare_forecast_draft
from research_os.services.forecast_lifecycle import prepare_open_forecast
from research_os.services.forecast_resolution import prepare_resolution_draft
from research_os.services.recommendation import prepare_recommendation_draft
from research_os.services.recommendation_lifecycle import (
    prepare_activate_recommendation,
    prepare_close_recommendation,
    prepare_supersede_recommendation,
    prepare_supersede_valuation,
)
from research_os.services.scenario_workflow import render_scenario_template
from research_os.services.validation import validate_repository
from research_os.services.valuation import prepare_valuation_draft
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)

_MAX_JSON_BYTES = 32_768


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DraftSpec(_StrictModel):
    spec: dict[str, Any] = Field(default_factory=dict, max_length=80)
    created_at: str = Field(min_length=10, max_length=10)


class ForecastOpenSpec(_StrictModel):
    forecast_id: str = Field(min_length=1, max_length=80)
    as_of: str = Field(min_length=10, max_length=10)


class ResolutionSpec(_StrictModel):
    spec: dict[str, Any] = Field(default_factory=dict, max_length=80)
    created_at: str = Field(min_length=10, max_length=10)


class RecommendationLifecycleSpec(_StrictModel):
    rec_id: str = Field(min_length=1, max_length=80)
    as_of: str = Field(min_length=10, max_length=10)
    reason: str = Field(default="", max_length=2000)


class SupersedeSpec(_StrictModel):
    old_id: str = Field(min_length=1, max_length=80)
    new_id: str = Field(min_length=1, max_length=80)
    as_of: str = Field(min_length=10, max_length=10)


class ScenarioSpec(_StrictModel):
    company_id: str = Field(min_length=1, max_length=80)
    as_of: str = Field(min_length=10, max_length=10)
    question: str = Field(default="", max_length=2000)


def _parse(raw: str, model: type[_StrictModel]) -> Any:
    if len(raw.encode("utf-8")) > _MAX_JSON_BYTES:
        raise ValueError("decision input exceeds 32768 byte limit")
    try:
        return model.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"invalid {model.__name__} fields") from exc


def _wrap(
    root: Path,
    *,
    actor: str,
    operation: str,
    target_type: str,
    target_id: str,
    writes: dict[Path, str],
    normalized_input: dict[str, Any],
    summary: dict[str, Any],
) -> PreparedRepositoryMutation:
    return prepare_repository_mutation(
        root,
        operation=operation,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        writes={path: content.encode("utf-8") for path, content in writes.items()},
        normalized_input=normalized_input,
        summary=summary,
    )


def _draft(
    root: Path,
    *,
    actor: str,
    raw: str,
    model: type[DraftSpec] | type[ResolutionSpec],
    operation: str,
    target_type: str,
    prepare: Callable[..., tuple[Path, str]],
) -> PreparedRepositoryMutation:
    parsed = _parse(raw, model)
    path, content = prepare(root, spec=parsed.spec, created_at=parsed.created_at)
    return _wrap(
        root,
        actor=actor,
        operation=operation,
        target_type=target_type,
        target_id=path.stem,
        writes={path: content},
        normalized_input={"spec": parsed.spec, "created_at": parsed.created_at},
        summary={"status_after": "draft", "review_status_after": "pending"},
    )


def prepare_forecast_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    return _draft(
        root,
        actor=actor,
        raw=spec_json,
        model=DraftSpec,
        operation="forecast.draft",
        target_type="forecast",
        prepare=prepare_forecast_draft,
    )


def prepare_forecast_opening(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, ForecastOpenSpec)
    writes = prepare_open_forecast(
        root, forecast_id=spec.forecast_id, actor=actor, as_of=spec.as_of
    )
    return _wrap(
        root,
        actor=actor,
        operation="forecast.open",
        target_type="forecast",
        target_id=spec.forecast_id,
        writes=writes,
        normalized_input=spec.model_dump(),
        summary={"status_after": "open", "review_status_required": "reviewed"},
    )


def prepare_forecast_resolution(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, ResolutionSpec)
    path, content = prepare_resolution_draft(
        root, spec=spec.spec, created_at=spec.created_at
    )
    forecast_id = str(spec.spec.get("forecast_id", ""))
    objects, _ = validate_repository(root)
    forecast = next((obj for obj in objects if obj.object_id == forecast_id), None)
    if forecast is None:
        raise ValueError(f"unknown Forecast {forecast_id}")
    document = MarkdownDocument.read(forecast.path)
    decision = str(spec.spec.get("decision", ""))
    document.set_metadata("status", "void" if decision == "void" else "resolved")
    document.set_metadata("updated_at", spec.created_at)
    document.set_metadata("resolved_at", str(spec.spec.get("resolved_at", "")))
    document.set_metadata("resolved_by", actor)
    return _wrap(
        root,
        actor=actor,
        operation="forecast.resolve",
        target_type="forecast_resolution",
        target_id=path.stem,
        writes={path: content, forecast.path: document.render()},
        normalized_input={"spec": spec.spec, "created_at": spec.created_at},
        summary={"status_after": "resolved", "forecast_id": forecast_id},
    )


def prepare_valuation_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    return _draft(
        root,
        actor=actor,
        raw=spec_json,
        model=DraftSpec,
        operation="valuation.draft",
        target_type="valuation_snapshot",
        prepare=prepare_valuation_draft,
    )


def prepare_recommendation_creation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    return _draft(
        root,
        actor=actor,
        raw=spec_json,
        model=DraftSpec,
        operation="recommendation.draft",
        target_type="recommendation",
        prepare=prepare_recommendation_draft,
    )


def prepare_recommendation_activation(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, RecommendationLifecycleSpec)
    writes = prepare_activate_recommendation(
        root, rec_id=spec.rec_id, actor=actor, as_of=spec.as_of
    )
    return _wrap(
        root,
        actor=actor,
        operation="recommendation.activate",
        target_type="recommendation",
        target_id=spec.rec_id,
        writes=writes,
        normalized_input=spec.model_dump(),
        summary={"status_after": "active"},
    )


def prepare_recommendation_closing(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, RecommendationLifecycleSpec)
    if not spec.reason:
        raise ValueError("close reason is required")
    writes = prepare_close_recommendation(
        root, rec_id=spec.rec_id, actor=actor, as_of=spec.as_of, reason=spec.reason
    )
    return _wrap(
        root,
        actor=actor,
        operation="recommendation.close",
        target_type="recommendation",
        target_id=spec.rec_id,
        writes=writes,
        normalized_input=spec.model_dump(),
        summary={"status_after": "closed"},
    )


def prepare_recommendation_supersession(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, SupersedeSpec)
    writes = prepare_supersede_recommendation(
        root,
        old_rec_id=spec.old_id,
        new_rec_id=spec.new_id,
        actor=actor,
        as_of=spec.as_of,
    )
    return _wrap(
        root,
        actor=actor,
        operation="recommendation.supersede",
        target_type="recommendation",
        target_id=spec.old_id,
        writes=writes,
        normalized_input=spec.model_dump(),
        summary={"status_after": "superseded", "successor": spec.new_id},
    )


def prepare_valuation_supersession(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, SupersedeSpec)
    writes = prepare_supersede_valuation(
        root,
        old_val_id=spec.old_id,
        new_val_id=spec.new_id,
        actor=actor,
        as_of=spec.as_of,
    )
    return _wrap(
        root,
        actor=actor,
        operation="valuation.supersede",
        target_type="valuation_snapshot",
        target_id=spec.old_id,
        writes=writes,
        normalized_input=spec.model_dump(),
        summary={"status_after": "superseded", "successor": spec.new_id},
    )


def prepare_scenario_template(
    root: Path, *, actor: str, spec_json: str
) -> PreparedRepositoryMutation:
    spec = _parse(spec_json, ScenarioSpec)
    content = render_scenario_template(
        company_id=spec.company_id, as_of=spec.as_of, question=spec.question
    )
    path = Path("05_Research/Scenarios") / f"SCN-{spec.company_id}-{spec.as_of}.md"
    return _wrap(
        root,
        actor=actor,
        operation="scenario.template",
        target_type="scenario_template",
        target_id=path.stem,
        writes={path: content},
        normalized_input=spec.model_dump(),
        summary={"status_after": "pending", "review_status_after": "pending"},
    )
