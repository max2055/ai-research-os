"""Immutable Candidate DB snapshots with integrity and hash manifests."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_os.services.candidate_db import candidate_db_path

_AUTHORITATIVE_TOP_LEVEL = {
    "01_Inbox",
    "02_Knowledge",
    "03_Theses",
    "04_Evidence",
    "05_Research",
    "06_Reports",
    "07_Templates",
    "08_Indexes",
}


def _parse_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_path(snapshot: Path) -> Path:
    return snapshot.with_suffix(snapshot.suffix + ".manifest.json")


def _validate_destination(root: Path, destination: Path) -> Path:
    root = root.resolve()
    destination = destination.expanduser().resolve()
    try:
        relative = destination.relative_to(root)
    except ValueError:
        return destination
    if relative.parts and relative.parts[0] in _AUTHORITATIVE_TOP_LEVEL:
        raise ValueError("backup destination cannot be an authoritative directory")
    return destination


def _source_metadata(connection: sqlite3.Connection) -> tuple[int, str | None]:
    version_row = connection.execute("PRAGMA user_version").fetchone()
    version = int(version_row[0]) if version_row else 0
    timestamps = []
    for table, column in (
        ("candidates", "created_at"),
        ("candidate_actions", "acted_at"),
        ("discovery_runs", "started_at"),
    ):
        try:
            row = connection.execute(f"SELECT MAX({column}) FROM {table}").fetchone()
        except sqlite3.DatabaseError:
            continue
        if row and row[0]:
            timestamps.append(str(row[0]))
    return version, max(timestamps, default=None)


def create_candidate_snapshot(
    root: Path,
    destination: Path,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Create one immutable SQLite snapshot and sibling JSON manifest."""
    root = root.resolve()
    source = candidate_db_path(root)
    if not source.is_file():
        raise FileNotFoundError(f"Candidate DB not found: {source}")
    destination = _validate_destination(root, destination)
    manifest_path = _manifest_path(destination)
    if destination.exists() or manifest_path.exists():
        raise FileExistsError(f"backup already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    created_at = _parse_time(now).astimezone(UTC)

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temp_path = Path(temp_name)
    source_connection: sqlite3.Connection | None = None
    target_connection: sqlite3.Connection | None = None
    try:
        source_uri = f"file:{source.resolve().as_posix()}?mode=ro"
        source_connection = sqlite3.connect(source_uri, uri=True)
        version, source_max_updated_at = _source_metadata(source_connection)
        target_connection = sqlite3.connect(temp_path)
        source_connection.backup(target_connection)
        target_connection.commit()
        integrity_row = target_connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity_row or integrity_row[0] != "ok":
            raise ValueError("Candidate snapshot failed SQLite integrity_check")
        target_connection.close()
        target_connection = None

        with temp_path.open("rb") as stream:
            os.fsync(stream.fileno())
        sha256 = _sha256(temp_path)
        size_bytes = temp_path.stat().st_size
        temp_path.replace(destination)

        manifest = {
            "format_version": 1,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "snapshot_file": destination.name,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "schema_version": version,
            "sqlite_integrity": "ok",
            "source_max_updated_at": source_max_updated_at,
        }
        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        manifest_descriptor, manifest_temp_name = tempfile.mkstemp(
            prefix=f".{manifest_path.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        try:
            with os.fdopen(manifest_descriptor, "w", encoding="utf-8") as stream:
                stream.write(manifest_text)
                stream.flush()
                os.fsync(stream.fileno())
            Path(manifest_temp_name).replace(manifest_path)
        finally:
            manifest_temp = Path(manifest_temp_name)
            if manifest_temp.exists():
                manifest_temp.unlink()
        return manifest
    finally:
        if target_connection is not None:
            target_connection.close()
        if source_connection is not None:
            source_connection.close()
        if temp_path.exists():
            temp_path.unlink()


def verify_candidate_snapshot(snapshot: Path, manifest: Path) -> dict[str, Any]:
    """Verify file presence, manifest hash, size and SQLite integrity."""
    if not snapshot.is_file() or not manifest.is_file():
        return {"status": "missing"}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid_manifest"}
    if _sha256(snapshot) != data.get("sha256"):
        return {"status": "hash_mismatch"}
    if snapshot.stat().st_size != data.get("size_bytes"):
        return {"status": "size_mismatch"}
    connection: sqlite3.Connection | None = None
    try:
        uri = f"file:{snapshot.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        row = connection.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            return {"status": "integrity_failed"}
        version_row = connection.execute("PRAGMA user_version").fetchone()
        version = int(version_row[0]) if version_row else 0
        if version != data.get("schema_version"):
            return {"status": "schema_mismatch"}
        return {
            "status": "ok",
            "sha256": data["sha256"],
            "schema_version": version,
        }
    except sqlite3.DatabaseError:
        return {"status": "integrity_failed"}
    finally:
        if connection is not None:
            connection.close()


def backup_age_status(
    manifest: Path,
    *,
    now: str | None = None,
    max_age_hours: int = 24,
) -> dict[str, Any]:
    """Classify a manifest against the operational RPO threshold."""
    if max_age_hours < 1:
        raise ValueError("max_age_hours must be positive")
    if not manifest.is_file():
        return {"status": "missing", "age_hours": None}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        created_at = _parse_time(str(data["created_at"]))
    except (KeyError, OSError, ValueError, json.JSONDecodeError):
        return {"status": "invalid", "age_hours": None}
    current = _parse_time(now)
    age_hours = (
        current.astimezone(UTC) - created_at.astimezone(UTC)
    ).total_seconds() / 3600
    return {
        "status": "fresh" if age_hours <= max_age_hours else "stale",
        "age_hours": round(age_hours, 2),
        "max_age_hours": max_age_hours,
    }
