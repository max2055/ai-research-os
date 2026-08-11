from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from research_os.repositories.markdown import MarkdownDocument
    from research_os.schemas import validate_metadata
    from research_os.services.impact_draft import (
        apply_impact_draft,
        prepare_impact_batch,
        prepare_impact_draft,
    )
    from research_os.services.impact_proposal import propose_direct_impacts
    from research_os.services.validation import validate_repository
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("install product dependencies to run Schema tests") from exc

ROOT = Path(__file__).resolve().parents[2]
_REAL_EVENT = "EVT-20260225-034"


def _real_proposal() -> dict:
    objects, findings = validate_repository(ROOT)
    assert not [f for f in findings if f.level == "error"]
    proposals = propose_direct_impacts(objects, event_id=_REAL_EVENT)
    assert proposals, "expected at least one direct proposal for the real event"
    return proposals[0]


class PrepareImpactDraftTests(unittest.TestCase):
    """C-011: proposal dict -> schema-valid pending IMP Markdown (read-only)."""

    def test_draft_roundtrips_through_schema(self) -> None:
        proposal = _real_proposal()
        relative, content = prepare_impact_draft(
            ROOT, proposal=proposal, created_at="2026-08-07"
        )
        self.assertTrue(relative.name.startswith("IMP-"))
        self.assertTrue(relative.name.endswith(".md"))
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / relative.name
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(content, encoding="utf-8")
            doc = MarkdownDocument.read(tmp_path)
            obj = validate_metadata(doc.metadata)
            self.assertEqual("impact_assertion", obj.type)
            self.assertEqual("pending", obj.review_status)
            self.assertEqual(proposal["project_ids"], doc.metadata["project_ids"])
            # extra traceability fields survive round-trip
            self.assertEqual(proposal["relation_id"], doc.metadata["relation_id"])
            self.assertEqual(proposal["predicate"], doc.metadata["predicate"])

    def test_draft_is_pending_with_direct_generation(self) -> None:
        _, content = prepare_impact_draft(
            ROOT, proposal=_real_proposal(), created_at="2026-08-07"
        )
        self.assertIn("review_status: pending", content)
        self.assertIn("generation_method: direct-proposal", content)
        self.assertIn("# Impact Assertion", content)

    def test_draft_preserves_proposal_project_scope(self) -> None:
        proposal = dict(_real_proposal())
        proposal["project_ids"] = ["PRJ-001"]
        _, content = prepare_impact_draft(
            ROOT, proposal=proposal, created_at="2026-08-07"
        )
        self.assertIn("project_ids: [PRJ-001]", content)

    def test_rejects_bad_date(self) -> None:
        with self.assertRaises(ValueError):
            prepare_impact_draft(
                ROOT, proposal=_real_proposal(), created_at="2026/08/07"
            )

    def test_rejects_missing_subject_event(self) -> None:
        proposal = dict(_real_proposal())
        proposal["subject_id"] = "EVT-does-not-exist"
        with self.assertRaises(ValueError):
            prepare_impact_draft(ROOT, proposal=proposal, created_at="2026-08-07")


class PrepareImpactBatchTests(unittest.TestCase):
    """C-014: propose + draft (dry-run) / materialize (apply)."""

    def test_dry_run_previews_without_writing(self) -> None:
        before = set((ROOT / "05_Research/Assertions").glob("IMP-*.md"))
        output = prepare_impact_batch(
            ROOT, event_id=_REAL_EVENT, created_at="2026-08-07"
        )
        after = set((ROOT / "05_Research/Assertions").glob("IMP-*.md"))
        self.assertIn("DRY-RUN: no files changed", output)
        self.assertEqual(before, after)


class ApplyImpactDraftTests(unittest.TestCase):
    """C-011: atomic write, refuses overwrite (temp dir, no repo pollution)."""

    def test_apply_writes_then_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relative = Path("05_Research/Assertions/IMP-test-001.md")
            content = "---\nid: IMP-test-001\ntype: impact_assertion\n---\n# Impact\n"
            path = apply_impact_draft(root, relative, content)
            self.assertTrue(path.exists())
            with self.assertRaises(FileExistsError):
                apply_impact_draft(root, relative, content)


if __name__ == "__main__":
    unittest.main()
