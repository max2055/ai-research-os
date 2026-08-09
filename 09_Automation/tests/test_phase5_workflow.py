"""WP-501 (E-007~010): forecast lifecycle workflow tests.

E-007 forecast draft renderer, E-008 open transition, E-009 due/stale queries,
E-010 resolution workflow. The repository-validation gate is patched to a
controlled object list (the real repo has no Forecasts yet); writes go to temp
dirs so the real repository is never touched. Mirrors test_analysis_runner.py.
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
    from research_os.schemas import validate_metadata
    from research_os.services.forecast_draft import (
        apply_forecast_draft,
        prepare_forecast_draft,
    )
    from research_os.services.forecast_due import (
        due_forecasts,
        due_within,
        forecast_status_report,
        overdue_forecasts,
        render_forecast_status,
        unresolved_forecasts,
    )
    from research_os.services.forecast_lifecycle import (
        apply_open_forecast,
        prepare_open_forecast,
    )
    from research_os.services.forecast_resolution import (
        apply_resolution,
        prepare_resolution_draft,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-501 tests") from exc

_SAFE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml(value: object) -> str:
    if isinstance(value, str) and _SAFE.match(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _materialize(root: Path, relative: Path, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_forecast(
    root: Path,
    *,
    id: str = "FCT-20260809-001",
    status: str = "draft",
    review_status: str = "pending",
    resolution_date: str = "2027-01-31",
    forecast_as_of: str = "2026-08-09",
    **extra: object,
) -> ResearchObject:
    meta: dict[str, object] = {
        "id": id,
        "type": "forecast",
        "title": "Will X ramp?",
        "created_at": "2026-08-09",
        "updated_at": "2026-08-09",
        "schema_version": 2,
        "project_ids": [],
        "status": status,
        "review_status": review_status,
        "tags": [],
        "scope_ids": [],
        "question": "Will X ramp by end of year?",
        "outcome_type": "binary",
        "outcome_definition": "X disclosed in the quarterly report.",
        "base_rate": "unknown",
        "forecast_as_of": forecast_as_of,
        "horizon": "quarter",
        "resolution_date": resolution_date,
        "resolution_source_requirements": [],
        "evidence_ids": [],
        "analysis_run_ids": [],
        "assumptions": [],
        "alternative_outcomes": [],
        "falsification_conditions": [],
    }
    meta.update(extra)
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {_yaml(value)}")
    lines.append("---")
    content = "\n".join(lines) + "\n\n# Forecast\n\n## Question\n\nWill X ramp?\n"
    path = root / "05_Research/Forecasts" / f"{id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ResearchObject(path=path, metadata=dict(meta), body="# Forecast\n")


def _project() -> ResearchObject:
    return ResearchObject(
        path=Path("05_Research/Projects/PRJ-001.md"),
        metadata={"id": "PRJ-001", "type": "project", "title": "P"},
        body="",
    )


def _event() -> ResearchObject:
    return ResearchObject(
        path=Path("04_Evidence/Events/EVT-20260520-032.md"),
        metadata={"id": "EVT-20260520-032", "type": "event", "title": "E"},
        body="",
    )


def _source() -> ResearchObject:
    return ResearchObject(
        path=Path("01_Inbox/Articles/SRC-20260809-001.md"),
        metadata={"id": "SRC-20260809-001", "type": "source", "title": "S"},
        body="",
    )


def _patch(root, module: str, objects: list[ResearchObject]):
    return mock.patch(
        f"research_os.services.{module}.validate_repository",
        return_value=(objects, []),
    )


_SPEC = {
    "title": "TSMC 2nm ramp",
    "project_ids": ["PRJ-001"],
    "question": "Will TSMC 2nm ramp to >50% of wafer starts by end of 2026?",
    "outcome_type": "binary",
    "outcome_definition": "TSMC discloses N2 > 10% of quarterly revenue.",
    "probability": 0.6,
    "forecast_as_of": "2026-08-09",
    "horizon": "quarter",
    "resolution_date": "2027-01-31",
    "resolution_source_requirements": ["TSMC Q4 2026 earnings"],
    "evidence_ids": ["EVT-20260520-032"],
    "assumptions": ["CoWoS capacity expands on plan"],
    "falsification_conditions": ["TSMC reports N2 below 10% of revenue"],
}


class E007ForecastDraftTests(unittest.TestCase):
    """E-007: spec -> pending FCT object (dry-run) + atomic apply."""

    def test_prepare_roundtrips_through_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch(root, "forecast_draft", [_project(), _event()]):
                relative, content = prepare_forecast_draft(
                    root, spec=_SPEC, created_at="2026-08-09"
                )
            self.assertTrue(relative.name.startswith("FCT-20260809-"))
            self.assertTrue(relative.name.endswith(".md"))
            _materialize(root, relative, content)
            doc = MarkdownDocument.read(root / relative)
            obj = validate_metadata(doc.metadata)
            self.assertEqual("forecast", obj.type)
            self.assertEqual("draft", obj.status)
            self.assertEqual("pending", obj.review_status)
            self.assertEqual("binary", obj.outcome_type)
            self.assertEqual(_SPEC["question"], obj.question)

    def test_prepare_is_pending_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch(root, "forecast_draft", [_project(), _event()]):
                _, content = prepare_forecast_draft(
                    root, spec=_SPEC, created_at="2026-08-09"
                )
            self.assertIn("status: draft", content)
            self.assertIn("review_status: pending", content)
            self.assertIn("probability: 0.6", content)

    def test_rejects_resolution_date_not_after_as_of(self) -> None:
        spec = dict(_SPEC, resolution_date="2026-08-01")
        with tempfile.TemporaryDirectory() as tmp, _patch(
            Path(tmp), "forecast_draft", [_project(), _event()]
        ), self.assertRaises(ValueError):
            prepare_forecast_draft(Path(tmp), spec=spec, created_at="2026-08-09")

    def test_rejects_numeric_range_without_range_or_unit(self) -> None:
        spec = dict(_SPEC, outcome_type="numeric_range")
        with tempfile.TemporaryDirectory() as tmp, _patch(
            Path(tmp), "forecast_draft", [_project(), _event()]
        ), self.assertRaises(ValueError):
            prepare_forecast_draft(Path(tmp), spec=spec, created_at="2026-08-09")

    def test_rejects_missing_question(self) -> None:
        spec = dict(_SPEC, question="  ")
        with tempfile.TemporaryDirectory() as tmp, _patch(
            Path(tmp), "forecast_draft", [_project(), _event()]
        ), self.assertRaises(ValueError):
            prepare_forecast_draft(Path(tmp), spec=spec, created_at="2026-08-09")

    def test_rejects_unknown_evidence_ref(self) -> None:
        spec = dict(_SPEC, evidence_ids=["EVT-does-not-exist"])
        with tempfile.TemporaryDirectory() as tmp, _patch(
            Path(tmp), "forecast_draft", [_project(), _event()]
        ), self.assertRaises(ValueError):
            prepare_forecast_draft(Path(tmp), spec=spec, created_at="2026-08-09")

    def test_apply_writes_then_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relative = Path("05_Research/Forecasts/FCT-test-001.md")
            content = "---\nid: FCT-test-001\ntype: forecast\n---\n# Forecast\n"
            path = apply_forecast_draft(root, relative, content)
            self.assertTrue(path.exists())
            with self.assertRaises(FileExistsError):
                apply_forecast_draft(root, relative, content)


class E008OpenTransitionTests(unittest.TestCase):
    """E-008: open requires reviewed; only status/audit fields change."""

    def test_refuses_unreviewed_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, review_status="pending")
            with _patch(
                root, "forecast_lifecycle", [forecast]
            ), self.assertRaises(ValueError) as ctx:
                    prepare_open_forecast(
                        root,
                        forecast_id="FCT-20260809-001",
                        actor="max",
                        as_of="2026-08-10",
                    )
            self.assertIn("reviewed", str(ctx.exception))

    def test_refuses_non_draft_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(
                root, status="resolved", review_status="reviewed"
            )
            with _patch(
                root, "forecast_lifecycle", [forecast]
            ), self.assertRaises(ValueError) as ctx:
                    prepare_open_forecast(
                        root,
                        forecast_id="FCT-20260809-001",
                        actor="max",
                        as_of="2026-08-10",
                    )
            self.assertIn("resolved", str(ctx.exception))

    def test_prepare_opens_reviewed_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, review_status="reviewed")
            with _patch(root, "forecast_lifecycle", [forecast]):
                updates = prepare_open_forecast(
                    root,
                    forecast_id="FCT-20260809-001",
                    actor="max",
                    as_of="2026-08-10",
                )
            content = updates[forecast.path]
            self.assertIn("status: open", content)
            self.assertIn("opened_by: max", content)

    def test_apply_opens_and_keeps_criteria_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, review_status="reviewed")
            with _patch(root, "forecast_lifecycle", [forecast]):
                apply_open_forecast(
                    root,
                    forecast_id="FCT-20260809-001",
                    actor="max",
                    as_of="2026-08-10",
                )
            doc = MarkdownDocument.read(forecast.path)
            self.assertEqual("open", doc.metadata["status"])
            self.assertEqual("2026-08-10", str(doc.metadata["opened_at"]))
            # original resolution criteria untouched
            self.assertEqual("2027-01-31", str(doc.metadata["resolution_date"]))
            self.assertEqual(
                "Will X ramp by end of year?", doc.metadata["question"]
            )


class E009DueStaleTests(unittest.TestCase):
    """E-009: due / overdue / unresolved / window queries."""

    def _objs(self) -> list[ResearchObject]:
        def obj(id: str, status: str, resolution_date: str) -> ResearchObject:
            return ResearchObject(
                path=Path(f"05_Research/Forecasts/{id}.md"),
                metadata={
                    "id": id,
                    "type": "forecast",
                    "title": id,
                    "status": status,
                    "resolution_date": resolution_date,
                },
                body="",
            )

        return [
            obj("FCT-20260801-001", "open", "2026-08-15"),
            obj("FCT-20260801-002", "open", "2026-08-05"),  # overdue
            obj("FCT-20260801-003", "open", "2026-08-09"),  # due today
            obj("FCT-20260801-004", "resolved", "2026-08-10"),
            obj("FCT-20260801-005", "open", "2026-08-30"),
        ]

    def test_due_includes_on_or_before(self) -> None:
        due = due_forecasts(self._objs(), as_of="2026-08-09")
        ids = {obj.object_id for obj in due}
        self.assertEqual(
            {"FCT-20260801-002", "FCT-20260801-003"}, ids
        )

    def test_overdue_is_strictly_past(self) -> None:
        overdue = overdue_forecasts(self._objs(), as_of="2026-08-09")
        self.assertEqual(["FCT-20260801-002"], [o.object_id for o in overdue])

    def test_unresolved_returns_all_open(self) -> None:
        unresolved = unresolved_forecasts(self._objs(), as_of="2026-08-09")
        ids = {obj.object_id for obj in unresolved}
        self.assertEqual(
            {"FCT-20260801-001", "FCT-20260801-002", "FCT-20260801-003",
             "FCT-20260801-005"},
            ids,
        )

    def test_due_within_window(self) -> None:
        within = due_within(self._objs(), as_of="2026-08-09", days=10)
        ids = {obj.object_id for obj in within}
        # 08-15 (6d) and 08-09 (0d) inside window; 08-05 overdue excluded (before)
        self.assertEqual({"FCT-20260801-001", "FCT-20260801-003"}, ids)

    def test_status_report_aggregates_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch(root, "forecast_due", self._objs()):
                report = forecast_status_report(root, as_of="2026-08-09")
            self.assertEqual(5, report["total"])
            self.assertEqual(4, report["open"])
            self.assertEqual(1, report["resolved"])
            self.assertEqual(2, report["due"])
            self.assertEqual(1, report["overdue"])

    def test_render_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch(root, "forecast_due", self._objs()):
                rendered = render_forecast_status(root, as_of="2026-08-09")
            self.assertIn("# Forecast status", rendered)
            self.assertIn("FCT-20260801-003", rendered)


class E010ResolutionTests(unittest.TestCase):
    """E-010: resolution workflow — original Forecast is never edited."""

    def _resolution_spec(self, **overrides: object) -> dict[str, object]:
        spec: dict[str, object] = {
            "forecast_id": "FCT-20260809-001",
            "resolved_at": "2027-02-01",
            "outcome": "TSMC reported N2 above 10% of revenue.",
            "observed_value": "12%",
            "source_ids": ["SRC-20260809-001"],
            "decision": "correct",
            "resolution_reason": "Q4 2026 earnings confirmed the threshold.",
            "scoring_method": "manual",
            "reviewer": "max",
        }
        spec.update(overrides)
        return spec

    def test_prepare_roundtrips_through_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, status="open", review_status="reviewed")
            objects = [forecast, _source()]
            with _patch(root, "forecast_resolution", objects):
                relative, content = prepare_resolution_draft(
                    root, spec=self._resolution_spec(), created_at="2027-02-02"
                )
            self.assertTrue(relative.name.startswith("RES-20270202-"))
            _materialize(root, relative, content)
            doc = MarkdownDocument.read(root / relative)
            obj = validate_metadata(doc.metadata)
            self.assertEqual("forecast_resolution", obj.type)
            self.assertEqual("correct", obj.decision)
            self.assertEqual("FCT-20260809-001", obj.forecast_id)
            self.assertEqual("pending", obj.review_status)

    def test_refuses_non_open_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, status="draft", review_status="reviewed")
            with _patch(
                root, "forecast_resolution", [forecast, _source()]
            ), self.assertRaises(ValueError) as ctx:
                    prepare_resolution_draft(
                        root, spec=self._resolution_spec(), created_at="2027-02-02"
                    )
            self.assertIn("open", str(ctx.exception))

    def test_requires_source_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, status="open", review_status="reviewed")
            spec = self._resolution_spec(source_ids=[])
            with _patch(
                root, "forecast_resolution", [forecast, _source()]
            ), self.assertRaises(ValueError) as ctx:
                    prepare_resolution_draft(
                        root, spec=spec, created_at="2027-02-02"
                    )
            self.assertIn("source_id", str(ctx.exception))

    def test_ambiguous_requires_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, status="open", review_status="reviewed")
            spec = self._resolution_spec(
                decision="ambiguous", resolution_reason="  "
            )
            with _patch(
                root, "forecast_resolution", [forecast, _source()]
            ), self.assertRaises(ValueError) as ctx:
                    prepare_resolution_draft(
                        root, spec=spec, created_at="2027-02-02"
                    )
            self.assertIn("reason", str(ctx.exception))

    def test_apply_resolves_forecast_without_editing_criteria(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, status="open", review_status="reviewed")
            with _patch(root, "forecast_resolution", [forecast, _source()]):
                paths = apply_resolution(
                    root, spec=self._resolution_spec(), created_at="2027-02-02"
                )
            self.assertEqual(2, len(paths))
            resolutions = list((root / "05_Research/Resolutions").glob("RES-*.md"))
            self.assertEqual(1, len(resolutions))
            doc = MarkdownDocument.read(forecast.path)
            self.assertEqual("resolved", doc.metadata["status"])
            self.assertEqual("2027-02-01", str(doc.metadata["resolved_at"]))
            # original question/criteria untouched
            self.assertEqual(
                "Will X ramp by end of year?", doc.metadata["question"]
            )
            self.assertEqual("2027-01-31", str(doc.metadata["resolution_date"]))

    def test_apply_void_decision_voids_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = _write_forecast(root, status="open", review_status="reviewed")
            spec = self._resolution_spec(
                decision="void",
                resolution_reason="Question became moot after acquisition.",
            )
            with _patch(root, "forecast_resolution", [forecast, _source()]):
                apply_resolution(root, spec=spec, created_at="2027-02-02")
            doc = MarkdownDocument.read(forecast.path)
            self.assertEqual("void", doc.metadata["status"])


if __name__ == "__main__":
    unittest.main()
