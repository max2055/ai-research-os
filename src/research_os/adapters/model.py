"""D-008 model adapter interface (RCP-v03-007, Phase 4 §5/§10).

Provider-independent boundary between the Analysis Run pipeline and whatever
model executes the versioned prompt. An adapter must:

- accept a rendered prompt and a ``timeout`` and return the raw model output as
  a string, raising ``TimeoutError`` if the provider exceeds the timeout;
- accept ``model_id`` / ``model_parameters`` so the frozen run records the
  model that was ACTUALLY called (reproducibility, Phase 4 §3);
- be deterministically instantiable so a dry-run never makes a real provider
  call (Phase 4 §10 "timeout/provider failure", "retry 不创建重复 Run").

``build_adapter`` resolves a provider name to an adapter. ``echo`` is the
deterministic no-op (dry-runs/tests); ``deepseek`` is the first real provider
(D-008 later integration) — its key comes from the server-side llm-config store
or the ``DEEPSEEK_API_KEY`` env var, and its request/response handling lives in
``research_os.llm`` so the runner stays provider-independent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, cast

from research_os.llm import llm_adapter, llm_config, provider_catalog


class ModelAdapter(Protocol):
    """A model provider call boundary."""

    def generate(
        self,
        prompt: str,
        *,
        timeout: float | None = None,
        model_id: str | None = None,
        model_parameters: dict[str, Any] | None = None,
    ) -> str:
        """Return raw model output; raise TimeoutError on provider timeout."""
        ...


class EchoAdapter:
    """Deterministic no-op adapter: returns the prompt verbatim.

    Used for dry-runs and tests. Because it never makes a network call it also
    never times out, so a retry cannot create a duplicate Run.
    """

    provider = "echo"

    def generate(
        self,
        prompt: str,
        *,
        timeout: float | None = None,
        model_id: str | None = None,
        model_parameters: dict[str, Any] | None = None,
    ) -> str:
        del timeout, model_id, model_parameters
        return prompt


class DeepSeekAdapter:
    """Real provider: DeepSeek Chat Completions (openai_chat).

    The adapter is bound to the DeepSeek preset (base_url / api_format /
    timeout / default params) and resolves the API key at call time from the
    server-side llm-config store (or ``DEEPSEEK_API_KEY``). A transient key for
    dashboard "test connection" flows is injected directly via ``key=`` and
    never persisted by this adapter.
    """

    provider = "deepseek"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_format: str | None = None,
        key: str | None = None,
        config_path: Path | None = None,
        timeout: float | None = None,
    ) -> None:
        preset = provider_catalog.get_preset("deepseek")
        self.base_url = base_url or preset.base_url
        self.api_format = api_format or preset.api_format
        self.key = key
        self.config_path = config_path
        self.timeout = timeout or preset.timeout
        self._default_model = preset.default_model
        self._default_params = dict(preset.default_params)

    def generate(
        self,
        prompt: str,
        *,
        timeout: float | None = None,
        model_id: str | None = None,
        model_parameters: dict[str, Any] | None = None,
    ) -> str:
        key = self.key or llm_config.get_api_key(self.config_path, provider="deepseek")
        if not key:
            raise ValueError(
                "DeepSeek API key is not configured. Save it in the /llm "
                "dashboard, write 00_System/llm.local.json, or set "
                "DEEPSEEK_API_KEY."
            )
        model = model_id or self._default_model
        params: dict[str, object] = {
            **self._default_params,
            **(model_parameters or {}),
        }
        if self.api_format == "openai_responses":
            return llm_adapter.responses_completion(
                base_url=self.base_url,
                key=key,
                model=model,
                prompt=prompt,
                params=params,
                timeout=timeout or self.timeout,
            )
        return llm_adapter.chat_completion(
            base_url=self.base_url,
            key=key,
            model=model,
            prompt=prompt,
            params=params,
            timeout=timeout or self.timeout,
        )


class UnknownProvider(ValueError):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"unknown model provider {provider!r}")


MODEL_ADAPTERS: dict[str, type[Any]] = {
    EchoAdapter.provider: EchoAdapter,
    DeepSeekAdapter.provider: DeepSeekAdapter,
}


def build_adapter(provider: str, *, config_path: Path | None = None) -> ModelAdapter:
    adapter_type = MODEL_ADAPTERS.get(provider)
    if adapter_type is None:
        raise UnknownProvider(provider)
    if adapter_type is DeepSeekAdapter:
        return cast(ModelAdapter, adapter_type(config_path=config_path))
    return cast(ModelAdapter, adapter_type())
