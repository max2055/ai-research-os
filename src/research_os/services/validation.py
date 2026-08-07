"""Repository-wide semantic validation over formal Markdown schemas."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from research_os.domain.models import Finding, ResearchObject
from research_os.domain.policies import (
    ID_PATTERNS,
    RELATIONSHIPS,
    REQUIRED_HEADINGS,
    checklist_item_checked,
    headings,
    is_iso_date,
)
from research_os.repositories.markdown import MarkdownDocument, object_paths


def add(
    findings: list[Finding],
    level: str,
    code: str,
    obj_or_path: ResearchObject | Path,
    message: str,
) -> None:
    path = obj_or_path.path if isinstance(obj_or_path, ResearchObject) else obj_or_path
    findings.append(Finding(level, code, path, message))


def taxonomy_codes(root: Path) -> set[str]:
    text = (root / "00_System" / "Taxonomy.md").read_text(encoding="utf-8")
    codes = set(re.findall(r"`([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)`", text))
    codes.update(
        re.findall(
            r"^#{3,4}\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)(?:：|\s)",
            text,
            flags=re.MULTILINE,
        )
    )
    return codes


def load_objects(
    root: Path,
) -> tuple[list[ResearchObject], list[Finding]]:
    objects: list[ResearchObject] = []
    findings: list[Finding] = []
    for path in object_paths(root):
        try:
            document = MarkdownDocument.read(path)
            schema = document.validate()
            objects.append(
                ResearchObject(
                    path=path,
                    metadata=schema.semantic_metadata(),
                    body=document.body.lstrip("\r\n"),
                )
            )
        except (OSError, ValueError, ValidationError) as exc:
            add(findings, "error", "SCH001", path, str(exc))
    return objects, findings


def validate_identity(
    obj: ResearchObject,
    findings: list[Finding],
) -> None:
    pattern = ID_PATTERNS.get(obj.object_type)
    if pattern is None:
        add(
            findings,
            "error",
            "ID001",
            obj,
            f"unsupported type {obj.object_type!r}",
        )
        return
    if not pattern.fullmatch(obj.object_id):
        add(
            findings,
            "error",
            "ID002",
            obj,
            f"id {obj.object_id!r} does not match type {obj.object_type!r}",
        )
    if not obj.path.name.startswith(obj.object_id):
        add(
            findings,
            "error",
            "ID003",
            obj,
            "filename must begin with the permanent object id",
        )


def validate_headings(
    obj: ResearchObject,
    findings: list[Finding],
) -> None:
    missing = sorted(REQUIRED_HEADINGS.get(obj.object_type, set()) - headings(obj.body))
    if missing:
        add(
            findings,
            "error",
            "BODY001",
            obj,
            "missing sections: " + ", ".join(missing),
        )


def validate_type_semantics(
    obj: ResearchObject,
    findings: list[Finding],
) -> None:
    meta = obj.metadata
    if obj.object_type == "source":
        if not meta.get("url") and not meta.get("local_path"):
            add(findings, "error", "SRC006", obj, "url or local_path is required")
        processing_status = meta.get("processing_status")
        if processing_status in {"captured", "processed"} and (
            not meta.get("asset_paths")
            or not meta.get("content_sha256")
            or not meta.get("fetched_at")
        ):
            add(
                findings,
                "error",
                "SRC008",
                obj,
                "captured/processed Source requires assets, hash and fetched_at",
            )
        if processing_status == "failed" and not meta.get("processing_error"):
            add(
                findings,
                "error",
                "SRC009",
                obj,
                "failed Source requires processing_error",
            )
        if processing_status != "failed" and meta.get("processing_error"):
            add(
                findings,
                "error",
                "SRC010",
                obj,
                "processing_error is only valid when processing_status is failed",
            )
    elif obj.object_type == "event":
        impact_ids: set[str] = set()
        for line in obj.body.splitlines():
            match = re.match(
                r"^\|\s*(THS-\d{3})\s*\|\s*([a-z]+)\s*\|",
                line,
            )
            if not match:
                continue
            impact_ids.add(match.group(1))
            if match.group(2) not in RELATIONSHIPS:
                add(
                    findings,
                    "error",
                    "EVT003",
                    obj,
                    f"invalid Thesis relationship {match.group(2)!r}",
                )
        linked_ids = {str(value) for value in meta.get("thesis_links", [])}
        for thesis_id in sorted(impact_ids - linked_ids):
            add(
                findings,
                "error",
                "EVT004",
                obj,
                f"Thesis impact table uses {thesis_id} absent from thesis_links",
            )
        for thesis_id in sorted(linked_ids - impact_ids):
            add(
                findings,
                "error",
                "EVT005",
                obj,
                f"thesis_links includes {thesis_id} absent from Thesis impact table",
            )
    elif obj.object_type == "thesis":
        if meta.get("review_status") == "reviewed" and not is_iso_date(
            meta.get("review_date")
        ):
            add(
                findings,
                "error",
                "THS002",
                obj,
                "reviewed Thesis requires review_date",
            )
    elif obj.object_type == "report":
        status = meta.get("status")
        review_status = meta.get("review_status")
        if status == "final" and review_status != "reviewed":
            add(
                findings,
                "error",
                "RPT003",
                obj,
                "final Report must have review_status reviewed",
            )
        if status == "draft" and review_status == "reviewed":
            add(
                findings,
                "error",
                "RPT004",
                obj,
                "reviewed Report must not remain draft",
            )
        if status == "final" and review_status == "reviewed" and "待审核" in obj.body:
            add(
                findings,
                "error",
                "RPT005",
                obj,
                "final/reviewed Report contains ambiguous pending-review text",
            )
        if bool(meta.get("superseded_by")) != (
            status == "superseded" and review_status == "superseded"
        ):
            add(
                findings,
                "error",
                "RPT009",
                obj,
                "superseded_by requires superseded status and review_status",
            )


def validate_taxonomy(
    obj: ResearchObject,
    codes: set[str],
    findings: list[Finding],
) -> None:
    for field in ("tags", "technologies"):
        for value in obj.metadata.get(field, []):
            if isinstance(value, str) and value not in codes:
                add(
                    findings,
                    "error",
                    "TAX001",
                    obj,
                    f"unknown Taxonomy code {value!r} in {field}",
                )


def expect_refs(
    obj: ResearchObject,
    field: str,
    expected_type: str | None,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    for value in obj.metadata.get(field, []) or []:
        target = by_id.get(str(value))
        if target is None:
            add(
                findings,
                "error",
                "REF001",
                obj,
                f"{field} references missing object {value!r}",
            )
        elif expected_type is not None and target.object_type != expected_type:
            add(
                findings,
                "error",
                "REF002",
                obj,
                f"{field} references {target.object_type}, expected {expected_type}",
            )


def expect_ref(
    obj: ResearchObject,
    field: str,
    expected_type: str | None,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    value = obj.metadata.get(field)
    if not value:
        return
    target = by_id.get(str(value))
    if target is None:
        add(
            findings,
            "error",
            "REF001",
            obj,
            f"{field} references missing object {value!r}",
        )
    elif expected_type is not None and target.object_type != expected_type:
        add(
            findings,
            "error",
            "REF002",
            obj,
            f"{field} references {target.object_type}, expected {expected_type}",
        )


def validate_refs(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if obj.object_type != "project":
        expect_refs(obj, "project_ids", "project", by_id, findings)
    for field, expected_type in (
        ("companies", "company"),
        ("source_ids", "source"),
        ("evidence_ids", "event"),
    ):
        if field in obj.metadata:
            expect_refs(obj, field, expected_type, by_id, findings)
    if obj.object_type == "event":
        expect_refs(obj, "thesis_links", "thesis", by_id, findings)
    elif obj.object_type == "thesis":
        expect_refs(obj, "supporting_evidence", "event", by_id, findings)
        expect_refs(obj, "contradicting_evidence", "event", by_id, findings)
    elif obj.object_type == "report":
        expect_refs(obj, "thesis_ids", "thesis", by_id, findings)
        expect_ref(obj, "supersedes", "report", by_id, findings)
        expect_ref(obj, "superseded_by", "report", by_id, findings)
    elif obj.object_type == "company":
        expect_refs(obj, "related_entities", "company", by_id, findings)
    elif obj.object_type == "project":
        current_report = obj.metadata.get("current_report_id")
        if current_report:
            expect_ref(
                obj,
                "current_report_id",
                "report",
                by_id,
                findings,
            )
    elif obj.object_type == "review":
        for target_id in obj.metadata.get("target_ids", []):
            if str(target_id) not in by_id:
                add(
                    findings,
                    "error",
                    "REF001",
                    obj,
                    f"target_ids references missing object {target_id!r}",
                )
    elif obj.object_type == "action":
        source_review_id = obj.metadata.get("source_review_id")
        if source_review_id:
            expect_ref(
                obj,
                "source_review_id",
                "review",
                by_id,
                findings,
            )
    if obj.object_type == "source":
        expect_refs(
            obj,
            "upstream_source_ids",
            "source",
            by_id,
            findings,
        )
    # v0.3 entity reference integrity (WP-103). References are format-validated
    # by the schema (WP-102); existence/type checks live here now that entities
    # exist in the Universe.
    if obj.object_type == "company":
        expect_refs(obj, "sector_ids", "sector", by_id, findings)
        expect_refs(obj, "product_ids", "product", by_id, findings)
        expect_refs(obj, "technology_ids", "technology", by_id, findings)
        expect_refs(obj, "security_ids", "security", by_id, findings)
        expect_refs(obj, "source_channel_ids", "source_channel", by_id, findings)
        expect_refs(obj, "key_metric_ids", "metric", by_id, findings)
    elif obj.object_type == "sector":
        expect_refs(obj, "core_company_ids", "company", by_id, findings)
        expect_refs(obj, "tracked_company_ids", "company", by_id, findings)
        parent_id = obj.metadata.get("parent_id")
        if parent_id:
            expect_ref(obj, "parent_id", "sector", by_id, findings)
    elif obj.object_type == "security":
        expect_ref(obj, "issuer_company_id", "company", by_id, findings)
    elif obj.object_type in {"product", "technology"}:
        expect_refs(obj, "owner_company_ids", "company", by_id, findings)
        expect_refs(obj, "sector_ids", "sector", by_id, findings)
        parent_id = obj.metadata.get("parent_id")
        if parent_id:
            expect_ref(
                obj,
                "parent_id",
                obj.object_type,
                by_id,
                findings,
            )
    elif obj.object_type == "metric":
        expect_refs(obj, "owner_entity_ids", None, by_id, findings)
    elif obj.object_type == "source_channel":
        expect_refs(obj, "entity_ids", "company", by_id, findings)
        expect_refs(obj, "sector_ids", "sector", by_id, findings)
    elif obj.object_type == "ontology_assertion":
        expect_ref(obj, "subject_id", None, by_id, findings)
        expect_ref(obj, "object_id", None, by_id, findings)
        expect_refs(obj, "evidence_ids", "event", by_id, findings)
        expect_refs(obj, "source_ids", "source", by_id, findings)
    elif obj.object_type == "impact_assertion":
        expect_refs(obj, "trigger_event_ids", "event", by_id, findings)
        expect_ref(obj, "subject_id", None, by_id, findings)
        expect_ref(obj, "target_id", None, by_id, findings)
        expect_refs(obj, "evidence_ids", "event", by_id, findings)


def validate_reviewed_assertion_evidence(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    """Phase 0-1 §5: a reviewed assertion must have >=1 reviewed Evidence."""
    if obj.object_type not in {"ontology_assertion", "impact_assertion"}:
        return
    if obj.metadata.get("review_status") != "reviewed":
        return
    evidence_ids = obj.metadata.get("evidence_ids", []) or []
    if not evidence_ids:
        add(
            findings,
            "error",
            "REF003",
            obj,
            f"reviewed {obj.object_type} has no evidence_ids",
        )
        return
    for evidence_id in evidence_ids:
        target = by_id.get(str(evidence_id))
        if target is not None and target.metadata.get("review_status") == "reviewed":
            return
    add(
        findings,
        "error",
        "REF004",
        obj,
        f"reviewed {obj.object_type} has no reviewed Evidence",
    )


def validate_source_assets(
    root: Path,
    objects: list[ResearchObject],
    findings: list[Finding],
) -> None:
    for obj in objects:
        if obj.object_type != "source":
            continue
        for value in obj.metadata.get("asset_paths", []):
            relative = Path(str(value))
            target = (root / relative).resolve()
            if relative.is_absolute() or not target.is_relative_to(root):
                add(
                    findings,
                    "error",
                    "AST001",
                    obj,
                    f"asset path escapes repository: {value}",
                )
            elif not target.is_file():
                add(
                    findings,
                    "warning",
                    "AST002",
                    obj,
                    f"archived asset is unavailable locally: {value}",
                )


def _section(body: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def validate_generated_event(
    root: Path,
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if (
        obj.object_type != "event"
        or obj.metadata.get("generation_method", "manual") == "manual"
    ):
        return
    anchors = obj.metadata.get("citation_anchors", [])
    fact_ids = set(re.findall(r"(?m)^- \*\*(F[1-9]\d*)\*\*", obj.body))
    anchor_ids = {str(anchor.get("fact_id")) for anchor in anchors}
    if not anchors or fact_ids != anchor_ids:
        add(
            findings,
            "error",
            "EVT006",
            obj,
            "generated Event Facts and citation_anchors must match one-to-one",
        )
    source_ids = {str(value) for value in obj.metadata.get("source_ids", [])}
    for anchor in anchors:
        source_id = str(anchor.get("source_id"))
        source = by_id.get(source_id)
        asset = Path(str(anchor.get("asset_path", "")))
        if source_id not in source_ids or source is None:
            add(
                findings,
                "error",
                "EVT007",
                obj,
                f"citation anchor references unlisted Source {source_id}",
            )
            continue
        if str(asset) not in {
            str(value) for value in source.metadata.get("asset_paths", [])
        }:
            add(
                findings,
                "error",
                "EVT008",
                obj,
                f"citation asset is not owned by {source_id}: {asset}",
            )
            continue
        target = root / asset
        if not target.is_file():
            add(
                findings,
                "error",
                "EVT009",
                obj,
                f"citation asset is unavailable: {asset}",
            )
            continue
        quote = str(anchor.get("quote", ""))
        actual_hash = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        if actual_hash != anchor.get("quote_sha256"):
            add(findings, "error", "EVT010", obj, "citation quote hash mismatch")
        locator = str(anchor.get("locator", ""))
        match = re.fullmatch(r"L(\d+)(?:-L?(\d+))?", locator)
        if not match:
            continue
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        # Locators are generated from newline boundaries. PDF text can contain
        # form-feed characters that ``splitlines()`` treats as an additional
        # line even though they do not increment the generated Lx locator.
        lines = target.read_text(encoding="utf-8").split("\n")
        located = "\n".join(lines[start - 1 : end])
        # A precise quote may begin or end within the located line range. The
        # quote hash protects its exact text; the locator only needs to resolve
        # to a range containing it.
        if quote not in located:
            add(
                findings,
                "error",
                "EVT011",
                obj,
                f"citation locator does not resolve to quote: {asset}#{locator}",
            )
    groups = obj.metadata.get("source_independence_groups", [])
    grouped = [str(value) for group in groups for value in group]
    if sorted(grouped) != sorted(source_ids) or len(grouped) != len(set(grouped)):
        add(
            findings,
            "error",
            "EVT012",
            obj,
            "source_independence_groups must partition source_ids",
        )
    for heading in ("Alternative explanations", "Unknowns"):
        content = _section(obj.body, heading)
        if not content or "TODO" in content.upper():
            add(
                findings,
                "error",
                "EVT013",
                obj,
                f"generated Event requires substantive {heading}",
            )


def validate_generated_report(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if (
        obj.object_type != "report"
        or obj.metadata.get("generation_method", "manual") == "manual"
    ):
        return
    if "TODO" in obj.body.upper():
        add(findings, "error", "RPT006", obj, "generated Report contains TODO")
    non_reviewed = [
        str(event_id)
        for event_id in obj.metadata.get("evidence_ids", [])
        if by_id.get(str(event_id))
        and by_id[str(event_id)].metadata.get("review_status") != "reviewed"
    ]
    if non_reviewed:
        add(
            findings,
            "error",
            "RPT007",
            obj,
            "generated Report references non-reviewed Evidence: "
            + ", ".join(non_reviewed),
        )
    contradicting = [
        event.object_id
        for event_id in obj.metadata.get("evidence_ids", [])
        if (event := by_id.get(str(event_id)))
        if re.search(
            r"(?m)^\|\s*THS-\d{3}\s*\|\s*contradicting\s*\|",
            event.body,
        )
    ]
    missing = [
        event_id
        for event_id in contradicting
        if event_id not in _section(obj.body, "Contradicting Evidence")
    ]
    if missing:
        add(
            findings,
            "error",
            "RPT008",
            obj,
            "generated Report omitted contradicting Evidence: " + ", ".join(missing),
        )


def validate_report_supersession(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if obj.object_type != "report":
        return
    successor_id = obj.metadata.get("superseded_by")
    if successor_id:
        successor = by_id.get(str(successor_id))
        if successor and successor.metadata.get("supersedes") != obj.object_id:
            add(
                findings,
                "error",
                "RPT010",
                obj,
                f"superseded_by is not reciprocal in {successor_id}",
            )
    prior_id = obj.metadata.get("supersedes")
    if (
        prior_id
        and obj.metadata.get("status") == "final"
        and obj.metadata.get("review_status") == "reviewed"
    ):
        prior = by_id.get(str(prior_id))
        if prior and prior.metadata.get("superseded_by") != obj.object_id:
            add(
                findings,
                "error",
                "RPT011",
                obj,
                f"final Report supersession is not reciprocal in {prior_id}",
            )


def validate_generation_fingerprints(
    objects: list[ResearchObject],
    findings: list[Finding],
) -> None:
    seen: dict[tuple[str, str], ResearchObject] = {}
    for obj in objects:
        value = obj.metadata.get("generation_fingerprint")
        if not value:
            continue
        key = (obj.object_type, str(value))
        if key in seen:
            add(
                findings,
                "error",
                "GEN001",
                obj,
                f"generation fingerprint duplicates {seen[key].object_id}",
            )
        else:
            seen[key] = obj


def validate_review_invariants(
    obj: ResearchObject,
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    if obj.metadata.get("review_status") != "reviewed":
        return
    if obj.object_type == "report":
        for event_id in obj.metadata.get("evidence_ids", []):
            event = by_id.get(str(event_id))
            if event and event.metadata.get("review_status") != "reviewed":
                add(
                    findings,
                    "error",
                    "REV001",
                    obj,
                    f"reviewed Report references non-reviewed Event {event_id}",
                )
    elif obj.object_type == "thesis":
        evidence = list(obj.metadata.get("supporting_evidence", []))
        evidence += list(obj.metadata.get("contradicting_evidence", []))
        for event_id in evidence:
            event = by_id.get(str(event_id))
            if event and event.metadata.get("review_status") != "reviewed":
                add(
                    findings,
                    "error",
                    "REV002",
                    obj,
                    f"reviewed Thesis references non-reviewed Event {event_id}",
                )
    elif obj.object_type == "event":
        for source_id in obj.metadata.get("source_ids", []):
            source = by_id.get(str(source_id))
            if source and source.metadata.get("review_status") != "reviewed":
                add(
                    findings,
                    "warning",
                    "REV003",
                    obj,
                    f"reviewed Event has pending Source-level review {source_id}",
                )


def validate_source_processing(
    objects: list[ResearchObject],
    by_id: dict[str, ResearchObject],
    findings: list[Finding],
) -> None:
    referenced = {
        str(source_id)
        for obj in objects
        if obj.object_type == "event"
        for source_id in obj.metadata.get("source_ids", [])
    }
    for source_id in sorted(referenced):
        source = by_id.get(source_id)
        if (
            source
            and source.object_type == "source"
            and not checklist_item_checked(
                source.body,
                "Event extraction completed",
            )
        ):
            add(
                findings,
                "error",
                "SRC007",
                source,
                "Source is referenced by an Event but extraction "
                "is not marked complete",
            )


def validate_repository(
    root: Path,
) -> tuple[list[ResearchObject], list[Finding]]:
    root = root.resolve()
    objects, findings = load_objects(root)
    by_id: dict[str, ResearchObject] = {}
    for obj in objects:
        validate_identity(obj, findings)
        if obj.object_id in by_id:
            add(
                findings,
                "error",
                "ID004",
                obj,
                f"duplicate id also used by {by_id[obj.object_id].path}",
            )
        elif obj.object_id:
            by_id[obj.object_id] = obj
    try:
        codes = taxonomy_codes(root)
    except OSError as exc:
        add(findings, "error", "TAX000", root / "00_System/Taxonomy.md", str(exc))
        codes = set()
    for obj in objects:
        validate_type_semantics(obj, findings)
        validate_headings(obj, findings)
        validate_taxonomy(obj, codes, findings)
        validate_refs(obj, by_id, findings)
        validate_review_invariants(obj, by_id, findings)
        validate_generated_event(root, obj, by_id, findings)
        validate_generated_report(obj, by_id, findings)
        validate_report_supersession(obj, by_id, findings)
        validate_reviewed_assertion_evidence(obj, by_id, findings)
    validate_source_processing(objects, by_id, findings)
    validate_source_assets(root, objects, findings)
    validate_generation_fingerprints(objects, findings)
    findings.sort(
        key=lambda item: (str(item.path), item.level, item.code, item.message)
    )
    return objects, findings


def count_by_type(
    objects: Iterable[ResearchObject],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for obj in objects:
        counts[obj.object_type] = counts.get(obj.object_type, 0) + 1
    return counts
