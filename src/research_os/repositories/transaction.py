"""Transactional multi-file writes with preflight and rollback."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class TransactionError(RuntimeError):
    """Raised when a file transaction cannot be committed."""


@dataclass(frozen=True)
class StagedWrite:
    path: Path
    content: bytes
    must_exist: bool


class FileTransaction:
    def __init__(
        self,
        root: Path,
        *,
        replacer: Callable[[Path, Path], None] = os.replace,
    ) -> None:
        self.root = root.resolve()
        self.replacer = replacer
        self._writes: list[StagedWrite] = []

    def _resolve(self, path: Path) -> Path:
        target = path if path.is_absolute() else self.root / path
        target = target.resolve()
        if not target.is_relative_to(self.root):
            raise TransactionError(f"path escapes transaction root: {path}")
        return target

    def stage_create(self, path: Path, content: str) -> None:
        self.stage_create_bytes(path, content.encode("utf-8"))

    def stage_replace(self, path: Path, content: str) -> None:
        self.stage_replace_bytes(path, content.encode("utf-8"))

    def stage_create_bytes(self, path: Path, content: bytes) -> None:
        self._stage(path, content, must_exist=False)

    def stage_replace_bytes(self, path: Path, content: bytes) -> None:
        self._stage(path, content, must_exist=True)

    def _stage(self, path: Path, content: bytes, *, must_exist: bool) -> None:
        target = self._resolve(path)
        if any(write.path == target for write in self._writes):
            raise TransactionError(f"path staged more than once: {target}")
        self._writes.append(StagedWrite(target, content, must_exist))

    @staticmethod
    def _temporary_file(path: Path, content: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".txn",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return temporary

    def commit(self) -> list[Path]:
        if not self._writes:
            return []
        for write in self._writes:
            if write.must_exist and not write.path.is_file():
                raise TransactionError(f"replace target does not exist: {write.path}")
            if not write.must_exist and write.path.exists():
                raise TransactionError(f"create target already exists: {write.path}")

        originals = {
            write.path: (write.path.read_bytes() if write.path.exists() else None)
            for write in self._writes
        }
        temporary_files = {
            write.path: self._temporary_file(write.path, write.content)
            for write in self._writes
        }
        applied: list[Path] = []
        try:
            for write in self._writes:
                self.replacer(temporary_files[write.path], write.path)
                applied.append(write.path)
        except OSError as exc:
            for path in reversed(applied):
                original = originals[path]
                if original is None:
                    path.unlink(missing_ok=True)
                    continue
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{path.name}.",
                    suffix=".rollback",
                    dir=path.parent,
                )
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(original)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(Path(temporary_name), path)
            raise TransactionError(f"transaction rolled back: {exc}") from exc
        finally:
            for temporary in temporary_files.values():
                temporary.unlink(missing_ok=True)
        return applied
