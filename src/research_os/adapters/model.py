"""D-008 model adapter interface (RCP-v03-007, Phase 4 §5/§10).

Provider-independent boundary between the Analysis Run pipeline and whatever
model executes the versioned prompt. An adapter must:

- accept a rendered prompt and a ``timeout`` and return the raw model output as
  a string, raising ``TimeoutError`` if the provider exceeds the timeout;
- be deterministically instantiable so a dry-run never makes a real provider
  call (Phase 4 §10 "timeout/provider failure", "retry 不创建重复 Run").

``build_adapter`` resolves a provider name to an adapter. Only the deterministic
``echo`` provider is registered today; real providers (Anthropic/OpenAI/…) are a
later integration and must conform to the same Protocol so the runner is
provider-independent.
"""

from __future__ import annotations

from typing import Protocol


class ModelAdapter(Protocol):
    """A model provider call boundary."""

    def generate(self, prompt: str, *, timeout: float | None = None) -> str:
        """Return raw model output; raise TimeoutError on provider timeout."""
        ...


class EchoAdapter:
    """Deterministic no-op adapter: returns the prompt verbatim.

    Used for dry-runs and tests. Because it never makes a network call it also
    never times out, so a retry cannot create a duplicate Run.
    """

    provider = "echo"

    def generate(self, prompt: str, *, timeout: float | None = None) -> str:
        del timeout
        return prompt


class UnknownProvider(ValueError):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"unknown model provider {provider!r}")


MODEL_ADAPTERS: dict[str, type[ModelAdapter]] = {
    EchoAdapter.provider: EchoAdapter,
}


def build_adapter(provider: str) -> ModelAdapter:
    adapter_type = MODEL_ADAPTERS.get(provider)
    if adapter_type is None:
        raise UnknownProvider(provider)
    return adapter_type()
