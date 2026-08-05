"""Runtime domain objects independent of storage and validation libraries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    path: Path
    message: str

    def format(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{self.level.upper()} {self.code} {display_path}: {self.message}"


@dataclass(frozen=True)
class ResearchObject:
    path: Path
    metadata: dict[str, Any]
    body: str

    @property
    def object_id(self) -> str:
        return str(self.metadata.get("id", ""))

    @property
    def object_type(self) -> str:
        return str(self.metadata.get("type", ""))
