"""provider-catalog: structured provider presets.

The user never hand-fills Base URL / API protocol / token caps — each provider
is a frozen preset. Adding a provider is one catalog entry; the UI, model
fetch, adapter and config all read from here. DeepSeek first; the catalog is
kept deliberately lean (no CC-Switch mega-catalog, sponsors, speedtest or
proxy management).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    name: str
    base_url: str
    # API protocol, decided by the preset — never guessed from a failed call.
    api_format: str  # "openai_chat" | "openai_responses"
    api_key_url: str
    default_params: dict[str, object] = field(default_factory=dict)
    recommended_models: list[str] = field(default_factory=list)
    default_model: str = ""
    timeout: float = 120.0
    models_endpoint: str = "/models"


PROVIDER_CATALOG: list[ProviderPreset] = [
    ProviderPreset(
        id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com",
        api_format="openai_chat",
        api_key_url="https://platform.deepseek.com/api_keys",
        default_params={"max_tokens": 4096, "temperature": 0.3},
        recommended_models=["deepseek-chat", "deepseek-reasoner"],
        default_model="deepseek-chat",
        timeout=120.0,
    ),
]

_PRESETS = {preset.id: preset for preset in PROVIDER_CATALOG}


def get_preset(provider_id: str) -> ProviderPreset:
    preset = _PRESETS.get(provider_id)
    if preset is None:
        raise ValueError(f"unknown model provider {provider_id!r}")
    return preset
