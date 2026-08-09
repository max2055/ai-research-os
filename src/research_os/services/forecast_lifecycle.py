"""E-008 forecast open transition (Phase 5, WP-501).

A Forecast moves from ``draft`` to ``open`` only through this lifecycle step
(RCP-v03-008, Phase 5 §3): ``open`` requires ``review_status=reviewed``. The
transition edits ONLY the status/audit fields of the existing Forecast file —
the question, outcome definition, probability, and resolution criteria are
untouched (they are immutable once opened).
"""

from __future__ import annotations

from pathlib import Path

from research_os.domain.policies import is_iso_date
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.services.validation import validate_repository

_OPENABLE_STATUSES = frozenset({"draft"})


def prepare_open_forecast(
    root: Path,
    *,
    forecast_id: str,
    actor: str,
    as_of: str,
) -> dict[Path, str]:
    """Prepare the status edit that opens a Forecast (dry-run, no writes).

    Returns ``{path: content}`` for the Forecast to be flipped to ``open``.
    Raises if the Forecast is not reviewed (E-008 gate) or not openable.
    """
    if not is_iso_date(as_of):
        raise ValueError("as_of must be YYYY-MM-DD")
    if not actor.strip():
        raise ValueError("actor is required")
    objects, findings = validate_repository(root)
    if any(finding.level == "error" for finding in findings):
        raise ValueError(
            "repository validation must pass before opening a forecast"
        )
    by_id = {obj.object_id: obj for obj in objects}
    forecast = by_id.get(forecast_id)
    if forecast is None or forecast.object_type != "forecast":
        raise ValueError(f"unknown Forecast {forecast_id}")
    if forecast.metadata.get("review_status") != "reviewed":
        raise ValueError(
            f"cannot open {forecast_id}: review_status must be reviewed"
        )
    status = str(forecast.metadata.get("status"))
    if status not in _OPENABLE_STATUSES:
        raise ValueError(f"cannot open {forecast_id} from status {status!r}")

    document = MarkdownDocument.read(forecast.path)
    document.set_metadata("status", "open")
    document.set_metadata("updated_at", as_of)
    document.set_metadata("opened_at", as_of)
    document.set_metadata("opened_by", actor)
    return {forecast.path: document.render()}


def apply_open_forecast(
    root: Path,
    *,
    forecast_id: str,
    actor: str,
    as_of: str,
) -> list[Path]:
    """Atomically open a reviewed Forecast (single-file transaction)."""
    root = root.resolve()
    updates = prepare_open_forecast(
        root, forecast_id=forecast_id, actor=actor, as_of=as_of
    )
    transaction = FileTransaction(root)
    for path, content in updates.items():
        transaction.stage_replace(path, content)
    return transaction.commit()
