"""Explicit local-file capture adapter."""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from research_os.adapters.base import CapturedAsset
from research_os.adapters.url import propose_html_published_date

DEFAULT_MAX_BYTES = 50 * 1024 * 1024


class FileCaptureAdapter:
    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
        captured_at: str | None = None,
    ) -> None:
        self.path = path.resolve()
        self.max_bytes = max_bytes
        self.captured_at = captured_at

    def capture(self) -> CapturedAsset:
        size = self.path.stat().st_size
        if size > self.max_bytes:
            raise ValueError(
                f"local file exceeds {self.max_bytes} byte limit: {self.path}"
            )
        content = self.path.read_bytes()
        media_type = (
            mimetypes.guess_type(self.path.name)[0] or "application/octet-stream"
        )
        captured_at = self.captured_at or datetime.now(UTC).isoformat()
        proposal = (
            propose_html_published_date(content)
            if media_type in {"text/html", "application/xhtml+xml"}
            else None
        )
        return CapturedAsset(
            content=content,
            media_type=media_type,
            original_locator=str(self.path),
            final_locator=str(self.path),
            captured_at=captured_at,
            published_date_proposal=proposal,
            metadata={
                "filename": self.path.name,
                "source_size": str(size),
            },
        )
