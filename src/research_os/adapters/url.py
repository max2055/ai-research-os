"""Bounded, explicit single-URL capture adapter."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from research_os.adapters.base import CapturedAsset

DEFAULT_MAX_BYTES = 20 * 1024 * 1024
TRACKING_PARAMETERS = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid"})


def canonicalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http or https")
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower()
    port = parsed.port
    if port and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
            if not key.lower().startswith("utm_")
            and key.lower() not in TRACKING_PARAMETERS
        )
    )
    path = parsed.path or "/"
    return urlunsplit((scheme, hostname, path, query, ""))


class _PublishedDateParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.candidates: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "meta":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        label_value = (
            values.get("property") or values.get("name") or values.get("itemprop")
        )
        label = (label_value or "").lower()
        if label in {
            "article:published_time",
            "date",
            "datepublished",
            "publishdate",
            "publication_date",
        }:
            self.candidates.append(values.get("content", ""))


def normalize_date_candidate(value: str) -> str | None:
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if not match:
        return None
    candidate = match.group(0)
    try:
        date.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def propose_html_published_date(content: bytes) -> str | None:
    text = content.decode("utf-8", errors="replace")
    parser = _PublishedDateParser()
    parser.feed(text)
    json_ld = re.findall(
        r'"datePublished"\s*:\s*"([^"]+)"',
        text,
        flags=re.IGNORECASE,
    )
    proposals = {
        candidate
        for raw in [*parser.candidates, *json_ld]
        if (candidate := normalize_date_candidate(raw))
    }
    return next(iter(proposals)) if len(proposals) == 1 else None


class UrlCaptureAdapter:
    def __init__(
        self,
        url: str,
        *,
        timeout: float = 30,
        max_bytes: int = DEFAULT_MAX_BYTES,
        captured_at: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.url = canonicalize_url(url)
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.captured_at = captured_at
        # SEC EDGAR rejects short UA strings (403); a compliant contact
        # format "Name Contact@domain" is required. The default stays generic
        # for non-SEC hosts; callers capturing sec.gov may pass a compliant UA.
        self.user_agent = user_agent or "AI-Research-OS/0.2 explicit-single-url-capture"

    def capture(self) -> CapturedAsset:
        request = Request(
            self.url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/pdf,text/plain,*/*;q=0.1",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
            content = response.read(self.max_bytes + 1)
            if len(content) > self.max_bytes:
                raise ValueError(f"URL response exceeds {self.max_bytes} byte limit")
            media_type = response.headers.get_content_type()
            final_url = canonicalize_url(response.geturl())
            metadata = {
                "http_status": str(response.status),
                "content_type": response.headers.get("Content-Type", ""),
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
            }
        proposal = (
            propose_html_published_date(content)
            if media_type in {"text/html", "application/xhtml+xml"}
            else None
        )
        captured_at = self.captured_at or datetime.now(UTC).isoformat()
        return CapturedAsset(
            content=content,
            media_type=media_type,
            original_locator=self.url,
            final_locator=final_url,
            captured_at=captured_at,
            published_date_proposal=proposal,
            metadata=metadata,
        )
