"""Bounded discovery adapters for explicitly configured research sources."""

from __future__ import annotations

import json
import math
import random
import re
import socket
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, OpenerDirector, Request, build_opener
from xml.etree import ElementTree

from research_os.adapters.url import canonicalize_url

DEFAULT_DISCOVERY_LIMIT = 20
MAX_DISCOVERY_LIMIT = 100
DEFAULT_RESPONSE_LIMIT = 5 * 1024 * 1024
MAX_FETCH_ATTEMPTS = 3
MAX_DISCOVERY_REDIRECTS = 5
RETRIABLE_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})
_ABSOLUTE_MAX_RETRY_DELAY = 8.0


@dataclass
class FetchTelemetry:
    attempts: int = 0
    retries: int = 0
    http_errors: int = 0


class DiscoveryTransportError(ValueError):
    failure_class: str
    attempts: int

    def __init__(self, failure_class: str, attempts: int) -> None:
        self.failure_class = failure_class
        self.attempts = attempts
        super().__init__(f"{failure_class} after {attempts} attempts")


class _RedirectPolicyError(ValueError):
    def __init__(self, failure_class: str) -> None:
        self.failure_class = failure_class
        super().__init__(failure_class)


class _AllowlistedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_hosts: frozenset[str]) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts
        self.redirects = 0

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        target = urljoin(req.full_url, newurl)
        try:
            parsed = urlsplit(target)
        except ValueError:
            raise _RedirectPolicyError("redirect_policy") from None
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or not _host_allowed(target, self.allowed_hosts)
        ):
            raise _RedirectPolicyError("redirect_policy")
        self.redirects += 1
        if self.redirects > MAX_DISCOVERY_REDIRECTS:
            raise _RedirectPolicyError("redirect_limit")
        redirected = super().redirect_request(req, fp, code, msg, headers, target)
        if redirected is None or isinstance(redirected, Request):
            return redirected
        raise _RedirectPolicyError("redirect_policy")


@dataclass(frozen=True)
class SourceCandidate:
    adapter: str
    external_id: str
    title: str
    url: str
    published_at: str | None
    publisher: str
    metadata: dict[str, str] = field(default_factory=dict)


class DiscoveryAdapter(Protocol):
    def discover(self) -> tuple[SourceCandidate, ...]: ...


class TextFetcher(Protocol):
    def __call__(
        self,
        url: str,
        *,
        headers: dict[str, str],
        allowed_hosts: frozenset[str],
        max_bytes: int,
    ) -> str: ...


def fetch_text(
    url: str,
    *,
    headers: dict[str, str],
    allowed_hosts: frozenset[str],
    max_bytes: int = DEFAULT_RESPONSE_LIMIT,
    timeout: float = 30.0,
    max_attempts: int = MAX_FETCH_ATTEMPTS,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    sleeper: Callable[[float], None] = time.sleep,
    jitter_source: Callable[[], float] = random.random,
    telemetry: FetchTelemetry | None = None,
) -> str:
    _validate_fetch_policy(
        url,
        allowed_hosts=allowed_hosts,
        max_bytes=max_bytes,
        timeout=timeout,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
    )
    for attempt in range(1, max_attempts + 1):
        if telemetry is not None:
            telemetry.attempts += 1
        try:
            request = Request(url, headers=headers)
            opener = _build_discovery_opener(allowed_hosts)
            with opener.open(request, timeout=timeout) as response:  # noqa: S310
                content = response.read(max_bytes + 1)
            if not isinstance(content, bytes):
                raise DiscoveryTransportError("response_type", attempt)
            if len(content) > max_bytes:
                raise DiscoveryTransportError("response_too_large", attempt)
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                raise DiscoveryTransportError("decode", attempt) from None
        except DiscoveryTransportError:
            raise
        except _RedirectPolicyError as exc:
            raise DiscoveryTransportError(exc.failure_class, attempt) from None
        except Exception as exc:
            failure_class, retriable, retry_after = _classify_transport_failure(
                exc, max_delay=max_delay
            )
            if telemetry is not None and failure_class.startswith("http_"):
                telemetry.http_errors += 1
            if not retriable or attempt >= max_attempts:
                raise DiscoveryTransportError(failure_class, attempt) from None
            if telemetry is not None:
                telemetry.retries += 1
            if retry_after is not None:
                sleeper(retry_after)
            else:
                delay_cap = min(_ABSOLUTE_MAX_RETRY_DELAY, max_delay)
                exponential = min(delay_cap, base_delay * (2 ** (attempt - 1)))
                jitter = min(1.0, max(0.0, jitter_source()))
                sleeper(exponential * jitter)
    raise AssertionError("unreachable discovery retry state")


def _validate_fetch_policy(
    url: str,
    *,
    allowed_hosts: frozenset[str],
    max_bytes: int,
    timeout: float,
    max_attempts: int,
    base_delay: float,
    max_delay: float,
) -> None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise DiscoveryTransportError("policy", 0) from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or not allowed_hosts
        or not _host_allowed(url, allowed_hosts)
        or max_bytes <= 0
        or not 1 <= max_attempts <= MAX_FETCH_ATTEMPTS
        or timeout <= 0
        or not math.isfinite(timeout)
        or base_delay < 0
        or not math.isfinite(base_delay)
        or max_delay < 0
        or not math.isfinite(max_delay)
    ):
        raise DiscoveryTransportError("policy", 0)


def _build_discovery_opener(allowed_hosts: frozenset[str]) -> OpenerDirector:
    return build_opener(_AllowlistedRedirectHandler(allowed_hosts))


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _unwrap_transport_failure(exc: Exception) -> object:
    reason: object = exc
    while isinstance(reason, URLError) and isinstance(reason.reason, Exception):
        reason = reason.reason
    return reason


def _retry_after_delay(error: HTTPError, *, max_delay: float) -> float | None:
    value = error.headers.get("Retry-After") if error.headers is not None else None
    if not value:
        return None
    stripped = value.strip()
    if re.fullmatch(r"\d+", stripped):
        delay = float(stripped)
    else:
        try:
            retry_at = parsedate_to_datetime(stripped)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        delay = (retry_at - _utc_now()).total_seconds()
        if delay < 0:
            return None
    return min(delay, max_delay, _ABSOLUTE_MAX_RETRY_DELAY)


def _classify_transport_failure(
    exc: Exception, *, max_delay: float
) -> tuple[str, bool, float | None]:
    reason = _unwrap_transport_failure(exc)

    if isinstance(reason, HTTPError):
        status = int(reason.code)
        if 300 <= status < 400:
            return "redirect_policy", False, None
        return (
            f"http_{status}",
            status in RETRIABLE_HTTP_STATUSES,
            _retry_after_delay(reason, max_delay=max_delay),
        )
    if isinstance(reason, ssl.SSLCertVerificationError):
        return "certificate", False, None
    if isinstance(reason, ssl.SSLEOFError):
        return "tls_interruption", True, None
    if isinstance(reason, ssl.SSLError):
        detail = str(reason).upper()
        if "EOF" in detail or "HANDSHAKE" in detail:
            return "tls_interruption", True, None
        return "tls", False, None
    if isinstance(reason, ConnectionResetError):
        return "connection_reset", True, None
    if isinstance(reason, TimeoutError):
        return "timeout", True, None
    if isinstance(reason, socket.gaierror):
        if reason.errno == socket.EAI_AGAIN:
            return "temporary_dns", True, None
        return "permanent_dns", False, None
    return "transport", False, None


def _bounded_limit(value: int) -> int:
    if not 1 <= value <= MAX_DISCOVERY_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_DISCOVERY_LIMIT}")
    return value


def _host_allowed(url: str, allowed_hosts: frozenset[str]) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host in {value.lower() for value in allowed_hosts}


def _normalized_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if match:
        candidate = match.group(0)
        try:
            date.fromisoformat(candidate)
        except ValueError:
            return None
        return candidate
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None


def _xml_text(element: ElementTree.Element, names: tuple[str, ...]) -> str:
    for child in element:
        local_name = child.tag.rsplit("}", 1)[-1].lower()
        if local_name in names and child.text:
            return child.text.strip()
    return ""


def _entry_link(element: ElementTree.Element) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = child.attrib.get("href")
        if href and child.attrib.get("rel", "alternate") == "alternate":
            return href
        if child.text:
            return child.text.strip()
    return ""


def parse_feed(
    content: str,
    *,
    adapter: str,
    publisher: str,
    allowed_hosts: frozenset[str],
    limit: int,
) -> tuple[SourceCandidate, ...]:
    root = ElementTree.fromstring(content)
    entries = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}
    ]
    candidates: list[SourceCandidate] = []
    for entry in entries:
        link = _entry_link(entry)
        if not link or not _host_allowed(link, allowed_hosts):
            continue
        title = _xml_text(entry, ("title",)) or "(untitled)"
        external_id = _xml_text(entry, ("guid", "id")) or link
        published = _xml_text(
            entry,
            ("pubdate", "published", "updated"),
        )
        candidates.append(
            SourceCandidate(
                adapter=adapter,
                external_id=external_id,
                title=title,
                url=canonicalize_url(link),
                published_at=_normalized_date(published),
                publisher=publisher,
            )
        )
        if len(candidates) >= limit:
            break
    return tuple(candidates)


class RSSDiscoveryAdapter:
    def __init__(
        self,
        feed_url: str,
        *,
        allowed_hosts: frozenset[str],
        publisher: str,
        limit: int = DEFAULT_DISCOVERY_LIMIT,
        fetcher: TextFetcher = fetch_text,
    ) -> None:
        self.feed_url = canonicalize_url(feed_url)
        if not allowed_hosts or not _host_allowed(self.feed_url, allowed_hosts):
            raise ValueError("RSS feed host must be in the explicit allowlist")
        self.allowed_hosts = allowed_hosts
        self.publisher = publisher
        self.limit = _bounded_limit(limit)
        self.fetcher = fetcher

    def discover(self) -> tuple[SourceCandidate, ...]:
        content = self.fetcher(
            self.feed_url,
            headers={"User-Agent": "AI-Research-OS/0.2 bounded-rss-discovery"},
            allowed_hosts=self.allowed_hosts,
            max_bytes=DEFAULT_RESPONSE_LIMIT,
        )
        return parse_feed(
            content,
            adapter="rss",
            publisher=self.publisher,
            allowed_hosts=self.allowed_hosts,
            limit=self.limit,
        )


class GitHubReleaseDiscoveryAdapter:
    def __init__(
        self,
        repository: str,
        *,
        limit: int = DEFAULT_DISCOVERY_LIMIT,
        fetcher: TextFetcher = fetch_text,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GitHub repository must be OWNER/REPO")
        self.repository = repository
        self.limit = _bounded_limit(limit)
        self.fetcher = fetcher

    def discover(self) -> tuple[SourceCandidate, ...]:
        api_url = (
            f"https://api.github.com/repos/{self.repository}/releases"
            f"?per_page={self.limit}"
        )
        content = self.fetcher(
            api_url,
            headers={
                "User-Agent": "AI-Research-OS/0.2 bounded-github-discovery",
                "Accept": "application/vnd.github+json",
            },
            allowed_hosts=frozenset({"api.github.com"}),
            max_bytes=DEFAULT_RESPONSE_LIMIT,
        )
        payload = json.loads(content)
        if not isinstance(payload, list):
            raise ValueError("GitHub releases response must be a list")
        candidates: list[SourceCandidate] = []
        for release in payload[: self.limit]:
            if not isinstance(release, dict):
                continue
            url = str(release.get("html_url", ""))
            tag = str(release.get("tag_name", ""))
            if not url or not tag or not _host_allowed(url, frozenset({"github.com"})):
                continue
            candidates.append(
                SourceCandidate(
                    adapter="github_release",
                    external_id=str(release.get("id", tag)),
                    title=str(release.get("name") or tag),
                    url=canonicalize_url(url),
                    published_at=_normalized_date(str(release.get("published_at", ""))),
                    publisher=self.repository,
                    metadata={"repository": self.repository, "tag": tag},
                )
            )
        return tuple(candidates)


class ArxivDiscoveryAdapter:
    def __init__(
        self,
        query: str,
        *,
        limit: int = DEFAULT_DISCOVERY_LIMIT,
        fetcher: TextFetcher = fetch_text,
    ) -> None:
        if not query.strip():
            raise ValueError("arXiv query must be explicit and non-empty")
        self.query = query.strip()
        self.limit = _bounded_limit(limit)
        self.fetcher = fetcher

    def discover(self) -> tuple[SourceCandidate, ...]:
        query = urlencode(
            {
                "search_query": self.query,
                "start": 0,
                "max_results": self.limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        url = f"https://export.arxiv.org/api/query?{query}"
        content = self.fetcher(
            url,
            headers={"User-Agent": "AI-Research-OS/0.2 bounded-arxiv-discovery"},
            allowed_hosts=frozenset({"arxiv.org", "export.arxiv.org"}),
            max_bytes=DEFAULT_RESPONSE_LIMIT,
        )
        return parse_feed(
            content,
            adapter="arxiv",
            publisher="arXiv",
            allowed_hosts=frozenset({"arxiv.org", "export.arxiv.org"}),
            limit=self.limit,
        )


class SECDiscoveryAdapter:
    def __init__(
        self,
        cik: str,
        *,
        forms: frozenset[str],
        user_agent: str,
        limit: int = DEFAULT_DISCOVERY_LIMIT,
        fetcher: TextFetcher = fetch_text,
    ) -> None:
        digits = re.sub(r"\D", "", cik)
        if not 1 <= len(digits) <= 10:
            raise ValueError("SEC CIK must contain 1 to 10 digits")
        if not forms:
            raise ValueError("SEC forms allowlist must be explicit")
        if not user_agent.strip():
            raise ValueError("SEC user agent/contact is required")
        self.cik = digits.zfill(10)
        self.forms = frozenset(value.upper() for value in forms)
        self.user_agent = user_agent.strip()
        self.limit = _bounded_limit(limit)
        self.fetcher = fetcher

    def discover(self) -> tuple[SourceCandidate, ...]:
        api_url = f"https://data.sec.gov/submissions/CIK{self.cik}.json"
        content = self.fetcher(
            api_url,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            allowed_hosts=frozenset({"data.sec.gov", "www.sec.gov"}),
            max_bytes=DEFAULT_RESPONSE_LIMIT,
        )
        payload = json.loads(content)
        recent = payload.get("filings", {}).get("recent", {})
        columns = {
            key: recent.get(key, [])
            for key in (
                "accessionNumber",
                "filingDate",
                "form",
                "primaryDocument",
            )
        }
        candidates: list[SourceCandidate] = []
        for accession, filing_date, form, document in zip(
            columns["accessionNumber"],
            columns["filingDate"],
            columns["form"],
            columns["primaryDocument"],
            strict=False,
        ):
            normalized_form = str(form).upper()
            if normalized_form not in self.forms:
                continue
            accession_text = str(accession)
            accession_compact = accession_text.replace("-", "")
            cik_compact = str(int(self.cik))
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik_compact}/"
                f"{accession_compact}/{quote(str(document))}"
            )
            candidates.append(
                SourceCandidate(
                    adapter="sec",
                    external_id=accession_text,
                    title=f"{normalized_form} filing {filing_date}",
                    url=canonicalize_url(url),
                    published_at=_normalized_date(str(filing_date)),
                    publisher=str(payload.get("name") or f"CIK {self.cik}"),
                    metadata={"cik": self.cik, "form": normalized_form},
                )
            )
            if len(candidates) >= self.limit:
                break
        return tuple(candidates)


class CompositeDiscoveryAdapter:
    """Iterate several bounded adapters, capping total results at ``limit``.

    A per-target failure is skipped so one bad repo/CIK does not kill the
    channel; if every target fails the first error is raised so the channel
    run records a clear failure rather than silently returning nothing.
    """

    def __init__(
        self,
        adapters: list[Any],
        *,
        limit: int = DEFAULT_DISCOVERY_LIMIT,
    ) -> None:
        if not adapters:
            raise ValueError("composite discovery requires at least one adapter")
        self.adapters = list(adapters)
        self.limit = _bounded_limit(limit)

    def discover(self) -> tuple[SourceCandidate, ...]:
        results: list[SourceCandidate] = []
        failures: list[Exception] = []
        for adapter in self.adapters:
            try:
                results.extend(adapter.discover())
            except Exception as exc:
                failures.append(exc)
            if len(results) >= self.limit:
                break
        if not results and failures:
            raise failures[0]
        return tuple(results[: self.limit])


def candidates_json(candidates: tuple[SourceCandidate, ...]) -> str:
    return (
        json.dumps(
            [
                {
                    "adapter": candidate.adapter,
                    "external_id": candidate.external_id,
                    "title": candidate.title,
                    "url": candidate.url,
                    "published_at": candidate.published_at,
                    "publisher": candidate.publisher,
                    "metadata": candidate.metadata,
                }
                for candidate in candidates
            ],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
