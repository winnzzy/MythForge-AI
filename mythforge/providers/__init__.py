"""
MythForge Provider SDK
======================

A generic, provider-agnostic SDK for LLM, Image, and Audio providers.

This package provides:

* **Provider interfaces** — Abstract base classes for LLM, Image, and Audio providers
* **Request/response models** — Typed dataclasses for all provider interactions
* **Provider registry** — Central registry with capability-based lookup
* **Provider factory** — Configuration-driven provider instantiation
* **Health checks** — Cached health monitoring with failure thresholds
* **Transaction recording** — Cost tracking and manifest integration
* **Retry framework** — Exponential backoff with jitter
* **Configuration** — YAML/JSON config loading with validation
* **Exceptions** — Typed exception hierarchy

Quick Start
-----------

1. Implement a provider::

    from mythforge.providers import (
        LLMProvider, ProviderCapability, LLMRequest, LLMResponse,
        HealthCheckResult, CostEstimate, ProviderConfig,
    )

    class MyLLM(LLMProvider):
        name = "my-llm"
        capabilities = [ProviderCapability.LLM]

        def __init__(self, config: ProviderConfig):
            self._config = config

        async def generate(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(text="Hello!", provider=self.name)

        async def stream(self, request):
            yield LLMStreamChunk(delta="Hello")

        async def health_check(self):
            return HealthCheckResult(provider=self.name, available=True)

        async def estimate_cost(self, operation, **kwargs):
            return CostEstimate(provider=self.name, operation=operation)

2. Register and use::

    from mythforge.providers import ProviderRegistry, ProviderSDKConfig

    config = ProviderSDKConfig()
    registry = ProviderRegistry(config=config)

    provider = MyLLM(config.get_provider("my-llm") or ProviderConfig(name="my-llm", type="llm"))
    await provider.initialise()
    registry.register(provider)

    llm = registry.get_llm()
    response = await llm.generate(LLMRequest(prompt="Hello"))
"""

# -- exceptions --
from .exceptions import (
    ProviderError,
    ProviderConfigError,
    ProviderNotAvailableError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderRegistrationError,
    MaxRetriesExceededError,
)

# -- models --
from .models import (
    ProviderCapability,
    ProviderStatus,
    TransactionStatus,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    ImageRequest,
    ImageEditRequest,
    ImageUpscaleRequest,
    ImageResponse,
    ImageAsset,
    NarrationRequest,
    MusicRequest,
    SFXRequest,
    AudioResponse,
    HealthCheckResult,
    Transaction,
    CostEstimate,
)

# -- interfaces --
from .interfaces import (
    BaseProvider,
    LLMProvider,
    ImageProvider,
    AudioProvider,
)

# -- retry --
from .retry import (
    RetryConfig,
    with_retry,
    RETRY_CONSERVATIVE,
    RETRY_AGGRESSIVE,
    RETRY_NONE,
)

# -- health --
from .health import (
    HealthCheckConfig,
    HealthCheckManager,
)

# -- transaction --
from .transaction import (
    ManifestHook,
    TransactionRecorder,
    TransactionContext,
)

# -- config --
from .config import (
    ProviderConfig,
    ProviderSDKConfig,
    ConfigLoader,
)

# -- registry --
from .registry import (
    ProviderFactory,
    ProviderRegistry,
)

__all__ = [
    # exceptions
    "ProviderError",
    "ProviderConfigError",
    "ProviderNotAvailableError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderRegistrationError",
    "MaxRetriesExceededError",
    # models
    "ProviderCapability",
    "ProviderStatus",
    "TransactionStatus",
    "LLMRequest",
    "LLMResponse",
    "LLMStreamChunk",
    "ImageRequest",
    "ImageEditRequest",
    "ImageUpscaleRequest",
    "ImageResponse",
    "ImageAsset",
    "NarrationRequest",
    "MusicRequest",
    "SFXRequest",
    "AudioResponse",
    "HealthCheckResult",
    "Transaction",
    "CostEstimate",
    # interfaces
    "BaseProvider",
    "LLMProvider",
    "ImageProvider",
    "AudioProvider",
    # retry
    "RetryConfig",
    "with_retry",
    "RETRY_CONSERVATIVE",
    "RETRY_AGGRESSIVE",
    "RETRY_NONE",
    # health
    "HealthCheckConfig",
    "HealthCheckManager",
    # transaction
    "ManifestHook",
    "TransactionRecorder",
    "TransactionContext",
    # config
    "ProviderConfig",
    "ProviderSDKConfig",
    "ConfigLoader",
    # registry
    "ProviderFactory",
    "ProviderRegistry",
]