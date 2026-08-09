"""WP-510 (E-011~013): valuation / scenario / recommendation workflow tests.

E-011 deterministic valuation, E-012 scenario workflow, E-013 recommendation
renderer + completeness/freshness gate. The repository-validation gate is
patched to a controlled object list; writes go to temp dirs so the real
repository is never touched. Mirrors test_phase5_workflow.py.
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
    from research_os.services.recommendation import (
        apply_recommendation_draft,
        prepare_recommendation_draft,
        recommendation_freshness,
        recommendation_gate,
    )
    from research_os.services.scenario_workflow import (
        extract_scenario_sections,
        render_scenario_template,
        scenario_set_for_valuation,
        validate_scenario_set,
    )
    from research_os.services.validation import (
        validate_valuation_rec_semantics,
    )
    from research_os.services.valuation import (
        apply_valuation_draft,
        compute_valuation,
        prepare_valuation_draft,
        valuation_freshness,
    )
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run WP-510 tests") from exc

_SAFE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _yaml(value: object) -> str:
    if isinstance(value, str) and _SAFE.match(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _obj(object_id: str, object_type: str, **meta: object) -> ResearchObject:
    full: dict[str, object] = {
        "id": object_id,
        "type": object_type,
        "title": object_id,
        "review_status": "reviewed",
    }
    full.update(meta)
    return ResearchObject(
        path=Path(f"{object_type}s/{object_id}.md"),
        metadata=full,
        body="",
    )


def _company() -> ResearchObject:
    return _obj("COM-micron", "company")


def _source() -> ResearchObject:
    return _obj("SRC-20260809-001", "source")


def _thesis() -> ResearchObject:
    return _obj("THS-004", "thesis")


def _val(
    root: Path,
    *,
    as_of: str = "2026-08-09",
    threshold: str = "7d",
) -> ResearchObject:
    path = root / "05_Research/Valuations/VAL-20260809-001.md"
    meta: dict[str, object] = {
        "id": "VAL-20260809-001",
        "type": "valuation_snapshot",
        "title": "v",
        "company_id": "COM-micron",
        "as_of": as_of,
        "market_price": 100.0,
        "shares": 1e9,
        "freshness_threshold": threshold,
    }
    content = (
        "---\n"
        + "\n".join(f"{k}: {_yaml(v)}" for k, v in meta.items())
        + "\n---\n# V\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ResearchObject(path=path, metadata=meta, body="# V\n")


def _scenario_run() -> ResearchObject:
    body = """# Run

## Drivers and probabilities

核心驱动: AI 资本开支。Downside 30%, Base 50%, Upside 20%。

## Downside scenario

- **驱动变量**: 需求下滑。
- **概率**: 30%。
- **结果**: 收入下降。

## Base scenario

- **驱动变量**: 需求平稳。
- **概率**: 50%。
- **结果**: 收入持平。

## Upside scenario

- **驱动变量**: 需求超预期。
- **概率**: 20%。
- **结果**: 收入上升。

## Sensitivity and catalysts

敏感性: 资本开支每变化 10%, 概率变化 5%。

## Falsification conditions

- Downside 证伪: 需求连续两季上升。
"""
    return ResearchObject(
        path=Path("05_Research/Analysis/ANL-20260809-041.md"),
        metadata={
            "id": "ANL-20260809-041",
            "type": "analysis_run",
            "title": "scenario run",
            "mode_id": "MOD-ANL-scenario-v2",
            "status": "completed",
            "review_status": "pending",
        },
        body=body,
    )


def _patch(module: str, objects: list[ResearchObject]):
    return mock.patch(
        f"research_os.services.{module}.validate_repository",
        return_value=(objects, []),
    )


_VAL_SPEC = {
    "company_id": "COM-micron",
    "as_of": "2026-08-09",
    "market_price": 120.0,
    "currency": "USD",
    "shares": 1.11e9,
    "debt": 18e9,
    "cash": 6e9,
    "valuation_identity": "ev/ebitda",
    "denominator_period": "FY2025",
    "denominator_value": 22e9,
    "source_ids": ["SRC-20260809-001"],
}


class E011ValuationTests(unittest.TestCase):
    """E-011: deterministic Equity/Enterprise Value + matched-period multiple."""

    def test_compute_valuation_equity_and_ev(self) -> None:
        result = compute_valuation(
            market_price=100.0,
            shares=1e9,
            debt=20e9,
            cash=5e9,
            valuation_identity="ev/ebitda",
            denominator=10e9,
        )
        self.assertEqual(100e9, result["equity_value"])
        self.assertEqual(115e9, result["enterprise_value"])  # 100 + 20 - 5
        self.assertEqual(11.5, result["multiple"])

    def test_compute_pe_uses_equity_value(self) -> None:
        result = compute_valuation(
            market_price=100.0,
            shares=1e9,
            valuation_identity="pe",
            denominator=5e9,
        )
        self.assertEqual(100e9, result["equity_value"])
        self.assertEqual(20.0, result["multiple"])  # 100 / 5

    def test_rejects_negative_price_and_nonpositive_shares(self) -> None:
        with self.assertRaises(ValueError):
            compute_valuation(market_price=-1, shares=1e9, valuation_identity="manual")
        with self.assertRaises(ValueError):
            compute_valuation(market_price=100, shares=0, valuation_identity="manual")

    def test_requires_denominator_for_multiples(self) -> None:
        with self.assertRaises(ValueError):
            compute_valuation(
                market_price=100, shares=1e9, valuation_identity="ev/ebitda"
            )

    def test_prepare_draft_roundtrips_through_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch("valuation", [_company(), _source()]):
                relative, content = prepare_valuation_draft(
                    root, spec=_VAL_SPEC, created_at="2026-08-09"
                )
            self.assertTrue(relative.name.startswith("VAL-"))
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            obj = validate_metadata(MarkdownDocument.read(path).metadata)
            self.assertEqual("valuation_snapshot", obj.type)
            self.assertEqual("draft", obj.status)
            self.assertEqual("pending", obj.review_status)
            self.assertEqual("COM-micron", obj.company_id)
            self.assertIn("Enterprise Value", content)

    def test_apply_writes_then_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relative = Path("05_Research/Valuations/VAL-test-001.md")
            content = "---\nid: VAL-test-001\ntype: valuation_snapshot\n---\n# V\n"
            path = apply_valuation_draft(root, relative, content)
            self.assertTrue(path.exists())
            with self.assertRaises(FileExistsError):
                apply_valuation_draft(root, relative, content)

    def test_freshness_fresh_and_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = _val(root, as_of="2026-07-01")
            with _patch("valuation", [stale]):
                result = valuation_freshness(
                    root, val_id="VAL-20260809-001", as_of="2026-08-09"
                )
            self.assertFalse(result["fresh"])
            self.assertEqual(39, result["age_days"])


class E012ScenarioTests(unittest.TestCase):
    """E-012: three-scenario extraction + §5 completeness validation."""

    def test_extract_returns_all_sections(self) -> None:
        sections = extract_scenario_sections(_scenario_run())
        self.assertEqual(6, len(sections))
        for title in (
            "Drivers and probabilities",
            "Downside scenario",
            "Base scenario",
            "Upside scenario",
            "Sensitivity and catalysts",
            "Falsification conditions",
        ):
            self.assertIn(title, sections)
            self.assertGreater(len(sections[title]), 20)

    def test_validate_complete_set_has_no_problems(self) -> None:
        sections = extract_scenario_sections(_scenario_run())
        self.assertEqual([], validate_scenario_set(sections))

    def test_validate_missing_scenario_reports_problem(self) -> None:
        sections = extract_scenario_sections(_scenario_run())
        del sections["Upside scenario"]
        problems = validate_scenario_set(sections)
        self.assertTrue(any("Upside scenario" in p for p in problems))

    def test_scenario_set_for_valuation_rejects_non_scenario_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = _obj(
                "ANL-20260809-001",
                "analysis_run",
                mode_id="MOD-ANL-value-chain-v1",
                body="# Run\n\n## Mode-specific output\n\nvalue chain\n",
            )
            with _patch(
                "scenario_workflow", [run]
            ), self.assertRaises(ValueError) as ctx:
                scenario_set_for_valuation(Path(tmp), run_id="ANL-20260809-001")
            self.assertIn("scenario", str(ctx.exception))

    def test_scenario_set_for_valuation_validates_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = _scenario_run()
            with _patch("scenario_workflow", [run]):
                result = scenario_set_for_valuation(
                    Path(tmp), run_id="ANL-20260809-041"
                )
            self.assertEqual("MOD-ANL-scenario-v2", result["mode_id"])
            self.assertEqual([], result["problems"])

    def test_template_has_three_scenarios_and_sensitivity(self) -> None:
        template = render_scenario_template(
            company_id="COM-micron", as_of="2026-08-09", question="HBM demand?"
        )
        self.assertIn("Downside scenario", template)
        self.assertIn("Base scenario", template)
        self.assertIn("Upside scenario", template)
        self.assertIn("Two-variable sensitivity matrix", template)


_REC_SPEC = {
    "company_id": "COM-micron",
    "as_of": "2026-08-09",
    "time_horizon": "year",
    "research_posture": "research",
    "direction": "positive",
    "conviction": "medium",
    "thesis_ids": ["THS-004"],
    "evidence_ids": ["SRC-20260809-001"],
    "expected_case": "HBM 需求由 AI 带动，周期上行。",
    "downside_case": "内存周期下行。",
    "upside_case": "HBM 结构性短缺。",
    "catalysts": ["HBM 出货增长"],
    "falsification_conditions": ["DRAM 价格持续下行"],
    "key_risks": ["价格周期性"],
    "unknowns": ["HBM 需求长期持续性"],
    "freshness_date": "2026-08-09",
}


class E013RecommendationTests(unittest.TestCase):
    """E-013: REC renderer + §12 completeness/freshness gate."""

    def test_prepare_draft_roundtrips_through_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch("recommendation", [_company(), _source(), _thesis()]):
                relative, content = prepare_recommendation_draft(
                    root, spec=_REC_SPEC, created_at="2026-08-09"
                )
            self.assertTrue(relative.name.startswith("REC-"))
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            obj = validate_metadata(MarkdownDocument.read(path).metadata)
            self.assertEqual("recommendation", obj.type)
            self.assertEqual("research", obj.research_posture)
            self.assertEqual("pending", obj.review_status)

    def test_rejects_buy_sell_position_sizing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = dict(_REC_SPEC, expected_case="建议买入 Micron，目标价 200 元。")
            with _patch(
                "recommendation", [_company(), _source(), _thesis()]
            ), self.assertRaises(ValueError) as ctx:
                prepare_recommendation_draft(root, spec=bad, created_at="2026-08-09")
            self.assertIn("buy/sell", str(ctx.exception))

    def test_gate_complete_spec_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with _patch(
                "recommendation", [_company(), _source(), _thesis()]
            ):
                result = recommendation_gate(
                    root, spec=_REC_SPEC, as_of="2026-08-09"
                )
            self.assertEqual([], result["problems"])

    def test_gate_flags_incomplete_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incomplete = dict(_REC_SPEC, unknowns=[], falsification_conditions=[])
            with _patch(
                "recommendation", [_company(), _source(), _thesis()]
            ):
                result = recommendation_gate(
                    root, spec=incomplete, as_of="2026-08-09"
                )
            joined = " | ".join(result["problems"])
            self.assertIn("unknowns", joined)
            self.assertIn("falsification_conditions", joined)

    def test_gate_flags_stale_valuation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = _val(root, as_of="2026-07-01")
            with _patch(
                "recommendation", [_company(), _source(), _thesis(), stale]
            ), _patch("valuation", [stale]):
                result = recommendation_gate(
                    root,
                    spec=dict(_REC_SPEC, valuation_snapshot_id="VAL-20260809-001"),
                    as_of="2026-08-09",
                )
            self.assertTrue(any("stale" in p for p in result["problems"]))

    def test_freshness_fresh_and_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = _obj(
                "REC-20260809-001",
                "recommendation",
                freshness_date="2026-08-09",
            )
            with _patch("recommendation", [rec]):
                fresh = recommendation_freshness(
                    root, rec_id="REC-20260809-001", as_of="2026-08-09"
                )
                stale = recommendation_freshness(
                    root, rec_id="REC-20260809-001", as_of="2027-03-01"
                )
            self.assertTrue(fresh["fresh"])
            self.assertFalse(stale["fresh"])

    def test_apply_writes_then_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relative = Path("05_Research/Recommendations/REC-test-001.md")
            content = "---\nid: REC-test-001\ntype: recommendation\n---\n# R\n"
            path = apply_recommendation_draft(root, relative, content)
            self.assertTrue(path.exists())
            with self.assertRaises(FileExistsError):
                apply_recommendation_draft(root, relative, content)


class E019LicenseValidationTests(unittest.TestCase):
    """E-019: reviewed valuation requires data_license + provider/timestamp."""

    def _val_meta(self, **overrides: object) -> dict[str, object]:
        meta: dict[str, object] = {
            "id": "VAL-20260809-001",
            "type": "valuation_snapshot",
            "title": "v",
            "review_status": "reviewed",
            "company_id": "COM-micron",
            "as_of": "2026-08-09",
            "market_price": 100.0,
            "shares": 1e9,
            "data_license": "SEC-public-domain",
            "source_ids": ["SRC-20260809-001"],
        }
        meta.update(overrides)
        return meta

    def _source_meta(self, **overrides: object) -> dict[str, object]:
        meta: dict[str, object] = {
            "id": "SRC-20260809-001",
            "type": "source",
            "title": "s",
            "review_status": "reviewed",
            "publisher": "MICRON TECHNOLOGY INC",
            "accessed_at": "2026-08-09",
        }
        meta.update(overrides)
        return meta

    def _codes(
        self,
        val_meta: dict[str, object],
        source_meta: dict[str, object],
    ) -> list[str]:
        from research_os.domain.models import Finding

        val = ResearchObject(
            path=Path("05_Research/Valuations/VAL-20260809-001.md"),
            metadata=val_meta,
            body="",
        )
        source = ResearchObject(
            path=Path("01_Inbox/Articles/SRC-20260809-001.md"),
            metadata=source_meta,
            body="",
        )
        findings: list[Finding] = []
        validate_valuation_rec_semantics(
            val, {source.object_id: source}, findings
        )
        return [finding.code for finding in findings]

    def test_compliant_reviewed_valuation_passes(self) -> None:
        codes = self._codes(self._val_meta(), self._source_meta())
        self.assertEqual([], codes)

    def test_missing_data_license_flagged(self) -> None:
        codes = self._codes(
            self._val_meta(data_license=""), self._source_meta()
        )
        self.assertIn("VAL004", codes)

    def test_source_without_provider_timestamp_flagged(self) -> None:
        codes = self._codes(
            self._val_meta(),
            self._source_meta(publisher="", accessed_at=""),
        )
        self.assertIn("VAL005", codes)

    def test_unreviewed_valuation_not_flagged(self) -> None:
        codes = self._codes(
            self._val_meta(review_status="pending", data_license=""),
            self._source_meta(),
        )
        self.assertNotIn("VAL004", codes)
        self.assertNotIn("VAL005", codes)


if __name__ == "__main__":
    unittest.main()
