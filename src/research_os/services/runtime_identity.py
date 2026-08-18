"""Canonical repository identity and mutation-free product startup checks."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from research_os.services.candidate_db import candidate_db_health, candidate_db_path
from research_os.services.operations_db import operations_db_path

_ROOT_MARKERS = (
    Path("README.md"),
    Path("pyproject.toml"),
    Path("00_System/Research_Rules.md"),
)


class RuntimePreflightError(RuntimeError):
    """The product entry does not identify one safe canonical runtime."""


@dataclass(frozen=True)
class RuntimeIdentity:
    status: str
    root: str
    branch: str
    commit: str
    dirty: bool
    interpreter: str
    package_path: str
    candidate_db: dict[str, Any]
    operations_db: dict[str, Any]
    config_paths: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=True, sort_keys=True)


def repository_root_from_package(package_file: Path | None = None) -> Path:
    """Find the repository containing the imported package, independent of cwd."""
    origin = Path(
        package_file or Path(__file__).resolve().parents[1] / "__init__.py"
    ).resolve()
    for parent in (origin.parent, *origin.parents):
        if all((parent / marker).is_file() for marker in _ROOT_MARKERS):
            return parent.resolve()
    raise RuntimePreflightError(
        f"imported package is not inside an AI Research OS repository: {origin}"
    )


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimePreflightError(
            f"cannot verify Git runtime identity: {exc}"
        ) from exc
    return result.stdout.strip()


def _database_identity(path: Path, health: dict[str, Any]) -> dict[str, Any]:
    result = {"path": str(path.resolve()), **health}
    if path.is_file():
        stat = path.stat()
        result.update({"device": stat.st_dev, "inode": stat.st_ino})
    return result


def _operations_database_health(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "missing", "size_bytes": 0, "schema_version": None}
    try:
        with sqlite3.connect(
            f"file:{path.resolve().as_posix()}?mode=ro", uri=True
        ) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            version = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
        schema_version = int(version[0]) if version is not None else None
        status = (
            "ok"
            if integrity and integrity[0] == "ok" and schema_version == 1
            else "invalid"
        )
        return {
            "status": status,
            "integrity": str(integrity[0]) if integrity else "unknown",
            "schema_version": schema_version,
            "size_bytes": path.stat().st_size,
        }
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return {
            "status": "corrupt",
            "integrity": "unknown",
            "schema_version": None,
            "size_bytes": path.stat().st_size,
        }


def preflight_product_runtime(
    root: Path,
    *,
    package_file: Path | None = None,
) -> RuntimeIdentity:
    """Verify code, repository and operational data agree before any write."""
    resolved_root = Path(root).resolve()
    package_path = Path(
        package_file or Path(__file__).resolve().parents[1] / "__init__.py"
    ).resolve()
    code_root = repository_root_from_package(package_path)
    if code_root != resolved_root:
        raise RuntimePreflightError(
            f"code root does not match runtime root: {code_root} != {resolved_root}"
        )

    git_marker = resolved_root / ".git"
    if git_marker.is_file():
        raise RuntimePreflightError(
            "product startup from a linked Git worktree is forbidden; "
            "start the canonical primary checkout"
        )
    if not git_marker.is_dir():
        raise RuntimePreflightError(
            "canonical repository must contain a .git directory"
        )

    missing = [
        str(marker)
        for marker in _ROOT_MARKERS
        if not (resolved_root / marker).is_file()
    ]
    if missing:
        raise RuntimePreflightError(
            "repository markers are missing: " + ", ".join(missing)
        )

    git_root = Path(_git(resolved_root, "rev-parse", "--show-toplevel")).resolve()
    if git_root != resolved_root:
        raise RuntimePreflightError(
            f"Git root does not match runtime root: {git_root} != {resolved_root}"
        )
    unmerged = _git(resolved_root, "diff", "--name-only", "--diff-filter=U")
    if unmerged:
        raise RuntimePreflightError("repository has unresolved merge conflicts")

    candidate_path = candidate_db_path(resolved_root)
    candidate_health = candidate_db_health(candidate_path)
    if candidate_health["status"] != "ok":
        raise RuntimePreflightError(
            f"canonical Candidate DB is not ready: {candidate_health['status']}"
        )
    operations_path = operations_db_path(resolved_root)
    operations_health = _operations_database_health(operations_path)
    if operations_health["status"] not in {"ok", "missing"}:
        raise RuntimePreflightError(
            f"canonical Operations DB is not ready: {operations_health['status']}"
        )
    return RuntimeIdentity(
        status="verified",
        root=str(resolved_root),
        branch=_git(resolved_root, "branch", "--show-current") or "detached",
        commit=_git(resolved_root, "rev-parse", "HEAD"),
        dirty=bool(
            _git(resolved_root, "status", "--porcelain", "--untracked-files=no")
        ),
        interpreter=str(Path(sys.executable).resolve()),
        package_path=str(package_path),
        candidate_db=_database_identity(candidate_path, candidate_health),
        operations_db=_database_identity(operations_path, operations_health),
        config_paths={
            "web_identity": str(resolved_root / "00_System" / "web.local.json"),
            "llm": str(resolved_root / "00_System" / "llm.local.json"),
            "durable_backup": str(
                resolved_root / "09_Automation" / "operational" / "durable_backup.json"
            ),
        },
    )
