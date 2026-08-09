"""WP-511 (E-014~015): supersession/close lifecycle + calibration engine tests.

E-014 recommendation/valuation supersession & close (atomic dual-pointer
updates); E-015 calibration (Brier, buckets, interval coverage, timeliness,
void/ambiguous rate). Repository validation is patched; writes go to temp dirs.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from research_os.domain.models import ResearchObject
    from research_os.repositories.markdown import MarkdownDocument
    from research_os.services.calibration import (
        brier_score,
        calibration_buckets,
        calibration_report,
        interval_coverage,
        render_calibration_report,
        resolution_timeliness,
        resolved_pairs,
        void_ambiguous_rate,
    )
    from research_os.services.recommendation_lifecycle import (
        activate_recommendation,
        close_recommendation,
        prepare_supersede_recommendation,
        supersede_recommendation,
        supersede_valuation,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-511 tests") from exc

_SAFE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml(value: object) -> str:
    if isinstance(value, str) and _SAFE.match(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _write_object(
    root: Path,
    *,
    object_id: str,
    object_type: str,
    folder: str,
    status: str,
    review_status: str,
    **extra: object,
) -> ResearchObject:
    meta: dict[str, object] = {
        "id": object_id,
        "type": object_type,
        "title": object_id,
        "created_at": "2026-08-09",
        "updated_at": "2026-08-09",
        "schema_version": 2,
        "project_ids": [],
        "status": status,
        "review_status": review_status,
        "tags": [],
    }
    meta.update(extra)
    path = root / folder / f"{object_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {_yaml(value)}")
    lines.append("---")
    path.write_text("\n".join(lines) + "\n\n# {object_type}\n", encoding="utf-8")
    return ResearchObject(path=path, metadata=dict(meta), body="# body\n")


def _rec(
    root: Path,
    object_id: str,
    status: str,
    review_status: str = "reviewed",
) -> ResearchObject:
    return _write_object(
        root,
        object_id=object_id,
        object_type="recommendation",
        folder="05_Research/Recommendations",
        status=status,
        review_status=review_status,
    )


def _val(
    root: Path,
    object_id: str,
    status: str = "active",
    review_status: str = "reviewed",
) -> ResearchObject:
    return _write_object(
        root,
        object_id=object_id,
        object_type="valuation_snapshot",
        folder="05_Research/Valuations",
        status=status,
        review_status=review_status,
        company_id="COM-micron",
        as_of="2026-08-09",
        market_price=100.0,
        shares=1e9,
    )


def _patch(objects: list[ResearchObject]):
    return mock.patch(
        "research_os.services.recommendation_lifecycle.validate_repository",
        return_value=(objects, []),
    )


class E014LifecycleTests(unittest.TestCase):
    """E-014: activate/close/supersede with atomic dual-pointer updates."""

    def test_activate_requires_reviewed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = _rec(root, "REC-20260809-001", "draft", review_status="pending")
            with _patch([rec]), self.assertRaises(ValueError) as ctx:
                activate_recommendation(
                    root, rec_id="REC-20260809-001", actor="max", as_of="2026-08-10"
                )
            self.assertIn("reviewed", str(ctx.exception))

    def test_activate_flips_draft_to_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = _rec(root, "REC-20260809-001", "draft")
            with _patch([rec]):
                activate_recommendation(
                    root, rec_id="REC-20260809-001", actor="max", as_of="2026-08-10"
                )
            doc = MarkdownDocument.read(rec.path)
            self.assertEqual("active", doc.metadata["status"])
            self.assertEqual("max", doc.metadata["activated_by"])

    def test_close_requires_reason_and_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = _rec(root, "REC-20260809-001", "active")
            with _patch([rec]):
                with self.assertRaises(ValueError):
                    close_recommendation(
                        root,
                        rec_id="REC-20260809-001",
                        actor="max",
                        as_of="2026-08-10",
                        reason="  ",
                    )
                close_recommendation(
                    root,
                    rec_id="REC-20260809-001",
                    actor="max",
                    as_of="2026-08-10",
                    reason="thesis played out",
                )
            doc = MarkdownDocument.read(rec.path)
            self.assertEqual("closed", doc.metadata["status"])
            self.assertEqual("thesis played out", doc.metadata["close_reason"])

    def test_supersede_updates_both_pointers_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _rec(root, "REC-20260809-001", "active")
            new = _rec(root, "REC-20260809-002", "active")
            with _patch([old, new]):
                supersede_recommendation(
                    root,
                    old_rec_id="REC-20260809-001",
                    new_rec_id="REC-20260809-002",
                    actor="max",
                    as_of="2026-08-10",
                )
            old_doc = MarkdownDocument.read(old.path)
            new_doc = MarkdownDocument.read(new.path)
            self.assertEqual("superseded", old_doc.metadata["status"])
            self.assertEqual("REC-20260809-002", old_doc.metadata["superseded_by"])
            self.assertEqual("REC-20260809-001", new_doc.metadata["supersedes"])

    def test_supersede_requires_reviewed_active_successor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _rec(root, "REC-20260809-001", "active")
            draft = _rec(root, "REC-20260809-002", "draft")
            with _patch([old, draft]), self.assertRaises(ValueError) as ctx:
                supersede_recommendation(
                    root,
                    old_rec_id="REC-20260809-001",
                    new_rec_id="REC-20260809-002",
                    actor="max",
                    as_of="2026-08-10",
                )
            self.assertIn("successor", str(ctx.exception))

    def test_supersede_valuation_dual_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _val(root, "VAL-20260809-001")
            new = _val(root, "VAL-20260809-002")
            with _patch([old, new]):
                supersede_valuation(
                    root,
                    old_val_id="VAL-20260809-001",
                    new_val_id="VAL-20260809-002",
                    actor="max",
                    as_of="2026-08-10",
                )
            old_doc = MarkdownDocument.read(old.path)
            new_doc = MarkdownDocument.read(new.path)
            self.assertEqual("superseded", old_doc.metadata["status"])
            self.assertEqual("VAL-20260809-002", old_doc.metadata["superseded_by"])
            self.assertEqual("VAL-20260809-001", new_doc.metadata["supersedes"])

    def test_prepare_supersede_is_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = _rec(root, "REC-20260809-001", "active")
            new = _rec(root, "REC-20260809-002", "active")
            with _patch([old, new]):
                updates = prepare_supersede_recommendation(
                    root,
                    old_rec_id="REC-20260809-001",
                    new_rec_id="REC-20260809-002",
                    actor="max",
                    as_of="2026-08-10",
                )
            # dry-run: files unchanged on disk
            status = MarkdownDocument.read(old.path).metadata["status"]
            self.assertEqual("active", status)
            self.assertEqual(2, len(updates))
            self.assertIn(old.path, updates)
            self.assertIn(new.path, updates)


def _forecast(**meta: object) -> ResearchObject:
    full: dict[str, object] = {
        "id": meta.pop("id", "FCT-20260809-001"),
        "type": "forecast",
        "title": "f",
        "review_status": "reviewed",
    }
    full.update(meta)
    path = Path("05_Research/Forecasts/f.md")
    return ResearchObject(path=path, metadata=full, body="")


def _resolution(**meta: object) -> ResearchObject:
    full: dict[str, object] = {
        "id": meta.pop("id", "RES-20260809-001"),
        "type": "forecast_resolution",
        "title": "r",
        "review_status": "reviewed",
        "forecast_id": "FCT-20260809-001",
    }
    full.update(meta)
    path = Path("05_Research/Resolutions/r.md")
    return ResearchObject(path=path, metadata=full, body="")


def _pair(
    fcid: str,
    *,
    outcome_type: str,
    probability: float | None = None,
    resolution_date: str = "2026-08-01",
    decision: str,
    resolved_at: str = "2026-08-01",
    range_low: int | None = None,
    range_high: int | None = None,
    observed_value: str | None = None,
) -> tuple[ResearchObject, ResearchObject]:
    forecast_meta: dict[str, object] = {
        "id": fcid,
        "outcome_type": outcome_type,
        "resolution_date": resolution_date,
    }
    if probability is not None:
        forecast_meta["probability"] = probability
    if range_low is not None:
        forecast_meta["range_low"] = range_low
    if range_high is not None:
        forecast_meta["range_high"] = range_high
    res_meta: dict[str, object] = {
        "id": f"RES-{fcid}",
        "forecast_id": fcid,
        "decision": decision,
        "resolved_at": resolved_at,
    }
    if observed_value is not None:
        res_meta["observed_value"] = observed_value
    return _forecast(**forecast_meta), _resolution(**res_meta)


def _sample_pairs() -> list[tuple[ResearchObject, ResearchObject]]:
    return [
        _pair("FCT-1", outcome_type="binary", probability=0.8, decision="correct"),
        _pair(
            "FCT-2",
            outcome_type="binary",
            probability=0.7,
            decision="incorrect",
            resolved_at="2026-08-05",
        ),
        _pair(
            "FCT-3",
            outcome_type="binary",
            probability=0.5,
            decision="void",
            resolved_at="2026-08-03",
        ),
        _pair(
            "FCT-4",
            outcome_type="numeric_range",
            range_low=10,
            range_high=20,
            decision="correct",
            observed_value="15",
        ),
        _pair(
            "FCT-5",
            outcome_type="numeric_range",
            range_low=10,
            range_high=20,
            decision="incorrect",
            observed_value="30",
        ),
    ]


class E015CalibrationTests(unittest.TestCase):
    """E-015: Brier / buckets / interval coverage / timeliness / void rate."""

    def test_brier_score_correctness(self) -> None:
        result = brier_score(_sample_pairs())
        self.assertEqual(2, result["n"])
        self.assertAlmostEqual(0.265, result["brier"], places=3)

    def test_calibration_buckets(self) -> None:
        buckets = calibration_buckets(_sample_pairs())
        by_bucket = {row["bucket"]: row for row in buckets}
        self.assertEqual(1, by_bucket["0.6-0.8"]["n"])
        self.assertEqual(0, by_bucket["0.6-0.8"]["observed_frequency"])
        self.assertEqual(1, by_bucket["0.8-1.0"]["n"])
        self.assertEqual(1, by_bucket["0.8-1.0"]["observed_frequency"])

    def test_interval_coverage(self) -> None:
        result = interval_coverage(_sample_pairs())
        self.assertEqual(2, result["n"])
        self.assertEqual(0.5, result["coverage"])

    def test_timeliness_and_void_rate(self) -> None:
        timeliness = resolution_timeliness(_sample_pairs())
        self.assertEqual(5, timeliness["n"])
        self.assertEqual(2, timeliness["late"])
        rate = void_ambiguous_rate(_sample_pairs())
        self.assertEqual(5, rate["n"])
        self.assertEqual(1, rate["void"])
        self.assertEqual(0.2, rate["rate"])

    def test_report_aggregates_and_renders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            objects: list[ResearchObject] = []
            for forecast, res in _sample_pairs():
                objects.append(forecast)
                objects.append(res)
            with mock.patch(
                "research_os.services.calibration.validate_repository",
                return_value=(objects, []),
            ):
                report = calibration_report(root)
            self.assertEqual(5, report["n_resolutions"])
            self.assertEqual(2, report["brier"]["n"])
            rendered = render_calibration_report(report)
            self.assertIn("# Forecast calibration", rendered)
            self.assertIn("Brier", rendered)

    def test_resolved_pairs_only_reviewed(self) -> None:
        objects: list[ResearchObject] = []
        for forecast, res in _sample_pairs():
            objects.append(forecast)
            objects.append(res)
        pending = _resolution(
            id="RES-P", forecast_id="FCT-1", decision="correct", review_status="pending"
        )
        objects.append(pending)
        pairs = resolved_pairs(objects)
        self.assertEqual(5, len(pairs))


if __name__ == "__main__":
    unittest.main()
