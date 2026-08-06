#!/usr/bin/env python3
"""Single command-line entry point for AI Research OS automation."""

from __future__ import annotations

import argparse
import hashlib
import platform
import sys
from datetime import date
from pathlib import Path

from research_os.adapters.discovery import (
    ArxivDiscoveryAdapter,
    DiscoveryAdapter,
    GitHubReleaseDiscoveryAdapter,
    RSSDiscoveryAdapter,
    SECDiscoveryAdapter,
    candidates_json,
)
from research_os.adapters.file import FileCaptureAdapter
from research_os.adapters.url import UrlCaptureAdapter
from research_os.repositories.transaction import TransactionError
from research_os.runtime import product as runtime


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="AI Research OS automation")
    parser.add_argument("--root", type=Path, default=default_root)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "doctor",
        help="check runtime, repository health and recoverability",
    )
    validate = subparsers.add_parser("validate", help="validate the repository")
    validate.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as validation failures",
    )
    index = subparsers.add_parser("index", help="check or rebuild indexes")
    mode = index.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="check for index drift")
    mode.add_argument("--apply", action="store_true", help="write canonical indexes")
    index.add_argument("--project", help="scope indexes to one Project ID")

    def add_common_draft_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--title", required=True)
        command.add_argument("--slug", required=True)
        command.add_argument("--date", default=date.today().isoformat())
        command.add_argument("--tags", default="")
        command.add_argument("--project", default="PRJ-001")
        command.add_argument("--apply", action="store_true")

    source = subparsers.add_parser("new-source", help="preview or create a Source")
    add_common_draft_arguments(source)
    source.add_argument("--source-type", required=True)
    source.add_argument("--publisher", required=True)
    source.add_argument("--published-at", required=True)
    source_location = source.add_mutually_exclusive_group(required=True)
    source_location.add_argument("--url", default="")
    source_location.add_argument("--local-path", default="")
    source.add_argument("--source-grade", required=True)
    source.add_argument("--companies", default="")
    source.add_argument("--technologies", default="")
    source.add_argument("--products", default="")

    event = subparsers.add_parser("new-event", help="preview or create an Event")
    add_common_draft_arguments(event)
    event.add_argument("--event-date", required=True)
    event.add_argument("--source-ids", required=True)
    event.add_argument("--companies", default="")
    event.add_argument("--technologies", default="")
    event.add_argument("--products", default="")
    event.add_argument("--thesis-links", default="")
    event.add_argument("--confidence", type=float, required=True)

    report = subparsers.add_parser("new-report", help="preview or create a Report")
    add_common_draft_arguments(report)
    report.add_argument("--period-start", required=True)
    report.add_argument("--period-end", required=True)
    report.add_argument("--thesis-ids", default="")
    report.add_argument("--evidence-ids", required=True)

    entity = subparsers.add_parser(
        "new-entity",
        help="preview or create a v0.3 Sector or Company entity",
    )
    # Entities are cross-project Universe primitives (A-005 §2): project_ids
    # default to empty, NOT PRJ-001. Do not reuse add_common_draft_arguments
    # (its --project default of PRJ-001 would leak into every entity).
    entity.add_argument("--title", required=True)
    entity.add_argument("--slug", required=True)
    entity.add_argument("--date", default=date.today().isoformat())
    entity.add_argument("--tags", default="")
    entity.add_argument("--project", default="")
    entity.add_argument("--apply", action="store_true")
    entity.add_argument(
        "--type",
        choices=("sector", "company"),
        required=True,
        help="entity type (v0.3; schema_version=2)",
    )
    entity.add_argument("--definition", default="")
    entity.add_argument("--in-scope", default="")
    entity.add_argument("--out-of-scope", default="")
    entity.add_argument("--value-chain-position", default="")
    entity.add_argument("--key-inputs", default="")
    entity.add_argument("--key-outputs", default="")
    entity.add_argument("--key-metrics", default="")
    entity.add_argument("--core-company-ids", default="")
    entity.add_argument("--tracked-company-ids", default="")
    entity.add_argument("--source-channel-ids", default="")
    entity.add_argument("--evidence-ids", default="")
    entity.add_argument("--sector-ids", default="", help="company: SEG-ID references")
    entity.add_argument("--region-primary", default="", help="company: REG-<region>")
    entity.add_argument(
        "--coverage-tier",
        default="",
        help="company: core|tracked|discovery",
    )
    entity.add_argument("--legal-name", default="", help="company")
    entity.add_argument("--company-stage", default="", help="company")
    entity.add_argument("--headquarters", default="", help="company")
    entity.add_argument("--aliases", default="", help="company")

    assertion = subparsers.add_parser(
        "new-assertion",
        help="preview or create an Ontology Assertion (REL-*)",
    )
    assertion.add_argument("--subject", required=True)
    assertion.add_argument("--predicate", required=True)
    assertion.add_argument("--object", dest="object_id", required=True)
    assertion.add_argument("--date", default=date.today().isoformat())
    assertion.add_argument("--valid-from", default=date.today().isoformat())
    assertion.add_argument("--as-of", default=date.today().isoformat())
    assertion.add_argument("--title", default="")
    assertion.add_argument("--scope", default="")
    assertion.add_argument("--confidence", type=float, default=0.5)
    assertion.add_argument("--project", default="")
    assertion.add_argument("--apply", action="store_true")

    status = subparsers.add_parser(
        "status",
        help="show the read-only research queue and health",
    )
    status.add_argument("--project", help="scope status to one Project ID")
    metrics = subparsers.add_parser("metrics", help="calculate quality metrics")
    metrics.add_argument("--as-of", default=date.today().isoformat())
    metrics.add_argument("--format", choices=("markdown", "json"), default="markdown")
    metrics.add_argument("--project", help="scope metrics to one Project ID")
    metrics_mode = metrics.add_mutually_exclusive_group()
    metrics_mode.add_argument(
        "--snapshot",
        action="store_true",
        help="write an immutable JSON snapshot; refuses overwrite",
    )
    metrics_mode.add_argument(
        "--compare",
        type=Path,
        help="compare a prior JSON snapshot with current repository metrics",
    )
    universe = subparsers.add_parser(
        "universe", help="inspect the Universe (A-014 registry CLI)"
    )
    universe_commands = universe.add_subparsers(
        dest="universe_command", required=True
    )
    universe_commands.add_parser("list", help="list companies (read-only)")
    universe_commands.add_parser(
        "coverage", help="Universe coverage metrics (A-018)"
    )

    channels = subparsers.add_parser(
        "channels", help="manage Source Channels (B-006 Registry CLI)"
    )
    channels_commands = channels.add_subparsers(
        dest="channel_command", required=True
    )
    channels_commands.add_parser("list", help="list channels (read-only)")
    channels_commands.add_parser(
        "check", help="show which channels are schedulable (reviewed + enabled)"
    )
    channel_enable = channels_commands.add_parser(
        "enable", help="enable a channel for scheduling"
    )
    channel_enable.add_argument("--id", required=True)
    channel_enable.add_argument("--apply", action="store_true")
    channel_disable = channels_commands.add_parser(
        "disable", help="disable a channel"
    )
    channel_disable.add_argument("--id", required=True)
    channel_disable.add_argument("--apply", action="store_true")

    export = subparsers.add_parser("export", help="export derived ontology views")
    export.add_argument("--format", choices=("jsonl", "sqlite"), required=True)
    export.add_argument("--output", type=Path)
    export.add_argument("--apply", action="store_true")
    discover = subparsers.add_parser(
        "discover", help="run bounded discovery for a Channel (B-007)"
    )
    discover_commands = discover.add_subparsers(dest="discover_command", required=True)
    discover_run = discover_commands.add_parser(
        "run", help="run discovery for one Channel"
    )
    discover_run.add_argument("--channel", required=True)
    discover_run.add_argument("--apply", action="store_true")
    discover_due = discover_commands.add_parser(
        "due", help="list channels due for discovery"
    )
    discover_due.add_argument("--as-of", default="")
    candidates = subparsers.add_parser(
        "candidates", help="Candidate Queue (B-018)"
    )
    candidates_commands = candidates.add_subparsers(
        dest="candidates_command", required=True
    )
    candidates_list = candidates_commands.add_parser(
        "list", help="list candidates, highest priority first"
    )
    candidates_list.add_argument("--status", default="new")
    candidates_list.add_argument("--channel", help="filter by source channel id")
    candidates_list.add_argument("--entity", help="filter by resolved entity id")
    candidates_list.add_argument(
        "--tier",
        choices=("core", "tracked", "discovery"),
        help="filter by resolved company coverage tier",
    )
    candidates_list.add_argument(
        "--min-priority", type=float, help="only candidates at/above this score"
    )
    candidates_list.add_argument("--limit", type=int, default=50)
    candidates_show = candidates_commands.add_parser(
        "show", help="show one candidate in detail"
    )
    candidates_show.add_argument("--id", required=True)
    candidates_promote = candidates_commands.add_parser(
        "promote", help="promote a candidate to a permanent Source (B-019)"
    )
    candidates_promote.add_argument("--id", required=True)
    candidates_promote.add_argument(
        "--actor",
        required=True,
        help="who is promoting (recorded in the action log)",
    )
    candidates_promote.add_argument(
        "--source-type",
        help="override Source type (default from channel)",
    )
    candidates_promote.add_argument(
        "--source-grade",
        help="override Source grade (default from channel)",
    )
    candidates_promote.add_argument(
        "--publisher", help="override publisher (default from candidate/channel)"
    )
    candidates_promote.add_argument("--project", default="PRJ-001")
    candidates_promote.add_argument(
        "--user-agent",
        help="compliant User-Agent (Name Contact@email); required for sec.gov",
    )
    candidates_promote.add_argument("--apply", action="store_true")
    candidates_dismiss = candidates_commands.add_parser(
        "dismiss", help="dismiss a candidate with a reason (B-020)"
    )
    candidates_dismiss.add_argument("--id", required=True)
    candidates_dismiss.add_argument("--reason", required=True)
    candidates_dismiss.add_argument("--actor", required=True)
    candidates_dismiss.add_argument("--apply", action="store_true")
    candidates_restore = candidates_commands.add_parser(
        "restore", help="return a dismissed/expired candidate to the queue"
    )
    candidates_restore.add_argument("--id", required=True)
    candidates_restore.add_argument("--actor", required=True)
    candidates_restore.add_argument("--apply", action="store_true")
    candidates_expire = candidates_commands.add_parser(
        "expire", help="mark candidates past retention as expired (B-020)"
    )
    candidates_expire.add_argument("--channel", help="limit to one source channel")
    candidates_expire.add_argument("--as-of", default="")
    candidates_expire.add_argument("--apply", action="store_true")
    candidates_purge = candidates_commands.add_parser(
        "purge",
        help="delete dismissed/expired candidate rows, keep audit actions",
    )
    candidates_purge.add_argument("--apply", action="store_true")
    candidates_enrich = candidates_commands.add_parser(
        "enrich",
        help="backfill entity/sector/score proposals for unscored candidates",
    )
    candidates_enrich.add_argument("--apply", action="store_true")
    impact = subparsers.add_parser("impact", help="show ontology relationships")
    impact.add_argument("--id", required=True)
    impact.add_argument("--depth", type=int, default=1)
    subparsers.add_parser("scale", help="assess scale triggers and storage mode")

    project = subparsers.add_parser("project", help="manage research Projects")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_commands.add_parser("list", help="list Projects")
    project_status = project_commands.add_parser("status", help="show Project status")
    project_status.add_argument("--id", required=True)
    project_create = project_commands.add_parser("create", help="create Project draft")
    project_create.add_argument("--title", required=True)
    project_create.add_argument("--slug", required=True)
    project_create.add_argument("--date", default=date.today().isoformat())
    project_create.add_argument("--owner", required=True)
    project_create.add_argument("--question", required=True)
    project_create.add_argument("--charter-path", required=True)
    project_create.add_argument("--queue-path", required=True)
    project_create.add_argument("--review-cadence", required=True)
    project_create.add_argument("--next-review-date", required=True)
    project_create.add_argument("--tags", default="")
    project_create.add_argument("--apply", action="store_true")

    review = subparsers.add_parser("review", help="manage Review Decisions")
    review_commands = review.add_subparsers(dest="review_command", required=True)
    review_queue = review_commands.add_parser("queue", help="show Review Queue")
    review_queue.add_argument("--project")
    review_queue.add_argument(
        "--type",
        choices=(
            "source",
            "event",
            "thesis",
            "company",
            "report",
            "sector",
            "ontology_assertion",
            "product",
            "security",
            "source_channel",
        ),
    )
    review_queue.add_argument(
        "--status",
        choices=("pending", "reviewed", "rejected", "superseded"),
        default="pending",
    )
    review_apply = review_commands.add_parser(
        "apply",
        help="preview or atomically apply a Review Decision",
    )
    review_apply.add_argument("--targets", required=True)
    review_apply.add_argument(
        "--decision",
        choices=("approve", "edit", "reject"),
        required=True,
    )
    review_apply.add_argument("--reviewer", required=True)
    review_apply.add_argument("--date", default=date.today().isoformat())
    review_apply.add_argument("--notes", default="")
    review_apply.add_argument("--apply", action="store_true")

    actions = subparsers.add_parser("actions", help="manage research Actions")
    action_commands = actions.add_subparsers(dest="action_command", required=True)
    action_list = action_commands.add_parser("list", help="list Actions")
    action_list.add_argument("--project")
    action_list.add_argument("--owner")
    action_list.add_argument(
        "--status",
        choices=("open", "in_progress", "done", "cancelled"),
    )
    action_overdue = action_commands.add_parser("overdue", help="list overdue Actions")
    action_overdue.add_argument("--project")
    action_overdue.add_argument("--owner")
    action_overdue.add_argument("--as-of", default=date.today().isoformat())
    action_create = action_commands.add_parser("create", help="create an Action")
    action_create.add_argument("--title", required=True)
    action_create.add_argument("--owner", required=True)
    action_create.add_argument("--date", default=date.today().isoformat())
    action_create.add_argument("--due-date", required=True)
    action_create.add_argument("--success-evidence", required=True)
    action_create.add_argument("--projects", required=True)
    action_create.add_argument("--source-review-id")
    action_create.add_argument("--apply", action="store_true")
    action_close = action_commands.add_parser("close", help="close an Action")
    action_close.add_argument("--id", required=True)
    action_close.add_argument("--date", default=date.today().isoformat())
    action_close.add_argument("--success-evidence", required=True)
    action_close.add_argument("--apply", action="store_true")

    source_ops = subparsers.add_parser(
        "source",
        help="capture, process and review Sources",
    )
    source_commands = source_ops.add_subparsers(
        dest="source_command",
        required=True,
    )
    source_add = source_commands.add_parser(
        "add",
        help="capture and create a Source",
    )
    source_add.add_argument("--title", required=True)
    source_add.add_argument("--slug", required=True)
    source_add.add_argument("--date", default=date.today().isoformat())
    source_add.add_argument("--source-type", required=True)
    source_add.add_argument("--publisher", required=True)
    source_add.add_argument("--published-at", required=True)
    source_add_locator = source_add.add_mutually_exclusive_group(required=True)
    source_add_locator.add_argument("--url")
    source_add_locator.add_argument("--file", type=Path)
    source_add.add_argument("--source-grade", required=True)
    source_add.add_argument("--companies", default="")
    source_add.add_argument("--technologies", default="")
    source_add.add_argument("--products", default="")
    source_add.add_argument("--tags", default="")
    source_add.add_argument("--projects", default="PRJ-001")
    source_add.add_argument("--allow-duplicate", action="store_true")
    source_add.add_argument(
        "--user-agent",
        default="",
        help="compliant User-Agent (Name Contact@email); required for sec.gov",
    )
    source_add.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help="override capture size limit (default 20MiB; SEC 20-F larger)",
    )
    source_add.add_argument("--apply", action="store_true")

    source_fetch = source_commands.add_parser(
        "fetch",
        help="capture a new immutable version for an existing Source",
    )
    source_fetch.add_argument("--id", required=True)
    source_fetch_locator = source_fetch.add_mutually_exclusive_group(required=True)
    source_fetch_locator.add_argument("--url")
    source_fetch_locator.add_argument("--file", type=Path)
    source_fetch.add_argument("--allow-duplicate", action="store_true")
    source_fetch.add_argument("--apply", action="store_true")

    source_process = source_commands.add_parser(
        "process",
        help="extract text from the latest archived asset",
    )
    source_process.add_argument("--id", required=True)
    source_process.add_argument("--apply", action="store_true")

    source_commands.add_parser(
        "verify-assets",
        help="verify archived Source assets and hashes",
    )

    source_date = source_commands.add_parser(
        "confirm-date",
        help="human-confirm a proposed publication date",
    )
    source_date.add_argument("--id", required=True)
    source_date.add_argument("--date", required=True)
    source_date.add_argument("--override-proposal", action="store_true")
    source_date.add_argument("--apply", action="store_true")

    source_review = source_commands.add_parser(
        "review",
        help="apply a Source-level Review Decision",
    )
    source_review.add_argument("--id", required=True)
    source_review.add_argument(
        "--decision",
        choices=("approve", "edit", "reject"),
        required=True,
    )
    source_review.add_argument("--reviewer", required=True)
    source_review.add_argument("--date", default=date.today().isoformat())
    source_review.add_argument("--notes", default="")
    source_review.add_argument("--apply", action="store_true")

    source_discover = source_commands.add_parser(
        "discover",
        help="discover bounded Source candidates without writing",
    )
    discover_commands = source_discover.add_subparsers(
        dest="discover_command",
        required=True,
    )
    discover_rss = discover_commands.add_parser("rss", help="inspect one RSS/Atom feed")
    discover_rss.add_argument("--feed-url", required=True)
    discover_rss.add_argument("--allow-hosts", required=True)
    discover_rss.add_argument("--publisher", required=True)
    discover_rss.add_argument("--limit", type=int, default=20)
    discover_github = discover_commands.add_parser(
        "github",
        help="inspect releases for one GitHub repository",
    )
    discover_github.add_argument("--repository", required=True)
    discover_github.add_argument("--limit", type=int, default=20)
    discover_arxiv = discover_commands.add_parser(
        "arxiv",
        help="run one explicit bounded arXiv query",
    )
    discover_arxiv.add_argument("--query", required=True)
    discover_arxiv.add_argument("--limit", type=int, default=20)
    discover_sec = discover_commands.add_parser(
        "sec",
        help="inspect filings for one CIK and explicit form allowlist",
    )
    discover_sec.add_argument("--cik", required=True)
    discover_sec.add_argument("--forms", required=True)
    discover_sec.add_argument("--user-agent", required=True)
    discover_sec.add_argument("--limit", type=int, default=20)

    workflow = subparsers.add_parser(
        "workflow",
        help="generate reviewable Event, Report and knowledge proposals",
    )
    workflow_commands = workflow.add_subparsers(
        dest="workflow_command",
        required=True,
    )
    workflow_event = workflow_commands.add_parser(
        "event",
        help="generate an anchored Event draft from a JSON spec",
    )
    workflow_event.add_argument("--spec", type=Path, required=True)
    workflow_event.add_argument("--apply", action="store_true")
    workflow_report = workflow_commands.add_parser(
        "report",
        help="synthesize reviewed Evidence into a Report draft",
    )
    workflow_report.add_argument("--spec", type=Path, required=True)
    workflow_report.add_argument("--baseline", type=Path)
    workflow_report.add_argument("--apply", action="store_true")
    workflow_company = workflow_commands.add_parser(
        "company-update",
        help="propose a Company update from reviewed Evidence",
    )
    workflow_company.add_argument("--company", required=True)
    workflow_company.add_argument("--events", required=True)
    workflow_company.add_argument("--date", default=date.today().isoformat())
    workflow_company.add_argument("--apply", action="store_true")

    ui = subparsers.add_parser("ui", help="start the local read-only Dashboard")
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8765)

    jobs = subparsers.add_parser("jobs", help="run idempotent scheduler jobs")
    job_commands = jobs.add_subparsers(dest="job_command", required=True)
    job_list = job_commands.add_parser("list", help="list Job Run records")
    job_list.add_argument("--project")
    job_list.add_argument("--status", choices=("success", "failed"))
    job_run = job_commands.add_parser("run", help="execute and record one job")
    job_run.add_argument(
        "name",
        choices=(
            "validate",
            "indexes",
            "metrics",
            "source-process",
            "refresh",
            "discover",
            "expire",
        ),
    )
    job_run.add_argument("--project")
    job_run.add_argument("--target")
    job_run.add_argument("--as-of")

    benchmark = subparsers.add_parser(
        "benchmark",
        help="run the synthetic repository scale benchmark",
    )
    benchmark.add_argument("--sources", type=int, default=1000)
    benchmark.add_argument("--events", type=int, default=500)
    benchmark.add_argument("--max-seconds", type=float, default=10.0)
    release = subparsers.add_parser(
        "release",
        help="evaluate product release gates without changing the repository",
    )
    release_commands = release.add_subparsers(
        dest="release_command",
        required=True,
    )
    release_check = release_commands.add_parser(
        "check",
        help="show v0.2 release readiness and explicit blockers",
    )
    release_check.add_argument("--project", default="PRJ-002")
    return parser.parse_args()


def command_validate(root: Path, strict: bool) -> int:
    objects, findings = runtime.validate_repository(root)
    for finding in findings:
        print(finding.format(root.resolve()))
    counts = runtime.count_by_type(objects)
    count_text = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    errors = sum(finding.level == "error" for finding in findings)
    warnings = sum(finding.level == "warning" for finding in findings)
    print(f"Objects: {count_text}")
    print(f"Findings: errors={errors}, warnings={warnings}")
    if errors or (strict and warnings):
        return 1
    print("PASS: repository validation succeeded")
    return 0


def command_index(
    root: Path,
    apply: bool,
    project_id: str | None = None,
) -> int:
    root = root.resolve()
    objects, findings = runtime.validate_repository(root)
    errors = [finding for finding in findings if finding.level == "error"]
    if errors:
        for finding in errors:
            print(finding.format(root))
        print("ERROR: repository validation failed; indexes were not changed")
        return 1
    rendered = (
        runtime.render_project_indexes(objects, project_id)
        if project_id
        else runtime.render_indexes(objects)
    )
    drift = runtime.index_drift(root, rendered)
    if not apply:
        if drift:
            for path in drift:
                print(f"DRIFT {path}")
            print(f"FAIL: {len(drift)} index files differ from canonical output")
            return 1
        print("PASS: all indexes match canonical output")
        return 0
    runtime.apply_indexes(root, rendered)
    print(f"APPLIED: {len(rendered)} canonical index files written")
    return 0


def command_doctor(root: Path) -> int:
    root = root.resolve()
    objects, findings = runtime.validate_repository(root)
    errors = [finding for finding in findings if finding.level == "error"]
    warnings = [finding for finding in findings if finding.level == "warning"]
    drift = runtime.index_drift(root, runtime.render_indexes(objects))
    asset_results = runtime.verify_source_assets(root)
    asset_failures = [
        result
        for result in asset_results
        if result.status in {"missing", "invalid", "hash_mismatch"}
    ]
    try:
        from research_os.repositories.markdown import validate_documents

        schema_documents, schema_errors = validate_documents(root)
        product_dependencies = True
    except ModuleNotFoundError:
        schema_documents, schema_errors = [], []
        product_dependencies = False
    checks = {
        "Python >= 3.12": sys.version_info >= (3, 12),
        "Product dependencies": product_dependencies,
        "Repository root": (root / "README.md").is_file(),
        "Git baseline": (root / ".git").exists(),
        "Validation errors = 0": not errors,
        "Formal Schema errors = 0": product_dependencies and not schema_errors,
        "Index drift = 0": not drift,
        "Source asset integrity": not asset_failures,
    }
    print("# AI Research OS Doctor")
    print(f"Python: {platform.python_version()}")
    print(f"Root: {root}")
    for label, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {label}")
    print(
        f"Objects: {len(objects)}; schema objects: {len(schema_documents)}; "
        f"warnings: {len(warnings)}; drift files: {len(drift)}"
        f"; asset failures: {len(asset_failures)}"
    )
    return 0 if all(checks.values()) else 1


def output_draft(root: Path, relative: Path, content: str, apply: bool) -> int:
    if not apply:
        print(f"DRY-RUN target={relative}")
        print(content, end="")
        print("DRY-RUN: no files changed; rerun with --apply to create")
        return 0
    target = runtime.write_new_file(root.resolve(), relative, content)
    print(f"CREATED: {target.relative_to(root.resolve())}")
    return 0


def selected_capture_adapter(
    url: str | None,
    file_path: Path | None,
    user_agent: str | None = None,
    max_bytes: int | None = None,
) -> UrlCaptureAdapter | FileCaptureAdapter:
    if url:
        if max_bytes is None:
            return UrlCaptureAdapter(url, user_agent=user_agent)
        return UrlCaptureAdapter(url, user_agent=user_agent, max_bytes=max_bytes)
    if file_path:
        return FileCaptureAdapter(file_path)
    raise ValueError("URL or file is required")


def main() -> int:
    args = parse_args()
    if args.command == "doctor":
        return command_doctor(args.root)
    if args.command == "validate":
        return command_validate(args.root, args.strict)
    if args.command == "index":
        return command_index(args.root, args.apply, args.project)
    if args.command == "status":
        print(
            runtime.render_status(args.root.resolve(), args.project),
            end="",
        )
        return 0
    if args.command == "metrics":
        try:
            values = runtime.research_metrics(
                args.root.resolve(),
                args.as_of,
                args.project,
            )
            if args.snapshot:
                path = runtime.write_metrics_snapshot(args.root.resolve(), values)
                print(f"CREATED: {path.relative_to(args.root.resolve())}")
                return 0
            if args.compare:
                baseline = runtime.load_metrics_snapshot(args.compare.resolve())
                print(runtime.render_metrics_comparison(baseline, values), end="")
                return 0
            if args.format == "json":
                print(runtime.metrics_json(values), end="")
            else:
                print(runtime.render_metrics_markdown(values), end="")
            return 0
        except (FileExistsError, OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2

    if args.command == "discover":
        try:
            if args.discover_command == "run":
                discovery_result = runtime.run_discovery(
                    args.root.resolve(),
                    args.channel,
                    apply=args.apply,
                )
                print(runtime.render_discovery_result(discovery_result), end="")
                return 0
            if args.discover_command == "due":
                due = runtime.due_channels(
                    args.root.resolve(),
                    as_of=args.as_of or None,
                )
                for item in due:
                    print(item["channel_id"])
                return 0
        except (ValueError, OSError) as exc:
            print(f"ERROR: {exc}")
            return 2

    if args.command == "universe":
        if args.universe_command == "coverage":
            coverage = runtime.universe_coverage(args.root.resolve())
            print(runtime.render_universe_coverage(coverage), end="")
            return 0
        if args.universe_command == "list":
            objects, _ = runtime.validate_repository(args.root.resolve())
            companies = sorted(
                obj.object_id for obj in objects if obj.object_type == "company"
            )
            for company_id in companies:
                print(company_id)
            return 0

    if args.command == "channels":
        try:
            if args.channel_command == "list":
                channel_rows_result = runtime.channel_rows(args.root.resolve())
                print(runtime.render_channel_list(channel_rows_result), end="")
                return 0
            if args.channel_command == "check":
                channel_rows_result = runtime.channel_rows(args.root.resolve())
                print(runtime.render_channel_check(channel_rows_result), end="")
                return 0
            if args.channel_command in ("enable", "disable"):
                enabled = args.channel_command == "enable"
                path = runtime.set_channel_enabled(
                    args.root.resolve(), args.id, enabled
                )
                verb = "enabled" if enabled else "disabled"
                if args.apply:
                    from research_os.repositories.markdown import (
                        MarkdownDocument,
                    )

                    document = MarkdownDocument.read(path)
                    document.set_metadata("enabled", enabled)
                    path.write_text(document.render(), encoding="utf-8")
                    print(f"APPLIED: {path.relative_to(args.root.resolve())}")
                    return 0
                print(
                    f"DRY-RUN: would {verb} {args.id} "
                    f"(rerun with --apply)"
                )
                return 0
        except (ValueError, OSError) as exc:
            print(f"ERROR: {exc}")
            return 2

    if args.command == "candidates":
        try:
            if args.candidates_command == "list":
                queue = runtime.queue_rows(
                    args.root.resolve(),
                    status=args.status,
                    channel_id=args.channel,
                    entity_id=args.entity,
                    tier=args.tier,
                    min_priority=args.min_priority,
                    limit=args.limit,
                )
                print(runtime.render_candidate_list(queue), end="")
                return 0
            if args.candidates_command == "show":
                detail = runtime.queue_show(
                    args.root.resolve(),
                    args.id,
                )
                if detail is None:
                    print(f"ERROR: unknown candidate {args.id}")
                    return 2
                print(runtime.render_candidate_detail(detail), end="")
                return 0
            if args.candidates_command == "promote":
                promote_plan = runtime.prepare_promote(
                    args.root.resolve(),
                    args.id,
                    actor=args.actor,
                    source_type=args.source_type,
                    source_grade=args.source_grade,
                    publisher=args.publisher,
                    project_id=args.project,
                    user_agent=args.user_agent,
                )
                if not args.apply:
                    print(runtime.render_promote_plan(promote_plan), end="")
                    return 0
                promote_result = runtime.commit_promote(
                    args.root.resolve(), promote_plan
                )
                print(
                    f"PROMOTED: {promote_result['source_id']} -> "
                    f"{promote_result['source_path']}"
                )
                print(
                    f"APPLIED: candidate {promote_plan.candidate_id} linked to "
                    f"{promote_result['source_id']} "
                    f"(action {promote_result['action_id']})"
                )
                return 0
            if args.candidates_command == "dismiss":
                triage_result = runtime.dismiss_candidate(
                    args.root.resolve(),
                    args.id,
                    actor=args.actor,
                    reason=args.reason,
                    apply=args.apply,
                )
                print(runtime.render_triage_result(triage_result), end="")
                return 0
            if args.candidates_command == "restore":
                triage_result = runtime.restore_candidate(
                    args.root.resolve(),
                    args.id,
                    actor=args.actor,
                    apply=args.apply,
                )
                print(runtime.render_triage_result(triage_result), end="")
                return 0
            if args.candidates_command == "expire":
                triage_result = runtime.expire_candidates(
                    args.root.resolve(),
                    channel_id=args.channel,
                    as_of=args.as_of or None,
                    apply=args.apply,
                )
                print(runtime.render_triage_result(triage_result), end="")
                return 0
            if args.candidates_command == "purge":
                triage_result = runtime.purge_candidates(
                    args.root.resolve(),
                    apply=args.apply,
                )
                print(runtime.render_triage_result(triage_result), end="")
                return 0
            enriched = runtime.enrich_candidates(
                args.root.resolve(),
                apply=args.apply,
            )
            print(runtime.render_enrichment(enriched, applied=args.apply), end="")
            return 0
        except (OSError, TransactionError, ValueError) as exc:
            if isinstance(exc, runtime.AlreadyPromoted):
                print(
                    f"IDEMPOTENT: candidate already promoted to {exc.source_id}"
                )
                return 0
            print(f"ERROR: {exc}")
            return 2
    if args.command == "project":
        try:
            if args.project_command == "list":
                print(runtime.render_project_list(args.root.resolve()), end="")
                return 0
            if args.project_command == "status":
                print(
                    runtime.render_project_status(
                        args.root.resolve(),
                        args.id,
                    ),
                    end="",
                )
                return 0
            relative, content = runtime.prepare_project_draft(
                args.root.resolve(),
                title=args.title,
                slug=args.slug,
                created_at=args.date,
                owner=args.owner,
                research_question=args.question,
                charter_path=args.charter_path,
                queue_path=args.queue_path,
                review_cadence=args.review_cadence,
                next_review_date=args.next_review_date,
                tags=runtime.split_values(args.tags),
            )
            return output_draft(args.root, relative, content, args.apply)
        except (FileExistsError, OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "review":
        try:
            if args.review_command == "queue":
                print(
                    runtime.render_review_queue(
                        args.root.resolve(),
                        project_id=args.project,
                        object_type=args.type,
                        review_status=args.status,
                    ),
                    end="",
                )
                return 0
            target_ids = runtime.split_values(args.targets)
            if not args.apply:
                relative, content, updates = runtime.prepare_review(
                    args.root.resolve(),
                    target_ids=target_ids,
                    decision=args.decision,
                    reviewer=args.reviewer,
                    reviewed_at=args.date,
                    notes=args.notes,
                )
                print(f"DRY-RUN target={relative}")
                print(
                    "DRY-RUN updates="
                    + ", ".join(
                        str(path.relative_to(args.root.resolve())) for path in updates
                    )
                )
                print(content, end="")
                print("DRY-RUN: no files changed; rerun with --apply")
                return 0
            changed = runtime.apply_review(
                args.root.resolve(),
                target_ids=target_ids,
                decision=args.decision,
                reviewer=args.reviewer,
                reviewed_at=args.date,
                notes=args.notes,
            )
            for path in changed:
                print(f"APPLIED: {path.relative_to(args.root.resolve())}")
            return 0
        except (FileExistsError, OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "actions":
        try:
            if args.action_command == "list":
                print(
                    runtime.render_actions(
                        args.root.resolve(),
                        project_id=args.project,
                        owner=args.owner,
                        status=args.status,
                    ),
                    end="",
                )
                return 0
            if args.action_command == "overdue":
                print(
                    runtime.render_actions(
                        args.root.resolve(),
                        project_id=args.project,
                        owner=args.owner,
                        overdue_as_of=args.as_of,
                    ),
                    end="",
                )
                return 0
            if args.action_command == "create":
                relative, content = runtime.prepare_action_draft(
                    args.root.resolve(),
                    title=args.title,
                    owner=args.owner,
                    created_at=args.date,
                    due_date=args.due_date,
                    success_evidence=args.success_evidence,
                    project_ids=runtime.split_values(args.projects),
                    source_review_id=args.source_review_id,
                )
                return output_draft(args.root, relative, content, args.apply)
            if not args.apply:
                print(f"DRY-RUN close={args.id}")
                print("DRY-RUN: no files changed; rerun with --apply")
                return 0
            target = runtime.close_action(
                args.root.resolve(),
                args.id,
                closed_at=args.date,
                success_evidence=args.success_evidence,
            )
            print(f"APPLIED: {target.relative_to(args.root.resolve())}")
            return 0
        except (FileExistsError, OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "source":
        try:
            if args.source_command == "discover":
                discovery_adapter: DiscoveryAdapter
                if args.discover_command == "rss":
                    discovery_adapter = RSSDiscoveryAdapter(
                        args.feed_url,
                        allowed_hosts=frozenset(runtime.split_values(args.allow_hosts)),
                        publisher=args.publisher,
                        limit=args.limit,
                    )
                elif args.discover_command == "github":
                    discovery_adapter = GitHubReleaseDiscoveryAdapter(
                        args.repository,
                        limit=args.limit,
                    )
                elif args.discover_command == "arxiv":
                    discovery_adapter = ArxivDiscoveryAdapter(
                        args.query,
                        limit=args.limit,
                    )
                else:
                    discovery_adapter = SECDiscoveryAdapter(
                        args.cik,
                        forms=frozenset(runtime.split_values(args.forms)),
                        user_agent=args.user_agent,
                        limit=args.limit,
                    )
                print(candidates_json(discovery_adapter.discover()), end="")
                return 0
            if args.source_command == "add":
                adapter = selected_capture_adapter(
                    args.url,
                    args.file,
                    args.user_agent or None,
                    args.max_bytes,
                )
                plan = runtime.prepare_new_source_capture(
                    args.root.resolve(),
                    adapter,
                    title=args.title,
                    slug=args.slug,
                    created_at=args.date,
                    source_type=args.source_type,
                    publisher=args.publisher,
                    published_at=args.published_at,
                    source_grade=args.source_grade,
                    companies=runtime.split_values(args.companies),
                    technologies=runtime.split_values(args.technologies),
                    products=runtime.split_values(args.products),
                    tags=runtime.split_values(args.tags),
                    project_ids=runtime.split_values(args.projects),
                    allow_duplicate=args.allow_duplicate,
                )
                print(f"CAPTURE SHA256: {plan.content_sha256}")
                print(f"CAPTURE canonical_url: {plan.canonical_url or '—'}")
                print(
                    "CAPTURE published_date_proposal: "
                    f"{plan.published_date_proposal or '—'}"
                )
                if not args.apply:
                    print(f"DRY-RUN target={plan.source_path}")
                    for path in plan.assets:
                        print(f"DRY-RUN asset={path}")
                    print(plan.source_content, end="")
                    print("DRY-RUN: no files changed; rerun with --apply")
                    return 0
                changed = runtime.commit_new_source_capture(
                    args.root.resolve(),
                    plan,
                )
                for path in changed:
                    print(f"CREATED: {path.relative_to(args.root.resolve())}")
                return 0
            if args.source_command == "fetch":
                adapter = selected_capture_adapter(args.url, args.file)
                if not args.apply:
                    captured = adapter.capture()
                    digest = hashlib.sha256(captured.content).hexdigest()
                    print(f"DRY-RUN source={args.id}")
                    print(f"CAPTURE SHA256: {digest}")
                    print(f"CAPTURE bytes: {len(captured.content)}")
                    print("DRY-RUN: no files changed; rerun with --apply")
                    return 0
                changed = runtime.capture_existing_source(
                    args.root.resolve(),
                    args.id,
                    adapter,
                    allow_duplicate=args.allow_duplicate,
                )
                for path in changed:
                    print(f"APPLIED: {path.relative_to(args.root.resolve())}")
                return 0
            if args.source_command == "process":
                if not args.apply:
                    print(f"DRY-RUN source={args.id}")
                    print("DRY-RUN: no files changed; rerun with --apply")
                    return 0
                changed = runtime.process_source_asset(
                    args.root.resolve(),
                    args.id,
                )
                for path in changed:
                    print(f"APPLIED: {path.relative_to(args.root.resolve())}")
                return 0
            if args.source_command == "verify-assets":
                results = runtime.verify_source_assets(args.root.resolve())
                for result in results:
                    print(
                        f"{result.status.upper()} {result.source_id}: {result.message}"
                    )
                failures = {
                    "missing",
                    "invalid",
                    "hash_mismatch",
                }
                return int(any(result.status in failures for result in results))
            if args.source_command == "confirm-date":
                if not args.apply:
                    print(f"DRY-RUN source={args.id} published_at={args.date}")
                    print("DRY-RUN: no files changed; rerun with --apply")
                    return 0
                target = runtime.confirm_published_date(
                    args.root.resolve(),
                    args.id,
                    args.date,
                    allow_proposal_override=args.override_proposal,
                )
                print(f"APPLIED: {target.relative_to(args.root.resolve())}")
                return 0
            if not args.apply:
                relative, content, updates = runtime.prepare_review(
                    args.root.resolve(),
                    target_ids=[args.id],
                    decision=args.decision,
                    reviewer=args.reviewer,
                    reviewed_at=args.date,
                    notes=args.notes,
                )
                print(f"DRY-RUN target={relative}")
                print(
                    "DRY-RUN updates="
                    + ", ".join(
                        str(path.relative_to(args.root.resolve())) for path in updates
                    )
                )
                print(content, end="")
                print("DRY-RUN: no files changed; rerun with --apply")
                return 0
            changed = runtime.apply_review(
                args.root.resolve(),
                target_ids=[args.id],
                decision=args.decision,
                reviewer=args.reviewer,
                reviewed_at=args.date,
                notes=args.notes,
            )
            for path in changed:
                print(f"APPLIED: {path.relative_to(args.root.resolve())}")
            return 0
        except (FileExistsError, OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "workflow":
        try:
            if args.workflow_command == "event":
                event_spec_value = runtime.load_spec(
                    args.spec.resolve(),
                    runtime.EventDraftSpec,
                )
                relative, content = runtime.prepare_reviewable_event_draft(
                    args.root.resolve(),
                    event_spec_value,
                )
                if not args.apply:
                    print(f"DRY-RUN target={relative}")
                    print(content, end="")
                    print("DRY-RUN: no files changed; rerun with --apply")
                    return 0
                changed = runtime.apply_event_draft(
                    args.root.resolve(),
                    relative,
                    content,
                    event_spec_value.source_ids,
                    event_spec_value.created_at,
                )
                for path in changed:
                    print(f"APPLIED: {path.relative_to(args.root.resolve())}")
                return 0
            if args.workflow_command == "report":
                report_spec_value = runtime.load_spec(
                    args.spec.resolve(),
                    runtime.ReportDraftSpec,
                )
                report_baseline = (
                    runtime.load_metrics_snapshot(args.baseline.resolve())
                    if args.baseline
                    else None
                )
                relative, content = runtime.prepare_synthesized_report(
                    args.root.resolve(),
                    report_spec_value,
                    baseline=report_baseline,
                )
                return output_draft(args.root, relative, content, args.apply)
            relative, content = runtime.prepare_company_update_proposal(
                args.root.resolve(),
                company_id=args.company,
                event_ids=runtime.split_values(args.events),
                created_at=args.date,
            )
            if not args.apply:
                print(f"DRY-RUN target={relative}")
                print(content, end="")
                print("DRY-RUN: no files changed; rerun with --apply")
                return 0
            target = runtime.apply_company_update_proposal(
                args.root.resolve(),
                relative,
                content,
            )
            print(f"CREATED: {target.relative_to(args.root.resolve())}")
            return 0
        except (FileExistsError, OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "ui":
        try:
            from research_os.ui.app import run_ui

            run_ui(
                args.root.resolve(),
                host=args.host,
                port=args.port,
            )
            return 0
        except (ImportError, OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "jobs":
        try:
            if args.job_command == "list":
                rows = runtime.job_rows(
                    args.root.resolve(),
                    project_id=args.project,
                    status=args.status,
                )
                print("# Job Runs")
                for row in rows:
                    print(
                        f"{row.object_id} {row.metadata['status']} "
                        f"{row.metadata['job_name']}: {row.metadata['message']}"
                    )
                return 0
            job_result = runtime.run_job(
                args.root.resolve(),
                args.name,
                project_id=args.project,
                target=args.target,
                as_of=args.as_of,
            )
            print(
                f"{job_result.status.upper()} {job_result.job_id}: "
                f"{job_result.message}\n"
                f"RECORD: {job_result.path.relative_to(args.root.resolve())}"
            )
            return 0 if job_result.status == "success" else 1
        except (OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "benchmark":
        try:
            benchmark_result = runtime.run_scale_benchmark(
                sources=args.sources,
                events=args.events,
                max_seconds=args.max_seconds,
            )
            for key, value in benchmark_result.as_dict().items():
                print(f"{key}: {value}")
            return 0 if benchmark_result.passed else 1
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "release":
        try:
            readiness = runtime.release_readiness(
                args.root.resolve(),
                project_id=args.project,
            )
            print(runtime.render_release_readiness(readiness), end="")
            return 0 if readiness.ready else 1
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "scale":
        print(runtime.render_scale_assessment(args.root.resolve()), end="")
        return 0
    if args.command == "impact":
        try:
            print(
                runtime.render_impact(args.root.resolve(), args.id, args.depth),
                end="",
            )
            return 0
        except (OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    if args.command == "export":
        try:
            root = args.root.resolve()
            if args.format == "jsonl":
                content = runtime.ontology_jsonl(root)
                if args.output is None:
                    print(content, end="")
                    return 0
                if not args.apply:
                    print(f"DRY-RUN target={args.output}")
                    print("DRY-RUN: no files changed; rerun with --apply to write")
                    return 0
                target = args.output
                if not target.is_absolute():
                    target = root / target
                target = runtime.write_text_export(target, content)
                print(f"CREATED: {target}")
                return 0
            if args.output is None:
                raise ValueError("SQLite export requires --output")
            if not args.apply:
                print(f"DRY-RUN target={args.output}")
                print("DRY-RUN: no database created; rerun with --apply")
                return 0
            target = args.output
            if not target.is_absolute():
                target = root / target
            runtime.write_sqlite_export(root, target)
            print(f"CREATED: {target}")
            return 0
        except (FileExistsError, OSError, TransactionError, ValueError) as exc:
            print(f"ERROR: {exc}")
            return 2
    try:
        if args.command == "new-source":
            relative, content = runtime.prepare_source_draft(
                args.root.resolve(),
                title=args.title,
                slug=args.slug,
                created_at=args.date,
                source_type=args.source_type,
                publisher=args.publisher,
                published_at=args.published_at,
                url=args.url,
                local_path=args.local_path,
                source_grade=args.source_grade,
                companies=runtime.split_values(args.companies),
                technologies=runtime.split_values(args.technologies),
                products=runtime.split_values(args.products),
                tags=runtime.split_values(args.tags),
                project_ids=[args.project],
            )
            return output_draft(args.root, relative, content, args.apply)
        if args.command == "new-entity":
            relative, content = runtime.prepare_entity_draft(
                args.root.resolve(),
                entity_type=args.type,
                slug=args.slug,
                title=args.title,
                created_at=args.date,
                definition=args.definition,
                in_scope=runtime.split_values(args.in_scope),
                out_of_scope=runtime.split_values(args.out_of_scope),
                value_chain_position=args.value_chain_position,
                key_inputs=runtime.split_values(args.key_inputs),
                key_outputs=runtime.split_values(args.key_outputs),
                key_metrics=runtime.split_values(args.key_metrics),
                core_company_ids=runtime.split_values(args.core_company_ids),
                tracked_company_ids=runtime.split_values(args.tracked_company_ids),
                source_channel_ids=runtime.split_values(args.source_channel_ids),
                evidence_ids=runtime.split_values(args.evidence_ids),
                sector_ids=runtime.split_values(args.sector_ids),
                region_primary=args.region_primary or None,
                coverage_tier=args.coverage_tier or None,
                legal_name=args.legal_name or None,
                company_stage=args.company_stage or None,
                headquarters=args.headquarters or None,
                aliases=runtime.split_values(args.aliases),
                tags=runtime.split_values(args.tags),
                project_ids=runtime.split_values(getattr(args, "project", "")),
            )
            return output_draft(args.root, relative, content, args.apply)
        if args.command == "new-assertion":
            relative, content = runtime.prepare_assertion_draft(
                args.root.resolve(),
                subject_id=args.subject,
                predicate=args.predicate,
                object_id=args.object_id,
                created_at=args.date,
                valid_from=args.valid_from,
                as_of=args.as_of,
                title=args.title,
                scope=args.scope,
                confidence=args.confidence,
                project_ids=runtime.split_values(args.project),
            )
            return output_draft(args.root, relative, content, args.apply)
        if args.command == "new-event":
            source_ids = runtime.split_values(args.source_ids)
            relative, content = runtime.prepare_event_draft(
                args.root.resolve(),
                title=args.title,
                slug=args.slug,
                created_at=args.date,
                event_date=args.event_date,
                source_ids=source_ids,
                companies=runtime.split_values(args.companies),
                technologies=runtime.split_values(args.technologies),
                products=runtime.split_values(args.products),
                thesis_links=runtime.split_values(args.thesis_links),
                confidence=args.confidence,
                tags=runtime.split_values(args.tags),
                project_ids=[args.project],
            )
            if not args.apply:
                return output_draft(args.root, relative, content, False)
            changed = runtime.apply_event_draft(
                args.root.resolve(),
                relative,
                content,
                source_ids,
                args.date,
            )
            target = (args.root.resolve() / relative).resolve()
            print(f"CREATED: {target.relative_to(args.root.resolve())}")
            for path in changed:
                if path != target:
                    print(
                        "UPDATED: "
                        f"{path.relative_to(args.root.resolve())} "
                        "(Event extraction completed)"
                    )
            return 0
        if args.command == "new-report":
            relative, content = runtime.prepare_report_draft(
                args.root.resolve(),
                title=args.title,
                slug=args.slug,
                created_at=args.date,
                period_start=args.period_start,
                period_end=args.period_end,
                thesis_ids=runtime.split_values(args.thesis_ids),
                evidence_ids=runtime.split_values(args.evidence_ids),
                tags=runtime.split_values(args.tags),
                project_ids=[args.project],
            )
            return output_draft(args.root, relative, content, args.apply)
    except (FileExistsError, OSError, TransactionError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    raise AssertionError(f"unhandled command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
