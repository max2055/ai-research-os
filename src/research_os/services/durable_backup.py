"""Age-encrypted durable backup and verified disposable restore."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Protocol, cast

from research_os.services.backup import (
    create_candidate_snapshot,
    verify_candidate_snapshot,
)
from research_os.services.candidate_db import candidate_db_health, candidate_db_path
from research_os.services.operations_db import operations_db_path

BackupSet = Literal["candidate", "source_assets"]

DURABLE_BACKUP_RELATIVE_DIR = Path("09_Automation/operational/backups/durable")
LATEST_SUCCESS_NAME = "latest-success.json"
INNER_MANIFEST_NAME = "inner-manifest.json"
CANDIDATE_ARCHIVE_PATH = "09_Automation/operational/candidates.db"
CANDIDATE_MANIFEST_ARCHIVE_PATH = (
    "09_Automation/operational/candidates.db.manifest.json"
)
OPERATIONS_ARCHIVE_PATH = "operations/operations.db"
OPERATIONS_MANIFEST_ARCHIVE_PATH = "operations/operations.db.manifest.json"
_BACKUP_SETS: tuple[BackupSet, ...] = ("candidate", "source_assets")
_AUTHORITATIVE_TOP_LEVEL = frozenset(
    {
        "01_Inbox",
        "02_Knowledge",
        "03_Theses",
        "04_Evidence",
        "05_Research",
        "06_Reports",
        "07_Templates",
        "08_Indexes",
    }
)
_BACKUP_ID_PATTERN = re.compile(r"BKP-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}")
_SOURCE_ID_PATTERN = re.compile(r"SRC-[0-9]{8}-[0-9]{3}")
_GITHUB_REPOSITORY_PATTERN = re.compile(
    r"(?:github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"
)
_OUTER_MANIFEST_KEYS = frozenset(
    {
        "backup_id",
        "backup_set",
        "created_at",
        "ciphertext_name",
        "ciphertext_sha256",
        "ciphertext_size_bytes",
        "remote_asset_id",
    }
)


class DurableBackupError(RuntimeError):
    """Raised when a durable backup transaction cannot be completed safely."""


@dataclass(frozen=True)
class RemoteAsset:
    name: str
    asset_id: str
    size_bytes: int


@dataclass(frozen=True)
class EncryptedAsset:
    backup_set: BackupSet
    name: str
    sha256: str
    size_bytes: int
    remote: RemoteAsset


class BackupBackend(Protocol):
    """Private immutable storage operations used by durable backup."""

    repository: str
    release_tag: str

    def preflight(self, asset_names: tuple[str, ...]) -> None: ...

    def upload(self, path: Path, *, name: str) -> RemoteAsset: ...

    def inspect(self, *, name: str) -> RemoteAsset: ...

    def download(self, *, name: str, destination: Path) -> None: ...


@dataclass(frozen=True)
class DurableBackupRequest:
    root: Path
    recipients: tuple[str, ...]
    backend: BackupBackend
    apply: bool


@dataclass(frozen=True)
class DurableBackupReceipt:
    backup_id: str
    created_at: str
    status: str
    sets: tuple[EncryptedAsset, ...]
    remote_repository: str
    remote_release: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "created_at": self.created_at,
            "status": self.status,
            "sets": [asdict(item) for item in self.sets],
            "remote_repository": self.remote_repository,
            "remote_release": self.remote_release,
        }


@dataclass(frozen=True)
class SourceAssetInventoryEntry:
    source_id: str
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class DurableRestoreResult:
    backup_id: str
    status: str
    destination: Path
    candidate_sha256: str
    candidate_schema_version: int
    source_asset_count: int
    operations_sha256: str = ""
    operations_schema_version: int = 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_utc(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("backup timestamp must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError("backup timestamp must include timezone")
    return parsed.astimezone(UTC)


def _created_at(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_backup_id(value: datetime) -> str:
    random_suffix = os.urandom(6).hex()
    return f"BKP-{value.strftime('%Y%m%dT%H%M%SZ')}-{random_suffix}"


def _validate_backup_id(value: str) -> str:
    if _BACKUP_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("backup_id has invalid format")
    return value


def canonical_github_repository(value: str) -> str:
    """Bind a legacy owner/name identifier to the supported GitHub host."""
    match = _GITHUB_REPOSITORY_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(
            "GitHub repository must be owner/name or github.com/owner/name"
        )
    return f"github.com/{match.group(1)}/{match.group(2)}"


def _asset_names(backup_id: str) -> tuple[str, ...]:
    names: list[str] = []
    for backup_set in _BACKUP_SETS:
        names.extend(
            (
                f"{backup_id}-{backup_set}.tar.age",
                f"{backup_id}-{backup_set}.manifest.json",
            )
        )
    return tuple(names)


def durable_receipt_path(root: Path, backup_id: str) -> Path:
    validated_backup_id = _validate_backup_id(backup_id)
    return root.resolve() / DURABLE_BACKUP_RELATIVE_DIR / f"{validated_backup_id}.json"


def durable_latest_success_path(root: Path) -> Path:
    return root.resolve() / DURABLE_BACKUP_RELATIVE_DIR / LATEST_SUCCESS_NAME


def _validate_safe_relative(value: str, *, label: str) -> PurePosixPath:
    if not value or "\\" in value:
        raise ValueError(f"{label} must be a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{label} must be a safe relative path")
    if path.as_posix() != value:
        raise ValueError(f"{label} must be a normalized relative path")
    return path


def _source_id_for_path(relative: PurePosixPath) -> str:
    parts = relative.parts
    if len(parts) < 4 or parts[:2] != ("01_Inbox", "_assets"):
        raise ValueError("Source asset path is outside the authoritative asset tree")
    source_id = parts[2]
    if _SOURCE_ID_PATTERN.fullmatch(source_id) is None:
        raise ValueError("Source asset path is not owned by a Source ID")
    return source_id


def build_source_asset_inventory(root: Path) -> tuple[SourceAssetInventoryEntry, ...]:
    """Hash regular Source assets while rejecting links and unsafe layout."""
    root = root.resolve()
    asset_root = root / "01_Inbox" / "_assets"
    if asset_root.is_symlink():
        raise ValueError("Source asset root cannot be a symlink")
    if not asset_root.is_dir():
        raise FileNotFoundError("Source asset root is missing")

    entries: list[SourceAssetInventoryEntry] = []
    for directory, dirnames, filenames in os.walk(asset_root, followlinks=False):
        folder = Path(directory)
        for name in [*dirnames, *filenames]:
            child = folder / name
            if child.is_symlink():
                raise ValueError("Source asset inventory cannot contain a symlink")
        for name in filenames:
            if name == ".DS_Store":
                continue
            path = folder / name
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("Source asset inventory accepts regular files only")
            if metadata.st_nlink != 1:
                raise ValueError("Source asset inventory cannot contain hard links")
            try:
                relative_text = path.relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError("Source asset path escapes repository root") from exc
            relative = _validate_safe_relative(relative_text, label="Source asset path")
            source_id = _source_id_for_path(relative)
            entries.append(
                SourceAssetInventoryEntry(
                    source_id=source_id,
                    path=relative.as_posix(),
                    size_bytes=metadata.st_size,
                    sha256=_sha256(path),
                )
            )
    entries.sort(key=lambda item: item.path)
    return tuple(entries)


def _validate_recipients(recipients: tuple[str, ...]) -> tuple[str, ...]:
    if not recipients:
        raise ValueError("at least one age recipient is required")
    cleaned: list[str] = []
    for recipient in recipients:
        if not recipient.strip() or any(
            character in recipient for character in "\r\n\x00"
        ):
            raise ValueError("age recipient is invalid")
        cleaned.append(recipient)
    return tuple(cleaned)


def _recipient_arguments(recipients: tuple[str, ...]) -> list[str]:
    arguments: list[str] = []
    for recipient in recipients:
        arguments.extend(("--recipient", recipient))
    return arguments


def _preflight_age(recipients: tuple[str, ...]) -> None:
    result = subprocess.run(
        ["age", "--encrypt", *_recipient_arguments(recipients)],
        input=b"",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise DurableBackupError("age recipient preflight failed")


def _encrypt_age(source: Path, destination: Path, recipients: tuple[str, ...]) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    result = subprocess.run(
        [
            "age",
            "--encrypt",
            *_recipient_arguments(recipients),
            "--output",
            str(destination),
            str(source),
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not destination.is_file():
        raise DurableBackupError("age encryption failed")
    destination.chmod(0o600)


def _decrypt_age(source: Path, destination: Path, identity: Path) -> None:
    if destination.exists():
        raise FileExistsError(destination)
    result = subprocess.run(
        [
            "age",
            "--decrypt",
            "--identity",
            str(identity),
            "--output",
            str(destination),
            str(source),
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not destination.is_file():
        raise DurableBackupError("age decryption failed")
    destination.chmod(0o600)


def _temporary_directory(parent: Path | None, *, prefix: str) -> Path:
    if parent is not None:
        parent = parent.resolve()
        if not parent.is_dir():
            raise FileNotFoundError("temporary parent is unavailable")
    path = Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
    path.chmod(0o700)
    return path


def _remove_temporary_directory(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise DurableBackupError("durable backup temporary cleanup failed") from exc


class _TemporaryWorkspaceSignalGuard:
    """Remove one owned workspace before honoring default termination signals."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._previous: dict[int, Any] = {}

    def install(self) -> None:
        for termination_signal in (signal.SIGTERM, signal.SIGHUP):
            if signal.getsignal(termination_signal) is not signal.SIG_DFL:
                continue
            try:
                previous = signal.signal(termination_signal, self._handle)
            except ValueError:
                self.restore()
                return
            self._previous[termination_signal] = previous

    def restore(self) -> None:
        previous = self._previous
        self._previous = {}
        for termination_signal, handler in previous.items():
            signal.signal(termination_signal, handler)

    def _handle(self, signum: int, frame: object) -> None:
        del frame
        self.restore()
        try:
            _remove_temporary_directory(self._path)
        finally:
            os.kill(os.getpid(), signum)


def _tar_info(name: str, size: int, timestamp: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o600
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = timestamp
    return info


def _add_bytes(
    archive: tarfile.TarFile, name: str, payload: bytes, timestamp: int
) -> None:
    import io

    archive.addfile(_tar_info(name, len(payload), timestamp), io.BytesIO(payload))


def _add_file(archive: tarfile.TarFile, name: str, path: Path, timestamp: int) -> None:
    with path.open("rb") as stream:
        archive.addfile(_tar_info(name, path.stat().st_size, timestamp), stream)


def _write_candidate_archive(
    root: Path,
    work: Path,
    *,
    backup_id: str,
    created_at: str,
    timestamp: int,
) -> Path:
    snapshot = work / "candidate-snapshot" / "candidates.db"
    manifest = create_candidate_snapshot(root, snapshot, now=created_at)
    manifest_path = snapshot.with_suffix(snapshot.suffix + ".manifest.json")
    verified = verify_candidate_snapshot(snapshot, manifest_path)
    if verified.get("status") != "ok":
        raise DurableBackupError("Candidate snapshot verification failed")

    live_operations = operations_db_path(root)
    if not live_operations.is_file():
        raise DurableBackupError("Operations DB preflight failed")
    operations_snapshot = work / "operations-snapshot" / "operations.db"
    operations_snapshot.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(live_operations)
    destination_connection = sqlite3.connect(operations_snapshot)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()
    with sqlite3.connect(operations_snapshot) as check:
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise DurableBackupError("Operations DB snapshot verification failed")
        row = check.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
    if row is None:
        raise DurableBackupError("Operations DB schema verification failed")
    operations_manifest = {
        "sha256": _sha256(operations_snapshot),
        "size_bytes": operations_snapshot.stat().st_size,
        "schema_version": int(row[0]),
        "created_at": created_at,
    }
    operations_manifest_path = operations_snapshot.with_suffix(".db.manifest.json")
    operations_manifest_path.write_text(
        json.dumps(operations_manifest, sort_keys=True) + "\n", encoding="utf-8"
    )

    inner = {
        "format_version": 1,
        "backup_id": backup_id,
        "backup_set": "candidate",
        "created_at": created_at,
        "candidate": manifest,
        "operations": operations_manifest,
    }
    archive_path = work / f"{backup_id}-candidate.tar"
    with tarfile.open(archive_path, "x") as archive:
        _add_bytes(
            archive,
            INNER_MANIFEST_NAME,
            (json.dumps(inner, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            timestamp,
        )
        _add_file(archive, CANDIDATE_ARCHIVE_PATH, snapshot, timestamp)
        _add_file(
            archive,
            CANDIDATE_MANIFEST_ARCHIVE_PATH,
            manifest_path,
            timestamp,
        )
        _add_file(archive, OPERATIONS_ARCHIVE_PATH, operations_snapshot, timestamp)
        _add_file(
            archive,
            OPERATIONS_MANIFEST_ARCHIVE_PATH,
            operations_manifest_path,
            timestamp,
        )
    archive_path.chmod(0o600)
    return archive_path


def _write_source_archive(
    root: Path,
    work: Path,
    inventory: tuple[SourceAssetInventoryEntry, ...],
    *,
    backup_id: str,
    created_at: str,
    timestamp: int,
) -> Path:
    inner = {
        "format_version": 1,
        "backup_id": backup_id,
        "backup_set": "source_assets",
        "created_at": created_at,
        "assets": [asdict(item) for item in inventory],
    }
    archive_path = work / f"{backup_id}-source_assets.tar"
    with tarfile.open(archive_path, "x") as archive:
        _add_bytes(
            archive,
            INNER_MANIFEST_NAME,
            (json.dumps(inner, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            timestamp,
        )
        for entry in inventory:
            _add_file(archive, entry.path, root / entry.path, timestamp)
    archive_path.chmod(0o600)
    return archive_path


def _archive_member_sha256(archive: tarfile.TarFile, member: tarfile.TarInfo) -> str:
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("archive member is unreadable")
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def _validated_operations_manifest(
    value: object, *, created_at: str
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {
        "sha256",
        "size_bytes",
        "schema_version",
        "created_at",
    }:
        raise ValueError("Operations manifest is invalid")
    sha256 = value.get("sha256")
    size_bytes = value.get("size_bytes")
    schema_version = value.get("schema_version")
    if (
        not isinstance(sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", sha256) is None
        or not isinstance(size_bytes, int)
        or isinstance(size_bytes, bool)
        or size_bytes < 1
        or not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version < 1
        or value.get("created_at") != created_at
    ):
        raise ValueError("Operations manifest is invalid")
    return value


def _archived_json(
    archive: tarfile.TarFile, member: tarfile.TarInfo, *, label: str
) -> object:
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"{label} is unreadable")
    try:
        return json.loads(stream.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is invalid") from exc


def _verify_plaintext_archive(
    archive_path: Path,
    backup_set: BackupSet,
    *,
    backup_id: str,
    created_at: str,
) -> None:
    context = DurableBackupReceipt(
        backup_id=backup_id,
        created_at=created_at,
        status="plaintext_verification",
        sets=(),
        remote_repository="",
        remote_release="",
    )
    try:
        with tarfile.open(archive_path, "r:*") as archive:
            members = _validated_tar_members(archive)
            inner = _inner_manifest(archive, members)
            _validate_inner_common(inner, context, backup_set)
            if backup_set == "candidate":
                expected = {
                    INNER_MANIFEST_NAME,
                    CANDIDATE_ARCHIVE_PATH,
                    CANDIDATE_MANIFEST_ARCHIVE_PATH,
                    OPERATIONS_ARCHIVE_PATH,
                    OPERATIONS_MANIFEST_ARCHIVE_PATH,
                }
                if set(members) != expected or any(
                    not member.isfile() for member in members.values()
                ):
                    raise ValueError("Candidate archive member set is invalid")
                candidate = inner.get("candidate")
                if not isinstance(candidate, dict):
                    raise ValueError("Candidate inner manifest is invalid")
                expected_hash = candidate.get("sha256")
                expected_size = candidate.get("size_bytes")
                snapshot_member = members[CANDIDATE_ARCHIVE_PATH]
                if (
                    not isinstance(expected_hash, str)
                    or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None
                    or not isinstance(expected_size, int)
                    or isinstance(expected_size, bool)
                    or expected_size < 1
                    or snapshot_member.size != expected_size
                    or _archive_member_sha256(archive, snapshot_member) != expected_hash
                ):
                    raise ValueError("Candidate archive hash does not match manifest")
                manifest_member = members[CANDIDATE_MANIFEST_ARCHIVE_PATH]
                manifest_stream = archive.extractfile(manifest_member)
                if manifest_stream is None:
                    raise ValueError("Candidate snapshot manifest is unreadable")
                try:
                    archived_manifest: object = json.loads(
                        manifest_stream.read().decode("utf-8")
                    )
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError("Candidate snapshot manifest is invalid") from exc
                if archived_manifest != candidate:
                    raise ValueError(
                        "Candidate snapshot manifest does not match inner manifest"
                    )
                operations = _validated_operations_manifest(
                    inner.get("operations"), created_at=created_at
                )
                operations_member = members[OPERATIONS_ARCHIVE_PATH]
                if operations_member.size != operations.get(
                    "size_bytes"
                ) or _archive_member_sha256(
                    archive, operations_member
                ) != operations.get("sha256"):
                    raise ValueError("Operations archive hash does not match manifest")
                archived_operations_manifest = _archived_json(
                    archive,
                    members[OPERATIONS_MANIFEST_ARCHIVE_PATH],
                    label="Operations snapshot manifest",
                )
                if archived_operations_manifest != operations:
                    raise ValueError(
                        "Operations snapshot manifest does not match inner manifest"
                    )
                return

            raw_assets = inner.get("assets")
            if not isinstance(raw_assets, list) or not raw_assets:
                raise ValueError("Source inventory is missing")
            inventory = tuple(_inventory_entry(item) for item in raw_assets)
            paths = [item.path for item in inventory]
            if len(paths) != len(set(paths)):
                raise ValueError("Source inventory contains duplicate paths")
            if set(members) != {INNER_MANIFEST_NAME, *paths}:
                raise ValueError("Source archive member set does not match inventory")
            for entry in inventory:
                member = members[entry.path]
                if (
                    not member.isfile()
                    or member.size != entry.size_bytes
                    or _archive_member_sha256(archive, member) != entry.sha256
                ):
                    raise ValueError("Source archive hash does not match inventory")
    except (OSError, tarfile.TarError, ValueError) as exc:
        raise DurableBackupError(
            f"plaintext archive integrity verification failed for {backup_set}"
        ) from exc


def _verify_remote_asset(
    uploaded: RemoteAsset,
    inspected: RemoteAsset,
    *,
    expected_name: str,
    expected_size: int,
) -> None:
    if (
        uploaded != inspected
        or inspected.name != expected_name
        or inspected.size_bytes != expected_size
        or not inspected.asset_id
    ):
        raise DurableBackupError("remote backup asset verification failed")


def _outer_manifest(
    *,
    backup_id: str,
    backup_set: BackupSet,
    created_at: str,
    encrypted: Path,
    remote: RemoteAsset,
) -> dict[str, object]:
    return {
        "backup_id": backup_id,
        "backup_set": backup_set,
        "created_at": created_at,
        "ciphertext_name": encrypted.name,
        "ciphertext_sha256": _sha256(encrypted),
        "ciphertext_size_bytes": encrypted.stat().st_size,
        "remote_asset_id": remote.asset_id,
    }


def _write_json_file(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _atomic_json(path: Path, payload: dict[str, Any], *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        if path.exists() and not overwrite:
            raise FileExistsError(path)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_durable_backup(
    request: DurableBackupRequest,
    *,
    now: str | None = None,
    backup_id: str | None = None,
    temp_parent: Path | None = None,
) -> DurableBackupReceipt:
    """Create, encrypt, upload and record both durable backup sets."""
    root = request.root.resolve()
    if not root.is_dir():
        raise FileNotFoundError("repository root is unavailable")
    created_time = _parse_utc(now)
    created_at = _created_at(created_time)
    resolved_backup_id = _validate_backup_id(
        backup_id or _default_backup_id(created_time)
    )
    recipients = _validate_recipients(request.recipients)
    inventory = build_source_asset_inventory(root)
    if not inventory:
        raise ValueError("Source asset inventory is empty")
    database_health = candidate_db_health(candidate_db_path(root))
    if database_health.get("status") != "ok":
        raise DurableBackupError("Candidate DB preflight failed")

    receipt_path = durable_receipt_path(root, resolved_backup_id)
    if receipt_path.exists():
        raise FileExistsError(receipt_path)
    names = _asset_names(resolved_backup_id)
    request.backend.preflight(names)
    _preflight_age(recipients)
    if not request.apply:
        return DurableBackupReceipt(
            backup_id=resolved_backup_id,
            created_at=created_at,
            status="dry_run",
            sets=(),
            remote_repository=request.backend.repository,
            remote_release=request.backend.release_tag,
        )

    work = _temporary_directory(temp_parent, prefix="research-os-durable-create-")
    signal_guard = _TemporaryWorkspaceSignalGuard(work)
    signal_guard.install()
    encrypted_assets: list[EncryptedAsset] = []
    try:
        plaintext_archives: dict[BackupSet, Path] = {
            "candidate": _write_candidate_archive(
                root,
                work,
                backup_id=resolved_backup_id,
                created_at=created_at,
                timestamp=int(created_time.timestamp()),
            ),
            "source_assets": _write_source_archive(
                root,
                work,
                inventory,
                backup_id=resolved_backup_id,
                created_at=created_at,
                timestamp=int(created_time.timestamp()),
            ),
        }
        for backup_set in _BACKUP_SETS:
            _verify_plaintext_archive(
                plaintext_archives[backup_set],
                backup_set,
                backup_id=resolved_backup_id,
                created_at=created_at,
            )
        for backup_set in _BACKUP_SETS:
            encrypted_name = f"{resolved_backup_id}-{backup_set}.tar.age"
            encrypted_path = work / encrypted_name
            _encrypt_age(plaintext_archives[backup_set], encrypted_path, recipients)
            uploaded = request.backend.upload(encrypted_path, name=encrypted_name)
            inspected = request.backend.inspect(name=encrypted_name)
            _verify_remote_asset(
                uploaded,
                inspected,
                expected_name=encrypted_name,
                expected_size=encrypted_path.stat().st_size,
            )
            outer = _outer_manifest(
                backup_id=resolved_backup_id,
                backup_set=backup_set,
                created_at=created_at,
                encrypted=encrypted_path,
                remote=inspected,
            )
            outer_name = f"{resolved_backup_id}-{backup_set}.manifest.json"
            outer_path = work / outer_name
            _write_json_file(outer_path, outer)
            outer_uploaded = request.backend.upload(outer_path, name=outer_name)
            outer_inspected = request.backend.inspect(name=outer_name)
            _verify_remote_asset(
                outer_uploaded,
                outer_inspected,
                expected_name=outer_name,
                expected_size=outer_path.stat().st_size,
            )
            encrypted_assets.append(
                EncryptedAsset(
                    backup_set=backup_set,
                    name=encrypted_name,
                    sha256=cast(str, outer["ciphertext_sha256"]),
                    size_bytes=cast(int, outer["ciphertext_size_bytes"]),
                    remote=inspected,
                )
            )

    finally:
        signal_guard.restore()
        _remove_temporary_directory(work)

    receipt = DurableBackupReceipt(
        backup_id=resolved_backup_id,
        created_at=created_at,
        status="verified",
        sets=tuple(encrypted_assets),
        remote_repository=request.backend.repository,
        remote_release=request.backend.release_tag,
    )
    payload = receipt.as_dict()
    _atomic_json(receipt_path, payload, overwrite=False)
    _atomic_json(durable_latest_success_path(root), payload, overwrite=True)
    return receipt


def _parse_remote_asset(value: object) -> RemoteAsset:
    if not isinstance(value, dict):
        raise ValueError("durable receipt remote asset is invalid")
    name = value.get("name")
    asset_id = value.get("asset_id")
    size_bytes = value.get("size_bytes")
    if (
        not isinstance(name, str)
        or not isinstance(asset_id, str)
        or not isinstance(size_bytes, int)
        or isinstance(size_bytes, bool)
        or size_bytes < 0
    ):
        raise ValueError("durable receipt remote asset is invalid")
    return RemoteAsset(name=name, asset_id=asset_id, size_bytes=size_bytes)


def load_durable_backup_receipt(path: Path) -> DurableBackupReceipt:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("durable receipt is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("durable receipt is invalid")
    backup_id = payload.get("backup_id")
    created_at = payload.get("created_at")
    status = payload.get("status")
    repository = payload.get("remote_repository")
    release = payload.get("remote_release")
    raw_sets = payload.get("sets")
    if (
        not isinstance(backup_id, str)
        or not isinstance(created_at, str)
        or not isinstance(status, str)
        or not isinstance(repository, str)
        or not isinstance(release, str)
        or not isinstance(raw_sets, list)
    ):
        raise ValueError("durable receipt is invalid")
    _validate_backup_id(backup_id)
    try:
        repository = canonical_github_repository(repository)
    except ValueError as exc:
        raise ValueError("durable receipt is invalid") from exc
    sets: list[EncryptedAsset] = []
    for raw in raw_sets:
        if not isinstance(raw, dict):
            raise ValueError("durable receipt set is invalid")
        backup_set = raw.get("backup_set")
        name = raw.get("name")
        sha256 = raw.get("sha256")
        size_bytes = raw.get("size_bytes")
        if (
            backup_set not in _BACKUP_SETS
            or not isinstance(name, str)
            or not isinstance(sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", sha256) is None
            or not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 1
        ):
            raise ValueError("durable receipt set is invalid")
        sets.append(
            EncryptedAsset(
                backup_set=cast(BackupSet, backup_set),
                name=name,
                sha256=sha256,
                size_bytes=size_bytes,
                remote=_parse_remote_asset(raw.get("remote")),
            )
        )
    return DurableBackupReceipt(
        backup_id=backup_id,
        created_at=created_at,
        status=status,
        sets=tuple(sets),
        remote_repository=repository,
        remote_release=release,
    )


def _verified_assets(
    receipt: DurableBackupReceipt, backend: BackupBackend
) -> dict[BackupSet, EncryptedAsset]:
    if (
        receipt.remote_repository != backend.repository
        or receipt.remote_release != backend.release_tag
    ):
        raise ValueError("durable receipt backend does not match configured backend")
    if receipt.status != "verified" or len(receipt.sets) != len(_BACKUP_SETS):
        raise ValueError("durable receipt is not a complete verified backup")
    _validate_backup_id(receipt.backup_id)

    assets: dict[BackupSet, EncryptedAsset] = {}
    for encrypted in receipt.sets:
        expected_name = f"{receipt.backup_id}-{encrypted.backup_set}.tar.age"
        if (
            encrypted.backup_set in assets
            or encrypted.name != expected_name
            or encrypted.remote.name != encrypted.name
            or encrypted.remote.size_bytes != encrypted.size_bytes
            or not encrypted.remote.asset_id
            or encrypted.size_bytes < 1
            or re.fullmatch(r"[0-9a-f]{64}", encrypted.sha256) is None
        ):
            raise ValueError("durable receipt set metadata is invalid")
        assets[encrypted.backup_set] = encrypted
    if set(assets) != set(_BACKUP_SETS):
        raise ValueError("durable receipt is not a complete verified backup")
    return assets


def _validate_restore_destination(root: Path, destination: Path) -> Path:
    root = root.resolve()
    expanded = destination.expanduser()
    if expanded.is_symlink():
        raise ValueError("restore destination cannot be a symlink")
    resolved = expanded.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        relative = None
    if relative is not None and (
        not relative.parts or relative.parts[0] in _AUTHORITATIVE_TOP_LEVEL
    ):
        raise ValueError("restore destination cannot be an authoritative path")
    if root.is_relative_to(resolved):
        raise ValueError("restore destination cannot contain the live repository")
    live_assets = (root / "01_Inbox/_assets").resolve()
    if resolved == live_assets or resolved.is_relative_to(live_assets):
        raise ValueError("restore destination cannot be an authoritative path")
    if resolved == candidate_db_path(root).resolve():
        raise ValueError("restore destination cannot be the live Candidate DB")
    if resolved.exists() and (not resolved.is_dir() or any(resolved.iterdir())):
        raise ValueError("restore destination must be absent or empty")
    return resolved


def _outer_manifest_name(backup_id: str, backup_set: BackupSet) -> str:
    return f"{backup_id}-{backup_set}.manifest.json"


def _load_outer_manifest(
    path: Path, receipt: DurableBackupReceipt, encrypted: EncryptedAsset
) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("remote outer manifest is invalid") from exc
    if not isinstance(payload, dict) or set(payload) != _OUTER_MANIFEST_KEYS:
        raise ValueError("remote outer manifest is invalid")
    if (
        payload.get("backup_id") != receipt.backup_id
        or payload.get("backup_set") != encrypted.backup_set
        or payload.get("created_at") != receipt.created_at
        or payload.get("ciphertext_name") != encrypted.name
        or payload.get("ciphertext_sha256") != encrypted.sha256
        or payload.get("ciphertext_size_bytes") != encrypted.size_bytes
        or payload.get("remote_asset_id") != encrypted.remote.asset_id
    ):
        raise ValueError("remote outer manifest does not match receipt")
    return cast(dict[str, object], payload)


def _download_verified_ciphertext(
    receipt: DurableBackupReceipt,
    encrypted: EncryptedAsset,
    backend: BackupBackend,
    work: Path,
) -> Path:
    outer_name = _outer_manifest_name(receipt.backup_id, encrypted.backup_set)
    outer_remote = backend.inspect(name=outer_name)
    outer_path = work / outer_name
    backend.download(name=outer_name, destination=outer_path)
    if (
        outer_remote.name != outer_name
        or outer_remote.size_bytes != outer_path.stat().st_size
    ):
        raise ValueError("remote outer manifest metadata mismatch")
    _load_outer_manifest(outer_path, receipt, encrypted)

    inspected = backend.inspect(name=encrypted.name)
    if inspected != encrypted.remote or inspected.size_bytes != encrypted.size_bytes:
        raise ValueError("remote ciphertext metadata mismatch")
    ciphertext = work / encrypted.name
    backend.download(name=encrypted.name, destination=ciphertext)
    if (
        ciphertext.stat().st_size != encrypted.size_bytes
        or _sha256(ciphertext) != encrypted.sha256
    ):
        raise ValueError("remote ciphertext hash verification failed")
    return ciphertext


def verify_durable_backup_remote(
    receipt: DurableBackupReceipt,
    *,
    backend: BackupBackend,
    temp_parent: Path | None = None,
) -> dict[str, object]:
    """Download outer metadata and ciphertext to verify immutable remote bytes."""
    assets = _verified_assets(receipt, backend)
    work = _temporary_directory(temp_parent, prefix="research-os-durable-verify-")
    try:
        for backup_set in _BACKUP_SETS:
            _download_verified_ciphertext(receipt, assets[backup_set], backend, work)
        return {
            "status": "verified",
            "backup_id": receipt.backup_id,
            "sets": len(assets),
        }
    finally:
        _remove_temporary_directory(work)


def _validated_tar_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    members: dict[str, tarfile.TarInfo] = {}
    for member in archive.getmembers():
        raw_name = member.name
        path = _validate_safe_relative(raw_name, label="archive member")
        normalized = path.as_posix()
        if normalized in members:
            raise ValueError("archive contains duplicate members")
        if member.issym() or member.islnk():
            raise ValueError("archive links are not allowed")
        if member.isdev() or member.isfifo():
            raise ValueError("archive device members are not allowed")
        if not member.isfile() and not member.isdir():
            raise ValueError("archive member type is not allowed")
        members[normalized] = member
    return members


def _inner_manifest(
    archive: tarfile.TarFile, members: dict[str, tarfile.TarInfo]
) -> dict[str, object]:
    member = members.get(INNER_MANIFEST_NAME)
    if member is None or not member.isfile():
        raise ValueError("encrypted archive inner manifest is missing")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("encrypted archive inner manifest is unreadable")
    try:
        payload: object = json.loads(stream.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("encrypted archive inner manifest is invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("encrypted archive inner manifest is invalid")
    return cast(dict[str, object], payload)


def _extract_regular_member(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
    destination: Path,
) -> None:
    if not member.isfile():
        return
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError("archive member is unreadable")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        shutil.copyfileobj(stream, output)
    destination.chmod(0o600)


def _validate_inner_common(
    inner: dict[str, object], receipt: DurableBackupReceipt, backup_set: BackupSet
) -> None:
    if (
        inner.get("format_version") != 1
        or inner.get("backup_id") != receipt.backup_id
        or inner.get("backup_set") != backup_set
        or inner.get("created_at") != receipt.created_at
    ):
        raise ValueError("encrypted archive inner manifest does not match receipt")


def _restore_candidate_archive(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    inner: dict[str, object],
    receipt: DurableBackupReceipt,
    staging: Path,
) -> tuple[str, int]:
    _validate_inner_common(inner, receipt, "candidate")
    expected = {
        INNER_MANIFEST_NAME,
        CANDIDATE_ARCHIVE_PATH,
        CANDIDATE_MANIFEST_ARCHIVE_PATH,
        OPERATIONS_ARCHIVE_PATH,
        OPERATIONS_MANIFEST_ARCHIVE_PATH,
    }
    if set(members) != expected or any(not item.isfile() for item in members.values()):
        raise ValueError("Candidate archive member set is invalid")
    candidate_manifest = inner.get("candidate")
    if not isinstance(candidate_manifest, dict):
        raise ValueError("Candidate inner manifest is invalid")
    for name in (
        CANDIDATE_ARCHIVE_PATH,
        CANDIDATE_MANIFEST_ARCHIVE_PATH,
        OPERATIONS_ARCHIVE_PATH,
        OPERATIONS_MANIFEST_ARCHIVE_PATH,
    ):
        _extract_regular_member(archive, members[name], staging / name)
    snapshot = staging / CANDIDATE_ARCHIVE_PATH
    manifest_path = staging / CANDIDATE_MANIFEST_ARCHIVE_PATH
    try:
        on_disk_manifest: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Candidate snapshot manifest is invalid") from exc
    if on_disk_manifest != candidate_manifest:
        raise ValueError("Candidate snapshot manifest does not match inner manifest")
    verified = verify_candidate_snapshot(snapshot, manifest_path)
    if verified.get("status") != "ok":
        raise ValueError("Candidate snapshot verification failed")
    sha256 = verified.get("sha256")
    schema_version = verified.get("schema_version")
    if not isinstance(sha256, str) or not isinstance(schema_version, int):
        raise ValueError("Candidate snapshot verification is incomplete")
    operations_manifest = _validated_operations_manifest(
        inner.get("operations"), created_at=receipt.created_at
    )
    operations_manifest_path = staging / OPERATIONS_MANIFEST_ARCHIVE_PATH
    try:
        on_disk_operations_manifest: object = json.loads(
            operations_manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Operations snapshot manifest is invalid") from exc
    if on_disk_operations_manifest != operations_manifest:
        raise ValueError("Operations snapshot manifest does not match inner manifest")
    operations_snapshot = staging / OPERATIONS_ARCHIVE_PATH
    if operations_snapshot.stat().st_size != operations_manifest.get(
        "size_bytes"
    ) or _sha256(operations_snapshot) != operations_manifest.get("sha256"):
        raise ValueError("Operations snapshot hash does not match manifest")
    with sqlite3.connect(operations_snapshot) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Operations snapshot integrity check failed")
        operations_row = connection.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
    if operations_row is None or int(operations_row[0]) != operations_manifest.get(
        "schema_version"
    ):
        raise ValueError("Operations snapshot schema check failed")
    return sha256, schema_version


def _inventory_entry(value: object) -> SourceAssetInventoryEntry:
    if not isinstance(value, dict) or set(value) != {
        "source_id",
        "path",
        "size_bytes",
        "sha256",
    }:
        raise ValueError("Source inventory entry is invalid")
    source_id = value.get("source_id")
    path_value = value.get("path")
    size_bytes = value.get("size_bytes")
    sha256 = value.get("sha256")
    if (
        not isinstance(source_id, str)
        or _SOURCE_ID_PATTERN.fullmatch(source_id) is None
        or not isinstance(path_value, str)
        or not isinstance(size_bytes, int)
        or isinstance(size_bytes, bool)
        or size_bytes < 0
        or not isinstance(sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", sha256) is None
    ):
        raise ValueError("Source inventory entry is invalid")
    relative = _validate_safe_relative(path_value, label="Source inventory path")
    if _source_id_for_path(relative) != source_id:
        raise ValueError("Source inventory path does not match Source ID")
    return SourceAssetInventoryEntry(source_id, path_value, size_bytes, sha256)


def _restore_source_archive(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    inner: dict[str, object],
    receipt: DurableBackupReceipt,
    staging: Path,
) -> int:
    _validate_inner_common(inner, receipt, "source_assets")
    raw_assets = inner.get("assets")
    if not isinstance(raw_assets, list) or not raw_assets:
        raise ValueError("Source inventory is missing")
    inventory = tuple(_inventory_entry(item) for item in raw_assets)
    paths = [item.path for item in inventory]
    if len(paths) != len(set(paths)):
        raise ValueError("Source inventory contains duplicate paths")
    expected = {INNER_MANIFEST_NAME, *paths}
    if set(members) != expected:
        raise ValueError("Source archive member set does not match inventory")
    for entry in inventory:
        member = members[entry.path]
        if not member.isfile() or member.size != entry.size_bytes:
            raise ValueError("Source archive size does not match inventory")
        target = staging / entry.path
        _extract_regular_member(archive, member, target)
        if target.stat().st_size != entry.size_bytes or _sha256(target) != entry.sha256:
            raise ValueError("Source archive hash does not match inventory")
    return len(inventory)


def restore_durable_backup(
    root: Path,
    receipt: DurableBackupReceipt,
    *,
    backend: BackupBackend,
    identity: Path,
    destination: Path,
    temp_parent: Path | None = None,
) -> DurableRestoreResult:
    """Restore a verified receipt into an absent or empty disposable directory."""
    root = root.resolve()
    destination = _validate_restore_destination(root, destination)
    if identity.is_symlink() or not identity.is_file():
        raise ValueError("age identity file is unavailable")
    by_set = _verified_assets(receipt, backend)

    work = _temporary_directory(temp_parent, prefix="research-os-durable-restore-")
    signal_guard = _TemporaryWorkspaceSignalGuard(work)
    signal_guard.install()
    staging = work / "staging"
    staging.mkdir(mode=0o700)
    candidate_sha256 = ""
    candidate_schema_version = 0
    source_asset_count = 0
    operations_sha256 = ""
    operations_schema_version = 0
    try:
        for backup_set in _BACKUP_SETS:
            encrypted = by_set[backup_set]
            ciphertext = _download_verified_ciphertext(
                receipt, encrypted, backend, work
            )
            archive_path = work / f"{receipt.backup_id}-{backup_set}.tar"
            _decrypt_age(ciphertext, archive_path, identity)
            try:
                with tarfile.open(archive_path, "r:*") as archive:
                    members = _validated_tar_members(archive)
                    inner = _inner_manifest(archive, members)
                    if backup_set == "candidate":
                        candidate_sha256, candidate_schema_version = (
                            _restore_candidate_archive(
                                archive, members, inner, receipt, staging
                            )
                        )
                        operations_path = staging / OPERATIONS_ARCHIVE_PATH
                        operations_sha256 = _sha256(operations_path)
                        with sqlite3.connect(operations_path) as connection:
                            operations_schema_version = int(
                                connection.execute(
                                    "SELECT value FROM schema_meta "
                                    "WHERE key='schema_version'"
                                ).fetchone()[0]
                            )
                    else:
                        source_asset_count = _restore_source_archive(
                            archive, members, inner, receipt, staging
                        )
            except (tarfile.TarError, OSError) as exc:
                raise ValueError("encrypted archive is invalid") from exc

        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.rmdir()
        shutil.move(str(staging), str(destination))
        return DurableRestoreResult(
            backup_id=receipt.backup_id,
            status="verified",
            destination=destination,
            candidate_sha256=candidate_sha256,
            candidate_schema_version=candidate_schema_version,
            source_asset_count=source_asset_count,
            operations_sha256=operations_sha256,
            operations_schema_version=operations_schema_version,
        )
    finally:
        signal_guard.restore()
        _remove_temporary_directory(work)
