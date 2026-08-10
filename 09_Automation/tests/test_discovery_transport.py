"""Transport policy tests for bounded discovery fetches."""

from __future__ import annotations

import socket
import ssl
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from email.message import Message
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from xml.etree import ElementTree

from research_os.adapters.discovery import (
    MAX_DISCOVERY_REDIRECTS,
    MAX_FETCH_ATTEMPTS,
    RETRIABLE_HTTP_STATUSES,
    DiscoveryTransportError,
    FetchTelemetry,
    RSSDiscoveryAdapter,
    fetch_text,
)


class _BytesResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> _BytesResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self.content[:size]


class _NonBytesResponse:
    def __enter__(self) -> _NonBytesResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> str:
        del size
        return "not bytes"


class _StaticOpener:
    def __init__(self, response: _BytesResponse) -> None:
        self.response = response
        self.opens = 0

    def open(self, request: object, timeout: float) -> _BytesResponse:
        del request, timeout
        self.opens += 1
        return self.response


class _OutcomeOpener:
    def __init__(self, outcome: _BytesResponse | _NonBytesResponse | Exception) -> None:
        self.outcome = outcome

    def open(
        self, request: object, timeout: float
    ) -> _BytesResponse | _NonBytesResponse:
        del request, timeout
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _opener_factory(
    outcomes: list[_BytesResponse | _NonBytesResponse | Exception],
) -> Iterator[_OutcomeOpener]:
    return iter(_OutcomeOpener(outcome) for outcome in outcomes)


def _opener_builder(
    openers: Iterator[_OutcomeOpener],
) -> Callable[[frozenset[str]], _OutcomeOpener]:
    def build(allowed_hosts: frozenset[str]) -> _OutcomeOpener:
        del allowed_hosts
        return next(openers)

    return build


def _http_error(
    status: int,
    *,
    retry_after: str | None = None,
    secret: str = "not-sensitive",
) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(
        f"https://example.com/feed?token={secret}",
        status,
        f"response body {secret}",
        headers,
        None,
    )


class _RedirectServerHandler(BaseHTTPRequestHandler):
    requested_paths: list[str] = []

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        self.requested_paths.append(path)
        if path == "/allowed":
            self._redirect("/final")
            return
        if path == "/cross-host":
            port = self.server.server_address[1]
            self._redirect(f"http://localhost:{port}/forbidden?token=secret")
            return
        if path == "/invalid-scheme":
            self._redirect("file:///tmp/discovery-secret")
            return
        if path.startswith("/chain/"):
            remaining = int(path.rsplit("/", 1)[-1])
            if remaining:
                self._redirect(f"/chain/{remaining - 1}")
                return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@contextmanager
def _redirect_server() -> Iterator[str]:
    _RedirectServerHandler.requested_paths = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RedirectServerHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class DiscoveryTransportContractTests(unittest.TestCase):
    def test_public_retry_contract_is_stable(self) -> None:
        self.assertEqual(3, MAX_FETCH_ATTEMPTS)
        self.assertEqual(5, MAX_DISCOVERY_REDIRECTS)
        self.assertEqual(
            frozenset({408, 425, 429, 500, 502, 503, 504}),
            RETRIABLE_HTTP_STATUSES,
        )

    def test_immediate_success_records_one_attempt_without_sleep(self) -> None:
        opener = _StaticOpener(_BytesResponse(b"discovery text"))
        sleeps: list[float] = []
        telemetry = FetchTelemetry()

        with patch(
            "research_os.adapters.discovery._build_discovery_opener",
            return_value=opener,
        ):
            result = fetch_text(
                "https://example.com/feed",
                headers={"Authorization": "Bearer secret"},
                allowed_hosts=frozenset({"example.com"}),
                sleeper=sleeps.append,
                telemetry=telemetry,
            )

        self.assertEqual("discovery text", result)
        self.assertEqual(1, opener.opens)
        self.assertEqual([], sleeps)
        self.assertEqual(
            FetchTelemetry(attempts=1, retries=0, http_errors=0), telemetry
        )

    def test_approved_transient_network_failures_retry_then_succeed(self) -> None:
        transient_errors = {
            "tls_eof": URLError(
                ssl.SSLEOFError(ssl.SSL_ERROR_EOF, "unexpected TLS EOF")
            ),
            "tls_handshake_interruption": URLError(
                ssl.SSLError(ssl.SSL_ERROR_SSL, "UNEXPECTED_EOF_WHILE_READING")
            ),
            "connection_reset": URLError(ConnectionResetError("reset")),
            "timeout": URLError(TimeoutError("timed out")),
            "temporary_dns": URLError(
                socket.gaierror(socket.EAI_AGAIN, "temporary DNS failure")
            ),
        }
        for label, transient_error in transient_errors.items():
            with self.subTest(label=label):
                sleeps: list[float] = []
                telemetry = FetchTelemetry()
                openers = _opener_factory(
                    [transient_error, _BytesResponse(b"recovered")]
                )
                with patch(
                    "research_os.adapters.discovery._build_discovery_opener",
                    side_effect=_opener_builder(openers),
                ):
                    result = fetch_text(
                        "https://example.com/feed",
                        headers={},
                        allowed_hosts=frozenset({"example.com"}),
                        base_delay=0.25,
                        sleeper=sleeps.append,
                        jitter_source=lambda: 1.0,
                        telemetry=telemetry,
                    )

                self.assertEqual("recovered", result)
                self.assertEqual([0.25], sleeps)
                self.assertEqual(
                    FetchTelemetry(attempts=2, retries=1, http_errors=0),
                    telemetry,
                )

    def test_permanent_dns_and_certificate_failures_do_not_retry(self) -> None:
        terminal_errors = {
            "permanent_dns": URLError(
                socket.gaierror(socket.EAI_NONAME, "host not found")
            ),
            "certificate": URLError(
                ssl.SSLCertVerificationError(1, "certificate verify failed")
            ),
        }
        for expected_class, terminal_error in terminal_errors.items():
            with self.subTest(expected_class=expected_class):
                sleeps: list[float] = []
                telemetry = FetchTelemetry()
                openers = _opener_factory([terminal_error])
                with (
                    patch(
                        "research_os.adapters.discovery._build_discovery_opener",
                        side_effect=_opener_builder(openers),
                    ),
                    self.assertRaises(DiscoveryTransportError) as caught,
                ):
                    fetch_text(
                        "https://example.com/feed",
                        headers={},
                        allowed_hosts=frozenset({"example.com"}),
                        sleeper=sleeps.append,
                        telemetry=telemetry,
                    )

                self.assertEqual(expected_class, caught.exception.failure_class)
                self.assertEqual(1, caught.exception.attempts)
                self.assertEqual([], sleeps)
                self.assertEqual(1, telemetry.attempts)
                self.assertEqual(0, telemetry.retries)

    def test_exhaustion_reports_only_safe_failure_class_and_attempt_count(self) -> None:
        secret = "top-secret-token"
        transient_error = URLError(
            socket.gaierror(socket.EAI_AGAIN, f"DNS body {secret}")
        )
        openers = _opener_factory([transient_error, transient_error, transient_error])
        sleeps: list[float] = []
        telemetry = FetchTelemetry()

        with (
            patch(
                "research_os.adapters.discovery._build_discovery_opener",
                side_effect=_opener_builder(openers),
            ),
            self.assertRaises(DiscoveryTransportError) as caught,
        ):
            fetch_text(
                f"https://example.com/feed?token={secret}",
                headers={"Authorization": f"Bearer {secret}"},
                allowed_hosts=frozenset({"example.com"}),
                base_delay=0.5,
                sleeper=sleeps.append,
                jitter_source=lambda: 1.0,
                telemetry=telemetry,
            )

        self.assertEqual("temporary_dns", caught.exception.failure_class)
        self.assertEqual(3, caught.exception.attempts)
        self.assertEqual("temporary_dns after 3 attempts", str(caught.exception))
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn("example.com", str(caught.exception))
        self.assertEqual([0.5, 1.0], sleeps)
        self.assertEqual(
            FetchTelemetry(attempts=3, retries=2, http_errors=0), telemetry
        )

    def test_http_status_matrix_retries_only_approved_statuses(self) -> None:
        for status in RETRIABLE_HTTP_STATUSES:
            with self.subTest(status=status, retriable=True):
                sleeps: list[float] = []
                telemetry = FetchTelemetry()
                openers = _opener_factory(
                    [_http_error(status), _BytesResponse(b"recovered")]
                )
                with patch(
                    "research_os.adapters.discovery._build_discovery_opener",
                    side_effect=_opener_builder(openers),
                ):
                    result = fetch_text(
                        "https://example.com/feed",
                        headers={},
                        allowed_hosts=frozenset({"example.com"}),
                        sleeper=sleeps.append,
                        jitter_source=lambda: 1.0,
                        telemetry=telemetry,
                    )
                self.assertEqual("recovered", result)
                self.assertEqual([0.5], sleeps)
                self.assertEqual(2, telemetry.attempts)
                self.assertEqual(1, telemetry.retries)
                self.assertEqual(1, telemetry.http_errors)

        for status in (400, 401, 403, 404, 409, 501):
            with self.subTest(status=status, retriable=False):
                secret = "response-secret"
                sleeps = []
                telemetry = FetchTelemetry()
                openers = _opener_factory([_http_error(status, secret=secret)])
                with (
                    patch(
                        "research_os.adapters.discovery._build_discovery_opener",
                        side_effect=_opener_builder(openers),
                    ),
                    self.assertRaises(DiscoveryTransportError) as caught,
                ):
                    fetch_text(
                        f"https://example.com/feed?token={secret}",
                        headers={"Cookie": f"session={secret}"},
                        allowed_hosts=frozenset({"example.com"}),
                        sleeper=sleeps.append,
                        telemetry=telemetry,
                    )
                self.assertEqual(f"http_{status}", caught.exception.failure_class)
                self.assertEqual(1, caught.exception.attempts)
                self.assertNotIn(secret, str(caught.exception))
                self.assertEqual([], sleeps)
                self.assertEqual(1, telemetry.http_errors)

    def test_retry_after_seconds_and_http_date_take_priority_with_cap(self) -> None:
        now = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
        cases = {
            "seconds": ("3", 3.0),
            "seconds_capped": ("30", 8.0),
            "http_date": (
                format_datetime(now + timedelta(seconds=6), usegmt=True),
                6.0,
            ),
            "http_date_capped": (
                format_datetime(now + timedelta(seconds=30), usegmt=True),
                8.0,
            ),
        }
        for label, (header, expected_delay) in cases.items():
            with self.subTest(label=label):
                sleeps: list[float] = []
                openers = _opener_factory(
                    [_http_error(429, retry_after=header), _BytesResponse(b"ok")]
                )
                with (
                    patch(
                        "research_os.adapters.discovery._build_discovery_opener",
                        side_effect=_opener_builder(openers),
                    ),
                    patch("research_os.adapters.discovery._utc_now", return_value=now),
                ):
                    fetch_text(
                        "https://example.com/feed",
                        headers={},
                        allowed_hosts=frozenset({"example.com"}),
                        base_delay=0.125,
                        sleeper=sleeps.append,
                        jitter_source=lambda: 0.01,
                    )
                self.assertEqual([expected_delay], sleeps)

    def test_invalid_and_past_retry_after_fall_back_to_jittered_backoff(self) -> None:
        now = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
        cases = {
            "invalid": "later",
            "negative": "-1",
            "past": format_datetime(now - timedelta(seconds=1), usegmt=True),
        }
        for label, header in cases.items():
            with self.subTest(label=label):
                sleeps: list[float] = []
                openers = _opener_factory(
                    [_http_error(503, retry_after=header), _BytesResponse(b"ok")]
                )
                with (
                    patch(
                        "research_os.adapters.discovery._build_discovery_opener",
                        side_effect=_opener_builder(openers),
                    ),
                    patch("research_os.adapters.discovery._utc_now", return_value=now),
                ):
                    fetch_text(
                        "https://example.com/feed",
                        headers={},
                        allowed_hosts=frozenset({"example.com"}),
                        base_delay=2.0,
                        sleeper=sleeps.append,
                        jitter_source=lambda: 0.25,
                    )
                self.assertEqual([0.5], sleeps)

    def test_exponential_backoff_applies_jitter_and_absolute_cap(self) -> None:
        transient = URLError(ConnectionResetError("reset"))
        openers = _opener_factory([transient, transient, _BytesResponse(b"recovered")])
        sleeps: list[float] = []
        with patch(
            "research_os.adapters.discovery._build_discovery_opener",
            side_effect=_opener_builder(openers),
        ):
            fetch_text(
                "https://example.com/feed",
                headers={},
                allowed_hosts=frozenset({"example.com"}),
                base_delay=10.0,
                max_delay=60.0,
                sleeper=sleeps.append,
                jitter_source=lambda: 0.5,
            )
        self.assertEqual([4.0, 4.0], sleeps)

    def test_initial_scheme_and_host_are_rejected_before_open(self) -> None:
        for url, allowed_hosts in (
            ("ftp://example.com/feed", frozenset({"example.com"})),
            ("https://blocked.example/feed", frozenset({"example.com"})),
            ("https:///missing-host", frozenset({"example.com"})),
            ("https://example.com/feed", frozenset()),
        ):
            with self.subTest(url=url, allowed_hosts=allowed_hosts):
                telemetry = FetchTelemetry()
                with (
                    patch(
                        "research_os.adapters.discovery._build_discovery_opener"
                    ) as build_opener,
                    self.assertRaises(DiscoveryTransportError) as caught,
                ):
                    fetch_text(
                        url,
                        headers={},
                        allowed_hosts=allowed_hosts,
                        telemetry=telemetry,
                    )
                self.assertEqual("policy", caught.exception.failure_class)
                self.assertEqual(0, caught.exception.attempts)
                self.assertEqual(FetchTelemetry(), telemetry)
                build_opener.assert_not_called()

    def test_retry_controls_enforce_global_bounds_before_open(self) -> None:
        invalid_options = (
            {"max_attempts": 0},
            {"max_attempts": MAX_FETCH_ATTEMPTS + 1},
            {"timeout": 0.0},
            {"base_delay": -0.1},
            {"max_delay": -0.1},
            {"max_bytes": 0},
        )
        for options in invalid_options:
            with self.subTest(options=options):
                with (
                    patch(
                        "research_os.adapters.discovery._build_discovery_opener"
                    ) as build_opener,
                    self.assertRaises(DiscoveryTransportError) as caught,
                ):
                    fetch_text(
                        "https://example.com/feed",
                        headers={},
                        allowed_hosts=frozenset({"example.com"}),
                        **options,
                    )
                self.assertEqual("policy", caught.exception.failure_class)
                self.assertEqual(0, caught.exception.attempts)
                build_opener.assert_not_called()

    def test_oversize_nonbytes_and_decode_failures_do_not_retry(self) -> None:
        cases = {
            "response_too_large": (_BytesResponse(b"1234"), 3),
            "response_type": (_NonBytesResponse(), 100),
            "decode": (_BytesResponse(b"\xff"), 100),
        }
        for expected_class, (response, max_bytes) in cases.items():
            with self.subTest(expected_class=expected_class):
                opener = _OutcomeOpener(response)
                telemetry = FetchTelemetry()
                sleeps: list[float] = []
                with (
                    patch(
                        "research_os.adapters.discovery._build_discovery_opener",
                        return_value=opener,
                    ) as build_opener,
                    self.assertRaises(DiscoveryTransportError) as caught,
                ):
                    fetch_text(
                        "https://example.com/feed?token=secret",
                        headers={"Authorization": "Bearer secret"},
                        allowed_hosts=frozenset({"example.com"}),
                        max_bytes=max_bytes,
                        sleeper=sleeps.append,
                        telemetry=telemetry,
                    )
                self.assertEqual(expected_class, caught.exception.failure_class)
                self.assertEqual(1, caught.exception.attempts)
                self.assertEqual(1, build_opener.call_count)
                self.assertEqual([], sleeps)
                self.assertEqual(
                    FetchTelemetry(attempts=1, retries=0, http_errors=0),
                    telemetry,
                )
                self.assertNotIn("secret", str(caught.exception))

    def test_allowlisted_redirect_is_followed(self) -> None:
        with _redirect_server() as base_url:
            telemetry = FetchTelemetry()
            result = fetch_text(
                f"{base_url}/allowed",
                headers={},
                allowed_hosts=frozenset({"127.0.0.1"}),
                telemetry=telemetry,
            )
        self.assertEqual("ok", result)
        self.assertEqual(["/allowed", "/final"], _RedirectServerHandler.requested_paths)
        self.assertEqual(FetchTelemetry(attempts=1), telemetry)

    def test_rejected_redirect_is_blocked_before_follow_without_retry(self) -> None:
        for endpoint in ("cross-host", "invalid-scheme"):
            with self.subTest(endpoint=endpoint), _redirect_server() as base_url:
                telemetry = FetchTelemetry()
                sleeps: list[float] = []
                with self.assertRaises(DiscoveryTransportError) as caught:
                    fetch_text(
                        f"{base_url}/{endpoint}?authorization=secret",
                        headers={"Authorization": "Bearer secret"},
                        allowed_hosts=frozenset({"127.0.0.1"}),
                        sleeper=sleeps.append,
                        telemetry=telemetry,
                    )
                self.assertEqual("redirect_policy", caught.exception.failure_class)
                self.assertEqual(1, caught.exception.attempts)
                self.assertEqual(
                    [f"/{endpoint}"], _RedirectServerHandler.requested_paths
                )
                self.assertEqual([], sleeps)
                self.assertEqual(FetchTelemetry(attempts=1), telemetry)
                self.assertNotIn("secret", str(caught.exception))

    def test_five_redirect_hops_are_allowed_and_sixth_is_blocked(self) -> None:
        with _redirect_server() as base_url:
            result = fetch_text(
                f"{base_url}/chain/{MAX_DISCOVERY_REDIRECTS}",
                headers={},
                allowed_hosts=frozenset({"127.0.0.1"}),
            )
        self.assertEqual("ok", result)
        self.assertEqual(
            [f"/chain/{remaining}" for remaining in range(5, -1, -1)],
            _RedirectServerHandler.requested_paths,
        )

        with _redirect_server() as base_url:
            telemetry = FetchTelemetry()
            with self.assertRaises(DiscoveryTransportError) as caught:
                fetch_text(
                    f"{base_url}/chain/{MAX_DISCOVERY_REDIRECTS + 1}",
                    headers={},
                    allowed_hosts=frozenset({"127.0.0.1"}),
                    telemetry=telemetry,
                )
        self.assertEqual("redirect_limit", caught.exception.failure_class)
        self.assertEqual(1, caught.exception.attempts)
        self.assertEqual(
            [f"/chain/{remaining}" for remaining in range(6, 0, -1)],
            _RedirectServerHandler.requested_paths,
        )
        self.assertEqual(FetchTelemetry(attempts=1), telemetry)

    def test_parse_failure_happens_after_one_fetch_without_transport_retry(
        self,
    ) -> None:
        opener = _StaticOpener(_BytesResponse(b"<not-closed>"))
        with (
            patch(
                "research_os.adapters.discovery._build_discovery_opener",
                return_value=opener,
            ) as build_opener,
            self.assertRaises(ElementTree.ParseError),
        ):
            RSSDiscoveryAdapter(
                "https://example.com/feed",
                allowed_hosts=frozenset({"example.com"}),
                publisher="Example",
            ).discover()
        self.assertEqual(1, opener.opens)
        self.assertEqual(1, build_opener.call_count)


if __name__ == "__main__":
    unittest.main()
