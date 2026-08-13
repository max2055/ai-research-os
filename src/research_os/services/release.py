"""Read-only release readiness checks with explicit human gates."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from research_os.domain.models import ResearchObject
from research_os.services.candidate_db import candidate_db_path
from research_os.services.indexing import (
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.projects import objects_for_project
from research_os.services.validation import validate_repository

PILOT_PROJECT_ID = "PRJ-002"
V03_PROJECT_ID = "PRJ-001"
HUMAN_REVIEWER_DENYLIST = frozenset(
    {"ai", "automation", "codex", "model", "research-os", "system"}
)
RESEARCH_QUALITY_ACTION_IDS = frozenset(
    {
        *(f"ACT-20260729-{number:03d}" for number in range(1, 7)),
        "ACT-20260730-001",
        "ACT-20260730-002",
    }
)
RECOVERY_PASS_ROWS = (
    "Encrypted archive",
    "Processed Sources restored",
    "Restored asset files",
    "Raw Source SHA-256",
    "Capture exceptions",
    "Install `.[dev,ui]`",
    "Ruff format and lint",
    "mypy strict",
    "Tests",
    "Coverage",
    "`research-os doctor`",
    "Formal objects",
    "Repository validation",
    "Global and project indexes",
)
V03_CHECK_KEYS = (
    "evidence_universe.pilot_universe",
    "evidence_universe.authoritative_references",
    "evidence_universe.repository_validation",
    "ingestion.pilot_completion",
    "ingestion.no_silent_missed_runs",
    "ingestion.channel_licenses",
    "impact_analysis.impact_field_gate",
    "impact_analysis.mode_field_gate",
    "impact_analysis.counterevidence_divergence",
    "decision.human_approved_forecasts",
    "decision.natural_resolutions",
    "decision.recommendation_pilot",
    "decision.no_automated_trading",
    "engineering.quality_suite",
    "engineering.performance_slo",
    "engineering.migration_recovery",
    "engineering.recovery_boundaries",
    "engineering.dashboard_security",
    "human.cadence_reviews",
    "human.known_limitations_read",
    "human.release_approval",
)
V03_PHASE6_PATH = (
    "00_System/v0.3_AI_Industry_Intelligence_OS/07_Phase_6_Productization_and_Scale.md"
)
V03_BACKLOG_PATH = "00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md"
IMPACT_ACCEPTANCE_PATH = "00_System/C020_Phase_3_Acceptance.md"
IMPACT_JUDGMENTS_PATH = "05_Research/Reviews/Field_Gate_20_Impact_Judgments.json"
MODE_ACCEPTANCE_PATH = "00_System/D020_Phase_4_Acceptance.md"
MODE_JUDGMENTS_PATH = "05_Research/Reviews/Field_Gate_10_Case_Judgments.json"
CANDIDATE_ACCEPTANCE_PATH = "05_Research/Operations/Pilot/Phase_Acceptance_B026.md"
PILOT_ACCEPTANCE_PATH = "05_Research/Operations/Pilot/v0.3_30_Day_Pilot_Acceptance.md"
DISCOVERY_AUDIT_PATH = "00_System/v0.3_Discovery_Job_Audit_2026-08-10.md"
LICENSE_AUDIT_PATH = "00_System/v0.3_Channel_License_Audit.md"
PERFORMANCE_PATH = "00_System/v0.3_Performance_Benchmark.md"
MIGRATION_PATH = "00_System/v0.3_Migration_Rehearsal.md"
RECOVERY_PATH = "00_System/v0.3_Recovery_Drill.md"
ENGINEERING_VERIFICATION_PATH = "00_System/v0.3_Release_Gate_Verification_2026-08-13.md"
LIMITATIONS_PATH = "00_System/v0.3_Known_Limitations.md"
UNIVERSE_ACCEPTANCE_PATH = "00_System/A020_Phase_Acceptance.md"
RELEASE_PACKET_PATH = "05_Research/Reviews/v0.3_Release_Packet.md"
MODE_DIMENSIONS = frozenset(
    {
        "citation",
        "no_outside_facts",
        "question_coverage",
        "counterevidence",
        "explicit_assumptions",
        "explainable_divergence",
        "saves_time",
        "no_overreach",
    }
)
IMPACT_EXPECTED_SAMPLE_SIZE = 20
MODE_EXPECTED_CASE_COUNT = 10
MODE_EXPECTED_RUN_COUNT = 34
V03_REVIEWER_DENY_TOKENS = frozenset(
    {
        "agent",
        "ai",
        "automation",
        "automated",
        "bot",
        "codex",
        "example",
        "human",
        "llm",
        "model",
        "none",
        "pending",
        "placeholder",
        "researcher",
        "reviewer",
        "synthetic",
        "system",
        "tbd",
        "test",
        "unknown",
        "人工",
        "占位",
        "审核人",
        "待定",
        "未知",
        "模型",
        "测试",
        "研究员",
        "示例",
        "系统",
        "自动化",
    }
)
V03_REVIEWER_DENY_COMPACT = frozenset(
    "".join(re.findall(r"[^\W_]+", value)) for value in V03_REVIEWER_DENY_TOKENS
)
QUALITY_PATHS = (
    "src/research_os",
    "09_Automation/tests",
    "requirements",
    "pyproject.toml",
)
SECURITY_PATHS = (
    "src/research_os/repositories/transaction.py",
    "src/research_os/services/actions.py",
    "src/research_os/services/candidate_db.py",
    "src/research_os/services/mutation_audit.py",
    "src/research_os/services/mutation_gateway.py",
    "src/research_os/services/product_capabilities.py",
    "src/research_os/services/triage.py",
    "src/research_os/services/web_candidate_mutations.py",
    "src/research_os/services/web_identity.py",
    "src/research_os/services/web_repository_mutations.py",
    "src/research_os/services/web_registry_mutations.py",
    "src/research_os/services/web_research_drafts.py",
    "src/research_os/services/web_review_mutations.py",
    "src/research_os/services/web_source_workflows.py",
    "src/research_os/ui/app.py",
    "09_Automation/tests/test_m6_security.py",
    "09_Automation/tests/test_product_capabilities.py",
    "09_Automation/tests/test_web_candidate_parity.py",
    "09_Automation/tests/test_web_mutation.py",
    "09_Automation/tests/test_web_repository_mutations.py",
    "09_Automation/tests/test_web_registry_parity.py",
    "09_Automation/tests/test_web_research_drafts.py",
    "09_Automation/tests/test_web_review_parity.py",
    "09_Automation/tests/test_web_source_parity.py",
)
PERFORMANCE_OPERATIONS = frozenset(
    {
        "Home",
        "Candidate Queue",
        "Company",
        "Sector",
        "Impact 3-hop",
        "Full validate",
        "Index render",
    }
)
RECOVERY_OBJECTIVES = frozenset(
    {
        "Recovery time objective (RTO)",
        "Recovery point objective (RPO)",
        "Repository validation",
        "Candidate snapshot integrity",
        "Archived Source assets",
    }
)
RECOVERY_PROCEDURES = frozenset(
    {
        "Git recovery",
        "Source assets",
        "Candidate store",
        "Snapshot verification",
        "Repository validation",
        "Global indexes",
        "Project indexes",
        "Full pytest",
        "Ruff",
        "mypy",
        "Dashboard",
        "Discovery",
    }
)
RECOVERY_CHAIN_ROWS = frozenset(
    {
        "Candidate",
        "Channel",
        "Candidate URL",
        "Promoted Source",
        "Source record",
        "Raw asset",
        "Raw bytes",
        "Expected and actual SHA-256",
    }
)
DASHBOARD_SMOKE_ROUTES = frozenset(
    {
        "/",
        "/home",
        "/impact",
        "/analysis",
        "/decision",
        "/operations",
        "/health",
        "/companies/COM-nvidia",
        "/sectors/SEG-memory-storage",
        "/pipeline/queue",
    }
)
MIGRATION_BASELINE_CHECKS = frozenset(
    {
        "Repository validation",
        "Global index check",
        "PRJ-001 index check",
        "PRJ-002 index check",
        "Schema and migration compatibility tests",
        "Formal objects hashed",
        "Candidate DB schema version",
        "Candidate DB SHA-256",
    }
)
MIGRATION_COMPANIES = frozenset(
    {
        "COM-anthropic",
        "COM-microsoft",
        "COM-openai",
        "COM-oracle",
        "COM-palantir",
        "COM-salesforce",
        "COM-sap",
        "COM-servicenow",
    }
)
MIGRATION_ROLLBACK_CHECKS = frozenset(
    {
        "Migrated files restored",
        "All formal object bytes restored",
        "Candidate DB SHA-256 unchanged",
        "Candidate DB schema version: 2",
        "Repository validation",
        "Global, PRJ-001, PRJ-002 indexes",
        "Full pytest",
    }
)
ACTION_SURFACE_PATHS = (
    "src/research_os/cli.py",
    "src/research_os/runtime/product.py",
    "src/research_os/services/jobs.py",
    "src/research_os/ui/app.py",
)
TRADING_SURFACE_TOKENS = frozenset(
    {
        "broker",
        "brokers",
        "buy",
        "execution",
        "order",
        "orders",
        "position",
        "positions",
        "sell",
        "trade",
        "trades",
        "trading",
    }
)
TRADING_DIRECTIVE_PATTERN = re.compile(
    r"(?:买入|卖出|买进|抛售|建仓|加仓|减仓|清仓|加注|梭哈|仓位|目标价|"
    r"\bposition[- ]siz(?:e|ing)\b|\btarget price\b|"
    r"(?:^|[.!?\n]\s*|[-*]\s+)\b(?:buy|sell|trade)\b|"
    r"\b(?:recommend|should|must|directive|instruction)\s+(?:to\s+)?"
    r"(?:buy|sell|trade)\b|"
    r"\b(?:buy|sell)\s+(?:the\s+)?(?:stock|shares?|security|position)\b|"
    r"\b(?:place|submit|route|send|execute)\b(?:\s+[a-z]+){0,5}\s+"
    r"(?:order|trade|broker)\b)",
    re.IGNORECASE,
)


class ReleaseEvaluationError(ValueError):
    """Raised when present release evidence cannot be evaluated safely."""


@dataclass(frozen=True)
class ReleaseCheck:
    key: str
    passed: bool
    requirement: str
    observed: str
    evidence_paths: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseReadiness:
    version: str
    project_id: str
    checks: tuple[ReleaseCheck, ...]

    @property
    def ready(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def blockers(self) -> tuple[ReleaseCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "project_id": self.project_id,
            "ready": self.ready,
            "checks": [check.as_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class _RecoveryChainEvidence:
    candidate_id: str
    candidate_status: str
    channel_id: str
    candidate_url: str
    source_id: str
    source_record: Path
    raw_asset: Path
    raw_bytes: int
    sha256: str


def _read(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _line_value(text: str, label: str) -> str:
    match = re.search(
        rf"(?mi)^(?:-\s*)?{re.escape(label)}\s*[：:]\s*(.*?)\s*$",
        text,
    )
    return match.group(1).strip() if match else ""


def _first_line_value(text: str, *labels: str) -> str:
    for label in labels:
        value = _line_value(text, label)
        if value:
            return value
    return ""


def _human_reviewer(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(normalized) and normalized not in HUMAN_REVIEWER_DENYLIST


def _table_row_passed(text: str, label: str) -> bool:
    return bool(
        re.search(
            rf"(?mi)^\|\s*{re.escape(label)}\s*\|\s*PASS(?:\s|—|-|\|)",
            text,
        )
    )


def _benchmark_time_passed(text: str) -> bool:
    total = re.search(
        r"(?mi)^\|\s*Total query time\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*s\s*\|",
        text,
    )
    maximum = re.search(
        r"(?mi)^\|\s*Maximum accepted\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*s\s*\|",
        text,
    )
    return bool(
        total
        and maximum
        and float(total.group(1)) <= float(maximum.group(1))
        and float(maximum.group(1)) <= 10.0
    )


def completed_cadence_records(
    root: Path,
    project_id: str,
    cadence: str,
) -> list[Path]:
    folder = (
        root
        / "05_Research"
        / "Projects"
        / project_id
        / "Reviews"
        / cadence.capitalize()
    )
    completed: list[Path] = []
    for path in sorted(folder.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        status = _line_value(text, "Review status").lower()
        reviewer = _line_value(text, "Reviewer")
        review_date = _line_value(text, "Review date")
        metrics_snapshot = _line_value(text, "Metrics snapshot")
        if (
            status == "completed"
            and _human_reviewer(reviewer)
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_date)
            and metrics_snapshot
        ):
            completed.append(path)
    return completed


def _approved_target_ids(objects: list[ResearchObject]) -> set[str]:
    return {
        str(target_id)
        for obj in objects
        if obj.object_type == "review"
        if obj.metadata.get("status") == "applied"
        if obj.metadata.get("decision") == "approve"
        if _human_reviewer(str(obj.metadata.get("reviewer", "")))
        for target_id in obj.metadata.get("target_ids", [])
    }


def _check(
    key: str,
    passed: bool,
    requirement: str,
    observed: str,
) -> ReleaseCheck:
    return ReleaseCheck(
        key=key,
        passed=passed,
        requirement=requirement,
        observed=observed,
    )


def release_readiness(
    root: Path,
    *,
    project_id: str = PILOT_PROJECT_ID,
) -> ReleaseReadiness:
    root = root.resolve()
    objects, findings = validate_repository(root)
    errors = [finding for finding in findings if finding.level == "error"]
    projects = {obj.object_id: obj for obj in objects if obj.object_type == "project"}
    project = projects.get(project_id)
    checks: list[ReleaseCheck] = [
        _check(
            "repository.validation",
            not errors,
            "0 validation errors",
            f"{len(errors)} errors",
        ),
    ]

    global_drift = index_drift(root, render_indexes(objects))
    checks.append(
        _check(
            "indexes.global",
            not global_drift,
            "0 global index drift files",
            f"{len(global_drift)} drift files",
        )
    )
    checks.append(
        _check(
            "pilot.project",
            project is not None and project.metadata.get("status") == "active",
            f"{project_id} exists and is active",
            (str(project.metadata.get("status")) if project is not None else "missing"),
        )
    )

    scoped: list[ResearchObject] = []
    if project is not None:
        scoped = objects_for_project(objects, project_id)
        pilot_drift = index_drift(
            root,
            render_project_indexes(objects, project_id),
        )
        checks.append(
            _check(
                "indexes.pilot",
                not pilot_drift,
                f"0 {project_id} index drift files",
                f"{len(pilot_drift)} drift files",
            )
        )
    else:
        checks.append(
            _check(
                "indexes.pilot",
                False,
                f"0 {project_id} index drift files",
                "project missing",
            )
        )

    sources = [obj for obj in scoped if obj.object_type == "source"]
    sources_complete = [
        obj
        for obj in sources
        if obj.metadata.get("processing_status") == "processed"
        and obj.metadata.get("asset_paths")
        and obj.metadata.get("content_sha256")
        and obj.metadata.get("fetched_at")
    ]
    checks += [
        _check(
            "pilot.sources.count",
            10 <= len(sources) <= 15,
            "10–15 real Sources",
            f"{len(sources)} Sources",
        ),
        _check(
            "pilot.sources.provenance",
            len(sources) >= 10 and len(sources_complete) == len(sources),
            "all pilot Sources archived, hashed and processed",
            f"{len(sources_complete)}/{len(sources)} complete",
        ),
    ]

    approved_target_ids = _approved_target_ids(objects)
    events = [obj for obj in scoped if obj.object_type == "event"]
    reviewed_events = [
        obj
        for obj in events
        if obj.metadata.get("review_status") == "reviewed"
        and obj.object_id in approved_target_ids
    ]
    checks += [
        _check(
            "pilot.events.count",
            8 <= len(events) <= 10,
            "8–10 real Events",
            f"{len(events)} Events",
        ),
        _check(
            "pilot.events.human_review",
            len(events) >= 8 and len(reviewed_events) == len(events),
            "every pilot Event reviewed through a human approve decision",
            f"{len(reviewed_events)}/{len(events)} human-approved",
        ),
    ]

    reports = [obj for obj in scoped if obj.object_type == "report"]
    reviewed_reports = [
        obj
        for obj in reports
        if obj.metadata.get("status") == "final"
        and obj.metadata.get("review_status") == "reviewed"
        and obj.object_id in approved_target_ids
    ]
    checks.append(
        _check(
            "pilot.report.human_review",
            bool(reviewed_reports),
            "at least one final Report with a human approve decision",
            f"{len(reviewed_reports)} qualifying Reports",
        )
    )

    weekly = completed_cadence_records(root, project_id, "weekly")
    monthly = completed_cadence_records(root, project_id, "monthly")
    checks += [
        _check(
            "pilot.cadence.weekly",
            len(weekly) >= 2,
            "at least two completed human Weekly reviews",
            f"{len(weekly)} completed",
        ),
        _check(
            "pilot.cadence.monthly",
            len(monthly) >= 1,
            "at least one completed human Monthly review",
            f"{len(monthly)} completed",
        ),
    ]

    m4_packet = _read(root, "05_Research/Reviews/M4_Field_Review_Packet.md")
    m4_passed = bool(
        re.search(r"(?mi)^-\s*Sources reviewed:\s*10/10\s*$", m4_packet)
        and re.search(r"(?mi)^-\s*Decision:\s*approve\s*$", m4_packet)
        and _human_reviewer(_line_value(m4_packet, "Reviewer"))
        and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            _line_value(m4_packet, "Date"),
        )
    )
    checks.append(
        _check(
            "m4.field_gate",
            m4_passed,
            "10/10 Source field review and explicit human approval",
            "approved" if m4_passed else "pending or incomplete",
        )
    )

    pilot_action_ids = {f"ACT-20260729-{number:03d}" for number in range(7, 11)}
    actions = {obj.object_id: obj for obj in objects if obj.object_type == "action"}

    def unresolved(ids: set[str]) -> list[str]:
        return sorted(
            object_id
            for object_id in ids
            if object_id not in actions
            or actions[object_id].metadata.get("status") not in {"done", "cancelled"}
        )

    quality_unresolved = unresolved(set(RESEARCH_QUALITY_ACTION_IDS))
    pilot_unresolved = unresolved(pilot_action_ids)
    checks += [
        _check(
            "research_quality.actions",
            not quality_unresolved,
            "RQ-01–RQ-08 closed or formally cancelled",
            (
                "all resolved"
                if not quality_unresolved
                else "unresolved: " + ", ".join(quality_unresolved)
            ),
        ),
        _check(
            "pilot.actions",
            not pilot_unresolved,
            "M6 pilot Actions closed or formally cancelled",
            (
                "all resolved"
                if not pilot_unresolved
                else "unresolved: " + ", ".join(pilot_unresolved)
            ),
        ),
    ]

    performance = _read(root, "00_System/M6_Performance_Benchmark.md")
    performance_passed = bool(
        _line_value(performance, "Status").lower() == "passed"
        and re.search(r"(?mi)^Sources:\s*1000\s*$", performance)
        and re.search(r"(?mi)^Events:\s*500\s*$", performance)
        and re.search(r"(?mi)^Decision:\s*pass\s*$", performance)
        and _benchmark_time_passed(performance)
    )
    recovery = _read(root, "00_System/M6_Recovery_Drill.md")
    recovery_passed = bool(
        _line_value(recovery, "Status").lower() == "passed"
        and re.search(r"(?mi)^Commit:\s*[0-9a-f]{7,40}\s*$", recovery)
        and all(_table_row_passed(recovery, row) for row in RECOVERY_PASS_ROWS)
    )
    checks += [
        _check(
            "engineering.performance",
            performance_passed,
            "recorded 1,000 Source / 500 Event benchmark passes",
            "passed" if performance_passed else "missing or pending",
        ),
        _check(
            "engineering.recovery",
            recovery_passed,
            "clean-clone Git plus real archived-asset recovery drill passes",
            "passed" if recovery_passed else "missing or pending",
        ),
    ]

    release_notes = _read(root, "00_System/Release_Notes_v0.2.md")
    limitations = _read(root, "00_System/Known_Limitations_v0.2.md")
    pilot_gate = _read(root, "05_Research/Projects/PRJ-002/Pilot_Gate.md")
    documents_ready = bool(release_notes and limitations)
    human_gate = bool(
        re.search(r"(?mi)^Release decision:\s*approve\s*$", pilot_gate)
        and _human_reviewer(_line_value(pilot_gate, "Reviewer"))
        and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            _line_value(pilot_gate, "Decision date"),
        )
    )
    checks += [
        _check(
            "release.documents",
            documents_ready,
            "release notes and known limitations exist",
            "present" if documents_ready else "missing",
        ),
        _check(
            "release.human_decision",
            human_gate,
            "explicit human v0.2 release approval after full-cycle use",
            "approved" if human_gate else "pending",
        ),
    ]
    return ReleaseReadiness(
        version="0.2",
        project_id=project_id,
        checks=tuple(checks),
    )


def _strict_date(value: object) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _v03_human_reviewer(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    tokens = re.findall(r"[^\W_]+", normalized)
    if not tokens or V03_REVIEWER_DENY_TOKENS.intersection(tokens):
        return False
    compact = "".join(tokens)
    deny_segment = any(
        "".join(tokens[start:end]) in V03_REVIEWER_DENY_COMPACT
        for start in range(len(tokens))
        for end in range(start + 1, len(tokens) + 1)
    )
    if compact == "na" or deny_segment:
        return False
    return not any(
        marker in compact
        for marker in (
            "agent",
            "automation",
            "bot",
            "codex",
            "model",
            "placeholder",
            "researchos",
            "synthetic",
            "system",
            "unknown",
        )
    )


def _human_date_allowed(value: object, as_of: date) -> bool:
    parsed = value if isinstance(value, date) else _strict_date(value)
    return parsed is not None and parsed <= as_of


def _current_human_evidence(reviewer: object, dated: object, as_of: date) -> bool:
    return _v03_human_reviewer(reviewer) and _human_date_allowed(dated, as_of)


@dataclass(frozen=True)
class _StaticStringValue:
    strings: frozenset[str]
    includes_unknown: bool = False
    may_be_scalar: bool = False
    may_be_collection: bool = False


_UNKNOWN_STATIC_STRING = _StaticStringValue(frozenset(), includes_unknown=True)
_EMPTY_STATIC_STRINGS = _StaticStringValue(frozenset(), may_be_collection=True)
_StringEnvironment = dict[str, _StaticStringValue]


def _merge_static_string_values(
    *values: _StaticStringValue,
) -> _StaticStringValue:
    return _StaticStringValue(
        frozenset(value for item in values for value in item.strings),
        includes_unknown=any(item.includes_unknown for item in values),
        may_be_scalar=any(item.may_be_scalar for item in values),
        may_be_collection=any(item.may_be_collection for item in values),
    )


def _merge_string_environments(
    *environments: _StringEnvironment,
) -> _StringEnvironment:
    names = {name for environment in environments for name in environment}
    return {
        name: _merge_static_string_values(
            *(
                environment.get(name, _UNKNOWN_STATIC_STRING)
                for environment in environments
            )
        )
        for name in names
    }


def _resolve_static_strings(
    node: ast.AST | None, environment: _StringEnvironment
) -> _StaticStringValue:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _StaticStringValue(frozenset({node.value}), may_be_scalar=True)
    if isinstance(node, ast.Name):
        return environment.get(node.id, _UNKNOWN_STATIC_STRING)
    if isinstance(node, ast.Starred):
        return _resolve_static_strings(node.value, environment)
    if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
        elements = _merge_static_string_values(
            *(_resolve_static_strings(element, environment) for element in node.elts)
        )
        return _StaticStringValue(
            elements.strings,
            includes_unknown=elements.includes_unknown,
            may_be_collection=True,
        )
    if isinstance(node, ast.IfExp):
        return _merge_static_string_values(
            _resolve_static_strings(node.body, environment),
            _resolve_static_strings(node.orelse, environment),
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_static_strings(node.left, environment)
        right = _resolve_static_strings(node.right, environment)
        scalar = left.may_be_scalar and right.may_be_scalar
        collection = left.may_be_collection and right.may_be_collection
        strings = {
            left_value + right_value
            for left_value in left.strings
            for right_value in right.strings
            if scalar
        }
        if collection:
            strings.update(left.strings)
            strings.update(right.strings)
        incompatible = (left.may_be_scalar and right.may_be_collection) or (
            left.may_be_collection and right.may_be_scalar
        )
        return _StaticStringValue(
            frozenset(strings),
            includes_unknown=(
                left.includes_unknown or right.includes_unknown or incompatible
            ),
            may_be_scalar=scalar,
            may_be_collection=collection,
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _resolve_static_strings(node.left, environment)
        right = _resolve_static_strings(node.right, environment)
        collection = left.may_be_collection and right.may_be_collection
        return _StaticStringValue(
            left.strings | right.strings if collection else frozenset(),
            includes_unknown=(
                left.includes_unknown or right.includes_unknown or not collection
            ),
            may_be_collection=collection,
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"frozenset", "list", "set", "tuple"}
        and len(node.args) <= 1
        and not node.keywords
    ):
        if not node.args:
            return _EMPTY_STATIC_STRINGS
        contents = _resolve_static_strings(node.args[0], environment)
        return _StaticStringValue(
            contents.strings,
            includes_unknown=contents.includes_unknown,
            may_be_collection=True,
        )
    return _UNKNOWN_STATIC_STRING


def _static_call_strings(
    node: ast.Call,
    environment: _StringEnvironment,
    keyword: str,
) -> frozenset[str]:
    if node.args:
        return _resolve_static_strings(node.args[0], environment).strings
    argument = next((item.value for item in node.keywords if item.arg == keyword), None)
    if argument is None:
        return frozenset()
    return _resolve_static_strings(argument, environment).strings


def _surface_is_trading_action(value: str) -> bool:
    normalized = unicodedata.normalize("NFKC", value).lower()
    tokens = set(re.findall(r"[a-z]+", normalized))
    return bool(tokens.intersection(TRADING_SURFACE_TOKENS))


class _ModuleSurfaceScanner:
    """Track only module-level static string flow at each public use site."""

    def __init__(self, relative: str) -> None:
        self.relative = relative
        self.findings: set[str] = set()

    def scan(self, tree: ast.Module) -> set[str]:
        self._scan_statements(tree.body, {})
        return self.findings

    def _record_candidates(self, candidates: frozenset[str]) -> None:
        for candidate in candidates:
            if _surface_is_trading_action(candidate):
                self.findings.add(f"{self.relative}:{candidate}")

    def _record_call(self, node: ast.Call, environment: _StringEnvironment) -> None:
        if not isinstance(node.func, ast.Attribute):
            return
        name = node.func.attr
        if name == "add_parser":
            self._record_candidates(_static_call_strings(node, environment, "name"))
        elif name in {
            "add_api_route",
            "delete",
            "get",
            "patch",
            "post",
            "put",
        }:
            self._record_candidates(
                frozenset(
                    value
                    for value in _static_call_strings(node, environment, "path")
                    if value.startswith("/")
                )
            )
        elif (
            name in {"add", "append"}
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"JOB_NAMES", "__all__"}
            and node.args
        ):
            self._record_candidates(
                _resolve_static_strings(node.args[0], environment).strings
            )

    def _record_direct_registry_use(
        self, node: ast.stmt, environment: _StringEnvironment
    ) -> None:
        value: ast.AST | None = None
        names: set[str] = set()
        if isinstance(node, ast.Assign):
            names = {
                target.id for target in node.targets if isinstance(target, ast.Name)
            }
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        ) or (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.op, (ast.Add, ast.BitOr))
        ):
            names = {node.target.id}
            value = node.value
        if names.intersection({"JOB_NAMES", "__all__"}):
            self._record_candidates(_resolve_static_strings(value, environment).strings)

    def _scan_expression(
        self, node: ast.AST | None, environment: _StringEnvironment
    ) -> None:
        if node is None:
            return
        for descendant in ast.walk(node):
            if isinstance(descendant, ast.Call):
                self._record_call(descendant, environment)

    def _scan_statement_header(
        self, statement: ast.stmt, environment: _StringEnvironment
    ) -> None:
        for _field, value in ast.iter_fields(statement):
            children = value if isinstance(value, list) else [value]
            for child in children:
                if not isinstance(child, ast.AST) or isinstance(
                    child, (ast.stmt, ast.ExceptHandler, ast.match_case)
                ):
                    continue
                self._scan_expression(child, environment)

    def _scan_nested_body(
        self, statements: list[ast.stmt], environment: _StringEnvironment
    ) -> None:
        # Nested runtime scopes retain the prior literal scan, without local flow.
        for statement in statements:
            for descendant in ast.walk(statement):
                if isinstance(descendant, ast.Call):
                    self._record_call(descendant, environment)
                elif isinstance(descendant, ast.stmt):
                    self._record_direct_registry_use(descendant, environment)

    @staticmethod
    def _bound_names(target: ast.AST) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.List, ast.Tuple)):
            return {
                name
                for element in target.elts
                for name in _ModuleSurfaceScanner._bound_names(element)
            }
        if isinstance(target, ast.Starred):
            return _ModuleSurfaceScanner._bound_names(target.value)
        return set()

    @staticmethod
    def _bind_unknown(
        environment: _StringEnvironment, target: ast.AST
    ) -> _StringEnvironment:
        updated = dict(environment)
        for name in _ModuleSurfaceScanner._bound_names(target):
            updated[name] = _UNKNOWN_STATIC_STRING
        return updated

    @staticmethod
    def _match_bound_names(pattern: ast.pattern) -> set[str]:
        names: set[str] = set()
        for descendant in ast.walk(pattern):
            if isinstance(descendant, (ast.MatchAs, ast.MatchStar)):
                if descendant.name is not None:
                    names.add(descendant.name)
            elif (
                isinstance(descendant, ast.MatchMapping) and descendant.rest is not None
            ):
                names.add(descendant.rest)
        return names

    def _scan_statements(
        self, statements: list[ast.stmt], environment: _StringEnvironment
    ) -> tuple[_StringEnvironment, list[_StringEnvironment]]:
        current = dict(environment)
        states = [dict(current)]
        for statement in statements:
            current = self._scan_statement(statement, current)
            states.append(dict(current))
        return current, states

    def _scan_loop(
        self,
        body: list[ast.stmt],
        environment: _StringEnvironment,
        target: ast.AST | None = None,
    ) -> _StringEnvironment:
        head = dict(environment)
        while True:
            body_environment = dict(head)
            if target is not None:
                body_environment = self._bind_unknown(body_environment, target)
            body_exit, _states = self._scan_statements(body, body_environment)
            widened = _merge_string_environments(environment, body_exit)
            if widened == head:
                return head
            head = widened

    def _scan_try(
        self,
        statement: ast.Try | ast.TryStar,
        environment: _StringEnvironment,
    ) -> _StringEnvironment:
        try_exit, try_states = self._scan_statements(statement.body, environment)
        normal_exit, _states = self._scan_statements(statement.orelse, try_exit)
        handler_input = _merge_string_environments(*try_states)
        exits = [normal_exit]
        for handler in statement.handlers:
            self._scan_expression(handler.type, handler_input)
            handler_environment = dict(handler_input)
            if handler.name is not None:
                handler_environment[handler.name] = _UNKNOWN_STATIC_STRING
            handler_exit, _states = self._scan_statements(
                handler.body, handler_environment
            )
            exits.append(handler_exit)
        continuing = _merge_string_environments(*exits)
        if not statement.finalbody:
            return continuing

        # Finally also runs on exceptions raised partway through the try body.
        all_finally_inputs = _merge_string_environments(continuing, *try_states)
        self._scan_statements(statement.finalbody, all_finally_inputs)
        final_exit, _states = self._scan_statements(statement.finalbody, continuing)
        return final_exit

    def _scan_statement(
        self, statement: ast.stmt, environment: _StringEnvironment
    ) -> _StringEnvironment:
        current = dict(environment)
        self._scan_statement_header(statement, current)
        self._record_direct_registry_use(statement, current)

        if isinstance(statement, ast.Assign):
            assigned = _resolve_static_strings(statement.value, current)
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    current[target.id] = assigned
                else:
                    current = self._bind_unknown(current, target)
            return current
        if isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            if statement.value is not None:
                current[statement.target.id] = _resolve_static_strings(
                    statement.value, current
                )
            return current
        if isinstance(statement, ast.AugAssign) and isinstance(
            statement.target, ast.Name
        ):
            if statement.target.id in {"JOB_NAMES", "__all__"} and isinstance(
                statement.op, (ast.Add, ast.BitOr)
            ):
                current[statement.target.id] = _merge_static_string_values(
                    current.get(statement.target.id, _UNKNOWN_STATIC_STRING),
                    _resolve_static_strings(statement.value, current),
                )
            else:
                current[statement.target.id] = _UNKNOWN_STATIC_STRING
            return current
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            if (
                isinstance(call.func, ast.Attribute)
                and call.func.attr in {"add", "append"}
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id in {"JOB_NAMES", "__all__"}
                and call.args
            ):
                registry = call.func.value.id
                current[registry] = _merge_static_string_values(
                    current.get(registry, _UNKNOWN_STATIC_STRING),
                    _resolve_static_strings(call.args[0], current),
                )
            return current
        if isinstance(statement, ast.If):
            body_exit, _states = self._scan_statements(statement.body, current)
            else_exit, _states = self._scan_statements(statement.orelse, current)
            return _merge_string_environments(body_exit, else_exit)
        if isinstance(statement, (ast.Try, ast.TryStar)):
            return self._scan_try(statement, current)
        if isinstance(statement, (ast.For, ast.AsyncFor)):
            loop_exit = self._scan_loop(statement.body, current, statement.target)
            else_exit, _states = self._scan_statements(statement.orelse, loop_exit)
            return _merge_string_environments(loop_exit, else_exit)
        if isinstance(statement, ast.While):
            loop_exit = self._scan_loop(statement.body, current)
            else_exit, _states = self._scan_statements(statement.orelse, loop_exit)
            return _merge_string_environments(loop_exit, else_exit)
        if isinstance(statement, ast.Match):
            exits = [current]
            for case in statement.cases:
                case_environment = dict(current)
                for name in self._match_bound_names(case.pattern):
                    case_environment[name] = _UNKNOWN_STATIC_STRING
                self._scan_expression(case.guard, case_environment)
                case_exit, _states = self._scan_statements(case.body, case_environment)
                exits.append(case_exit)
            return _merge_string_environments(*exits)
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            body_environment = dict(current)
            for item in statement.items:
                if item.optional_vars is not None:
                    body_environment = self._bind_unknown(
                        body_environment, item.optional_vars
                    )
            body_exit, _states = self._scan_statements(statement.body, body_environment)
            return _merge_string_environments(current, body_exit)
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            self._scan_nested_body(statement.body, current)
            current[statement.name] = _UNKNOWN_STATIC_STRING
            return current
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            for alias in statement.names:
                name = alias.asname or alias.name.split(".", 1)[0]
                current[name] = _UNKNOWN_STATIC_STRING
            return current
        if isinstance(statement, ast.Delete):
            for target in statement.targets:
                current = self._bind_unknown(current, target)
        return current


def _production_trading_surfaces(root: Path) -> tuple[str, ...]:
    findings: set[str] = set()
    for relative in ACTION_SURFACE_PATHS:
        path = root / relative
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, SyntaxError):
            continue
        findings.update(_ModuleSurfaceScanner(relative).scan(tree))
    return tuple(sorted(findings))


def _display_status(text: str) -> str:
    value = _line_value(text, "Status") or _line_value(text, "状态")
    normalized = value.strip().strip("*")
    quoted = re.match(r"^`([^`]+)`", normalized)
    return (quoted.group(1) if quoted else normalized.strip("`")).lower()


def _record_date(text: str, *labels: str) -> date | None:
    value = _first_line_value(
        text,
        *(labels or ("Decision date", "Review date", "Audit date", "Date", "日期")),
    )
    return _strict_date(value)


def _dated_pass_record(text: str, as_of: date) -> bool:
    record_date = _record_date(text)
    return (
        _display_status(text) == "passed"
        and record_date is not None
        and record_date <= as_of
    )


def _markdown_section(text: str, heading: str, *, level: int = 2) -> str:
    marker = "#" * level
    match = re.search(
        rf"(?ms)^{re.escape(marker)}\s+{re.escape(heading)}\s*\n"
        rf"(.*?)(?=^#{{1,{level}}}\s+|\Z)",
        text,
    )
    return match.group(1).strip() if match else ""


def _markdown_rows(text: str) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _unique_labeled_rows(
    text: str, expected: frozenset[str]
) -> dict[str, tuple[str, ...]] | None:
    rows = [row for row in _markdown_rows(text) if row and row[0] in expected]
    labels = [row[0] for row in rows]
    if len(rows) != len(expected) or set(labels) != expected:
        return None
    return {row[0]: row for row in rows}


def _plain_cell(value: str) -> str:
    return value.strip().replace("`", "").strip()


def _pass_cell(value: str) -> bool:
    return bool(re.fullmatch(r"pass(?:\s*[:;].*)?", _plain_cell(value), re.IGNORECASE))


def _sha256_cell(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", _plain_cell(value)))


def _duration_seconds(value: str) -> int | None:
    normalized = _plain_cell(value).lower()
    parts = {
        unit: int(amount)
        for amount, unit in re.findall(
            r"(\d+)\s*(hours?|minutes?|seconds?)", normalized
        )
    }
    if not parts:
        return None
    return sum(
        amount
        * (3600 if unit.startswith("hour") else 60 if unit.startswith("minute") else 1)
        for unit, amount in parts.items()
    )


def _performance_evidence_passed(text: str, as_of: date) -> tuple[bool, float | None]:
    operation_rows = _unique_labeled_rows(
        _markdown_section(text, "Real repository scale"), PERFORMANCE_OPERATIONS
    )
    operation_passed = operation_rows is not None
    if operation_rows is not None:
        for row in operation_rows.values():
            if len(row) != 5:
                operation_passed = False
                continue
            p95_match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)", _plain_cell(row[2]))
            slo_match = re.fullmatch(r"<\s*([0-9]+(?:\.[0-9]+)?)", _plain_cell(row[3]))
            if (
                p95_match is None
                or slo_match is None
                or float(p95_match.group(1)) >= float(slo_match.group(1))
                or not _pass_cell(row[4])
            ):
                operation_passed = False

    measured = _markdown_section(text, "Measured facts", level=3)
    candidate_labels = frozenset(
        {
            "Fixture rows",
            "Candidate schema",
            "Warmups / measured repeats",
            "Nearest-rank p95",
            "SLO",
            "Result",
        }
    )
    candidate_rows = _unique_labeled_rows(measured, candidate_labels)
    candidate_p95: float | None = None
    candidate_passed = candidate_rows is not None
    if candidate_rows is not None:
        values = {
            label: row[1] if len(row) == 2 else ""
            for label, row in candidate_rows.items()
        }
        p95_match = re.fullmatch(
            r"([0-9]+(?:\.[0-9]+)?)\s*s", _plain_cell(values["Nearest-rank p95"])
        )
        slo_match = re.fullmatch(
            r"<\s*([0-9]+(?:\.[0-9]+)?)\s*s", _plain_cell(values["SLO"])
        )
        if p95_match is not None:
            candidate_p95 = float(p95_match.group(1))
        candidate_passed = bool(
            re.fullmatch(r"10,000 exactly", _plain_cell(values["Fixture rows"]))
            and re.fullmatch(
                r"current version 3", _plain_cell(values["Candidate schema"])
            )
            and re.fullmatch(
                r"1\s*/\s*7", _plain_cell(values["Warmups / measured repeats"])
            )
            and p95_match is not None
            and slo_match is not None
            and candidate_p95 is not None
            and candidate_p95 < float(slo_match.group(1)) <= 2.0
            and _pass_cell(values["Result"])
        )
    writes = re.search(
        r"(?mi)^-\s*Read-only check:\s*authoritative writes:\s*(\d+)\s*$", text
    )
    passed = (
        _dated_pass_record(text, as_of)
        and operation_passed
        and candidate_passed
        and writes is not None
        and int(writes.group(1)) == 0
    )
    return passed, candidate_p95


def _dashboard_smoke_routes(text: str) -> frozenset[str]:
    match = re.search(
        r"(?s)Dashboard GET smoke returned HTTP 200 for (.*?)"
        r"No Web mutation was used\.",
        text,
    )
    if match is None:
        return frozenset()
    return frozenset(re.findall(r"`(/[^`]*)`", match.group(1)))


def _required_recovery_cell(values: dict[str, str], label: str) -> str:
    value = _plain_cell(values[label])
    if not value:
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain {label} must be a non-empty value"
        )
    return value


def _recovery_relative_path(value: str, label: str) -> Path:
    path = Path(value)
    if (
        path.is_absolute()
        or not path.parts
        or "\\" in value
        or any(part in {".", ".."} for part in path.parts)
    ):
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain {label} must be a safe "
            "repository-relative path"
        )
    return path


def _recovery_chain_evidence(text: str) -> _RecoveryChainEvidence | None:
    section = _markdown_section(text, "Candidate to Source to asset sample")
    if not section:
        return None
    rows = [
        row for row in _markdown_rows(section) if row and row[0] in RECOVERY_CHAIN_ROWS
    ]
    labels = [row[0] for row in rows]
    if set(labels) != RECOVERY_CHAIN_ROWS:
        return None
    if len(labels) != len(RECOVERY_CHAIN_ROWS):
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain rows must be unique"
        )
    if any(len(row) != 2 for row in rows):
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain rows must contain exactly two columns"
        )
    values = {row[0]: row[1] for row in rows}

    candidate = _required_recovery_cell(values, "Candidate")
    candidate_match = re.fullmatch(
        r"(CND-[0-9a-f]{20}),\s*status\s*([a-z][a-z0-9_-]*)", candidate
    )
    if candidate_match is None:
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain Candidate is malformed"
        )

    channel_id = _required_recovery_cell(values, "Channel")
    if re.fullmatch(r"CHN-[a-z0-9]+(?:-[a-z0-9]+)*", channel_id) is None:
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain Channel is malformed"
        )

    candidate_url = _required_recovery_cell(values, "Candidate URL")
    try:
        parsed_url = urlsplit(candidate_url)
    except ValueError as exc:
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain Candidate URL is malformed"
        ) from exc
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
        or any(character.isspace() for character in candidate_url)
    ):
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain Candidate URL is malformed"
        )

    source_id = _required_recovery_cell(values, "Promoted Source")
    if re.fullmatch(r"SRC-\d{8}-\d{3}", source_id) is None:
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain Promoted Source is malformed"
        )
    source_record = _recovery_relative_path(
        _required_recovery_cell(values, "Source record"), "Source record"
    )
    raw_asset = _recovery_relative_path(
        _required_recovery_cell(values, "Raw asset"), "Raw asset"
    )

    raw_bytes = _required_recovery_cell(values, "Raw bytes")
    if re.fullmatch(r"(?:[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)", raw_bytes) is None:
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain Raw bytes is malformed"
        )
    sha256 = _required_recovery_cell(values, "Expected and actual SHA-256")
    if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
        raise ReleaseEvaluationError(
            f"{RECOVERY_PATH}: recovery chain SHA-256 is malformed"
        )
    return _RecoveryChainEvidence(
        candidate_id=candidate_match.group(1),
        candidate_status=candidate_match.group(2),
        channel_id=channel_id,
        candidate_url=candidate_url,
        source_id=source_id,
        source_record=source_record,
        raw_asset=raw_asset,
        raw_bytes=int(raw_bytes.replace(",", "")),
        sha256=sha256,
    )


def _candidate_recovery_row(
    root: Path, candidate_id: str
) -> tuple[str, str, str, str, str] | None:
    path = candidate_db_path(root)
    if not path.is_file():
        return None
    connection: sqlite3.Connection | None = None
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        row = connection.execute(
            "SELECT candidate_id, channel_id, canonical_url, status, "
            "promoted_source_id FROM candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
    except (OSError, sqlite3.Error):
        return None
    finally:
        if connection is not None:
            connection.close()
    if row is None:
        return None
    return (
        str(row[0] or ""),
        str(row[1] or ""),
        str(row[2] or ""),
        str(row[3] or ""),
        str(row[4] or ""),
    )


def _path_sha256(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _recovery_chain_matches_repository(
    root: Path,
    objects: list[ResearchObject],
    chain: _RecoveryChainEvidence,
) -> bool:
    candidate = _candidate_recovery_row(root, chain.candidate_id)
    if candidate is None:
        return False
    candidate_id, channel_id, candidate_url, status, source_id = candidate
    if (
        candidate_id != chain.candidate_id
        or channel_id != chain.channel_id
        or candidate_url != chain.candidate_url
        or status != chain.candidate_status
        or status != "promoted"
        or source_id != chain.source_id
    ):
        return False

    by_id = {obj.object_id: obj for obj in objects}
    source = by_id.get(chain.source_id)
    channel = by_id.get(chain.channel_id)
    if (
        source is None
        or source.object_type != "source"
        or channel is None
        or channel.object_type != "source_channel"
    ):
        return False
    try:
        source_record = source.path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    if source_record != chain.source_record:
        return False

    source_url = str(
        source.metadata.get("canonical_url") or source.metadata.get("url") or ""
    )
    declared_assets = source.metadata.get("asset_paths")
    if (
        source_url != chain.candidate_url
        or not isinstance(declared_assets, list)
        or chain.raw_asset.as_posix() not in {str(value) for value in declared_assets}
        or str(source.metadata.get("content_sha256") or "") != chain.sha256
    ):
        return False

    try:
        asset_path = (root / chain.raw_asset).resolve()
        if not asset_path.is_relative_to(root.resolve()) or not asset_path.is_file():
            return False
        actual_bytes = asset_path.stat().st_size
    except OSError:
        return False
    return actual_bytes == chain.raw_bytes and _path_sha256(asset_path) == chain.sha256


def _recovery_evidence_passed(
    root: Path, text: str, as_of: date, objects: list[ResearchObject]
) -> bool:
    objectives = _unique_labeled_rows(
        _markdown_section(text, "Recovery objectives"), RECOVERY_OBJECTIVES
    )
    procedures = _unique_labeled_rows(
        _markdown_section(text, "Procedure and evidence"), RECOVERY_PROCEDURES
    )
    chain = _recovery_chain_evidence(text)
    if objectives is None or procedures is None or chain is None:
        return False
    if any(len(row) != 3 for row in objectives.values()):
        return False
    rto = objectives["Recovery time objective (RTO)"]
    rpo = objectives["Recovery point objective (RPO)"]
    objective_passed = (
        _plain_cell(rto[1]).lower() == "less than 4 hours"
        and (rto_seconds := _duration_seconds(rto[2])) is not None
        and rto_seconds < 4 * 60 * 60
        and _pass_cell(rto[2])
        and _plain_cell(rpo[1]).lower() == "no more than 24 hours"
        and (rpo_seconds := _duration_seconds(rpo[2])) is not None
        and rpo_seconds <= 24 * 60 * 60
        and _pass_cell(rpo[2])
        and _plain_cell(objectives["Repository validation"][1]).lower()
        == "0 errors, 0 warnings"
        and _pass_cell(objectives["Repository validation"][2])
        and "sqlite integrity ok, hash exact"
        in _plain_cell(objectives["Candidate snapshot integrity"][1]).lower()
        and _pass_cell(objectives["Candidate snapshot integrity"][2])
        and re.fullmatch(
            r"pass:\s*148/148",
            _plain_cell(objectives["Archived Source assets"][2]),
            re.IGNORECASE,
        )
        is not None
    )
    procedure_passed = (
        all(len(row) == 3 and _pass_cell(row[2]) for row in procedures.values())
        and "0 errors, 0 warnings"
        in _plain_cell(procedures["Repository validation"][2]).lower()
    )
    commit = _plain_cell(_line_value(text, "Commit"))
    snapshot_hash = _line_value(text, "Snapshot SHA-256")
    chain_passed = _recovery_chain_matches_repository(root, objects, chain)
    return bool(
        _dated_pass_record(text, as_of)
        and re.fullmatch(r"[0-9a-f]{40}", commit)
        and objective_passed
        and procedure_passed
        and _sha256_cell(snapshot_hash)
        and _plain_cell(_line_value(text, "Candidate DB schema version")) == "2"
        and _plain_cell(_line_value(text, "SQLite integrity")).lower() == "ok"
        and chain_passed
        and _dashboard_smoke_routes(text) == DASHBOARD_SMOKE_ROUTES
    )


def _recovery_boundaries_passed(text: str) -> bool:
    boundary = " ".join(_markdown_section(text, "Recovery boundary").lower().split())
    return all(
        statement in boundary
        for statement in (
            (
                "git restores rules, markdown authority, code, tests, and "
                "generated-index inputs."
            ),
            (
                "the separate backups restore source assets and the candidate "
                "operational database."
            ),
            "did not restore secrets",
            ".env",
            "provider credentials",
            "launchd",
            "private remote configuration",
            "off-device encryption keys",
            "generated indexes are rebuilt, not treated as recovery authority.",
        )
    )


def _migration_evidence_passed(text: str, as_of: date) -> bool:
    baseline = _unique_labeled_rows(
        _markdown_section(text, "Baseline"), MIGRATION_BASELINE_CHECKS
    )
    forward = _unique_labeled_rows(
        _markdown_section(text, "Forward migration"), MIGRATION_COMPANIES
    )
    rollback = _unique_labeled_rows(
        _markdown_section(text, "Failure injection and rollback"),
        MIGRATION_ROLLBACK_CHECKS,
    )
    if baseline is None or forward is None or rollback is None:
        return False
    baseline_values = {
        label: row[1] if len(row) == 2 else "" for label, row in baseline.items()
    }
    baseline_passed = (
        _plain_cell(baseline_values["Repository validation"]).lower()
        == "pass: 0 errors, 0 warnings"
        and all(
            _pass_cell(baseline_values[label])
            for label in (
                "Global index check",
                "PRJ-001 index check",
                "PRJ-002 index check",
                "Schema and migration compatibility tests",
            )
        )
        and _plain_cell(baseline_values["Formal objects hashed"]) == "1035"
        and _plain_cell(baseline_values["Candidate DB schema version"]) == "2"
        and _sha256_cell(baseline_values["Candidate DB SHA-256"])
    )
    forward_passed = all(
        len(row) == 3
        and _sha256_cell(row[1])
        and _sha256_cell(row[2])
        and _plain_cell(row[1]) != _plain_cell(row[2])
        for row in forward.values()
    )
    rollback_values = {
        label: row[1] if len(row) == 2 else "" for label, row in rollback.items()
    }
    rollback_passed = (
        _plain_cell(rollback_values["Migrated files restored"]).lower() == "pass: 8/8"
        and _plain_cell(rollback_values["All formal object bytes restored"]).lower()
        == "pass: 1035/1035"
        and all(
            _pass_cell(rollback_values[label])
            for label in (
                "Candidate DB SHA-256 unchanged",
                "Candidate DB schema version: 2",
                "Repository validation",
                "Global, PRJ-001, PRJ-002 indexes",
                "Full pytest",
            )
        )
        and "0 errors, 0 warnings"
        in _plain_cell(rollback_values["Repository validation"]).lower()
    )
    normalized = " ".join(text.split())
    return bool(
        _dated_pass_record(text, as_of)
        and re.fullmatch(r"[0-9a-f]{40}", _plain_cell(_line_value(text, "Commit")))
        and _plain_cell(_line_value(text, "Source state"))
        == "v0.2 legacy Company objects at schema_version: 1"
        and _plain_cell(_line_value(text, "Target state"))
        == "v0.3 schema_version 2 compatibility path"
        and _plain_cell(_line_value(text, "Migration"))
        == "MIG-v0.3-F018-company-schema-v2"
        and _plain_cell(_line_value(text, "Target set"))
        == "8 legacy Company records only"
        and "selected exactly 8/8 legacy Company records" in normalized
        and "All 1027/1027 unowned formal objects retained their original bytes"
        in normalized
        and "engine refused with `rollback precondition changed`" in normalized
        and baseline_passed
        and forward_passed
        and rollback_passed
    )


def _verification_covers_paths(
    root: Path,
    record: str,
    paths: tuple[str, ...],
    *,
    extra_status_paths: tuple[str, ...] = (),
) -> bool:
    commit = _plain_cell(_line_value(record, "Commit"))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        return False
    try:
        historical = subprocess.run(
            ["git", "-C", str(root), "diff", "--quiet", commit, "HEAD", "--", *paths],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        current = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *paths,
                *extra_status_paths,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return historical.returncode == 0 and current.returncode == 0 and not current.stdout


def _verification_covers_tree(root: Path, record: str) -> bool:
    return _verification_covers_paths(
        root,
        record,
        QUALITY_PATHS,
        extra_status_paths=(ENGINEERING_VERIFICATION_PATH,),
    )


def _load_json_object(root: Path, relative: str) -> dict[str, Any] | None:
    path = root / relative
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseEvaluationError(f"{relative}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseEvaluationError(f"{relative}: JSON root must be an object")
    return payload


def _load_structured_gate(
    root: Path,
    acceptance_path: str,
    data_path: str,
) -> tuple[str, dict[str, Any] | None, str]:
    acceptance = _read(root, acceptance_path)
    payload = _load_json_object(root, data_path)
    if payload is not None:
        return acceptance, payload, ""
    missing = [data_path]
    if not acceptance:
        missing.insert(0, acceptance_path)
    return acceptance, None, "missing: " + ", ".join(missing)


def _required_mapping(
    payload: dict[str, Any], key: str, relative: str
) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ReleaseEvaluationError(f"{relative}: {key} must be an object")
    return value


def _required_list(payload: dict[str, Any], key: str, relative: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ReleaseEvaluationError(f"{relative}: {key} must be an array")
    return value


def _required_bool(payload: dict[str, Any], key: str, relative: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ReleaseEvaluationError(f"{relative}: {key} must be boolean")
    return value


def _required_string(payload: dict[str, Any], key: str, relative: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReleaseEvaluationError(f"{relative}: {key} must be a non-empty string")
    return value.strip()


def _unique_object_rows(
    payload: dict[str, Any],
    key: str,
    identifier_key: str,
    relative: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, raw in enumerate(_required_list(payload, key, relative)):
        context = f"{relative}: {key}[{index}]"
        if not isinstance(raw, dict):
            raise ReleaseEvaluationError(f"{context} must be an object")
        identifier = _required_string(raw, identifier_key, context)
        if identifier in identifiers:
            raise ReleaseEvaluationError(
                f"{relative}: duplicate {identifier_key} {identifier}"
            )
        identifiers.add(identifier)
        rows.append(raw)
    return rows


def _backlog_status(text: str, work_package: str) -> str:
    for line in text.splitlines():
        if not re.match(rf"^\|\s*{re.escape(work_package)}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        return cells[-1].lower() if len(cells) >= 2 else ""
    return ""


def _relative_paths(root: Path, objects: list[ResearchObject]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(obj.path.relative_to(root))
                for obj in objects
                if obj.path.is_relative_to(root)
            }
        )
    )


def _approval_paths_for(
    root: Path,
    approvals: list[ResearchObject],
    target_ids: set[str],
) -> tuple[str, ...]:
    related = [
        approval
        for approval in approvals
        if target_ids.intersection(
            str(target_id) for target_id in approval.metadata.get("target_ids", [])
        )
    ]
    return _relative_paths(root, related)


def _approved_targets_v03(
    objects: list[ResearchObject], as_of: date
) -> tuple[set[str], list[ResearchObject]]:
    approvals = [
        obj
        for obj in objects
        if obj.object_type == "review"
        and obj.metadata.get("status") == "applied"
        and obj.metadata.get("decision") == "approve"
        and _current_human_evidence(
            obj.metadata.get("reviewer"), obj.metadata.get("reviewed_at"), as_of
        )
    ]
    targets = {
        str(target_id)
        for approval in approvals
        for target_id in approval.metadata.get("target_ids", [])
    }
    return targets, approvals


def _v03_cadence_records(
    root: Path, cadence: str, pilot_start: date | None, as_of: date
) -> list[Path]:
    if pilot_start is None:
        return []
    records: list[Path] = []
    pattern = f"**/Reviews/{cadence}/*.md"
    for path in sorted((root / "05_Research").glob(pattern)):
        text = path.read_text(encoding="utf-8")
        review_date = _record_date(text, "Review date")
        if (
            _line_value(text, "Review status").lower() == "completed"
            and _current_human_evidence(
                _line_value(text, "Reviewer"), review_date, as_of
            )
            and review_date is not None
            and review_date >= pilot_start
            and bool(_line_value(text, "Metrics snapshot"))
            and bool(re.search(r"(?i)\bv0\.3\b|\bF-021\b|30[- ]day Pilot", text))
        ):
            records.append(path)
    return records


def _impact_approval_allowed(decision: str, sample_size: int) -> bool:
    if decision == "approve":
        return True
    counted = re.fullmatch(
        r"approve all (\d+) in-scope events; evt-046 excluded", decision
    )
    return counted is not None and int(counted.group(1)) == sample_size


def _impact_gate_evidence(
    root: Path, as_of: date, objects: list[ResearchObject]
) -> tuple[bool, str, dict[str, Any] | None]:
    acceptance, payload, missing = _load_structured_gate(
        root, IMPACT_ACCEPTANCE_PATH, IMPACT_JUDGMENTS_PATH
    )
    if payload is None:
        return False, missing, None

    sample_size = payload.get("sample_size")
    judgments = _unique_object_rows(
        payload, "judgments", "event_id", IMPACT_JUDGMENTS_PATH
    )
    metrics = _required_mapping(payload, "metrics", IMPACT_JUDGMENTS_PATH)
    approved = _required_mapping(payload, "approved", IMPACT_JUDGMENTS_PATH)
    if (
        not isinstance(sample_size, int)
        or isinstance(sample_size, bool)
        or sample_size < 1
    ):
        raise ReleaseEvaluationError(
            f"{IMPACT_JUDGMENTS_PATH}: sample_size must be a positive integer"
        )
    metrics_count = metrics.get("n")
    if not isinstance(metrics_count, int) or isinstance(metrics_count, bool):
        raise ReleaseEvaluationError(
            f"{IMPACT_JUDGMENTS_PATH}: metrics.n must be an integer"
        )
    if len(judgments) != sample_size or metrics_count != sample_size:
        raise ReleaseEvaluationError(
            f"{IMPACT_JUDGMENTS_PATH}: judgments and metrics.n must match sample_size"
        )
    by_id = {obj.object_id: obj for obj in objects}
    judgment_pass = True
    reviewed_events = True
    for index, judgment in enumerate(judgments):
        context = f"{IMPACT_JUDGMENTS_PATH}: judgments[{index}]"
        event_id = _required_string(judgment, "event_id", context)
        event = by_id.get(event_id)
        if event is None or event.object_type != "event":
            raise ReleaseEvaluationError(
                f"{IMPACT_JUDGMENTS_PATH}: {event_id} is not an existing Event"
            )
        reviewed_events = reviewed_events and (
            event.metadata.get("review_status") == "reviewed"
        )
        direct = _required_bool(judgment, "direct_precision", context)
        mechanism = _required_bool(judgment, "mechanism_backed", context)
        direction = _required_bool(judgment, "direction_ok", context)
        horizon = _required_bool(judgment, "horizon_ok", context)
        contrary = _required_bool(judgment, "contrary_omitted", context)
        judgment_pass = judgment_pass and all(
            (direct, mechanism, direction, horizon, not contrary)
        )
    gate_flags = all(
        _required_bool(metrics, key, IMPACT_JUDGMENTS_PATH)
        for key in (
            "gate_direct_precision",
            "gate_mechanism_backing",
            "gate_contrary_omissions",
        )
    )
    reviewer = _required_string(approved, "by", IMPACT_JUDGMENTS_PATH)
    approved_date = _required_string(approved, "date", IMPACT_JUDGMENTS_PATH)
    decision = _required_string(approved, "decision", IMPACT_JUDGMENTS_PATH)
    normalized_decision = decision.lower()
    decision_allowed = _impact_approval_allowed(normalized_decision, sample_size)
    if not decision_allowed:
        raise ReleaseEvaluationError(
            f"{IMPACT_JUDGMENTS_PATH}: approved.decision is not an allowed "
            "terminal decision"
        )
    accepted = _dated_pass_record(acceptance, as_of)
    human_approved = (
        _current_human_evidence(reviewer, approved_date, as_of) and decision_allowed
    )
    complete_sample = sample_size == IMPACT_EXPECTED_SAMPLE_SIZE
    passed = (
        complete_sample
        and reviewed_events
        and judgment_pass
        and gate_flags
        and accepted
        and human_approved
    )
    observed = (
        f"{sample_size}/{IMPACT_EXPECTED_SAMPLE_SIZE} structured judgments; "
        f"sampled Events {'reviewed' if reviewed_events else 'not all reviewed'}; "
        f"C-020 {'passed' if accepted else 'not passed'}; "
        f"human approval {'valid' if human_approved else 'invalid or future'}"
    )
    return passed, observed, payload


def _mode_gate_evidence(
    root: Path, as_of: date, objects: list[ResearchObject]
) -> tuple[bool, str, dict[str, Any] | None]:
    acceptance, payload, missing = _load_structured_gate(
        root, MODE_ACCEPTANCE_PATH, MODE_JUDGMENTS_PATH
    )
    if payload is None:
        return False, missing, None

    status = _required_string(payload, "status", MODE_JUDGMENTS_PATH).lower()
    dimensions = _required_list(payload, "dimensions", MODE_JUDGMENTS_PATH)
    runs = _unique_object_rows(payload, "runs", "run_id", MODE_JUDGMENTS_PATH)
    verdict = _required_mapping(payload, "gate_verdict", MODE_JUDGMENTS_PATH)
    reviewer = _required_string(payload, "reviewer", MODE_JUDGMENTS_PATH)
    confirmed_at = _required_string(payload, "confirmed_at", MODE_JUDGMENTS_PATH)
    if status != "confirmed":
        raise ReleaseEvaluationError(
            f"{MODE_JUDGMENTS_PATH}: status is not an allowed terminal status"
        )
    if (
        any(not isinstance(dimension, str) for dimension in dimensions)
        or set(dimensions) != MODE_DIMENSIONS
        or len(dimensions) != len(MODE_DIMENSIONS)
    ):
        raise ReleaseEvaluationError(
            f"{MODE_JUDGMENTS_PATH}: dimensions do not match the eight-field rubric"
        )
    expected_runs = verdict.get("runs")
    if not isinstance(expected_runs, int) or isinstance(expected_runs, bool):
        raise ReleaseEvaluationError(
            f"{MODE_JUDGMENTS_PATH}: gate_verdict.runs must be an integer"
        )
    if expected_runs != MODE_EXPECTED_RUN_COUNT or len(runs) != expected_runs:
        raise ReleaseEvaluationError(
            f"{MODE_JUDGMENTS_PATH}: expected exactly "
            f"{MODE_EXPECTED_RUN_COUNT} approved run rows"
        )
    by_id = {obj.object_id: obj for obj in objects}
    cases: set[str] = set()
    scores_valid = True
    for index, run in enumerate(runs):
        context = f"{MODE_JUDGMENTS_PATH}: runs[{index}]"
        run_id = _required_string(run, "run_id", context)
        case_id = _required_string(run, "case", context)
        recorded_mode = _required_string(run, "mode", context)
        run_object = by_id.get(run_id)
        if run_object is None or run_object.object_type != "analysis_run":
            raise ReleaseEvaluationError(
                f"{MODE_JUDGMENTS_PATH}: {run_id} is not an existing Analysis Run"
            )
        if run_object.metadata.get("status") != "completed":
            raise ReleaseEvaluationError(
                f"{MODE_JUDGMENTS_PATH}: {run_id} is not a completed Analysis Run"
            )
        mode_id = str(run_object.metadata.get("mode_id", ""))
        mode_match = re.fullmatch(r"MOD-ANL-(.+)-v\d+", mode_id)
        mode_object = by_id.get(mode_id)
        if (
            mode_match is None
            or mode_object is None
            or mode_object.object_type != "analysis_mode"
        ):
            raise ReleaseEvaluationError(
                f"{MODE_JUDGMENTS_PATH}: {run_id} references an unregistered mode"
            )
        mode_slug = mode_match.group(1)
        mode_version = mode_id.rsplit("-v", 1)[-1]
        allowed_labels = {mode_slug, f"{mode_slug}-v{mode_version}"}
        if recorded_mode not in allowed_labels:
            raise ReleaseEvaluationError(
                f"{MODE_JUDGMENTS_PATH}: {run_id} mode {recorded_mode!r} does not "
                f"match {mode_id}"
            )
        cases.add(case_id)
        scores = _required_mapping(run, "scores", context)
        if set(scores) != MODE_DIMENSIONS:
            raise ReleaseEvaluationError(
                f"{MODE_JUDGMENTS_PATH}: {run_id} scores do not match dimensions"
            )
        for score in scores.values():
            if (
                not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not 0.0 <= float(score) <= 1.0
            ):
                raise ReleaseEvaluationError(
                    f"{MODE_JUDGMENTS_PATH}: {run_id} has an invalid score"
                )
        scores_valid = scores_valid and all(
            float(score) >= 0.7 for score in scores.values()
        )
    if len(cases) != MODE_EXPECTED_CASE_COUNT:
        raise ReleaseEvaluationError(
            f"{MODE_JUDGMENTS_PATH}: expected exactly "
            f"{MODE_EXPECTED_CASE_COUNT} distinct cases"
        )
    thresholds = _required_mapping(verdict, "thresholds", MODE_JUDGMENTS_PATH)
    threshold_pass = all(
        _required_bool(thresholds, key, MODE_JUDGMENTS_PATH)
        for key in (
            "citation_resolvable_100pct",
            "no_outside_facts",
            "question_coverage_ge_90pct",
            "counterevidence_omission_lt_10pct",
            "human_incremental_value_ge_70pct",
            "open_discovery_judgeable_ge_half",
            "no_majority_voting",
        )
    )
    accepted = _dated_pass_record(acceptance, as_of)
    human_confirmed = status == "confirmed" and _current_human_evidence(
        reviewer, confirmed_at, as_of
    )
    passed = (
        _required_bool(verdict, "pass", MODE_JUDGMENTS_PATH)
        and scores_valid
        and threshold_pass
        and accepted
        and human_confirmed
    )
    observed = (
        f"{len(cases)} cases/{len(runs)} runs; "
        f"D-020 {'passed' if accepted else 'not passed'}; "
        f"human confirmation {'valid' if human_confirmed else 'invalid or future'}"
    )
    return passed, observed, payload


def _check_v03(
    key: str,
    passed: bool,
    requirement: str,
    observed: str,
    *evidence_paths: str,
) -> ReleaseCheck:
    return ReleaseCheck(
        key=key,
        passed=passed,
        requirement=requirement,
        observed=observed,
        evidence_paths=(V03_PHASE6_PATH, *evidence_paths),
    )


def release_readiness_v03(
    root: Path,
    *,
    as_of: str | None = None,
) -> ReleaseReadiness:
    """Evaluate the ordered Phase 6 v0.3 gate without mutating evidence."""
    root = root.resolve()
    effective_as_of = _validate_as_of(
        date.today().isoformat() if as_of is None else as_of
    )
    as_of_date = date.fromisoformat(effective_as_of)

    objects, findings = validate_repository(root)
    errors = [finding for finding in findings if finding.level == "error"]
    warnings = [finding for finding in findings if finding.level == "warning"]
    reference_errors = [finding for finding in errors if finding.code.startswith("REF")]
    global_drift = index_drift(root, render_indexes(objects))
    project_ids = sorted(
        obj.object_id
        for obj in objects
        if obj.object_type == "project" and obj.metadata.get("status") == "active"
    )
    project_drift = {
        project_id: index_drift(root, render_project_indexes(objects, project_id))
        for project_id in project_ids
    }
    drift_count = len(global_drift) + sum(
        len(paths) for paths in project_drift.values()
    )
    approved_targets, approvals = _approved_targets_v03(objects, as_of_date)

    sectors = [
        obj
        for obj in objects
        if obj.object_type == "sector" and obj.metadata.get("status") == "active"
    ]
    core_companies = [
        obj
        for obj in objects
        if obj.object_type == "company" and obj.metadata.get("coverage_tier") == "core"
    ]
    reviewed_sectors = [
        obj
        for obj in sectors
        if obj.metadata.get("review_status") == "reviewed"
        and obj.object_id in approved_targets
    ]
    reviewed_core = [
        obj
        for obj in core_companies
        if obj.metadata.get("review_status") == "reviewed"
        and obj.object_id in approved_targets
    ]
    universe_target_ids = {obj.object_id for obj in [*sectors, *core_companies]}
    universe_acceptance = _read(root, UNIVERSE_ACCEPTANCE_PATH)
    universe_record_passed = _dated_pass_record(universe_acceptance, as_of_date)
    universe_passed = (
        8 <= len(sectors) <= 10
        and 30 <= len(core_companies) <= 54
        and len(reviewed_sectors) == len(sectors)
        and len(reviewed_core) == len(core_companies)
        and universe_record_passed
    )

    checks: list[ReleaseCheck] = [
        _check_v03(
            "evidence_universe.pilot_universe",
            universe_passed,
            (
                "Pilot Universe has 8-10 reviewed Sectors, 30-54 reviewed Core "
                "Companies, and a passed spot-check"
            ),
            f"{len(reviewed_sectors)}/{len(sectors)} Sectors and "
            f"{len(reviewed_core)}/{len(core_companies)} Core Companies "
            "human-approved; "
            f"A-020 {'passed' if universe_record_passed else 'missing or not passed'}",
            UNIVERSE_ACCEPTANCE_PATH,
            "05_Research/Reviews/WP120_Entity_Review_Packet.md",
            *_approval_paths_for(root, approvals, universe_target_ids),
        ),
        _check_v03(
            "evidence_universe.authoritative_references",
            not reference_errors,
            "all authoritative object references resolve to the expected object types",
            f"{len(reference_errors)} reference errors across "
            f"{len(objects)} formal objects",
            "01_Inbox",
            "02_Knowledge",
            "03_Theses",
            "04_Evidence",
            "05_Research",
            "06_Reports",
        ),
        _check_v03(
            "evidence_universe.repository_validation",
            not errors and not warnings and drift_count == 0,
            (
                "strict validation has 0 errors and 0 warnings; global and "
                "active-project indexes have 0 drift"
            ),
            f"{len(errors)} errors, {len(warnings)} warnings, "
            f"{drift_count} index drift files",
            "08_Indexes",
        ),
    ]

    backlog = _read(root, V03_BACKLOG_PATH)
    candidate_acceptance = _read(root, CANDIDATE_ACCEPTANCE_PATH)
    candidate_gate_passed = _dated_pass_record(
        candidate_acceptance, as_of_date
    ) and _current_human_evidence(
        _first_line_value(candidate_acceptance, "Reviewer", "判定人"),
        _record_date(candidate_acceptance),
        as_of_date,
    )
    pilot_acceptance = _read(root, PILOT_ACCEPTANCE_PATH)
    pilot_start = _strict_date(
        _first_line_value(pilot_acceptance, "Pilot start date", "Start date")
    )
    pilot_decision = _first_line_value(
        pilot_acceptance, "Release decision", "Decision"
    ).lower()
    pilot_reviewer = _line_value(pilot_acceptance, "Reviewer")
    pilot_acceptance_date = _record_date(pilot_acceptance)
    thirty_days_elapsed = bool(
        pilot_start is not None and as_of_date >= pilot_start + timedelta(days=29)
    )
    pilot_completed = (
        candidate_gate_passed
        and _backlog_status(backlog, "WP-620") == "completed"
        and thirty_days_elapsed
        and _display_status(pilot_acceptance) == "passed"
        and pilot_decision == "approve"
        and _current_human_evidence(pilot_reviewer, pilot_acceptance_date, as_of_date)
        and pilot_acceptance_date is not None
        and pilot_start is not None
        and pilot_acceptance_date >= pilot_start + timedelta(days=29)
    )
    pilot_observed = (
        "B-026 and WP-620 completed with a real 30-day Pilot and human acceptance"
        if pilot_completed
        else f"B-026 {_display_status(candidate_acceptance) or 'missing'}; "
        f"WP-620 {_backlog_status(backlog, 'WP-620') or 'missing'}; "
        f"real 30-day Pilot acceptance "
        f"{'present' if pilot_acceptance else 'missing'}"
    )

    discovery_audit = _read(root, DISCOVERY_AUDIT_PATH)
    discovery_decision = _first_line_value(
        discovery_audit, "Audit decision", "Decision"
    ).lower()
    discovery_reviewer = _line_value(discovery_audit, "Reviewer")
    discovery_date = _record_date(discovery_audit)
    no_silent_misses = (
        _display_status(discovery_audit) == "passed"
        and _line_value(discovery_audit, "Review status").lower() == "reviewed"
        and discovery_decision == "approve"
        and _current_human_evidence(discovery_reviewer, discovery_date, as_of_date)
        and "remains open" not in discovery_audit.lower()
    )
    discovery_observed = (
        "reviewed audit passes with no unresolved missed or unauthorized runs"
        if no_silent_misses
        else (
            "operational audit pending or unresolved; no-silent-missed-run "
            "Gate not approved"
        )
    )

    enabled_channels = [
        obj
        for obj in objects
        if obj.object_type == "source_channel" and obj.metadata.get("enabled") is True
    ]
    licensed_channels = [
        obj
        for obj in enabled_channels
        if obj.metadata.get("review_status") == "reviewed"
        and obj.metadata.get("license_status") == "reviewed"
        and bool(obj.metadata.get("license_notes"))
        and _human_date_allowed(obj.metadata.get("robots_checked_at"), as_of_date)
        and obj.object_id in approved_targets
    ]
    license_audit = _read(root, LICENSE_AUDIT_PATH)
    audited_channel_ids = set(re.findall(r"(?m)^\|\s*(CHN-[^ |]+)\s*\|", license_audit))
    enabled_ids = {obj.object_id for obj in enabled_channels}
    licenses_passed = (
        bool(enabled_channels)
        and len(licensed_channels) == len(enabled_channels)
        and audited_channel_ids == enabled_ids
        and _dated_pass_record(license_audit, as_of_date)
    )
    checks += [
        _check_v03(
            "ingestion.pilot_completion",
            pilot_completed,
            (
                "WP-620 records the completed real 30-day Pilot with dated "
                "human acceptance"
            ),
            pilot_observed,
            V03_BACKLOG_PATH,
            CANDIDATE_ACCEPTANCE_PATH,
            PILOT_ACCEPTANCE_PATH,
        ),
        _check_v03(
            "ingestion.no_silent_missed_runs",
            no_silent_misses,
            (
                "a reviewed operational audit confirms no silent missed runs "
                "or unauthorized capture"
            ),
            discovery_observed,
            DISCOVERY_AUDIT_PATH,
            "05_Research/Operations/Jobs",
        ),
        _check_v03(
            "ingestion.channel_licenses",
            licenses_passed,
            (
                "every enabled Channel is human-reviewed with license notes "
                "and a dated robots record"
            ),
            f"{len(licensed_channels)}/{len(enabled_channels)} enabled Channels "
            "qualify; "
            f"audit covers {len(audited_channel_ids)}/{len(enabled_ids)}",
            LICENSE_AUDIT_PATH,
            "02_Knowledge/Channels",
        ),
    ]

    impact_passed, impact_observed, impact_payload = _impact_gate_evidence(
        root, as_of_date, objects
    )
    mode_passed, mode_observed, mode_payload = _mode_gate_evidence(
        root, as_of_date, objects
    )
    impact_contrary_visible = bool(
        impact_payload
        and isinstance(impact_payload.get("judgments"), list)
        and all(
            isinstance(item, dict) and item.get("contrary_omitted") is False
            for item in impact_payload["judgments"]
        )
    )
    divergence_visible = bool(
        mode_payload
        and isinstance(mode_payload.get("dimensions"), list)
        and {"counterevidence", "explainable_divergence"}.issubset(
            set(mode_payload["dimensions"])
        )
        and isinstance(mode_payload.get("gate_verdict"), dict)
        and isinstance(mode_payload["gate_verdict"].get("thresholds"), dict)
        and mode_payload["gate_verdict"]["thresholds"].get("no_majority_voting") is True
    )
    checks += [
        _check_v03(
            "impact_analysis.impact_field_gate",
            impact_passed,
            "the approved Impact Field Gate is structurally valid and C-020 passed",
            impact_observed,
            IMPACT_ACCEPTANCE_PATH,
            IMPACT_JUDGMENTS_PATH,
        ),
        _check_v03(
            "impact_analysis.mode_field_gate",
            mode_passed,
            "the 10-case Mode Field Gate is structurally valid and D-020 passed",
            mode_observed,
            MODE_ACCEPTANCE_PATH,
            MODE_JUDGMENTS_PATH,
        ),
        _check_v03(
            "impact_analysis.counterevidence_divergence",
            impact_contrary_visible and divergence_visible,
            (
                "counterevidence and explainable cross-mode divergence remain "
                "visible without majority voting"
            ),
            "Impact contrary paths visible and Mode divergence rubric active"
            if impact_contrary_visible and divergence_visible
            else "counterevidence or divergence evidence missing or incomplete",
            IMPACT_JUDGMENTS_PATH,
            MODE_JUDGMENTS_PATH,
        ),
    ]

    forecasts = [obj for obj in objects if obj.object_type == "forecast"]
    approved_forecasts = [
        obj
        for obj in forecasts
        if obj.metadata.get("review_status") == "reviewed"
        and obj.metadata.get("status") in {"open", "resolved", "void", "superseded"}
        and obj.object_id in approved_targets
        and _human_date_allowed(obj.metadata.get("forecast_as_of"), as_of_date)
    ]
    forecasts_passed = len(approved_forecasts) >= 10
    approved_forecast_ids = {obj.object_id for obj in approved_forecasts}

    forecasts_by_id = {obj.object_id: obj for obj in forecasts}
    resolutions = [obj for obj in objects if obj.object_type == "forecast_resolution"]
    natural_resolutions: list[ResearchObject] = []
    for resolution in resolutions:
        forecast = forecasts_by_id.get(str(resolution.metadata.get("forecast_id", "")))
        resolved_at = _strict_date(resolution.metadata.get("resolved_at"))
        resolution_due = (
            _strict_date(forecast.metadata.get("resolution_date"))
            if forecast is not None
            else None
        )
        if (
            forecast is not None
            and resolved_at is not None
            and resolution_due is not None
            and resolution_due <= resolved_at <= as_of_date
            and resolution.metadata.get("review_status") == "reviewed"
            and resolution.metadata.get("decision")
            in {"correct", "incorrect", "partial", "ambiguous"}
            and _v03_human_reviewer(resolution.metadata.get("reviewer"))
            and resolution.object_id in approved_targets
            and bool(resolution.metadata.get("source_ids"))
        ):
            natural_resolutions.append(resolution)
    natural_forecasts = [
        forecast
        for resolution in natural_resolutions
        if (
            forecast := forecasts_by_id.get(
                str(resolution.metadata.get("forecast_id", ""))
            )
        )
        is not None
    ]
    natural_evidence = [*natural_forecasts, *natural_resolutions]
    forecast_dates = [
        parsed
        for forecast in forecasts
        if (parsed := _strict_date(forecast.metadata.get("resolution_date")))
        is not None
    ]
    earliest_resolution = (
        min(forecast_dates).isoformat() if forecast_dates else "unknown"
    )
    natural_passed = (
        bool(natural_resolutions) and _backlog_status(backlog, "WP-530") == "completed"
    )
    natural_observed = (
        f"WP-530 completed; {len(natural_resolutions)} human-reviewed natural "
        "resolutions"
        if natural_passed
        else f"WP-530 {_backlog_status(backlog, 'WP-530') or 'missing'}; "
        f"{len(natural_resolutions)} natural resolutions; earliest real resolution "
        f"{earliest_resolution}"
    )

    recommendations = [obj for obj in objects if obj.object_type == "recommendation"]
    approved_recommendations = [
        obj
        for obj in recommendations
        if obj.metadata.get("review_status") == "reviewed"
        and obj.metadata.get("status") == "active"
        and obj.object_id in approved_targets
        and _human_date_allowed(obj.metadata.get("as_of"), as_of_date)
        and obj.metadata.get("research_posture")
        in {"avoid", "watch", "research", "investment_candidate"}
    ]
    company_by_id = {
        obj.object_id: obj for obj in objects if obj.object_type == "company"
    }
    recommendation_companies = {
        str(obj.metadata.get("company_id")) for obj in approved_recommendations
    }
    recommendation_sectors = {
        str(sector_id)
        for company_id in recommendation_companies
        if (company := company_by_id.get(company_id)) is not None
        for sector_id in company.metadata.get("sector_ids", [])
    }
    recommendation_passed = (
        len(approved_recommendations) >= 3
        and len(recommendation_companies) >= 3
        and len(recommendation_sectors) >= 2
    )
    approved_recommendation_ids = {obj.object_id for obj in approved_recommendations}

    forbidden_recommendations = [
        obj.object_id
        for obj in recommendations
        if TRADING_DIRECTIVE_PATTERN.search(
            unicodedata.normalize(
                "NFKC",
                obj.body + "\n" + json.dumps(obj.metadata, ensure_ascii=False),
            )
        )
    ]
    trading_surfaces = _production_trading_surfaces(root)
    limitations = _read(root, LIMITATIONS_PATH)
    normalized_limitations = " ".join(limitations.lower().split())
    no_trading = (
        not forbidden_recommendations
        and not trading_surfaces
        and "no automated investment action" in normalized_limitations
        and "no broker, order, or portfolio execution integration"
        in normalized_limitations
    )
    checks += [
        _check_v03(
            "decision.human_approved_forecasts",
            forecasts_passed,
            "at least 10 Forecasts are human-approved with dated frozen criteria",
            f"{len(approved_forecasts)}/{len(forecasts)} qualifying "
            "human-approved Forecasts",
            *_relative_paths(root, approved_forecasts),
            *_approval_paths_for(root, approvals, approved_forecast_ids),
        ),
        _check_v03(
            "decision.natural_resolutions",
            natural_passed,
            (
                "WP-530 includes at least one naturally due, sourced, "
                "human-reviewed Resolution"
            ),
            natural_observed,
            V03_BACKLOG_PATH,
            *_relative_paths(root, natural_evidence),
            *_approval_paths_for(
                root,
                approvals,
                {obj.object_id for obj in natural_evidence},
            ),
        ),
        _check_v03(
            "decision.recommendation_pilot",
            recommendation_passed,
            (
                "three human-approved Company Recommendation pilots cover at "
                "least two Sectors"
            ),
            f"{len(approved_recommendations)} Recommendations / "
            f"{len(recommendation_companies)} Companies / "
            f"{len(recommendation_sectors)} Sectors",
            "05_Research/Reviews/Field_Gate_3_Company_Pilot.md",
            *_relative_paths(root, approved_recommendations),
            *_approval_paths_for(root, approvals, approved_recommendation_ids),
        ),
        _check_v03(
            "decision.no_automated_trading",
            no_trading,
            (
                "the system contains no automated buy, sell, position-size, "
                "order, or execution instruction"
            ),
            "no forbidden Recommendation language or execution integration"
            if no_trading
            else "forbidden Recommendation language or missing no-execution boundary: "
            + ", ".join([*forbidden_recommendations, *trading_surfaces]),
            LIMITATIONS_PATH,
            "05_Research/Recommendations",
            *ACTION_SURFACE_PATHS,
        ),
    ]

    recovery = _read(root, RECOVERY_PATH)
    recovery_passed = _recovery_evidence_passed(root, recovery, as_of_date, objects)
    engineering_verification = _read(root, ENGINEERING_VERIFICATION_PATH)
    quality_rows = all(
        bool(
            re.search(
                rf"(?mi)^\|\s*{re.escape(label)}\s*\|[^\n]*\|\s*pass(?:\s*[;—-][^|]*)?\s*\|\s*$",
                engineering_verification,
            )
        )
        for label in (
            "full pytest suite",
            "Ruff lint and format",
            "mypy and compileall",
        )
    )
    coverage_rows = [
        line
        for line in engineering_verification.splitlines()
        if "coverage" in line.lower()
    ]
    coverage_passed = any(
        (match := re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", line))
        and float(match.group(1)) >= 80.0
        and "pass" in line.lower()
        for line in coverage_rows
    )
    quality_tree_current = _verification_covers_tree(root, engineering_verification)
    quality_passed = (
        _dated_pass_record(engineering_verification, as_of_date)
        and quality_rows
        and coverage_passed
        and quality_tree_current
    )

    performance = _read(root, PERFORMANCE_PATH)
    performance_passed, candidate_p95 = _performance_evidence_passed(
        performance, as_of_date
    )

    migration = _read(root, MIGRATION_PATH)
    migration_passed = _migration_evidence_passed(migration, as_of_date)
    migration_recovery_passed = migration_passed and recovery_passed
    recovery_boundaries_passed = recovery_passed and _recovery_boundaries_passed(
        recovery
    )
    dashboard_security_passed = (
        _dated_pass_record(engineering_verification, as_of_date)
        and _dashboard_smoke_routes(engineering_verification) == DASHBOARD_SMOKE_ROUTES
        and _verification_covers_paths(root, engineering_verification, SECURITY_PATHS)
    )
    checks += [
        _check_v03(
            "engineering.quality_suite",
            quality_passed,
            (
                "full tests, coverage >=80%, Ruff, and mypy have passed in "
                "recorded clean verification"
            ),
            "tests/coverage/Ruff/mypy recorded passed"
            if quality_passed
            else "quality evidence missing, incomplete, or stale for the current tree",
            ENGINEERING_VERIFICATION_PATH,
        ),
        _check_v03(
            "engineering.performance_slo",
            performance_passed,
            (
                "all Phase 6 read-model SLO rows and the 10k Candidate Queue "
                "p95 pass read-only"
            ),
            (
                f"7/7 SLO rows pass; Candidate Queue p95 "
                f"{candidate_p95:g}s; authoritative writes 0"
                if performance_passed and candidate_p95 is not None
                else "performance benchmark missing, stale, or incomplete"
            ),
            PERFORMANCE_PATH,
        ),
        _check_v03(
            "engineering.migration_recovery",
            migration_recovery_passed,
            "v0.2-to-v0.3 migration rollback and full clean-clone recovery both pass",
            f"migration {'passed' if migration_passed else 'missing or incomplete'}; "
            f"recovery {'passed' if recovery_passed else 'missing or incomplete'}",
            MIGRATION_PATH,
            RECOVERY_PATH,
        ),
        _check_v03(
            "engineering.recovery_boundaries",
            recovery_boundaries_passed,
            (
                "Git, Source assets, Candidate DB, secrets, and scheduler "
                "recovery boundaries are explicit"
            ),
            "all five recovery boundaries recorded"
            if recovery_boundaries_passed
            else "one or more recovery boundaries are missing",
            RECOVERY_PATH,
            "00_System/Recovery_Runbook.md",
        ),
        _check_v03(
            "engineering.dashboard_security",
            dashboard_security_passed,
            "Dashboard loopback smoke and security regression coverage pass",
            (
                "Dashboard smoke passed and security tests cover "
                "mutation/path/secret boundaries"
            )
            if dashboard_security_passed
            else "Dashboard smoke or security evidence missing",
            ENGINEERING_VERIFICATION_PATH,
            "09_Automation/tests/test_m6_security.py",
        ),
    ]

    weekly = _v03_cadence_records(root, "Weekly", pilot_start, as_of_date)
    monthly = _v03_cadence_records(root, "Monthly", pilot_start, as_of_date)
    cadence_passed = len(weekly) >= 2 and len(monthly) >= 1
    release_packet = _read(root, RELEASE_PACKET_PATH)
    limitations_ack = _first_line_value(
        release_packet,
        "Known limitations read",
        "Known limitations acknowledged",
    ).lower()
    packet_reviewer = _line_value(release_packet, "Reviewer")
    packet_decision = _first_line_value(
        release_packet, "Release decision", "Decision"
    ).lower()
    packet_human = _current_human_evidence(
        packet_reviewer, _record_date(release_packet), as_of_date
    )
    packet_terminal = _display_status(release_packet) in {
        "approved",
        "completed",
        "final",
        "passed",
    }
    limitations_read = (
        bool(limitations)
        and limitations_ack
        in {
            "acknowledged",
            "read",
            "yes",
        }
        and packet_human
        and packet_terminal
    )
    release_approved = packet_human and packet_terminal and packet_decision == "approve"
    checks += [
        _check_v03(
            "human.cadence_reviews",
            cadence_passed,
            (
                "two Weekly and one Monthly v0.3 review have real reviewers "
                "and dates no later than as_of"
            ),
            f"{len(weekly)} qualifying Weekly / {len(monthly)} qualifying "
            "Monthly reviews",
            *(str(path.relative_to(root)) for path in [*weekly, *monthly]),
        ),
        _check_v03(
            "human.known_limitations_read",
            limitations_read,
            "a named human explicitly acknowledges reading v0.3 Known Limitations",
            "named, dated acknowledgement present"
            if limitations_read
            else (
                "human Known Limitations acknowledgement missing, invalid, "
                "or future-dated"
            ),
            LIMITATIONS_PATH,
            RELEASE_PACKET_PATH,
        ),
        _check_v03(
            "human.release_approval",
            release_approved,
            (
                "F-024 has a named human reviewer, decision date no later than "
                "as_of, and approve decision"
            ),
            "F-024 human release packet approved"
            if release_approved
            else (
                "F-024 human release packet missing, invalid, pending, or future-dated"
            ),
            RELEASE_PACKET_PATH,
        ),
    ]

    if tuple(check.key for check in checks) != V03_CHECK_KEYS:
        raise ReleaseEvaluationError("internal v0.3 release key ordering error")
    return ReleaseReadiness(
        version="0.3",
        project_id=V03_PROJECT_ID,
        checks=tuple(checks),
    )


def release_readiness_for(
    root: Path,
    *,
    version: str = "0.2",
    project_id: str = PILOT_PROJECT_ID,
    as_of: str | None = None,
) -> ReleaseReadiness:
    """Dispatch to a versioned release contract while preserving v0.2."""
    if version == "0.2":
        if as_of is not None:
            _validate_as_of(as_of)
        return release_readiness(root, project_id=project_id)
    if version == "0.3":
        return release_readiness_v03(root, as_of=as_of)
    raise ReleaseEvaluationError("version must be 0.2 or 0.3")


def _validate_as_of(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ReleaseEvaluationError("as_of must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ReleaseEvaluationError("as_of must be YYYY-MM-DD") from exc
    return value


def render_release_readiness(readiness: ReleaseReadiness) -> str:
    lines = [
        f"# AI Research OS v{readiness.version} Release Readiness",
        "",
        f"- Pilot project: {readiness.project_id}",
        f"- Ready: {'yes' if readiness.ready else 'no'}",
        f"- Passed: {len(readiness.checks) - len(readiness.blockers)}/"
        f"{len(readiness.checks)}",
        "",
        "| Status | Gate | Requirement | Observed |",
        "|---|---|---|---|",
    ]
    for check in readiness.checks:
        lines.append(
            f"| {'PASS' if check.passed else 'BLOCKED'} | {check.key} | "
            f"{check.requirement} | {check.observed} |"
        )
    return "\n".join(lines) + "\n"
