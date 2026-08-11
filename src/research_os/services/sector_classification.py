"""B-016 Sector classification for candidates.

Multi-label keyword classification of candidate text against Sector
in_scope/definition terms. Returns the matched Sectors with a reason per
hit. A proposal only — never changes reviewed facts (Phase 2 §5.3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_NON_TEXT_RE = re.compile(r"[^\w一-鿿\s]+", re.UNICODE)


def _normalize(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"\(([一-鿿]+)\)", r" \1 ", lowered)
    return _NON_TEXT_RE.sub(" ", lowered).strip()


@dataclass(frozen=True)
class SectorIndex:
    """Keyword -> sector id lookup built from the Universe."""

    by_keyword: dict[str, str]

    @classmethod
    def from_objects(cls, sectors: list[Any]) -> SectorIndex:
        by_keyword: dict[str, str] = {}
        for sector in sectors:
            sector_id = sector.object_id
            meta = sector.metadata
            keywords: list[str] = []
            title = meta.get("title")
            if title:
                keywords.append(str(title))
            keywords += list(meta.get("in_scope", []) or [])
            definition = meta.get("definition")
            if definition:
                keywords += [
                    part.strip() for part in str(definition).split(",") if part.strip()
                ]
            for keyword in keywords:
                normalized = _normalize(keyword)
                if not normalized:
                    continue
                by_keyword[normalized] = sector_id
                spaced = normalized.replace("-", " ")
                if spaced != normalized:
                    by_keyword[spaced] = sector_id
                # "enterprise storage" -> also index each significant token
                for token in normalized.split():
                    if len(token) >= 3:
                        by_keyword.setdefault(token, sector_id)
        return cls(by_keyword=by_keyword)


def classify(
    index: SectorIndex,
    *,
    title: str,
    publisher: str = "",
) -> dict[str, Any]:
    """Classify candidate text to Sectors (multi-label).

    Returns {sector_ids: [...], reasons: {sector_id: [keywords]}}.
    Empty sector_ids means no keyword matched (unknown).
    """
    haystack = _normalize(f"{title} {publisher}")
    matched: dict[str, list[str]] = {}
    for keyword, sector_id in index.by_keyword.items():
        if keyword and keyword in haystack:
            matched.setdefault(sector_id, []).append(keyword)
    return {
        "sector_ids": sorted(matched),
        "reasons": {
            sector_id: sorted(keywords) for sector_id, keywords in matched.items()
        },
    }
