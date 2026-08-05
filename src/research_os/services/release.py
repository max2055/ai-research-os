"""Read-only v0.2 release readiness checks with explicit human gates."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.services.indexing import (
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.projects import objects_for_project
from research_os.services.validation import validate_repository

PILOT_PROJECT_ID = "PRJ-002"
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


@dataclass(frozen=True)
class ReleaseCheck:
    key: str
    passed: bool
    requirement: str
    observed: str

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


def _read(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _line_value(text: str, label: str) -> str:
    match = re.search(
        rf"(?mi)^(?:-\s*)?{re.escape(label)}\s*[：:]\s*(.*?)\s*$",
        text,
    )
    return match.group(1).strip() if match else ""


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
