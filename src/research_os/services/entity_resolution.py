"""B-015 Entity resolution for candidates.

Maps candidate title/publisher text to Universe entities via alias matching.
Output is a proposal only: classification is ``matched`` (one entity),
``ambiguous`` (multiple), or ``unknown`` (none). Proposals never change
reviewed facts; a human triages them (Phase 2 §5.3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_NON_TEXT_RE = re.compile(r"[^\w一-鿿\s]+", re.UNICODE)
_TICKER_RE = re.compile(r"\b[A-Z]{2,6}\b")


@dataclass(frozen=True)
class EntityIndex:
    """Normalized-name -> entity id lookup built from the Universe."""

    by_name: dict[str, str]

    @classmethod
    def from_objects(cls, companies: list[Any]) -> EntityIndex:
        by_name: dict[str, str] = {}
        for company in companies:
            entity_id = company.object_id
            names = _names_for(company.metadata)
            for name in names:
                normalized = _normalize(name)
                if not normalized:
                    continue
                by_name.setdefault(normalized, entity_id)
        return cls(by_name=by_name)


def _names_for(meta: dict[str, Any]) -> list[str]:
    names: list[str] = []
    title = meta.get("title")
    if title:
        names.append(str(title))
        # "X (中文名)" -> also index the Chinese name alone
        cn = re.search(r"\(([一-鿿]+)\)", str(title))
        if cn:
            names.append(cn.group(1))
    for alias in meta.get("aliases", []) or []:
        names.append(str(alias))
    return names


def _normalize(text: str) -> str:
    lowered = text.lower()
    # split Chinese names out of "X (中文)" titles
    lowered = re.sub(r"\(([一-鿿]+)\)", r" \1 ", lowered)
    return _NON_TEXT_RE.sub(" ", lowered).strip()


def _contains_name(haystack: str, name: str) -> bool:
    """Match CJK names by substring and Latin names by complete token phrase."""
    if re.search(r"[一-鿿]", name):
        return name in haystack
    phrase = r"\s+".join(re.escape(token) for token in name.split())
    return bool(re.search(rf"(?<!\w){phrase}(?!\w)", haystack))


def resolve(
    index: EntityIndex,
    *,
    title: str,
    publisher: str = "",
) -> dict[str, Any]:
    """Resolve candidate text to an entity proposal.

    Returns {status, entity_id?, matched_names}. Ambiguity: if multiple
    distinct entities match, status is ``ambiguous`` and entity_id is None.
    """
    haystack = f"{title} {publisher}"
    haystack_norm = _normalize(haystack)
    matched: dict[str, str] = {}
    for name, entity_id in index.by_name.items():
        if name and _contains_name(haystack_norm, name):
            matched[name] = entity_id

    unique_entities = set(matched.values())
    if not unique_entities:
        return {"status": "unknown", "entity_id": None, "matched_names": []}
    if len(unique_entities) > 1:
        return {
            "status": "ambiguous",
            "entity_id": None,
            "matched_names": sorted(matched),
        }
    return {
        "status": "matched",
        "entity_id": next(iter(unique_entities)),
        "matched_names": sorted(matched),
    }


def render_proposal(proposal: dict[str, Any]) -> str:
    return json.dumps(proposal, ensure_ascii=False, sort_keys=True)


def proposal_to_json(proposal: dict[str, Any]) -> str:
    return json.dumps(proposal, ensure_ascii=False, sort_keys=True)
