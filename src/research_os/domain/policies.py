"""Stable research policy constants and small pure helpers."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

REVIEW_STATUSES = frozenset({"pending", "reviewed", "rejected", "superseded"})
RELATIONSHIPS = frozenset({"supporting", "contradicting", "contextual"})
ID_PATTERNS = {
    "source": re.compile(r"^SRC-\d{8}-\d{3}$"),
    "event": re.compile(r"^EVT-\d{8}-\d{3}$"),
    "thesis": re.compile(r"^THS-\d{3}$"),
    "company": re.compile(r"^COM-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    "report": re.compile(r"^RPT-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    "project": re.compile(r"^PRJ-\d{3}$"),
    "review": re.compile(r"^REV-\d{8}-\d{3}$"),
    "action": re.compile(r"^ACT-\d{8}-\d{3}$"),
    "job": re.compile(r"^JOB-\d{14}-\d{3}$"),
    # v0.3 entities (RCP-v03-003, WP-102 registered schemas; this whitelist is
    # the validation counterpart of registry.SCHEMAS — both must stay in sync).
    "sector": re.compile(r"^SEG-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    "security": re.compile(r"^INS-[A-Z]{2,6}-[A-Z0-9][A-Z0-9.\-]*$"),
    "product": re.compile(r"^PRD-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    "technology": re.compile(r"^TEC-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    "metric": re.compile(r"^MET-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    "source_channel": re.compile(r"^CHN-[a-z0-9]+(?:-[a-z0-9]+)*$"),
    "ontology_assertion": re.compile(r"^REL-\d{8}-\d{3}$"),
    "impact_assertion": re.compile(r"^IMP-\d{8}-\d{3}$"),
}

# Ontology assertion predicates (Phase 0-1 §5). Relation direction is explicit;
# symmetric predicates (COMPETES_WITH etc.) are derived as reverse edges in the
# export layer, never duplicated as authoritative objects.
ONTOLOGY_PREDICATES = frozenset(
    {
        "SUPPLIES",
        "CUSTOMER_OF",
        "COMPETES_WITH",
        "SUBSTITUTES",
        "COMPLEMENTS",
        "DEPENDS_ON",
        "ENABLES",
        "CONSTRAINS",
        "OWNS",
        "PARTNERS_WITH",
        "PRODUCES",
        "USES",
    }
)
SYMMETRIC_PREDICATES = frozenset(
    {"COMPETES_WITH", "SUBSTITUTES", "COMPLEMENTS", "PARTNERS_WITH"}
)
REQUIRED_HEADINGS = {
    "event": {
        "Facts",
        "Inferences",
        "Research judgment",
        "Thesis impact",
        "Alternative explanations",
        "Unknowns",
        "Follow-up indicators",
    },
    "thesis": {
        "Core judgment",
        "Reasoning chain",
        "Supporting evidence",
        "Contradicting evidence",
        "Alternative explanations",
        "Falsification conditions",
        "Unknowns",
        "Review history",
    },
    "company": {
        "Company role in the value chain",
        "Business model",
        "Competitive advantages",
        "Risks",
        "Related Thesis",
    },
    "report": {
        "One-sentence conclusion",
        "Research question and scope",
        "Thesis assessment",
        "Contrarian view",
        "Falsification conditions",
        "Key indicators",
        "Investment implications",
    },
    "project": {
        "Research question",
        "Scope",
        "Success criteria",
        "Active Thesis",
        "Open actions",
    },
    "review": {"Decision", "Notes"},
    "action": {"Action", "Success evidence", "History"},
    "job": {"Job", "Result"},
}


def is_iso_date(value: Any, *, allow_unknown: bool = False) -> bool:
    if allow_unknown and value == "unknown":
        return True
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def headings(body: str) -> set[str]:
    return set(re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))


def checklist_item_checked(body: str, label: str) -> bool:
    return bool(
        re.search(
            rf"(?mi)^-\s+\[[xX]\]\s+{re.escape(label)}\s*$",
            body,
        )
    )


def source_processing_state(obj: Any) -> str:
    labels = (
        "Event extraction completed",
        "Entity links reviewed",
        "Thesis links reviewed",
    )
    completed = sum(checklist_item_checked(obj.body, label) for label in labels)
    if completed == len(labels):
        return "complete"
    if completed:
        return f"partial ({completed}/{len(labels)})"
    return "registered"
