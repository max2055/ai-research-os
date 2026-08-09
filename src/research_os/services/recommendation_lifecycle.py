"""E-014 recommendation/valuation supersession + close lifecycle (Phase 5, WP-511).

A Recommendation (REC-*) moves through draft -> active -> closed | superseded;
a ValuationSnapshot (VAL-*) can be superseded on a market-data error (Phase 5
§7/§12/§14). Supersession updates BOTH pointers atomically in one transaction:

- the successor object gets ``supersedes: <old_id>``;
- the old object gets ``superseded_by: <new_id>`` + ``status: superseded``.

The dual-pointer update is atomic (FileTransaction), so a half-linked pair can
never be committed. `validate_repository` enforces reciprocity (REC003/VAL003).
"""

from __future__ import annotations

from pathlib import Path

from research_os.domain.models import ResearchObject
from research_os.domain.policies import is_iso_date
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.services.validation import validate_repository

_ACTIVATABLE = frozenset({"draft"})
_CLOSABLE = frozenset({"active"})


def _read(root: Path, obj: ResearchObject) -> MarkdownDocument:
    return MarkdownDocument.read(obj.path)


def activate_recommendation(
    root: Path,
    *,
    rec_id: str,
    actor: str,
    as_of: str,
) -> Path:
    """Activate a reviewed Recommendation (draft -> active)."""
    updates = prepare_activate_recommendation(
        root, rec_id=rec_id, actor=actor, as_of=as_of
    )
    return _commit(root, updates)[0]


def prepare_activate_recommendation(
    root: Path,
    *,
    rec_id: str,
    actor: str,
    as_of: str,
) -> dict[Path, str]:
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    if not actor.strip():
        raise ValueError("actor is required")
    obj = _require_recommendation(root, rec_id)
    if obj.metadata.get("review_status") != "reviewed":
        raise ValueError(
            f"cannot activate {rec_id}: review_status must be reviewed"
        )
    status = str(obj.metadata.get("status"))
    if status not in _ACTIVATABLE:
        raise ValueError(f"cannot activate {rec_id} from status {status!r}")
    document = _read(root, obj)
    document.set_metadata("status", "active")
    document.set_metadata("activated_at", as_of)
    document.set_metadata("activated_by", actor)
    document.set_metadata("updated_at", as_of)
    return {obj.path: document.render()}


def close_recommendation(
    root: Path,
    *,
    rec_id: str,
    actor: str,
    as_of: str,
    reason: str,
) -> Path:
    """Close an active Recommendation (active -> closed) with a reason."""
    updates = prepare_close_recommendation(
        root, rec_id=rec_id, actor=actor, as_of=as_of, reason=reason
    )
    return _commit(root, updates)[0]


def prepare_close_recommendation(
    root: Path,
    *,
    rec_id: str,
    actor: str,
    as_of: str,
    reason: str,
) -> dict[Path, str]:
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    if not reason.strip():
        raise ValueError("close reason is required")
    obj = _require_recommendation(root, rec_id)
    status = str(obj.metadata.get("status"))
    if status not in _CLOSABLE:
        raise ValueError(f"cannot close {rec_id} from status {status!r}")
    document = _read(root, obj)
    document.set_metadata("status", "closed")
    document.set_metadata("closed_at", as_of)
    document.set_metadata("closed_by", actor)
    document.set_metadata("close_reason", reason)
    document.set_metadata("updated_at", as_of)
    return {obj.path: document.render()}


def supersede_recommendation(
    root: Path,
    *,
    old_rec_id: str,
    new_rec_id: str,
    actor: str,
    as_of: str,
) -> list[Path]:
    """Atomically link a new Recommendation as the successor of an old one."""
    updates = prepare_supersede_recommendation(
        root, old_rec_id=old_rec_id, new_rec_id=new_rec_id, actor=actor, as_of=as_of
    )
    return _commit(root, updates)


def prepare_supersede_recommendation(
    root: Path,
    *,
    old_rec_id: str,
    new_rec_id: str,
    actor: str,
    as_of: str,
) -> dict[Path, str]:
    """Dual-pointer supersession: old.superseded_by=new, new.supersedes=old.

    The old Recommendation must be ``active``; the successor must be reviewed
    and active (it replaces the old as the live posture). Both pointers are
    staged in one transaction — never a half-linked pair.
    """
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    if old_rec_id == new_rec_id:
        raise ValueError("cannot supersede a Recommendation with itself")
    old = _require_recommendation(root, old_rec_id)
    new = _require_recommendation(root, new_rec_id)
    if str(old.metadata.get("status")) != "active":
        raise ValueError(
            f"cannot supersede {old_rec_id}: status must be active, "
            f"is {old.metadata.get('status')!r}"
        )
    if new.metadata.get("review_status") != "reviewed" or str(
        new.metadata.get("status")
    ) != "active":
        raise ValueError(
            f"successor {new_rec_id} must be reviewed and active to supersede"
        )
    if old.metadata.get("superseded_by"):
        raise ValueError(
            f"{old_rec_id} is already superseded by {old.metadata['superseded_by']}"
        )

    old_doc = _read(root, old)
    old_doc.set_metadata("status", "superseded")
    old_doc.set_metadata("superseded_by", new_rec_id)
    old_doc.set_metadata("superseded_at", as_of)
    old_doc.set_metadata("superseded_by_actor", actor)
    old_doc.set_metadata("updated_at", as_of)
    new_doc = _read(root, new)
    new_doc.set_metadata("supersedes", old_rec_id)
    new_doc.set_metadata("updated_at", as_of)
    return {old.path: old_doc.render(), new.path: new_doc.render()}


def supersede_valuation(
    root: Path,
    *,
    old_val_id: str,
    new_val_id: str,
    actor: str,
    as_of: str,
) -> list[Path]:
    """Supersede a ValuationSnapshot on a market-data error (Phase 5 §14)."""
    updates = prepare_supersede_valuation(
        root, old_val_id=old_val_id, new_val_id=new_val_id, actor=actor, as_of=as_of
    )
    return _commit(root, updates)


def prepare_supersede_valuation(
    root: Path,
    *,
    old_val_id: str,
    new_val_id: str,
    actor: str,
    as_of: str,
) -> dict[Path, str]:
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    if old_val_id == new_val_id:
        raise ValueError("cannot supersede a ValuationSnapshot with itself")
    old = _require_valuation(root, old_val_id)
    new = _require_valuation(root, new_val_id)
    if old.metadata.get("superseded_by"):
        raise ValueError(f"{old_val_id} is already superseded")
    old_doc = _read(root, old)
    old_doc.set_metadata("status", "superseded")
    old_doc.set_metadata("superseded_by", new_val_id)
    old_doc.set_metadata("superseded_at", as_of)
    old_doc.set_metadata("updated_at", as_of)
    new_doc = _read(root, new)
    new_doc.set_metadata("supersedes", old_val_id)
    new_doc.set_metadata("updated_at", as_of)
    return {old.path: old_doc.render(), new.path: new_doc.render()}


def _require_recommendation(root: Path, rec_id: str) -> ResearchObject:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before a Recommendation lifecycle change"
        )
    obj = {o.object_id: o for o in objects}.get(rec_id)
    if obj is None or obj.object_type != "recommendation":
        raise ValueError(f"unknown Recommendation {rec_id}")
    return obj


def _require_valuation(root: Path, val_id: str) -> ResearchObject:
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before a Valuation lifecycle change"
        )
    obj = {o.object_id: o for o in objects}.get(val_id)
    if obj is None or obj.object_type != "valuation_snapshot":
        raise ValueError(f"unknown ValuationSnapshot {val_id}")
    return obj


def _commit(root: Path, updates: dict[Path, str]) -> list[Path]:
    transaction = FileTransaction(root)
    for path, content in updates.items():
        transaction.stage_replace(path, content)
    return transaction.commit()
