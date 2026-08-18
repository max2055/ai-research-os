"""Website preparation adapter for human Review Decisions."""

from __future__ import annotations

from pathlib import Path

from research_os.services.drafts import split_values
from research_os.services.reviews import prepare_review
from research_os.services.validation import validate_repository
from research_os.services.web_repository_mutations import (
    PreparedRepositoryMutation,
    prepare_repository_mutation,
)


def prepare_review_mutation(
    root: Path,
    *,
    actor: str,
    target_ids: str,
    decision: str,
    reviewed_at: str,
    notes: str,
) -> PreparedRepositoryMutation:
    targets = split_values(target_ids)
    relative, content, updates = prepare_review(
        root,
        target_ids=targets,
        decision=decision,
        reviewer=actor,
        reviewed_at=reviewed_at,
        notes=notes,
    )
    review_id = relative.stem
    root = root.resolve()
    objects, _ = validate_repository(root)
    by_id = {obj.object_id: obj for obj in objects}
    type_counts: dict[str, int] = {}
    for target_id in targets:
        object_type = by_id[target_id].object_type if target_id in by_id else "unknown"
        type_counts[object_type] = type_counts.get(object_type, 0) + 1
    writes = {relative: content.encode("utf-8")}
    writes.update(
        {
            path.relative_to(root): updated.encode("utf-8")
            for path, updated in updates.items()
        }
    )
    return prepare_repository_mutation(
        root,
        operation="review.apply",
        actor=actor,
        target_type="review",
        target_id=review_id,
        writes=writes,
        normalized_input={
            "target_ids": targets,
            "decision": decision,
            "reviewed_at": reviewed_at,
            "notes": notes,
        },
        summary={
            "decision": decision,
            "target_ids": targets,
            "target_count": len(targets),
            "type_counts": type_counts,
            "reviewed_at": reviewed_at,
        },
    )
