"""llm-adapter: build provider requests and parse provider responses.

The API protocol is decided by the provider preset (``openai_chat`` or
``openai_responses``) — never guessed from a failed call. The two protocols use
different endpoints, request bodies and parsers:

- ``openai_chat``      → POST {base_url}/chat/completions, ``messages`` body,
  parse ``choices[].message.content``;
- ``openai_responses`` → POST {base_url}/responses, ``input``/``instructions``/
  ``max_output_tokens`` body, parse ``output[]``/``output_text``.

DeepSeek compatibility: a Chat Completions success may carry
``message.content: null`` with the reasoning in ``reasoning_content``. That is a
VALID success envelope (used by test-connection); it is not misread as an error.
Reasoning models may spend the whole budget on reasoning, so test-connection
uses a reasonable ``max_tokens`` instead of squeezing it to a tiny value.
"""

from __future__ import annotations

import json
import time
from typing import Any

from research_os.llm import _http

# Re-exported for callers/tests; internal calls go through ``_http`` so the
# low-level ``http_request`` stays patchable.
LLMError = _http.LLMError

_PROBE_PROMPT = "Reply with exactly: OK"


def build_chat_request(
    *,
    base_url: str,
    model: str,
    prompt: str,
    params: dict[str, object],
    key: str,
) -> dict[str, Any]:
    body: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    body.update(params)
    return {
        "url": base_url.rstrip("/") + "/chat/completions",
        "headers": {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def build_responses_request(
    *,
    base_url: str,
    model: str,
    prompt: str,
    params: dict[str, object],
    key: str,
) -> dict[str, Any]:
    body: dict[str, object] = {"model": model, "input": prompt}
    body.update(params)
    return {
        "url": base_url.rstrip("/") + "/responses",
        "headers": {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def parse_chat_response(data: dict[str, Any]) -> tuple[str, bool]:
    """Parse a Chat Completions envelope -> ``(text, ok)``.

    ``ok`` reflects envelope validity, NOT non-empty content: a response with
    ``content: null`` and ``reasoning_content`` present is a valid success.
    """
    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise _http.LLMError(
            "invalid_response", "Chat Completions 响应缺少 choices"
        )
    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        return "", True
    return str(content), True


def parse_responses_response(data: dict[str, Any]) -> tuple[str, bool]:
    """Parse a Responses API envelope -> ``(text, ok)`` from output[]/output_text."""
    output = data.get("output") or []
    text_parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for block in item.get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "output_text":
                    text_parts.append(str(block.get("text", "")))
    if not text_parts:
        raise _http.LLMError("invalid_response", "Responses 响应缺少 output_text")
    return "\n".join(text_parts), True


def chat_completion(
    *,
    base_url: str,
    key: str,
    model: str,
    prompt: str,
    params: dict[str, object],
    timeout: float,
) -> str:
    request = build_chat_request(
        base_url=base_url, model=model, prompt=prompt, params=params, key=key
    )
    try:
        status, body = _http.http_request(
            "POST", request["url"], request["headers"], request["body"], timeout
        )
    except TimeoutError as exc:
        raise _http.LLMError("timeout", "供应商请求超时") from exc
    _http.raise_on_status(status, "chat completions")
    data = _http.json_decode(body, "chat completions")
    text, _ = parse_chat_response(data)
    return text


def responses_completion(
    *,
    base_url: str,
    key: str,
    model: str,
    prompt: str,
    params: dict[str, object],
    timeout: float,
) -> str:
    request = build_responses_request(
        base_url=base_url, model=model, prompt=prompt, params=params, key=key
    )
    try:
        status, body = _http.http_request(
            "POST", request["url"], request["headers"], request["body"], timeout
        )
    except TimeoutError as exc:
        raise _http.LLMError("timeout", "供应商请求超时") from exc
    _http.raise_on_status(status, "responses")
    data = _http.json_decode(body, "responses")
    text, _ = parse_responses_response(data)
    return text


def test_connection(
    *,
    base_url: str,
    api_format: str,
    key: str,
    model: str,
    timeout: float,
) -> dict[str, Any]:
    """Connectivity probe. Returns ``{ok, latency_ms, message}`` — never raises,
    never echoes the key, and does NOT require non-empty content (reasoning-only
    responses still prove the connection)."""
    started = time.monotonic()
    try:
        params: dict[str, object] = {"max_tokens": 4096}
        if api_format == "openai_responses":
            responses_completion(
                base_url=base_url,
                key=key,
                model=model,
                prompt=_PROBE_PROMPT,
                params=params,
                timeout=timeout,
            )
        else:
            chat_completion(
                base_url=base_url,
                key=key,
                model=model,
                prompt=_PROBE_PROMPT,
                params=params,
                timeout=timeout,
            )
        return {
            "ok": True,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "message": "连接成功",
        }
    except _http.LLMError as exc:
        return {
            "ok": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "message": _HUMAN_ERRORS.get(exc.error_type, exc.args[0]),
        }
    except TimeoutError:
        return {
            "ok": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "message": "连接超时",
        }
    except Exception as exc:  # noqa: BLE001 — boundary: never leak internals
        return {
            "ok": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "message": f"连接失败：{type(exc).__name__}",
        }


_HUMAN_ERRORS = {
    "auth": "认证失败：API Key 无效或已过期",
    "not_found": "接口不存在（404）",
    "rate_limited": "请求过于频繁，请稍后重试（429）",
    "server_error": "供应商服务暂时不可用",
    "timeout": "连接超时",
    "invalid_response": "供应商返回了无法解析的响应",
    "empty": "供应商返回为空",
}
