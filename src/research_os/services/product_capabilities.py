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
    route: str,
    authority: Authority,
    feature: Literal["F-026", "F-027", "F-028", "F-029"],
) -> tuple[ProductCapability, ...]:
    return tuple(
        ProductCapability(
            cli_key=key,
            owner=owner,
            disposition="web",
            web_routes=(route,),
            authority=authority,
            delivery_feature=feature,
        )
        for key in keys
    )


PRODUCT_CAPABILITIES = (
    *_capabilities(
        ("doctor", "validate", "index", "status", "scale"),
        owner="system_health",
        route="/health",
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
        route="/pipeline/channels/{channel_id}/change/preview",
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
        route="/operations/discovery/run/preview",
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
        route="/pipeline/queue/batch/preview",
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
    *_capabilities(
        ("new-entity", "workflow.company-update"),
        owner="entities",
        route="/universe/entities/new",
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("new-assertion",),
        owner="ontology",
        route="/ontology/assertions/new",
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("project.list", "project.status"),
        owner="projects",
        route="/projects",
        authority="read",
        feature="F-027",
    ),
    *_capabilities(
        ("project.create",),
        owner="projects",
        route="/projects/new",
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("project.advance-review",),
        owner="projects",
        route="/projects/{project_id}/advance/preview",
        authority="named_human",
        feature="F-027",
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
        ("/reviews/apply/preview", "/reviews/apply/commit"),
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
    *_capabilities(
        ("actions.create", "actions.close"),
        owner="actions",
        route="/operations/actions/change/preview",
        authority="named_human",
        feature="F-027",
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
        route="/impact/proposals/new",
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
        route="/decision/forecasts/new",
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("forecast.open", "forecast.resolve"),
        owner="decision",
        route="/decision/forecasts/change/preview",
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
        route="/decision/valuations/change/preview",
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("scenario.extract", "scenario.template"),
        owner="scenario",
        route="/decision/scenarios",
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
        route="/decision/recommendations/change/preview",
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
        route="/analysis/runs/new",
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("analyze.propose-thesis",),
        owner="analysis",
        route="/analysis/thesis-proposals/new",
        authority="named_human",
        feature="F-027",
    ),
    *_capabilities(
        ("jobs.list",),
        owner="jobs",
        route="/operations/jobs",
        authority="read",
        feature="F-028",
    ),
    *_capabilities(
        ("jobs.run",),
        owner="jobs",
        route="/operations/jobs/run/preview",
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
        route="/operations/backups/new",
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
