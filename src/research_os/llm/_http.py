"""Shared low-level HTTP + LLM error type for provider integrations.

``http_request`` is the single place that touches the network so the protocol
modules are trivially testable and the API key never appears in an exception
or a returned body (the Authorization header is never echoed back).
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(ValueError):
    """A provider interaction failed; ``error_type`` classifies it accurately.

    error_type values: auth / not_found / rate_limited / server_error /
    timeout / invalid_response / empty.
    """

    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type


def http_request(
    method: str,
    url: str,
    headers: dict[str, str] | None,
    body: str | bytes | None,
    timeout: float,
) -> tuple[int, bytes]:
    """Perform one request; return ``(status, body_bytes)``.

    Raises ``TimeoutError`` when the provider exceeds ``timeout``. HTTP error
    statuses are returned as ``(status, body)`` — callers map them via
    ``raise_on_status`` so the raw body (which may embed the request) is never
    propagated to logs or clients.
    """
    data = body.encode("utf-8") if isinstance(body, str) else body
    request = Request(
        url, data=data, headers=dict(headers or {}), method=method
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
            raise TimeoutError(f"request to {url} timed out") from exc
        raise LLMError(
            "server_error", f"network error talking to provider: {exc}"
        ) from exc


def raise_on_status(status: int, context: str) -> None:
    """Map an HTTP status to an accurate LLMError (never leaks the body)."""
    if status in (401, 403):
        raise LLMError("auth", "认证失败：API Key 无效或已过期")
    if status == 404:
        raise LLMError("not_found", f"{context} 接口不存在（404）")
    if status == 429:
        raise LLMError("rate_limited", "请求过于频繁，请稍后重试（429）")
    if status >= 500:
        raise LLMError("server_error", "供应商服务暂时不可用，请稍后重试")
    if status >= 400:
        raise LLMError("invalid_response", f"供应商返回 HTTP {status}")


def json_decode(body: bytes, context: str) -> dict[str, Any]:
    try:
        data = json.loads(body)
    except (ValueError, TypeError) as exc:
        raise LLMError("invalid_response", f"{context} 返回了非法 JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("invalid_response", f"{context} 返回结构非法")
    return data
