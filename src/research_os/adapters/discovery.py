"""Bounded discovery adapters for explicitly configured research sources."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from research_os.adapters.url import canonicalize_url

DEFAULT_DISCOVERY_LIMIT = 20
MAX_DISCOVERY_LIMIT = 100
DEFAULT_RESPONSE_LIMIT = 5 * 1024 * 1024


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
        max_bytes: int,
    ) -> str: ...


def fetch_text(
    url: str,
    *,
    headers: dict[str, str],
    max_bytes: int = DEFAULT_RESPONSE_LIMIT,
) -> str:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:  # noqa: S310
        content = response.read(max_bytes + 1)
    if not isinstance(content, bytes):
        raise TypeError("discovery response must be bytes")
    if len(content) > max_bytes:
        raise ValueError(f"discovery response exceeds {max_bytes} byte limit")
    return content.decode("utf-8", errors="replace")


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
