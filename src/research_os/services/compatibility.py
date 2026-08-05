"""Narrow adapters for the pre-package Python API."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml.error import YAMLError

from research_os.domain.models import ResearchObject
from research_os.repositories.markdown import MarkdownDocument
from research_os.repositories.transaction import FileTransaction
from research_os.services.drafts import source_extraction_updates


class FrontMatterError(ValueError):
    """Compatibility error raised for malformed Markdown front matter."""


def parse_front_matter(path: Path) -> ResearchObject:
    """Parse arbitrary front matter without requiring a domain schema."""
    try:
        document = MarkdownDocument.read(path)
    except (OSError, ValueError, YAMLError) as exc:
        raise FrontMatterError(str(exc)) from exc
    return ResearchObject(
        path=path,
        metadata=dict(document.metadata),
        body=document.body.lstrip("\r\n"),
    )


def mark_sources_extracted(
    root: Path,
    source_ids: list[str],
    updated_at: str,
) -> list[Path]:
    """Apply Source processing updates as one compatibility transaction."""
    root = root.resolve()
    updates = source_extraction_updates(root, source_ids, updated_at)
    transaction = FileTransaction(root)
    for path, content in updates.items():
        transaction.stage_replace(path, content)
    return transaction.commit()
