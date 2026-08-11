from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from research_os.schemas.impact_audit import ImpactAuditPacket
from research_os.services.impact_audit import (
    AUDIT_CHECK_NAMES,
    EXPECTED_PENDING_IMPACT_PATHS,
    check_rendered_packet,
    load_audit_spec,
    render_audit_packet,
    validate_audit_spec,
)

EVENT_ID = "EVT-20260101-001"
SOURCE_ID = "SRC-20260101-001"
RELATION_ID = "REL-20260101-001"
SOURCE_PATH = f"01_Inbox/Articles/{SOURCE_ID}-fixture.md"
EVENT_PATH = f"04_Evidence/Events/{EVENT_ID}-fixture.md"
RELATION_PATH = f"05_Research/Assertions/{RELATION_ID}.md"
ASSET_PATH = f"01_Inbox/_assets/{SOURCE_ID}/source.txt"
NOTE_FRAGMENT = "Keep this manual note."
ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = ROOT / "09_Automation" / "audit_impact_assertions.py"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _anchor() -> dict[str, str]:
    quote = "Fixture source directly supports the Event fact."
    return {
        "fact_id": "F1",
        "source_id": SOURCE_ID,
        "asset_path": ASSET_PATH,
        "locator": "L1",
        "quote": quote,
        "quote_sha256": _sha256(quote.encode("utf-8")),
    }


def _relation() -> dict[str, str]:
    return {
        "id": RELATION_ID,
        "path": RELATION_PATH,
        "subject_id": "COM-alpha",
        "predicate": "SUPPLIES",
        "object_id": "COM-beta",
        "evidence_ids": EVENT_ID,
        "review_status": "reviewed",
        "confidence": "0.6",
    }


def _entry(path: str) -> dict[str, object]:
    assertion_id = Path(path).stem
    anchor = _anchor()
    relation = _relation()
    return {
        "assertion_id": assertion_id,
        "path": path,
        "before_sha256": "0" * 64,
        "after_sha256": "0" * 64,
        "recommendation": "ready_for_human_review",
        "rationale": "All material checks pass; a human decision is still required.",
        "event": {
            "id": EVENT_ID,
            "path": EVENT_PATH,
            "title": "Fixture Event",
            "event_date": "2026-01-01",
            "review_status": "reviewed",
            "confidence": 0.7,
            "project_ids": ["PRJ-001"],
            "source_ids": [SOURCE_ID],
            "citation_anchors": [anchor],
        },
        "sources": (
            {
                "id": SOURCE_ID,
                "path": SOURCE_PATH,
                "title": "Fixture Source",
                "publisher": "Fixture Publisher",
                "published_at": "2026-01-01",
                "accessed_at": "2026-01-02",
                "url": "https://example.test/source",
                "local_path": "",
                "asset_paths": [ASSET_PATH],
                "content_sha256": "1" * 64,
                "citation_anchors": [anchor],
            },
        ),
        "subject": {"id": EVENT_ID, "type": "event"},
        "target": {"id": "COM-alpha", "type": "company"},
        "declared_relation": relation,
        "relevant_relations": (relation,),
        "rule_check": {
            "predicate": "SUPPLIES",
            "impact_type": "supply",
            "allowed": True,
            "default_direction": "mixed",
            "conditional": False,
            "weakest_link_confidence": 0.6,
        },
        "checks": {name: "pass" for name in AUDIT_CHECK_NAMES},
        "issues": (),
        "changes": (),
        "preserved_note_fragments": (NOTE_FRAGMENT,),
        "human_review_required": True,
    }


def _packet_payload() -> dict[str, object]:
    entries = tuple(_entry(path) for path in EXPECTED_PENDING_IMPACT_PATHS)
    return {
        "schema_version": 1,
        "audit_id": "impact-assertion-agent-audit-v1",
        "audit_date": "2026-08-10",
        "baseline_commit": "0" * 40,
        "scope": {
            "assertion_count": len(EXPECTED_PENDING_IMPACT_PATHS),
            "pending_assertion_paths": list(EXPECTED_PENDING_IMPACT_PATHS),
        },
        "guardrails": (
            "All Assertions remain pending.",
            "Human review is required.",
        ),
        "summary": {
            "total": len(entries),
            "ready_for_human_review": len(entries),
            "edit_required": 0,
            "reject_recommended": 0,
        },
        "assertions": entries,
    }


class AuditSchemaTests(unittest.TestCase):
    def test_rejects_unknown_recommendation_and_extra_field(self) -> None:
        payload = _packet_payload()
        payload["assertions"][0]["recommendation"] = "approved"
        with self.assertRaises(ValidationError):
            ImpactAuditPacket.model_validate(payload)

        payload = _packet_payload()
        payload["unexpected"] = True
        with self.assertRaises(ValidationError):
            ImpactAuditPacket.model_validate(payload)

    def test_recursively_rejects_human_review_fields(self) -> None:
        for forbidden in ("reviewer", "decision", "reviewed_at"):
            payload = _packet_payload()
            payload["assertions"][0]["event"][forbidden] = "must-not-exist"
            with self.subTest(forbidden=forbidden), self.assertRaises(ValidationError):
                ImpactAuditPacket.model_validate(payload)


class SyntheticAuditRepository:
    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self._build()

    def close(self) -> None:
        self._temporary.cleanup()

    def _build(self) -> None:
        asset_bytes = b"fixture source asset\n"
        _write(self.root, ASSET_PATH, asset_bytes.decode("utf-8"))
        anchor = _anchor()
        _write(
            self.root,
            SOURCE_PATH,
            f"""---
id: {SOURCE_ID}
type: source
title: Fixture Source
publisher: Fixture Publisher
published_at: 2026-01-01
accessed_at: 2026-01-02
url: https://example.test/source
local_path: ''
asset_paths: [{ASSET_PATH}]
content_sha256: {_sha256(asset_bytes)}
project_ids: [PRJ-001]
review_status: reviewed
---

# Source
""",
        )
        _write(
            self.root,
            EVENT_PATH,
            f"""---
id: {EVENT_ID}
type: event
title: Fixture Event
event_date: 2026-01-01
project_ids: [PRJ-001]
review_status: reviewed
confidence: 0.7
source_ids: [{SOURCE_ID}]
citation_anchors:
  - fact_id: {anchor["fact_id"]}
    source_id: {anchor["source_id"]}
    asset_path: {anchor["asset_path"]}
    locator: {anchor["locator"]}
    quote: {anchor["quote"]}
    quote_sha256: {anchor["quote_sha256"]}
---

# Event

## Facts

- F1: Fixture source directly supports the Event fact.

## Inferences

- The fact may affect supply.

## Research judgment

- The direction remains subject to human review.
""",
        )
        _write(
            self.root,
            RELATION_PATH,
            f"""---
id: {RELATION_ID}
type: ontology_assertion
subject_id: COM-alpha
predicate: SUPPLIES
object_id: COM-beta
evidence_ids: [{EVENT_ID}]
review_status: reviewed
confidence: 0.6
---

# Ontology Assertion
""",
        )
        for path in EXPECTED_PENDING_IMPACT_PATHS:
            assertion_id = Path(path).stem
            _write(
                self.root,
                path,
                f"""---
id: {assertion_id}
type: impact_assertion
project_ids: [PRJ-001]
review_status: pending
trigger_event_ids: [{EVENT_ID}]
subject_id: {EVENT_ID}
impact_type: supply
target_id: COM-alpha
direction: mixed
magnitude: unknown
horizon: unknown
mechanism: Fixture Event may affect supply for COM-alpha.
evidence_ids: [{EVENT_ID}]
confidence: 0.6
valid_from: 2026-01-01
generation_method: direct-proposal
relation_id: {RELATION_ID}
predicate: SUPPLIES
---

# Impact Assertion

## Assertion

- Fixture Event may affect supply for COM-alpha.

## Evidence

- {EVENT_ID}

## Review

- Pending human review.

## Notes

- {NOTE_FRAGMENT}
""",
            )
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "audit@example.test")
        _git(self.root, "config", "user.name", "Audit Fixture")
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-qm", "baseline")
        self.baseline_commit = _git(self.root, "rev-parse", "HEAD")

    def packet(self) -> ImpactAuditPacket:
        payload = _packet_payload()
        payload["baseline_commit"] = self.baseline_commit
        asset_hash = _sha256((self.root / ASSET_PATH).read_bytes())
        for entry in payload["assertions"]:
            path = self.root / entry["path"]
            digest = _sha256(path.read_bytes())
            entry["before_sha256"] = digest
            entry["after_sha256"] = digest
            entry["sources"][0]["content_sha256"] = asset_hash
        return ImpactAuditPacket.model_validate(payload)


class AuditValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = SyntheticAuditRepository()
        self.packet = self.repo.packet()

    def tearDown(self) -> None:
        self.repo.close()

    def _updated(self, mutate: object) -> ImpactAuditPacket:
        payload = self.packet.model_dump(mode="python")
        payload["assertions"] = list(payload["assertions"])
        mutate(payload)
        payload["assertions"] = tuple(payload["assertions"])
        return ImpactAuditPacket.model_validate(payload)

    def test_validates_exact_22_row_packet(self) -> None:
        self.assertEqual([], validate_audit_spec(self.repo.root, self.packet))

    def test_detects_scope_hash_notes_and_check_contract_drift(self) -> None:
        missing = self._updated(lambda payload: payload["assertions"].pop())
        self.assertTrue(
            any(
                "exact pending Impact paths" in error
                for error in validate_audit_spec(self.repo.root, missing)
            )
        )

        wrong_hash = self._updated(
            lambda payload: payload["assertions"][0].update({"after_sha256": "f" * 64})
        )
        self.assertTrue(
            any(
                "after_sha256" in error
                for error in validate_audit_spec(self.repo.root, wrong_hash)
            )
        )

        missing_note = self._updated(
            lambda payload: payload["assertions"][0].update(
                {"preserved_note_fragments": ("missing manual note",)}
            )
        )
        self.assertTrue(
            any(
                "preserved note fragment" in error
                for error in validate_audit_spec(self.repo.root, missing_note)
            )
        )

        missing_check = self._updated(
            lambda payload: payload["assertions"][0]["checks"].pop(
                next(iter(AUDIT_CHECK_NAMES))
            )
        )
        self.assertTrue(
            any(
                "exactly 20 audit checks" in error
                for error in validate_audit_spec(self.repo.root, missing_check)
            )
        )

    def test_enforces_project_rule_and_weakest_link_confidence(self) -> None:
        wrong_scope = self._updated(
            lambda payload: payload["assertions"][0]["event"].update(
                {"project_ids": ["PRJ-002"]}
            )
        )
        self.assertTrue(
            any(
                "Event project scope" in error
                for error in validate_audit_spec(self.repo.root, wrong_scope)
            )
        )

        wrong_rule = self._updated(
            lambda payload: payload["assertions"][0]["rule_check"].update(
                {"impact_type": "valuation"}
            )
        )
        self.assertTrue(
            any(
                "rule map" in error
                for error in validate_audit_spec(self.repo.root, wrong_rule)
            )
        )

        first = self.repo.root / EXPECTED_PENDING_IMPACT_PATHS[0]
        first.write_text(
            first.read_text(encoding="utf-8").replace(
                "confidence: 0.6", "confidence: 0.8"
            ),
            encoding="utf-8",
        )
        excessive = self._updated(
            lambda payload: payload["assertions"][0].update(
                {
                    "after_sha256": _sha256(first.read_bytes()),
                    "changes": (
                        {
                            "field": "confidence",
                            "before": 0.6,
                            "after": 0.8,
                            "evidence_basis": [EVENT_ID, RELATION_ID],
                        },
                    ),
                }
            )
        )
        self.assertTrue(
            any(
                "weakest-link confidence" in error
                for error in validate_audit_spec(self.repo.root, excessive)
            )
        )

    def test_requires_reject_for_unresolved_event_or_unverifiable_source(self) -> None:
        event_path = self.repo.root / EVENT_PATH
        event_text = event_path.read_text(encoding="utf-8")
        event_text = (
            event_text.replace(
                "- F1: Fixture source directly supports the Event fact.", "TODO"
            )
            .replace("- The fact may affect supply.", "TODO")
            .replace("- The direction remains subject to human review.", "TODO")
        )
        event_path.write_text(event_text, encoding="utf-8")
        self.assertTrue(
            any(
                "reject_recommended" in error
                for error in validate_audit_spec(self.repo.root, self.packet)
            )
        )

        event_path.write_text(
            event_text.replace("TODO", "Substantive restored content"),
            encoding="utf-8",
        )
        (self.repo.root / ASSET_PATH).unlink()
        self.assertTrue(
            any(
                "reject_recommended" in error
                for error in validate_audit_spec(self.repo.root, self.packet)
            )
        )

    def test_accepts_honestly_recorded_unverifiable_source_rejections(self) -> None:
        payload = self.packet.model_dump(mode="python")
        for entry in payload["assertions"]:
            entry["recommendation"] = "reject_recommended"
            entry["checks"]["source_asset"] = "fail"
            entry["checks"]["citation_anchor"] = "fail"
            entry["issues"] = ("The declared Source asset is unavailable.",)
        payload["summary"] = {
            "total": len(EXPECTED_PENDING_IMPACT_PATHS),
            "ready_for_human_review": 0,
            "edit_required": 0,
            "reject_recommended": len(EXPECTED_PENDING_IMPACT_PATHS),
        }
        packet = ImpactAuditPacket.model_validate(payload)
        (self.repo.root / ASSET_PATH).unlink()
        self.assertEqual([], validate_audit_spec(self.repo.root, packet))

    def test_load_render_and_drift_check_are_deterministic(self) -> None:
        spec = self.repo.root / "audit.json"
        markdown = self.repo.root / "audit.md"
        spec.write_text(self.packet.model_dump_json(indent=2) + "\n", encoding="utf-8")
        rendered = render_audit_packet(self.packet)
        self.assertEqual(rendered, render_audit_packet(self.packet))
        markdown.write_text(rendered, encoding="utf-8")
        self.assertEqual(self.packet, load_audit_spec(spec))
        self.assertEqual([], check_rendered_packet(self.repo.root, spec, markdown))
        markdown.write_text(rendered + "drift\n", encoding="utf-8")
        self.assertTrue(
            any(
                "rendered packet drift" in error
                for error in check_rendered_packet(self.repo.root, spec, markdown)
            )
        )

    def test_cli_applies_and_checks_the_deterministic_packet(self) -> None:
        spec = self.repo.root / "audit.json"
        spec.write_text(self.packet.model_dump_json(indent=2) + "\n", encoding="utf-8")
        command = (
            sys.executable,
            str(AUDIT_SCRIPT),
            "--root",
            str(self.repo.root),
            "--spec",
            str(spec),
        )
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        applied = subprocess.run(
            [*command, "--apply"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(0, applied.returncode, applied.stderr)
        checked = subprocess.run(
            [*command, "--check"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(0, checked.returncode, checked.stderr)
        packet_path = (
            self.repo.root
            / "05_Research"
            / "Reviews"
            / "Impact_Assertion_Agent_Audit_Packet.md"
        )
        self.assertEqual(render_audit_packet(self.packet), packet_path.read_text())


if __name__ == "__main__":
    unittest.main()
