"""llm-config: server-side LLM configuration persistence + desensitization.

The API key lives ONLY on the server filesystem, never in the browser,
localStorage, a URL or a log line. Persistence is a gitignored
``00_System/llm.local.json`` (covered by the ``*.local.json`` rule) with
0600 permissions. Public output is desensitized: ``public_config`` never
contains the key, only ``has_api_key`` + a masked ``key_masked``.

Editing an existing config with a blank key preserves the saved key; saving a
blank key with no saved key is refused.
"""

from __future__ import annotations

import json
import os
from contextlib import suppress
from datetime import date
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[3] / "00_System" / "llm.local.json"


def default_config() -> dict[str, Any]:
    return {"provider": "", "model": "", "api_key": "", "updated_at": ""}


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or CONFIG_PATH
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_config()
    if not isinstance(data, dict):
        return default_config()
    return {**default_config(), **{k: v for k, v in data.items() if v is not None}}


def save_config(
    path: Path | None = None,
    *,
    provider: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    """Persist the config. A blank ``api_key`` keeps the existing saved key."""
    path = path or CONFIG_PATH
    config = load_config(path)
    if api_key:
        config["api_key"] = api_key
    elif not config["api_key"]:
        raise ValueError("API key 是必填项（留空表示保留已有 Key）")
    config["provider"] = provider
    config["model"] = model
    config["updated_at"] = date.today().isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with suppress(OSError):
        path.chmod(0o600)
    return config


def mask_key(key: str) -> str:
    if not key:
        return "***"
    if len(key) <= 8:
        return "***" + key[-2:]
    return f"{key[:3]}***{key[-4:]}"


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    """Desensitized view — NEVER includes the api key value."""
    key = config.get("api_key", "") or ""
    return {
        "provider": config.get("provider", ""),
        "model": config.get("model", ""),
        "has_api_key": bool(key),
        "key_masked": mask_key(key),
        "updated_at": config.get("updated_at", ""),
    }


def get_api_key(path: Path | None = None, provider: str = "deepseek") -> str:
    """Resolve a provider's key: saved config first, then the env var."""
    config = load_config(path)
    if config.get("provider") == provider and config.get("api_key"):
        return str(config["api_key"])
    return os.environ.get(f"{provider.upper()}_API_KEY", "")
