"""Deterministic validation and rendering for pending Impact audits."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from research_os.domain.policies import IMPACT_RULE_MAP
from research_os.repositories.markdown import MarkdownDocument
from research_os.schemas.impact_assertion import (
    DIRECTIONS,
    HORIZONS,
    IMPACT_TYPES,
    MAGNITUDES,
)
from research_os.schemas.impact_audit import ImpactAuditEntry, ImpactAuditPacket

AUDIT_CHECK_NAMES = (
    "assertion_path",
    "assertion_identity",
    "schema_valid",
    "review_pending",
    "project_scope",
    "before_hash",
    "after_hash",
    "trigger_event",
    "event_reviewed",
    "event_substantive",
    "source_provenance",
    "source_asset",
    "citation_anchor",
    "subject_valid",
    "target_valid",
    "declared_relation",
    "relevant_relations",
    "rule_map",
    "weakest_link_confidence",
    "notes_preserved",
)

EXPECTED_PENDING_IMPACT_PATHS = (
    "05_Research/Assertions/IMP-20260807-001.md",
    "05_Research/Assertions/IMP-20260807-002.md",
    "05_Research/Assertions/IMP-20260807-003.md",
    "05_Research/Assertions/IMP-20260807-004.md",
    "05_Research/Assertions/IMP-20260807-005.md",
    "05_Research/Assertions/IMP-20260807-006.md",
    "05_Research/Assertions/IMP-20260807-007.md",
    "05_Research/Assertions/IMP-20260807-008.md",
    "05_Research/Assertions/IMP-20260807-009.md",
    "05_Research/Assertions/IMP-20260808-010.md",
    "05_Research/Assertions/IMP-20260808-011.md",
    "05_Research/Assertions/IMP-20260808-012.md",
    "05_Research/Assertions/IMP-20260808-013.md",
    "05_Research/Assertions/IMP-20260808-014.md",
    "05_Research/Assertions/IMP-20260808-015.md",
    "05_Research/Assertions/IMP-20260808-016.md",
    "05_Research/Assertions/IMP-20260808-017.md",
    "05_Research/Assertions/IMP-20260808-018.md",
    "05_Research/Assertions/IMP-20260809-001.md",
    "05_Research/Assertions/IMP-20260809-002.md",
    "05_Research/Assertions/IMP-20260809-003.md",
    "05_Research/Assertions/IMP-20260809-004.md",
)

_REQUIRED_ASSERTION_FIELDS = frozenset(
    {
        "id",
        "type",
        "project_ids",
        "review_status",
        "trigger_event_ids",
        "subject_id",
        "impact_type",
        "target_id",
        "direction",
        "magnitude",
        "horizon",
        "mechanism",
        "evidence_ids",
        "confidence",
    }
)
_EVENT_SECTIONS = frozenset({"Facts", "Inferences", "Research judgment"})
_UNRESOLVED_RE = re.compile(
    r"^(?:[-*]\s*)?(?:TODO|TBD|TBA|TBC|FIXME|XXX|UNKNOWN|PENDING|N/?A)\b.*$",
    re.IGNORECASE,
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_TYPE_PREFIX = {
    "event": "EVT-",
    "company": "COM-",
    "sector": "SEG-",
    "product": "PRD-",
    "technology": "TEC-",
    "metric": "MET-",
    "security": "INS-",
}


def load_audit_spec(path: Path) -> ImpactAuditPacket:
    """Load a JSON audit spec through the strict packet schema."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("audit spec must contain a JSON object")
    payload["guardrails"] = tuple(payload.get("guardrails", ()))
    assertions = payload.get("assertions", ())
    if isinstance(assertions, list):
        for entry in assertions:
            if not isinstance(entry, dict):
                continue
            for field in (
                "sources",
                "relevant_relations",
                "issues",
                "changes",
                "preserved_note_fragments",
            ):
                entry[field] = tuple(entry.get(field, ()))
        payload["assertions"] = tuple(assertions)
    return ImpactAuditPacket.model_validate(payload)


def validate_audit_spec(root: Path, packet: ImpactAuditPacket) -> list[str]:
    """Validate every packet claim against Git and current repository bytes."""
    root = root.resolve()
    errors: list[str] = []
    _validate_scope(root, packet, errors)
    _validate_summary(packet, errors)
    baseline_ok = _baseline_exists(root, packet.baseline_commit)
    if not baseline_ok:
        errors.append(f"baseline_commit does not resolve: {packet.baseline_commit}")
    for entry in packet.assertions:
        _validate_entry(root, packet, entry, baseline_ok, errors)
    return errors


def render_audit_packet(packet: ImpactAuditPacket) -> str:
    """Render a deterministic, non-authoritative Markdown review packet."""
    lines = [
        "# Pending Impact Assertion Agent Audit Packet",
        "",
        f"- Audit ID: `{packet.audit_id}`",
        f"- Audit date: {packet.audit_date}",
        f"- Baseline commit: `{packet.baseline_commit}`",
        f"- Scope: {len(packet.assertions)} pending Impact Assertions",
        "- Authority: agent audit only; human review remains required",
        "",
        "## Guardrails",
        "",
    ]
    lines.extend(f"- {_markdown_text(item)}" for item in packet.guardrails)
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Recommendation | Count |",
            "|---|---:|",
        ]
    )
    for name in (
        "total",
        "ready_for_human_review",
        "edit_required",
        "reject_recommended",
    ):
        lines.append(f"| `{name}` | {packet.summary.get(name, 0)} |")
    lines.extend(["", "## Assertion Audits", ""])
    for entry in packet.assertions:
        lines.extend(_render_entry(entry))
    return "\n".join(lines).rstrip() + "\n"


def check_rendered_packet(root: Path, spec: Path, markdown: Path) -> list[str]:
    """Validate a spec and report deterministic Markdown drift."""
    root = root.resolve()
    spec_path = _from_root(root, spec)
    markdown_path = _from_root(root, markdown)
    try:
        packet = load_audit_spec(spec_path)
    except (OSError, ValueError, ValidationError) as exc:
        return [f"audit spec invalid: {exc}"]
    errors = validate_audit_spec(root, packet)
    try:
        actual = markdown_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"rendered packet unavailable: {exc}")
        return errors
    expected = render_audit_packet(packet)
    if actual != expected:
        errors.append(f"rendered packet drift: {markdown_path}")
    return errors


def _validate_scope(root: Path, packet: ImpactAuditPacket, errors: list[str]) -> None:
    entry_paths = tuple(entry.path for entry in packet.assertions)
    scope_paths = tuple(packet.scope.get("pending_assertion_paths", ()))
    scope_count = packet.scope.get("assertion_count")
    if (
        entry_paths != EXPECTED_PENDING_IMPACT_PATHS
        or scope_paths != EXPECTED_PENDING_IMPACT_PATHS
        or scope_count != len(EXPECTED_PENDING_IMPACT_PATHS)
    ):
        errors.append(
            "packet must cover the exact pending Impact paths in deterministic order"
        )
    actual_paths = tuple(
        str(path.relative_to(root))
        for path in sorted((root / "05_Research" / "Assertions").glob("IMP-*.md"))
        if path.is_file()
    )
    if actual_paths != EXPECTED_PENDING_IMPACT_PATHS:
        errors.append("repository does not contain the exact pending Impact paths")


def _validate_summary(packet: ImpactAuditPacket, errors: list[str]) -> None:
    expected = {
        "total": len(packet.assertions),
        "ready_for_human_review": sum(
            entry.recommendation == "ready_for_human_review"
            for entry in packet.assertions
        ),
        "edit_required": sum(
            entry.recommendation == "edit_required" for entry in packet.assertions
        ),
        "reject_recommended": sum(
            entry.recommendation == "reject_recommended" for entry in packet.assertions
        ),
    }
    if packet.summary != expected:
        errors.append(f"summary counts do not match assertions: expected {expected}")


def _validate_entry(
    root: Path,
    packet: ImpactAuditPacket,
    entry: ImpactAuditEntry,
    baseline_ok: bool,
    errors: list[str],
) -> None:
    prefix = entry.assertion_id
    checks = set(entry.checks)
    if len(entry.checks) != len(AUDIT_CHECK_NAMES) or checks != set(AUDIT_CHECK_NAMES):
        errors.append(f"{prefix}: checks must contain exactly 20 audit checks")
    if not entry.human_review_required:
        errors.append(f"{prefix}: human_review_required must remain true")

    assertion_path = _repo_path(root, entry.path, prefix, errors)
    if assertion_path is None or not assertion_path.is_file():
        errors.append(f"{prefix}: assertion path is unavailable: {entry.path}")
        return
    current_bytes = assertion_path.read_bytes()
    current_text = current_bytes.decode("utf-8")
    if _sha256(current_bytes) != entry.after_sha256:
        errors.append(f"{prefix}: after_sha256 does not match current bytes")
    baseline_bytes: bytes | None = None
    if baseline_ok:
        baseline_bytes = _git_blob(root, packet.baseline_commit, entry.path)
        if baseline_bytes is None:
            errors.append(f"{prefix}: path is absent from baseline_commit")
        elif _sha256(baseline_bytes) != entry.before_sha256:
            errors.append(f"{prefix}: before_sha256 does not match baseline Git bytes")

    try:
        assertion = MarkdownDocument.read(assertion_path)
    except (OSError, ValueError) as exc:
        errors.append(f"{prefix}: assertion Markdown is invalid: {exc}")
        return
    meta = assertion.metadata
    if (
        Path(entry.path).stem != entry.assertion_id
        or meta.get("id") != entry.assertion_id
    ):
        errors.append(f"{prefix}: assertion identity does not match path/front matter")
    missing = sorted(_REQUIRED_ASSERTION_FIELDS - set(meta))
    if missing:
        errors.append(f"{prefix}: schema_valid missing fields: {', '.join(missing)}")
    _validate_assertion_enums(prefix, meta, errors)
    if meta.get("type") != "impact_assertion":
        errors.append(f"{prefix}: type must be impact_assertion")
    if meta.get("review_status") != "pending":
        errors.append(f"{prefix}: every audited Assertion must remain pending")
    if _string_list(meta.get("project_ids")) != ["PRJ-001"]:
        errors.append(f"{prefix}: Assertion project scope must be exactly PRJ-001")

    event, event_body = _validate_event(root, entry, meta, prefix, errors)
    source_provenance, source_available, anchors_valid = _validate_sources(
        root, entry, event, prefix, errors
    )
    event_substantive = bool(event_body) and _event_has_substance(event_body)
    _validate_recorded_check(
        entry, "event_substantive", event_substantive, prefix, errors
    )
    _validate_recorded_check(
        entry, "source_provenance", source_provenance, prefix, errors
    )
    _validate_recorded_check(entry, "source_asset", source_available, prefix, errors)
    _validate_recorded_check(entry, "citation_anchor", anchors_valid, prefix, errors)
    if not event_substantive and entry.recommendation != "reject_recommended":
        errors.append(
            f"{prefix}: unresolved Event requires recommendation reject_recommended"
        )
    if (
        not (source_provenance and source_available)
        and entry.recommendation != "reject_recommended"
    ):
        errors.append(
            f"{prefix}: unverifiable Source requires recommendation reject_recommended"
        )
    if any(
        value in {"fail", "unknown"} for value in entry.checks.values()
    ) and not entry.issues:
        errors.append(f"{prefix}: failed or unknown checks require a recorded issue")

    _validate_endpoint(entry.subject, meta.get("subject_id"), "subject", prefix, errors)
    _validate_endpoint(entry.target, meta.get("target_id"), "target", prefix, errors)
    weakest = _validate_relations(root, entry, meta, event, prefix, errors)
    _validate_confidence(entry, meta, weakest, prefix, errors)
    _validate_notes(entry, current_text, baseline_bytes, prefix, errors)


def _validate_assertion_enums(
    prefix: str, meta: Mapping[str, Any], errors: list[str]
) -> None:
    values = (
        ("impact_type", IMPACT_TYPES),
        ("direction", DIRECTIONS),
        ("magnitude", MAGNITUDES),
        ("horizon", HORIZONS),
    )
    for field, allowed in values:
        if meta.get(field) not in allowed:
            errors.append(
                f"{prefix}: schema_valid invalid {field}: {meta.get(field)!r}"
            )
    mechanism = meta.get("mechanism")
    if not isinstance(mechanism, str) or not mechanism.strip():
        errors.append(f"{prefix}: schema_valid mechanism is empty")


def _validate_event(
    root: Path,
    entry: ImpactAuditEntry,
    assertion: Mapping[str, Any],
    prefix: str,
    errors: list[str],
) -> tuple[Mapping[str, Any] | None, str]:
    event_id = entry.event.get("id")
    trigger_ids = _string_list(assertion.get("trigger_event_ids"))
    evidence_ids = _string_list(assertion.get("evidence_ids"))
    if (
        not isinstance(event_id, str)
        or event_id not in trigger_ids
        or event_id not in evidence_ids
        or assertion.get("subject_id") != event_id
    ):
        errors.append(f"{prefix}: trigger Event does not match Assertion references")
    raw_path = entry.event.get("path")
    if not isinstance(raw_path, str):
        errors.append(f"{prefix}: Event path is missing")
        return None, ""
    event_path = _repo_path(root, raw_path, prefix, errors)
    if event_path is None or not event_path.is_file():
        errors.append(f"{prefix}: trigger Event path is unavailable: {raw_path}")
        return None, ""
    try:
        document = MarkdownDocument.read(event_path)
    except (OSError, ValueError) as exc:
        errors.append(f"{prefix}: trigger Event Markdown is invalid: {exc}")
        return None, ""
    event = document.metadata
    expected_fields = (
        "id",
        "title",
        "event_date",
        "review_status",
        "confidence",
        "project_ids",
        "source_ids",
        "citation_anchors",
    )
    for field in expected_fields:
        if not _equivalent(entry.event.get(field), event.get(field)):
            errors.append(f"{prefix}: Event {field} does not match repository")
    if event.get("id") != event_id or event.get("type") != "event":
        errors.append(f"{prefix}: trigger Event identity/type is invalid")
    if event.get("review_status") != "reviewed":
        errors.append(f"{prefix}: trigger Event is not reviewed")
    if _string_list(event.get("project_ids")) != ["PRJ-001"]:
        errors.append(f"{prefix}: Event project scope must be exactly PRJ-001")
    if _string_list(entry.event.get("project_ids")) != ["PRJ-001"]:
        errors.append(f"{prefix}: Event project scope row must be exactly PRJ-001")
    return event, document.body


def _validate_sources(
    root: Path,
    entry: ImpactAuditEntry,
    event: Mapping[str, Any] | None,
    prefix: str,
    errors: list[str],
) -> tuple[bool, bool, bool]:
    if event is None:
        return False, False, False
    expected_ids = _string_list(event.get("source_ids"))
    packet_ids = [str(source.get("id", "")) for source in entry.sources]
    if packet_ids != expected_ids:
        errors.append(f"{prefix}: Source rows do not match Event source_ids")
    provenance_complete = bool(entry.sources)
    all_available = bool(entry.sources)
    all_anchors_valid = bool(entry.sources)
    event_anchors = _plain(event.get("citation_anchors") or [])
    for source in entry.sources:
        source_id = str(source.get("id", ""))
        raw_path = source.get("path")
        if not isinstance(raw_path, str):
            errors.append(f"{prefix}: {source_id} Source path is missing")
            provenance_complete = False
            all_available = False
            all_anchors_valid = False
            continue
        source_path = _repo_path(root, raw_path, prefix, errors)
        if source_path is None or not source_path.is_file():
            errors.append(f"{prefix}: {source_id} Source path is unavailable")
            provenance_complete = False
            all_available = False
            all_anchors_valid = False
            continue
        try:
            document = MarkdownDocument.read(source_path)
        except (OSError, ValueError) as exc:
            errors.append(f"{prefix}: {source_id} Source Markdown is invalid: {exc}")
            provenance_complete = False
            all_available = False
            all_anchors_valid = False
            continue
        meta = document.metadata
        provenance_fields = (
            "id",
            "title",
            "publisher",
            "published_at",
            "accessed_at",
            "url",
            "local_path",
            "asset_paths",
            "content_sha256",
        )
        for field in provenance_fields:
            if not _equivalent(source.get(field), meta.get(field)):
                errors.append(
                    f"{prefix}: {source_id} Source provenance {field} mismatch"
                )
        if meta.get("id") != source_id or meta.get("type") != "source":
            errors.append(f"{prefix}: {source_id} Source identity/type is invalid")
        required_text = ("title", "publisher", "published_at", "accessed_at")
        if any(not str(meta.get(field) or "").strip() for field in required_text):
            provenance_complete = False
        if (
            not str(meta.get("url") or "").strip()
            and not str(meta.get("local_path") or "").strip()
        ):
            provenance_complete = False
        if not _source_asset_verifiable(root, meta):
            all_available = False
        source_anchors = source.get("citation_anchors") or []
        expected_anchors = [
            anchor
            for anchor in event_anchors
            if isinstance(anchor, Mapping) and anchor.get("source_id") == source_id
        ]
        if not _equivalent(source_anchors, expected_anchors):
            errors.append(f"{prefix}: {source_id} citation anchors do not match Event")
        if not _anchors_valid(root, source_id, source_anchors):
            all_anchors_valid = False
    return provenance_complete, all_available, all_anchors_valid


def _source_asset_verifiable(root: Path, meta: Mapping[str, Any]) -> bool:
    expected_hash = str(meta.get("content_sha256") or "")
    if not _HASH_RE.fullmatch(expected_hash):
        return False
    candidates = _string_list(meta.get("asset_paths"))
    local_path = str(meta.get("local_path") or "").strip()
    if local_path:
        candidates.append(local_path)
    for raw_path in candidates:
        path = _quiet_repo_path(root, raw_path)
        if (
            path is not None
            and path.is_file()
            and _sha256(path.read_bytes()) == expected_hash
        ):
            return True
    return False


def _anchors_valid(
    root: Path,
    source_id: str,
    anchors: Any,
) -> bool:
    if not isinstance(anchors, Sequence) or isinstance(anchors, (str, bytes)):
        return False
    if not anchors:
        return False
    required = {
        "fact_id",
        "source_id",
        "asset_path",
        "locator",
        "quote",
        "quote_sha256",
    }
    valid = True
    for anchor in anchors:
        if not isinstance(anchor, Mapping) or not required <= set(anchor):
            valid = False
            continue
        quote = str(anchor.get("quote", ""))
        quote_hash = str(anchor.get("quote_sha256", ""))
        asset_path = str(anchor.get("asset_path", ""))
        if anchor.get("source_id") != source_id:
            valid = False
        if _sha256(quote.encode("utf-8")) != quote_hash:
            valid = False
        resolved = _quiet_repo_path(root, asset_path)
        if resolved is None or not resolved.is_file():
            valid = False
    return valid


def _validate_recorded_check(
    entry: ImpactAuditEntry,
    name: str,
    passed: bool,
    prefix: str,
    errors: list[str],
) -> None:
    recorded = entry.checks.get(name)
    if passed and recorded != "pass":
        errors.append(f"{prefix}: {name} must record pass")
    if not passed and recorded not in {"fail", "unknown"}:
        errors.append(f"{prefix}: {name} must record fail or unknown")


def _validate_endpoint(
    endpoint: Mapping[str, str],
    actual_id: Any,
    label: str,
    prefix: str,
    errors: list[str],
) -> None:
    endpoint_id = endpoint.get("id")
    endpoint_type = endpoint.get("type")
    expected_prefix = _TYPE_PREFIX.get(str(endpoint_type))
    if (
        endpoint_id != actual_id
        or expected_prefix is None
        or not str(endpoint_id).startswith(expected_prefix)
    ):
        errors.append(f"{prefix}: {label} id/type is invalid")


def _validate_relations(
    root: Path,
    entry: ImpactAuditEntry,
    assertion: Mapping[str, Any],
    event: Mapping[str, Any] | None,
    prefix: str,
    errors: list[str],
) -> float | None:
    event_confidence = _float_or_none(event.get("confidence")) if event else None
    relation_id = str(assertion.get("relation_id") or "")
    predicate = str(assertion.get("predicate") or "")
    declared_id = str(entry.declared_relation.get("id") or "")
    if (
        declared_id != relation_id
        or str(entry.declared_relation.get("predicate") or "") != predicate
    ):
        errors.append(f"{prefix}: declared relation does not match Assertion")
    if not relation_id or not predicate:
        if entry.relevant_relations:
            errors.append(f"{prefix}: manual Assertion cannot claim relevant relations")
        return event_confidence

    confidences: list[float] = []
    relevant_ids: list[str] = []
    for relation in entry.relevant_relations:
        relation_meta = _validate_relation_row(root, relation, prefix, errors)
        relation_row_id = str(relation.get("id") or "")
        relevant_ids.append(relation_row_id)
        if relation_meta is not None:
            confidence = _float_or_none(relation_meta.get("confidence"))
            if confidence is not None:
                confidences.append(confidence)
    if relevant_ids.count(relation_id) != 1 or len(relevant_ids) != len(
        set(relevant_ids)
    ):
        errors.append(
            f"{prefix}: relevant relations must include declared relation once"
        )
    declared_meta = _validate_relation_row(
        root, entry.declared_relation, prefix, errors
    )
    if declared_meta is not None and event is not None:
        if str(event.get("id")) not in _string_list(declared_meta.get("evidence_ids")):
            errors.append(f"{prefix}: declared relation does not cite trigger Event")
        if declared_meta.get("review_status") != "reviewed":
            errors.append(f"{prefix}: declared relation is not reviewed")
    _validate_rule_check(entry, assertion, predicate, prefix, errors)
    values = [value for value in [event_confidence, *confidences] if value is not None]
    return min(values) if values else None


def _validate_relation_row(
    root: Path,
    relation: Mapping[str, str],
    prefix: str,
    errors: list[str],
) -> Mapping[str, Any] | None:
    relation_id = str(relation.get("id") or "")
    raw_path = relation.get("path")
    if not relation_id or not raw_path:
        errors.append(f"{prefix}: relation row is missing id/path")
        return None
    path = _repo_path(root, raw_path, prefix, errors)
    if path is None or not path.is_file():
        errors.append(f"{prefix}: relation path is unavailable: {raw_path}")
        return None
    try:
        document = MarkdownDocument.read(path)
    except (OSError, ValueError) as exc:
        errors.append(f"{prefix}: relation Markdown is invalid: {exc}")
        return None
    meta = document.metadata
    fields = (
        "id",
        "subject_id",
        "predicate",
        "object_id",
        "review_status",
    )
    for field in fields:
        if not _equivalent(relation.get(field), meta.get(field)):
            errors.append(f"{prefix}: relation {relation_id} {field} mismatch")
    raw_packet_evidence: Any = relation.get("evidence_ids")
    packet_evidence = raw_packet_evidence
    actual_evidence = _string_list(meta.get("evidence_ids"))
    if isinstance(packet_evidence, str):
        packet_evidence = [packet_evidence]
    if not _equivalent(packet_evidence, actual_evidence):
        errors.append(f"{prefix}: relation {relation_id} evidence_ids mismatch")
    packet_confidence = _float_or_none(relation.get("confidence"))
    actual_confidence = _float_or_none(meta.get("confidence"))
    if packet_confidence != actual_confidence:
        errors.append(f"{prefix}: relation {relation_id} confidence mismatch")
    if meta.get("id") != relation_id or meta.get("type") != "ontology_assertion":
        errors.append(f"{prefix}: relation {relation_id} identity/type is invalid")
    return meta


def _validate_rule_check(
    entry: ImpactAuditEntry,
    assertion: Mapping[str, Any],
    predicate: str,
    prefix: str,
    errors: list[str],
) -> None:
    impact_type = str(assertion.get("impact_type") or "")
    rule = IMPACT_RULE_MAP.get(predicate, {}).get(impact_type)
    check = entry.rule_check
    if rule is None:
        errors.append(
            f"{prefix}: predicate/impact_type combination is absent from rule map"
        )
        return
    direction, conditional = rule
    expected = {
        "predicate": predicate,
        "impact_type": impact_type,
        "allowed": True,
        "default_direction": direction,
        "conditional": conditional,
    }
    if any(not _equivalent(check.get(key), value) for key, value in expected.items()):
        errors.append(f"{prefix}: rule map check does not match approved mapping")


def _validate_confidence(
    entry: ImpactAuditEntry,
    assertion: Mapping[str, Any],
    weakest: float | None,
    prefix: str,
    errors: list[str],
) -> None:
    assertion_confidence = _float_or_none(assertion.get("confidence"))
    packet_weakest = _float_or_none(entry.rule_check.get("weakest_link_confidence"))
    if weakest is None:
        if assertion_confidence is not None or packet_weakest is not None:
            errors.append(f"{prefix}: weakest-link confidence must remain unknown")
        return
    if packet_weakest is None or abs(packet_weakest - weakest) > 1e-12:
        errors.append(f"{prefix}: weakest-link confidence calculation is incorrect")
    if assertion_confidence is None or assertion_confidence > weakest + 1e-12:
        errors.append(f"{prefix}: Assertion exceeds weakest-link confidence")


def _validate_notes(
    entry: ImpactAuditEntry,
    current_text: str,
    baseline_bytes: bytes | None,
    prefix: str,
    errors: list[str],
) -> None:
    baseline_text = (
        baseline_bytes.decode("utf-8", errors="replace")
        if baseline_bytes is not None
        else ""
    )
    for fragment in entry.preserved_note_fragments:
        if (
            not fragment.strip()
            or fragment not in current_text
            or (baseline_text and fragment not in baseline_text)
        ):
            errors.append(f"{prefix}: preserved note fragment is missing: {fragment!r}")


def _event_has_substance(body: str) -> bool:
    current: str | None = None
    substantive: list[str] = []
    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip()
            continue
        if current not in _EVENT_SECTIONS or not stripped:
            continue
        cleaned = re.sub(r"^[-*]\s*", "", stripped).strip()
        if cleaned and not _UNRESOLVED_RE.fullmatch(cleaned):
            substantive.append(cleaned)
    return bool(substantive)


def _baseline_exists(root: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _git_blob(root: Path, commit: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def _repo_path(
    root: Path, raw_path: str, prefix: str, errors: list[str]
) -> Path | None:
    path = _quiet_repo_path(root, raw_path)
    if path is None:
        errors.append(f"{prefix}: unsafe repository path: {raw_path!r}")
    return path


def _quiet_repo_path(root: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (root / candidate).resolve()
    return resolved if resolved.is_relative_to(root) else None


def _from_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return [str(value)]


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(child) for child in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _equivalent(left: Any, right: Any) -> bool:
    return bool(_plain(left) == _plain(right))


def _render_entry(entry: ImpactAuditEntry) -> list[str]:
    rule_json = json.dumps(
        entry.rule_check, ensure_ascii=False, sort_keys=True, indent=2
    )
    lines = [
        f"### {entry.assertion_id}",
        "",
        f"- Path: `{entry.path}`",
        f"- Before SHA-256: `{entry.before_sha256}`",
        f"- After SHA-256: `{entry.after_sha256}`",
        f"- Recommendation: `{entry.recommendation}`",
        f"- Rationale: {_markdown_text(entry.rationale)}",
        "- Human review required: yes",
        "",
        "#### Context",
        "",
        f"- Event: `{entry.event.get('id', '')}`",
        f"- Subject: `{entry.subject.get('id', '')}` ({entry.subject.get('type', '')})",
        f"- Target: `{entry.target.get('id', '')}` ({entry.target.get('type', '')})",
        f"- Declared relation: `{entry.declared_relation.get('id', '') or 'none'}`",
        f"- Sources: {_id_list(entry.sources)}",
        "",
        "#### Rule Check",
        "",
        f"```json\n{rule_json}\n```",
        "",
        "#### Audit Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for name in AUDIT_CHECK_NAMES:
        lines.append(f"| `{name}` | `{entry.checks.get(name, 'missing')}` |")
    lines.extend(["", "#### Issues", ""])
    lines.extend(_bullet_items(entry.issues))
    lines.extend(["", "#### Proposed Changes", ""])
    if entry.changes:
        for change in entry.changes:
            lines.append(
                "- "
                + _markdown_text(json.dumps(change, ensure_ascii=False, sort_keys=True))
            )
    else:
        lines.append("- None.")
    lines.extend(["", "#### Preserved Notes", ""])
    lines.extend(f"- {_markdown_text(note)}" for note in entry.preserved_note_fragments)
    lines.append("")
    return lines


def _id_list(rows: Sequence[Mapping[str, Any]]) -> str:
    values = [f"`{row.get('id', '')}`" for row in rows]
    return ", ".join(values) if values else "none"


def _bullet_items(items: Sequence[str]) -> list[str]:
    return [f"- {_markdown_text(item)}" for item in items] if items else ["- None."]


def _markdown_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ").strip()
