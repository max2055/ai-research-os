"""Comment-preserving Markdown front matter repository."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from research_os.schemas import ManagedObjectSchema, validate_metadata

OBJECT_PATTERNS = (
    "01_Inbox/**/SRC-*.md",
    "04_Evidence/Events/EVT-*.md",
    "03_Theses/**/THS-*.md",
    "02_Knowledge/Companies/COM-*.md",
    "02_Knowledge/Sectors/SEG-*.md",
    "02_Knowledge/Products/PRD-*.md",
    "02_Knowledge/Securities/INS-*.md",
    "02_Knowledge/Channels/CHN-*.md",
    "05_Research/Assertions/REL-*.md",
    "05_Research/Assertions/IMP-*.md",
    "06_Reports/**/RPT-*.md",
    "05_Research/Projects/PRJ-*.md",
    "05_Research/Reviews/Decisions/REV-*.md",
    "05_Research/Reviews/Actions/ACT-*.md",
    "05_Research/Operations/Jobs/JOB-*.md",
)
FRONT_MATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<yaml>.*?)^---[ \t]*(?:\r?\n|$)(?P<body>.*)\Z",
    flags=re.MULTILINE | re.DOTALL,
)


def round_trip_yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.allow_duplicate_keys = False
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


@dataclass
class MarkdownDocument:
    path: Path
    metadata: CommentedMap
    body: str
    original_text: str
    _dirty: bool = field(default=False, init=False, repr=False)

    @classmethod
    def read(cls, path: Path) -> MarkdownDocument:
        text = path.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(text)
        if match is None:
            raise ValueError(f"{path}: missing or invalid YAML front matter")
        loaded = round_trip_yaml().load(match.group("yaml"))
        if not isinstance(loaded, CommentedMap):
            raise ValueError(f"{path}: front matter must be a mapping")
        return cls(
            path=path,
            metadata=loaded,
            body=match.group("body"),
            original_text=text,
        )

    def validate(self) -> ManagedObjectSchema:
        return validate_metadata(self.metadata)

    def set_metadata(self, key: str, value: Any) -> None:
        if key not in self.metadata or self.metadata.get(key) != value:
            self.metadata[key] = value
            self._dirty = True

    def set_body(self, body: str) -> None:
        if self.body != body:
            self.body = body
            self._dirty = True

    def render(self) -> str:
        if not self._dirty:
            return self.original_text
        stream = io.StringIO()
        round_trip_yaml().dump(self.metadata, stream)
        return f"---\n{stream.getvalue()}---\n{self.body}"


def object_paths(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for pattern in OBJECT_PATTERNS:
        paths.update(root.glob(pattern))
    return sorted(path for path in paths if path.is_file())


def load_documents(root: Path) -> list[MarkdownDocument]:
    return [MarkdownDocument.read(path) for path in object_paths(root)]


def validate_documents(
    root: Path,
) -> tuple[list[MarkdownDocument], list[tuple[Path, str]]]:
    documents: list[MarkdownDocument] = []
    errors: list[tuple[Path, str]] = []
    for path in object_paths(root):
        try:
            document = MarkdownDocument.read(path)
            document.validate()
            documents.append(document)
        except (OSError, ValueError, ValidationError) as exc:
            errors.append((path, str(exc)))
    return documents, errors
