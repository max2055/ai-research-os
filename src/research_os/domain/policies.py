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
    "analysis_mode": re.compile(r"^MOD-ANL-[a-z0-9]+(?:-[a-z0-9]+)*-v\d+$"),
    "analysis_run": re.compile(r"^ANL-\d{8}-\d{3}$"),
    "forecast": re.compile(r"^FCT-\d{8}-\d{3}$"),
    "forecast_resolution": re.compile(r"^RES-\d{8}-\d{3}$"),
    "valuation_snapshot": re.compile(r"^VAL-\d{8}-\d{3}$"),
    "recommendation": re.compile(r"^REC-\d{8}-\d{3}$"),
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

# Impact rule map projection (C-003). Machine-readable view of the approved
# policy in IMPACT_RULE_MAP.md: for each predicate, the primary impact_type
# that C-004 direct-impact proposals default to, and that type's default
# direction tendency. The rule map document is authoritative; these constants
# are its projection and must not drift without updating the doc. Unknown
# predicate/impact_type combinations never generate Impact (allowlist).
PRIMARY_IMPACT_TYPE = {
    "SUPPLIES": "supply",
    "CUSTOMER_OF": "demand",
    "COMPETES_WITH": "competition",
    "SUBSTITUTES": "competition",
    "COMPLEMENTS": "demand",
    "DEPENDS_ON": "supply",
    "ENABLES": "technology",
    "CONSTRAINS": "capacity",
    "OWNS": "capex",
    "PARTNERS_WITH": "technology",
    "PRODUCES": "capacity",
    "USES": "cost",
}
DEFAULT_IMPACT_DIRECTION = {
    "SUPPLIES": "mixed",
    "CUSTOMER_OF": "positive",
    "COMPETES_WITH": "mixed",
    "SUBSTITUTES": "mixed",
    "COMPLEMENTS": "positive",
    "DEPENDS_ON": "mixed",
    "ENABLES": "positive",
    "CONSTRAINS": "negative",
    "OWNS": "uncertain",
    "PARTNERS_WITH": "positive",
    "PRODUCES": "positive",
    "USES": "mixed",
}

# Full predicate -> impact_type allowlist (C-003, machine projection of
# IMPACT_RULE_MAP.md). value = (default_direction, conditional). Conditional
# entries require an explicit mechanism/human confirmation and are NOT emitted
# automatically by C-004 (e.g. OWNS->capex, CONSTRAINS->regulation). The rule
# map document is authoritative; these constants must not drift without updating
# it. Unknown predicate/impact_type combinations never generate Impact.
IMPACT_RULE_MAP: dict[str, dict[str, tuple[str, bool]]] = {
    "SUPPLIES": {
        "supply": ("mixed", False),
        "capacity": ("positive", False),
        "cost": ("mixed", False),
        "price": ("mixed", False),
        "margin": ("mixed", False),
        "capex": ("uncertain", True),
    },
    "CUSTOMER_OF": {
        "demand": ("positive", False),
        "revenue": ("positive", False),
        "margin": ("mixed", False),
        "capex": ("uncertain", True),
    },
    "COMPETES_WITH": {
        "competition": ("mixed", False),
        "price": ("negative", False),
        "margin": ("negative", False),
        "revenue": ("negative", False),
    },
    "SUBSTITUTES": {
        "competition": ("mixed", False),
        "demand": ("negative", False),
        "revenue": ("negative", False),
        "price": ("negative", False),
    },
    "COMPLEMENTS": {
        "demand": ("positive", False),
        "revenue": ("positive", False),
        "technology": ("positive", False),
    },
    "DEPENDS_ON": {
        "supply": ("mixed", False),
        "cost": ("negative", False),
        "technology": ("uncertain", True),
    },
    "ENABLES": {
        "technology": ("positive", False),
        "capacity": ("positive", False),
        "demand": ("positive", False),
        "revenue": ("uncertain", True),
    },
    "CONSTRAINS": {
        "capacity": ("negative", False),
        "supply": ("negative", False),
        "technology": ("negative", False),
        "regulation": ("uncertain", True),
        "price": ("uncertain", True),
    },
    "OWNS": {
        "capex": ("uncertain", True),
        "technology": ("uncertain", True),
        "revenue": ("uncertain", True),
        "valuation": ("uncertain", True),
    },
    "PARTNERS_WITH": {
        "technology": ("positive", False),
        "supply": ("positive", False),
        "demand": ("positive", False),
        "revenue": ("uncertain", True),
    },
    "PRODUCES": {
        "capacity": ("positive", False),
        "supply": ("positive", False),
        "technology": ("positive", False),
        "price": ("mixed", False),
        "revenue": ("positive", False),
        "margin": ("uncertain", True),
    },
    "USES": {
        "cost": ("mixed", False),
        "technology": ("positive", False),
        "demand": ("uncertain", True),
        "capacity": ("uncertain", True),
    },
}
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
