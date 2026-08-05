"""Capture adapter contract and immutable capture result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class CapturedAsset:
    content: bytes
    media_type: str
    original_locator: str
    final_locator: str
    captured_at: str
    published_date_proposal: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class CaptureAdapter(Protocol):
    def capture(self) -> CapturedAsset: ...
