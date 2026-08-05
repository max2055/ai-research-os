"""Dry-run, apply and rollback framework for Markdown schema migrations."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from research_os.repositories.markdown import MarkdownDocument, load_documents
from research_os.repositories.transaction import FileTransaction, TransactionError


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Migration(Protocol):
    migration_id: str

    def render(self, document: MarkdownDocument) -> str: ...


@dataclass(frozen=True)
class MigrationChange:
    path: str
    before_sha256: str
    after_sha256: str
    before_text: str
    after_text: str


@dataclass(frozen=True)
class MigrationPlan:
    migration_id: str
    changes: tuple[MigrationChange, ...]

    def summary(self) -> dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "change_count": len(self.changes),
            "changes": [
                {
                    "path": change.path,
                    "before_sha256": change.before_sha256,
                    "after_sha256": change.after_sha256,
                }
                for change in self.changes
            ],
        }


@dataclass(frozen=True)
class AddFieldMigration:
    migration_id: str
    field_name: str
    value: Any
    object_types: frozenset[str] | None = None

    def render(self, document: MarkdownDocument) -> str:
        object_type = document.metadata.get("type")
        if self.object_types is not None and object_type not in self.object_types:
            return document.original_text
        if document.metadata.get(self.field_name) == self.value:
            return document.original_text
        editable = MarkdownDocument(
            path=document.path,
            metadata=deepcopy(document.metadata),
            body=document.body,
            original_text=document.original_text,
        )
        editable.set_metadata(self.field_name, deepcopy(self.value))
        return editable.render()


@dataclass(frozen=True)
class SourceProvenanceMigration:
    migration_id: str = "MIG-20260729-003-source-provenance"

    def render(self, document: MarkdownDocument) -> str:
        if document.metadata.get("type") != "source":
            return document.original_text
        url = document.metadata.get("url")
        values: dict[str, Any] = {
            "canonical_url": (
                str(url)
                if isinstance(url, str) and url.startswith(("http://", "https://"))
                else None
            ),
            "asset_paths": [],
            "content_sha256": None,
            "fetched_at": None,
            "upstream_source_ids": [],
            "processing_status": "registered",
            "processing_error": None,
            "published_date_proposal": None,
        }
        if all(
            key in document.metadata and document.metadata.get(key) == value
            for key, value in values.items()
        ):
            return document.original_text
        editable = MarkdownDocument(
            path=document.path,
            metadata=deepcopy(document.metadata),
            body=document.body,
            original_text=document.original_text,
        )
        for key, value in values.items():
            if key not in editable.metadata:
                editable.set_metadata(key, deepcopy(value))
        return editable.render()


@dataclass(frozen=True)
class RegisterV03SchemasMigration:
    """MIG-v0.3-001: register v0.3 entity schemas (RCP-v03-003).

    Registering Sector/Security/Product/Technology/Metric schemas is a
    code-level change only (schemas/registry.py); no Markdown object is
    touched. The migration is a documented no-op so the migration log records
    "no object changed" explicitly, preserving traceability. Rollback = revert
    the schema-registration commit; no data to restore.
    """

    migration_id: str = "MIG-v0.3-001-register-v0.3-schemas"

    def render(self, document: MarkdownDocument) -> str:
        return document.original_text


class MigrationEngine:
    def __init__(
        self,
        root: Path,
        backup_root: Path = Path("09_Automation/migrations/backups"),
    ) -> None:
        self.root = root.resolve()
        self.backup_root = backup_root

    def plan(self, migration: Migration) -> MigrationPlan:
        changes: list[MigrationChange] = []
        for document in load_documents(self.root):
            after = migration.render(document)
            if after == document.original_text:
                continue
            changes.append(
                MigrationChange(
                    path=str(document.path.relative_to(self.root)),
                    before_sha256=sha256_text(document.original_text),
                    after_sha256=sha256_text(after),
                    before_text=document.original_text,
                    after_text=after,
                )
            )
        return MigrationPlan(migration.migration_id, tuple(changes))

    def apply(self, plan: MigrationPlan) -> list[Path]:
        migration_root = self.backup_root / plan.migration_id
        manifest_path = migration_root / "manifest.json"
        if (self.root / manifest_path).exists():
            raise TransactionError(f"migration backup already exists: {manifest_path}")
        transaction = FileTransaction(self.root)
        manifest_changes: list[dict[str, str]] = []
        for change in plan.changes:
            target = self.root / change.path
            current = target.read_text(encoding="utf-8")
            if sha256_text(current) != change.before_sha256:
                raise TransactionError(f"migration precondition changed: {change.path}")
            backup = migration_root / "files" / change.path
            transaction.stage_create(backup, change.before_text)
            transaction.stage_replace(Path(change.path), change.after_text)
            manifest_changes.append(
                {
                    "path": change.path,
                    "backup": str(backup),
                    "before_sha256": change.before_sha256,
                    "after_sha256": change.after_sha256,
                }
            )
        manifest = {
            "migration_id": plan.migration_id,
            "changes": manifest_changes,
        }
        transaction.stage_create(
            manifest_path,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        return transaction.commit()

    def rollback(self, migration_id: str) -> list[Path]:
        manifest_path = self.backup_root / migration_id / "manifest.json"
        absolute_manifest = self.root / manifest_path
        if not absolute_manifest.is_file():
            raise TransactionError(
                f"migration manifest does not exist: {manifest_path}"
            )
        manifest = json.loads(absolute_manifest.read_text(encoding="utf-8"))
        transaction = FileTransaction(self.root)
        for record in manifest["changes"]:
            target = self.root / record["path"]
            current = target.read_text(encoding="utf-8")
            if sha256_text(current) != record["after_sha256"]:
                raise TransactionError(
                    f"rollback precondition changed: {record['path']}"
                )
            backup = self.root / record["backup"]
            original = backup.read_text(encoding="utf-8")
            if sha256_text(original) != record["before_sha256"]:
                raise TransactionError(
                    f"migration backup hash mismatch: {record['backup']}"
                )
            transaction.stage_replace(Path(record["path"]), original)
        return transaction.commit()


def render_plan(plan: MigrationPlan) -> str:
    return json.dumps(plan.summary(), ensure_ascii=False, indent=2) + "\n"
