"""Deterministic text extraction for captured Source assets."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO

from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    method: str
    warnings: tuple[str, ...] = ()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
        elif tag.lower() in {"p", "br", "div", "section", "article", "li"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif tag.lower() in {"p", "div", "section", "article", "li"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._chunks.append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self._chunks).splitlines()]
        return "\n".join(line for line in lines if line).strip() + "\n"


def extract_text(content: bytes, media_type: str) -> ExtractionResult:
    normalized = media_type.split(";", 1)[0].strip().lower()
    if normalized in {"text/html", "application/xhtml+xml"}:
        parser = _TextExtractor()
        parser.feed(content.decode("utf-8", errors="replace"))
        text = parser.text()
        if not text.strip():
            raise ValueError("HTML extraction produced no text")
        return ExtractionResult(text=text, method="stdlib-html-parser")
    if normalized == "application/pdf":
        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        text = "\n\n".join(page for page in pages if page).strip()
        if not text:
            raise ValueError("PDF contains no extractable text; OCR is required")
        return ExtractionResult(
            text=text + "\n",
            method="pypdf",
            warnings=("PDF layout may not be preserved in extracted text.",),
        )
    if normalized.startswith("text/") or normalized in {
        "application/json",
        "application/xml",
    }:
        return ExtractionResult(
            text=content.decode("utf-8", errors="replace"),
            method="utf-8-text",
        )
    raise ValueError(f"unsupported extraction media type {media_type!r}")
