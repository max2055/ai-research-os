"""Derived ontology views, exports and relationship analysis."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from research_os.domain.models import ResearchObject
from research_os.domain.policies import SYMMETRIC_PREDICATES
from research_os.services.validation import count_by_type, validate_repository

ONTOLOGY_SCHEMA_VERSION = 1


def thesis_relationships(event: ResearchObject) -> dict[str, str]:
    result: dict[str, str] = {}
    mapping = {
        "supporting": "SUPPORTS",
        "contradicting": "CONTRADICTS",
        "contextual": "CONTEXTUALIZES",
    }
    for line in event.body.splitlines():
        match = re.match(
            r"^\|\s*(THS-\d{3})\s*\|\s*"
            r"(supporting|contradicting|contextual)\s*\|",
            line,
        )
        if match:
            result[match.group(1)] = mapping[match.group(2)]
    for thesis_id in event.metadata.get("thesis_links", []):
        result.setdefault(str(thesis_id), "RELATES_TO")
    return result


def ontology_graph(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = root.resolve()
    objects, findings = validate_repository(root)
    errors = [finding for finding in findings if finding.level == "error"]
    if errors:
        raise ValueError("repository validation must pass before ontology export")
    by_id = {obj.object_id: obj for obj in objects}
    nodes = [
        {
            "record_type": "node",
            "id": obj.object_id,
            "node_type": obj.object_type,
            "title": obj.metadata.get("title"),
            "review_status": obj.metadata.get("review_status"),
            "path": str(obj.path.relative_to(root)),
            "metadata": obj.metadata,
        }
        for obj in sorted(objects, key=lambda item: item.object_id)
    ]
    edge_keys: set[tuple[str, str, str]] = set()

    def edge(source: str, relation: str, target: str) -> None:
        if source not in by_id:
            raise ValueError(f"ontology edge source does not exist: {source}")
        if target not in by_id:
            raise ValueError(f"ontology edge target does not exist: {target}")
        edge_keys.add((source, relation, target))

    for obj in objects:
        meta = obj.metadata
        if obj.object_type != "project":
            for project_id in meta.get("project_ids", []):
                edge(obj.object_id, "BELONGS_TO", str(project_id))
        if obj.object_type == "event":
            for source_id in meta.get("source_ids", []):
                edge(str(source_id), "SUPPORTS_EVENT", obj.object_id)
            for company_id in meta.get("companies", []):
                edge(obj.object_id, "AFFECTS", str(company_id))
            for thesis_id, relation in thesis_relationships(obj).items():
                edge(obj.object_id, relation, thesis_id)
        elif obj.object_type == "thesis":
            for company_id in meta.get("companies", []):
                edge(obj.object_id, "CONCERNS", str(company_id))
        elif obj.object_type == "company":
            for company_id in meta.get("related_entities", []):
                edge(obj.object_id, "RELATED_TO", str(company_id))
            for source_id in meta.get("source_ids", []):
                edge(obj.object_id, "USES_SOURCE", str(source_id))
            for event_id in meta.get("evidence_ids", []):
                edge(obj.object_id, "EVIDENCED_BY", str(event_id))
        elif obj.object_type == "report":
            for event_id in meta.get("evidence_ids", []):
                edge(obj.object_id, "CITES", str(event_id))
            for thesis_id in meta.get("thesis_ids", []):
                edge(obj.object_id, "SYNTHESIZES", str(thesis_id))
        elif obj.object_type == "project":
            current_report_id = meta.get("current_report_id")
            if current_report_id:
                edge(obj.object_id, "CURRENT_REPORT", str(current_report_id))
        elif obj.object_type == "review":
            for target_id in meta.get("target_ids", []):
                edge(obj.object_id, "REVIEWS", str(target_id))
        elif obj.object_type == "action":
            source_review_id = meta.get("source_review_id")
            if source_review_id:
                edge(obj.object_id, "ORIGINATES_FROM", str(source_review_id))
        elif obj.object_type == "ontology_assertion":
            # Ontology assertion: subject -predicate-> object. The reverse
            # edge for symmetric predicates is derived below (export layer),
            # never duplicated as an authoritative object (Phase 0-1 §5).
            edge(obj.object_id, "ASSERTS", str(meta["subject_id"]))
            edge(obj.object_id, "ASSERTS", str(meta["object_id"]))
            relation = str(meta["predicate"])
            edge(str(meta["subject_id"]), relation, str(meta["object_id"]))
            if relation in SYMMETRIC_PREDICATES:
                edge(str(meta["object_id"]), relation, str(meta["subject_id"]))

    edges = [
        {
            "record_type": "edge",
            "source": source,
            "relation": relation,
            "target": target,
            "properties": {},
        }
        for source, relation, target in sorted(edge_keys)
    ]
    return nodes, edges


def ontology_jsonl(root: Path) -> str:
    nodes, edges = ontology_graph(root)
    header = {
        "record_type": "manifest",
        "schema_version": ONTOLOGY_SCHEMA_VERSION,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
    records = [header, *nodes, *edges]
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )


def write_text_export(output: Path, content: str) -> Path:
    """Atomically create an explicitly selected derived-output file."""
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise FileExistsError(
                f"refusing to overwrite existing file: {output}"
            ) from exc
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def write_sqlite_export(root: Path, output: Path) -> Path:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {output}")
    nodes, edges = ontology_graph(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    title TEXT,
                    review_status TEXT,
                    path TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE edges (
                    source_id TEXT NOT NULL REFERENCES nodes(id),
                    relation TEXT NOT NULL,
                    target_id TEXT NOT NULL REFERENCES nodes(id),
                    properties_json TEXT NOT NULL,
                    PRIMARY KEY (source_id, relation, target_id)
                );
                CREATE INDEX edges_target_idx ON edges(target_id, relation);
                CREATE INDEX nodes_type_idx ON nodes(node_type, review_status);
                """
            )
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                (
                    ("schema_version", str(ONTOLOGY_SCHEMA_VERSION)),
                    ("source_of_truth", "Markdown"),
                ),
            )
            connection.executemany(
                """
                INSERT INTO nodes(
                    id, node_type, title, review_status, path, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        node["id"],
                        node["node_type"],
                        node["title"],
                        node["review_status"],
                        node["path"],
                        json.dumps(
                            node["metadata"],
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    )
                    for node in nodes
                ),
            )
            connection.executemany(
                """
                INSERT INTO edges(
                    source_id, relation, target_id, properties_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    (
                        edge["source"],
                        edge["relation"],
                        edge["target"],
                        json.dumps(edge["properties"], sort_keys=True),
                    )
                    for edge in edges
                ),
            )
            connection.commit()
            foreign_key_errors = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if foreign_key_errors:
                raise ValueError(f"SQLite foreign key errors: {foreign_key_errors}")
        finally:
            connection.close()
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise FileExistsError(
                f"refusing to overwrite existing file: {output}"
            ) from exc
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def render_impact(root: Path, object_id: str, depth: int = 1) -> str:
    if depth < 1 or depth > 4:
        raise ValueError("depth must be between 1 and 4")
    nodes, edges = ontology_graph(root)
    by_id = {node["id"]: node for node in nodes}
    if object_id not in by_id:
        raise ValueError(f"unknown object id {object_id}")
    adjacency: dict[str, list[tuple[str, str, str]]] = {}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        relation = edge["relation"]
        adjacency.setdefault(source, []).append(("out", relation, target))
        adjacency.setdefault(target, []).append(("in", relation, source))

    visited = {object_id}
    frontier = {object_id}
    rows: list[tuple[int, str, str, str, str]] = []
    for level in range(1, depth + 1):
        next_frontier: set[str] = set()
        for current in sorted(frontier):
            for direction, relation, neighbor in sorted(adjacency.get(current, [])):
                rows.append((level, current, direction, relation, neighbor))
                if neighbor not in visited:
                    next_frontier.add(neighbor)
                    visited.add(neighbor)
        frontier = next_frontier
        if not frontier:
            break

    node = by_id[object_id]
    lines = [
        f"# Impact view: {object_id}",
        "",
        f"- Type: {node['node_type']}",
        f"- Title: {node['title']}",
        f"- Depth: {depth}",
        "",
        "| Hop | Current | Direction | Relation | Neighbor | Neighbor type |",
        "|---:|---|---|---|---|---|",
    ]
    for level, current, direction, relation, neighbor in rows:
        lines.append(
            f"| {level} | {current} | {direction} | {relation} | "
            f"{neighbor} | {by_id[neighbor]['node_type']} |"
        )
    if not rows:
        lines.append("| — | — | — | — | No relationships | — |")
    return "\n".join(lines) + "\n"


def render_scale_assessment(root: Path) -> str:
    objects, findings = validate_repository(root)
    counts = count_by_type(objects)
    event_count = counts.get("event", 0)
    source_count = counts.get("source", 0)
    sqlite_triggers = {
        "events_at_least_500": event_count >= 500,
        "sources_at_least_1000": source_count >= 1000,
    }
    automatic_triggered = any(sqlite_triggers.values())
    mode = "Evaluate SQLite derived index" if automatic_triggered else "File-first"
    errors = sum(finding.level == "error" for finding in findings)
    lines = [
        "# Scale assessment",
        "",
        f"- Recommended mode: **{mode}**",
        f"- Core objects: {len(objects)}",
        f"- Sources: {source_count}/1000 trigger",
        f"- Events: {event_count}/500 trigger",
        f"- Validation errors: {errors}",
        "",
        "## Automatic trigger status",
        "",
    ]
    for name, triggered in sqlite_triggers.items():
        lines.append(f"- {name}: {'triggered' if triggered else 'not triggered'}")
    lines += [
        "",
        "Manual triggers such as multiple active researchers, ten or more active "
        "topics, frequent multi-field aggregation or repeated three-hop impact "
        "queries must be assessed in the monthly review.",
        "",
        "SQLite and graph outputs remain disposable derived views; Markdown is "
        "the current source of truth.",
    ]
    return "\n".join(lines) + "\n"
