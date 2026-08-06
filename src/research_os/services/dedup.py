"""B-014 Candidate dedup.

Exact (canonical URL / content fingerprint) and near-duplicate (normalized
title) clustering. Clustering never drops records: every candidate is kept,
a ``duplicate_cluster_id`` marks group membership. Near-dup is only a
cluster, not an auto-dismiss (Phase 2 §5.2: "近似重复只形成 cluster，不自动
删除候选").
"""

from __future__ import annotations

import re
import uuid

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_TRAILING_VARIANT_RE = re.compile(r"-\d{1,2}$")


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, and drop trailing -NN variant suffixes."""
    lowered = title.lower()
    lowered = _TRAILING_VARIANT_RE.sub("", lowered)
    return _NORMALIZE_RE.sub(" ", lowered).strip()


def assign_clusters(
    candidates: list[dict[str, object]],
    *,
    existing: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    """Assign duplicate_cluster_id to each candidate.

    ``existing`` maps a normalized title (or canonical URL) to an existing
    cluster id, so a new run can extend an earlier cluster instead of opening
    a fresh one. Every candidate is returned unchanged except for the added
    ``duplicate_cluster_id`` key.
    """
    clusters: dict[str, str] = dict(existing or {})
    by_url: dict[str, str] = {}
    by_fingerprint: dict[str, str] = {}
    result: list[dict[str, object]] = []
    for candidate in candidates:
        cluster_id: str | None = None
        url = str(candidate.get("canonical_url") or "")
        fingerprint = str(candidate.get("content_fingerprint") or "")
        title = normalize_title(str(candidate.get("title") or ""))

        # exact by canonical URL
        if url and url in by_url:
            cluster_id = by_url[url]
        elif url and url in clusters:
            cluster_id = clusters[url]
        # exact by content fingerprint
        elif fingerprint and fingerprint in by_fingerprint:
            cluster_id = by_fingerprint[fingerprint]
        elif fingerprint and fingerprint in clusters:
            cluster_id = clusters[fingerprint]
        # near by normalized title
        elif title and title in clusters:
            cluster_id = clusters[title]

        if cluster_id is None:
            cluster_id = f"CLU-{uuid.uuid4().hex[:16]}"

        if url:
            clusters[url] = cluster_id
            by_url[url] = cluster_id
        if fingerprint:
            clusters[fingerprint] = cluster_id
            by_fingerprint[fingerprint] = cluster_id
        if title:
            clusters[title] = cluster_id

        result.append({**candidate, "duplicate_cluster_id": cluster_id})
    return result
