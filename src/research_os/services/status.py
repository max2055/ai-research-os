"""Human-readable repository status and review queue."""

from datetime import date
from pathlib import Path

from research_os.domain.policies import REVIEW_STATUSES, source_processing_state
from research_os.services.indexing import (
    display,
    index_drift,
    render_indexes,
    render_project_indexes,
)
from research_os.services.projects import objects_for_project
from research_os.services.validation import validate_repository


def render_status(root: Path, project_id: str | None = None) -> str:
    objects, findings = validate_repository(root)
    if project_id:
        objects = objects_for_project(objects, project_id)
        scoped_paths = {obj.path for obj in objects}
        findings = [finding for finding in findings if finding.path in scoped_paths]
    rendered = (
        render_project_indexes(objects, project_id)
        if project_id
        else render_indexes(objects)
    )
    drift = index_drift(root, rendered)
    lines = [
        (
            f"# AI Research OS Status — {project_id}"
            if project_id
            else "# AI Research OS Status"
        ),
        "",
        f"Generated from repository state: {date.today().isoformat()}",
        "",
        "## Object counts",
        "",
        "| Type | Total | Pending | Reviewed | Rejected | Superseded |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for object_type in ("source", "event", "thesis", "company", "report"):
        rows = [obj for obj in objects if obj.object_type == object_type]
        status_counts = {
            status: sum(obj.metadata.get("review_status") == status for obj in rows)
            for status in REVIEW_STATUSES
        }
        lines.append(
            f"| {object_type} | {len(rows)} | {status_counts['pending']} | "
            f"{status_counts['reviewed']} | {status_counts['rejected']} | "
            f"{status_counts['superseded']} |"
        )

    pending = sorted(
        (obj for obj in objects if obj.metadata.get("review_status") == "pending"),
        key=lambda obj: (obj.object_type, obj.object_id),
    )
    lines += [
        "",
        "## Review queue",
        "",
        "| ID | Type | Title | Processing |",
        "|---|---|---|---|",
    ]
    if pending:
        for obj in pending:
            processing = (
                source_processing_state(obj) if obj.object_type == "source" else "—"
            )
            lines.append(
                f"| {obj.object_id} | {obj.object_type} | "
                f"{display(obj.metadata.get('title'))} | {processing} |"
            )
    else:
        lines.append("| — | — | No pending objects | — |")

    theses = sorted(
        (obj for obj in objects if obj.object_type == "thesis"),
        key=lambda obj: obj.object_id,
    )
    lines += [
        "",
        "## Thesis evidence coverage",
        "",
        "| Thesis | Confidence | Supporting | Contradicting | Review status |",
        "|---|---:|---:|---:|---|",
    ]
    for obj in theses:
        supporting = obj.metadata.get("supporting_evidence", [])
        contradicting = obj.metadata.get("contradicting_evidence", [])
        lines.append(
            f"| {obj.object_id} | {display(obj.metadata.get('confidence'))} | "
            f"{len(supporting) if isinstance(supporting, list) else 0} | "
            f"{len(contradicting) if isinstance(contradicting, list) else 0} | "
            f"{display(obj.metadata.get('review_status'))} |"
        )

    errors = [item for item in findings if item.level == "error"]
    warnings = [item for item in findings if item.level == "warning"]
    lines += [
        "",
        "## System health",
        "",
        f"- Validation errors: {len(errors)}",
        f"- Validation warnings: {len(warnings)}",
        f"- Index drift files: {len(drift)}",
    ]
    if drift:
        lines.append("- Drift: " + ", ".join(str(path) for path in drift))
    return "\n".join(lines) + "\n"
