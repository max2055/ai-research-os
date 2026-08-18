"""Machine-checked map from legacy CLI leaves to the Web-only product."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import FastAPI

Disposition = Literal["web", "internal", "remove"]
Authority = Literal["read", "named_human", "operational_human", "automation"]


@dataclass(frozen=True)
class ProductCapability:
    cli_key: str
    owner: str
    disposition: Disposition
    web_routes: tuple[str, ...]
    authority: Authority
    delivery_feature: Literal["F-026", "F-027", "F-028", "F-029"]


def _capabilities(
    keys: tuple[str, ...],
    *,
    owner: str,
    route: str | tuple[str, ...],
    authority: Authority,
    feature: Literal["F-026", "F-027", "F-028", "F-029"],
) -> tuple[ProductCapability, ...]:
    return tuple(
        ProductCapability(
            cli_key=key,
            owner=owner,
            disposition="web",
            web_routes=(route,) if isinstance(route, str) else route,
            authority=authority,
            delivery_feature=feature,
        )
        for key in keys
    )


PRODUCT_CAPABILITIES = (
    *_capabilities(
        ("doctor", "validate", "index", "status", "scale"),
        owner="system_health",
        route=("/health", "/setup"),
        authority="read",
        feature="F-028",
    ),
    *_capabilities(
        ("metrics", "pipeline.metrics", "pilot.status"),
        owner="operations_metrics",
        route="/operations/metrics",
        authority="read",
        feature="F-028",
    ),
    *_capabilities(
        ("universe.list", "universe.coverage"),
        owner="universe",
        route="/companies",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("channels.list", "channels.check"),
        owner="channels",
        route="/pipeline/channels",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("channels.enable", "channels.disable"),
        owner="channels",
        route=(
            "/pipeline/channels/{channel_id}/change/preview",
            "/pipeline/channels/{channel_id}/change/commit",
        ),
        authority="named_human",
        feature="F-028",
    ),
    *_capabilities(
        ("discover.due",),
        owner="discovery",
        route="/operations/discovery",
        authority="read",
        feature="F-028",
    ),
    *_capabilities(
        ("discover.run",),
        owner="discovery",
        route=("/operations/discovery/run/preview", "/operations/discovery/run/commit"),
        authority="operational_human",
        feature="F-028",
    ),
    *_capabilities(
        ("candidates.list", "candidates.show"),
        owner="candidate_queue",
        route="/pipeline/queue",
        authority="read",
        feature="F-026",
    ),
    ProductCapability(
        "candidates.dismiss",
        "candidate_queue",
        "web",
        (
            "/pipeline/queue/{candidate_id}/dismiss/preview",
            "/pipeline/queue/{candidate_id}/dismiss/commit",
        ),
        "named_human",
        "F-026",
    ),
    ProductCapability(
        "candidates.restore",
        "candidate_queue",
        "web",
        (
            "/pipeline/queue/{candidate_id}/restore/preview",
            "/pipeline/queue/{candidate_id}/restore/commit",
        ),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "candidates.promote",
        "candidate_queue",
        "web",
        (
            "/pipeline/queue/{candidate_id}/promote/preview",
            "/pipeline/queue/{candidate_id}/promote/commit",
        ),
        "named_human",
        "F-027",
    ),
    *_capabilities(
        ("candidates.expire", "candidates.purge", "candidates.enrich"),
        owner="candidate_queue",
        route=("/pipeline/queue/batch/preview", "/pipeline/queue/batch/commit"),
        authority="operational_human",
        feature="F-027",
    ),
    *(
        ProductCapability(
            key,
            "sources",
            "web",
            ("/sources/new/preview", "/sources/new/commit"),
            "named_human",
            "F-027",
        )
        for key in ("new-source", "source.add")
    ),
    ProductCapability(
        "source.fetch",
        "sources",
        "web",
        (
            "/sources/{source_id}/fetch/preview",
            "/sources/{source_id}/fetch/commit",
        ),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "source.process",
        "sources",
        "web",
        (
            "/sources/{source_id}/process/preview",
            "/sources/{source_id}/process/commit",
        ),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "source.verify-assets",
        "sources",
        "web",
        ("/sources/{source_id}",),
        "read",
        "F-027",
    ),
    ProductCapability(
        "source.confirm-date",
        "sources",
        "web",
        (
            "/sources/{source_id}/confirm-date/preview",
            "/sources/{source_id}/confirm-date/commit",
        ),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "source.review",
        "reviews",
        "web",
        ("/reviews/apply/preview",),
        "named_human",
        "F-027",
    ),
    *_capabilities(
        (
            "source.discover.rss",
            "source.discover.github",
            "source.discover.arxiv",
            "source.discover.sec",
        ),
        owner="source_discovery",
        route="/operations/discovery/inspect",
        authority="operational_human",
        feature="F-028",
    ),
    *(
        ProductCapability(
            key,
            "evidence",
            "web",
            (
                "/evidence/events/new/preview",
                "/evidence/events/new/commit",
            ),
            "named_human",
            "F-027",
        )
        for key in ("new-event", "workflow.event")
    ),
    *(
        ProductCapability(
            key,
            "reports",
            "web",
            ("/reports/new/preview", "/reports/new/commit"),
            "named_human",
            "F-027",
        )
        for key in ("new-report", "workflow.report")
    ),
    ProductCapability(
        "new-entity",
        "entities",
        "web",
        (
            "/universe/entities/new/preview",
            "/universe/entities/new/commit",
        ),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "workflow.company-update",
        "entities",
        "web",
        (
            "/companies/{company_id}/update-proposals/new/preview",
            "/companies/{company_id}/update-proposals/new/commit",
        ),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "new-assertion",
        "ontology",
        "web",
        (
            "/ontology/assertions/new/preview",
            "/ontology/assertions/new/commit",
        ),
        "named_human",
        "F-027",
    ),
    *_capabilities(
        ("project.list", "project.status"),
        owner="projects",
        route="/projects",
        authority="read",
        feature="F-027",
    ),
    ProductCapability(
        "project.create",
        "projects",
        "web",
        ("/projects/new/preview", "/projects/new/commit"),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "project.advance-review",
        "projects",
        "web",
        (
            "/projects/{project_id}/advance/preview",
            "/projects/{project_id}/advance/commit",
        ),
        "named_human",
        "F-027",
    ),
    *_capabilities(
        ("review.queue",),
        owner="reviews",
        route="/reviews",
        authority="read",
        feature="F-027",
    ),
    ProductCapability(
        "review.apply",
        "reviews",
        "web",
        (
            "/reviews/apply/preview",
            "/reviews/apply/commit",
            "/reviews/cadence/preview",
            "/reviews/cadence/commit",
        ),
        "named_human",
        "F-027",
    ),
    *_capabilities(
        ("actions.list", "actions.overdue"),
        owner="actions",
        route="/operations/actions",
        authority="read",
        feature="F-027",
    ),
    ProductCapability(
        "actions.create",
        "actions",
        "web",
        (
            "/operations/actions/new/preview",
            "/operations/actions/new/commit",
        ),
        "named_human",
        "F-027",
    ),
    ProductCapability(
        "actions.close",
        "actions",
        "web",
        (
            "/operations/actions/{action_id}/close/preview",
            "/operations/actions/{action_id}/close/commit",
        ),
        "named_human",
        "F-027",
    ),
    *_capabilities(
        ("impact.graph", "impact.queue"),
        owner="impact",
        route="/impact",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("impact.propose",),
        owner="impact",
        route=("/impact/proposals/new/preview", "/impact/proposals/new/commit"),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("forecast.list", "forecast.status", "forecast.calibration"),
        owner="decision",
        route="/decision",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("forecast.draft",),
        owner="decision",
        route=("/decision/forecasts/new/preview", "/decision/forecasts/new/commit"),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("forecast.open", "forecast.resolve"),
        owner="decision",
        route=(
            "/decision/forecasts/change/preview",
            "/decision/forecasts/change/commit",
        ),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("valuation.list", "valuation.freshness"),
        owner="valuation",
        route="/decision/valuations",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("valuation.draft", "valuation.supersede"),
        owner="valuation",
        route=(
            "/decision/valuations/new/preview",
            "/decision/valuations/new/commit",
            "/decision/valuations/change/preview",
            "/decision/valuations/change/commit",
        ),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("scenario.extract", "scenario.template"),
        owner="scenario",
        route=("/decision/scenarios/new/preview", "/decision/scenarios/new/commit"),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("recommendation.list", "recommendation.gate", "recommendation.freshness"),
        owner="recommendation",
        route="/decision/recommendations",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        (
            "recommendation.draft",
            "recommendation.activate",
            "recommendation.close",
            "recommendation.supersede",
        ),
        owner="recommendation",
        route=(
            "/decision/recommendations/new/preview",
            "/decision/recommendations/new/commit",
            "/decision/recommendations/change/preview",
            "/decision/recommendations/change/commit",
        ),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("modes.list", "modes.show", "modes.check"),
        owner="analysis",
        route="/analysis/modes",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("analyze.show", "analyze.compare", "analyze.metrics"),
        owner="analysis",
        route="/analysis/runs",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("analyze.run", "analyze.replay", "analyze.eval"),
        owner="analysis",
        route=(
            "/analysis/runs/new/preview",
            "/analysis/runs/new/commit",
            "/analysis/runs/{run_id}/replay/preview",
            "/analysis/runs/{run_id}/replay/commit",
        ),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("analyze.propose-thesis",),
        owner="analysis",
        route=(
            "/analysis/thesis-proposals/new/preview",
            "/analysis/thesis-proposals/new/commit",
        ),
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("jobs.list",),
        owner="jobs",
        route=("/operations/jobs", "/operations/schedules"),
        authority="read",
        feature="F-028",
    ),
    *_capabilities(
        ("jobs.run",),
        owner="jobs",
        route=(
            "/operations/jobs/run/preview",
            "/operations/jobs/run/commit",
            "/operations/schedules/new/preview",
            "/operations/schedules/new/commit",
            "/operations/schedules/{schedule_id}/edit/preview",
            "/operations/schedules/edit/commit",
            "/operations/schedules/{schedule_id}/pause/preview",
            "/operations/schedules/{schedule_id}/resume/preview",
            "/operations/schedules/{schedule_id}/run-now/preview",
            "/operations/schedules/action/commit",
        ),
        authority="operational_human",
        feature="F-028",
    ),
    *_capabilities(
        ("brief.daily",),
        owner="brief",
        route="/brief",
        authority="operational_human",
        feature="F-028",
    ),
    *_capabilities(
        ("backup.candidate", "backup.durable.create"),
        owner="backup",
        route=(
            "/operations/backups",
            "/operations/backups/new",
            "/operations/backups/{backup_kind}/preview",
        ),
        authority="operational_human",
        feature="F-028",
    ),
    *_capabilities(
        ("backup.durable.verify-remote", "backup.durable.restore"),
        owner="recovery",
        route="/operations/recovery",
        authority="operational_human",
        feature="F-028",
    ),
    *_capabilities(
        ("benchmark", "benchmark-candidates"),
        owner="benchmarks",
        route="/operations/benchmarks",
        authority="operational_human",
        feature="F-028",
    ),
    *_capabilities(
        ("release.check",),
        owner="release",
        route="/health/release",
        authority="read",
        feature="F-028",
    ),
    *_capabilities(
        ("export",),
        owner="exports",
        route="/operations/exports",
        authority="operational_human",
        feature="F-028",
    ),
    ProductCapability(
        "ui",
        "web_shell",
        "web",
        ("/", "/llm/config", "/llm/models", "/llm/test"),
        "operational_human",
        "F-029",
    ),
)


def registered_mutation_routes(app: FastAPI) -> frozenset[str]:
    """Return exact non-GET application routes for capability auditing."""

    return frozenset(
        path
        for route in app.routes
        if (path := str(getattr(route, "path", "")))
        and (set(getattr(route, "methods", set())) - {"HEAD", "OPTIONS"}) - {"GET"}
    )
