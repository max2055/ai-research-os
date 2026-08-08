"""model-fetch: server-side model list loading.

``fetch_models`` proxies the provider's GET /models with a Bearer key (the key
travels client→server once in a POST body, then only server-side; it is never
echoed back and never lands in an error message or log). Models are normalized
to ``{id, ownedBy}``, sorted by id, and grouped by ``ownedBy`` by the UI. The
model list is cached only for the page session — persistence stores just the
selected model.
"""

from __future__ import annotations

from research_os.llm import _http

# Re-exported for callers/tests; internal calls go through ``_http`` so the
# low-level ``http_request`` stays patchable.
LLMError = _http.LLMError


def fetch_models(
    *,
    base_url: str,
    key: str,
    timeout: float,
) -> list[dict[str, str]]:
    """Return ``[{id, ownedBy}, ...]`` sorted by id, or raise ``LLMError``."""
    url = base_url.rstrip("/") + "/models"
    try:
        status, body = _http.http_request(
            "GET",
            url,
            {"Authorization": f"Bearer {key}", "Accept": "application/json"},
            None,
            timeout,
        )
    except TimeoutError as exc:
        raise _http.LLMError("timeout", "模型接口请求超时") from exc
    _http.raise_on_status(status, "models")
    data = _http.json_decode(body, "models")
    raw = data.get("data") or []
    models: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        models.append(
            {
                "id": str(item["id"]),
                "ownedBy": str(
                    item.get("owned_by") or item.get("ownedBy") or "unknown"
                ),
            }
        )
    if not models:
        raise _http.LLMError("empty", "模型接口未返回任何模型")
    models.sort(key=lambda model: model["id"])
    return models
