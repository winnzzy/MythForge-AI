# Provider SDK

A generic, provider-agnostic SDK for integrating LLM, Image, and Audio providers into MythForge.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Provider SDK                              │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ LLM      │  │ Image    │  │ Audio    │  │ Future   │        │
│  │ Providers │  │ Providers│  │ Providers│  │ Providers│        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │              │              │              │              │
│  ┌────┴──────────────┴──────────────┴──────────────┴─────┐       │
│  │              Provider Interfaces (ABCs)                │       │
│  │        LLMProvider  ImageProvider  AudioProvider       │       │
│  └────────────────────────┬──────────────────────────────┘       │
│                           │                                      │
│  ┌────────────────────────┴──────────────────────────────┐       │
│  │                 Provider Registry                      │       │
│  │         register / get / get_by_capability            │       │
│  │              health / retry / transactions             │       │
│  └───┬──────────┬──────────┬──────────┬─────────────────┘       │
│      │          │          │          │                          │
│  ┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐                      │
│  │Config │ │Health │ │Retry  │ │Txn    │                      │
│  │Loader │ │Checks │ │Config │ │Record │                      │
│  └───────┘ └───────┘ └───────┘ └───┬───┘                      │
│                                     │                           │
│  ┌──────────────────────────────────┴────────────────────┐      │
│  │               Manifest Bridge                          │      │
│  │         Transactions → CostRecord / ProviderRecord     │      │
│  └──────────────────────────┬────────────────────────────┘      │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Manifest Engine   │
                    │  (schema + engine)  │
                    └─────────────────────┘
```

## Package Structure

```
mythforge/providers/
├── __init__.py          # Public API — all exports
├── exceptions.py        # Typed exception hierarchy
├── models.py            # Request/response dataclasses
├── interfaces.py        # Abstract base classes (LLM, Image, Audio)
├── retry.py             # Exponential backoff with jitter
├── health.py            # Cached health check manager
├── transaction.py       # Transaction recorder + manifest hooks
├── config.py            # YAML/JSON config loader + validation
├── registry.py          # Provider registry + factory
└── manifest_hooks.py    # Manifest Engine integration bridge
```

## Quick Start

### 1. Implement a Provider

```python
from mythforge.providers import (
    LLMProvider, ProviderCapability, ProviderConfig,
    LLMRequest, LLMResponse, LLMStreamChunk,
    HealthCheckResult, CostEstimate,
)


class GeminiLLM(LLMProvider):
    """Gemini LLM provider implementation."""

    name = "gemini"
    capabilities = [ProviderCapability.LLM]

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._client = None

    async def initialise(self) -> None:
        import google.generativeai as genai
        import os
        api_key = os.environ.get(self._config.api_key_env or "GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(self._config.model or "gemini-2.0-flash")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        response = await self._client.generate_content_async(request.prompt)
        return LLMResponse(
            text=response.text,
            provider=self.name,
            model=self._config.model or "gemini-2.0-flash",
            tokens_in=response.usage_metadata.prompt_token_count,
            tokens_out=response.usage_metadata.candidates_token_count,
        )

    async def stream(self, request: LLMRequest):
        async for chunk in self._client.generate_content_async(
            request.prompt, stream=True
        ):
            if chunk.text:
                yield LLMStreamChunk(delta=chunk.text)

    async def health_check(self) -> HealthCheckResult:
        try:
            import time
            start = time.monotonic()
            await self._client.generate_content_async("ping")
            latency = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                provider=self.name, available=True, latency_ms=latency
            )
        except Exception as exc:
            return HealthCheckResult(
                provider=self.name, available=False, error=str(exc)
            )

    async def estimate_cost(self, operation: str, **kwargs) -> CostEstimate:
        prompt_tokens = kwargs.get("prompt_tokens", 0)
        cost_per_1k = 0.00015  # Gemini Flash pricing
        return CostEstimate(
            provider=self.name,
            operation=operation,
            estimated_cost_usd=(prompt_tokens / 1000) * cost_per_1k,
        )

    async def shutdown(self) -> None:
        self._client = None
```

### 2. Configure Providers

```yaml
# config/providers.yaml
providers:
  - name: gemini
    type: llm
    primary: true
    enabled: true
    model: gemini-2.0-flash
    api_key_env: GEMINI_API_KEY
    timeout_s: 30
    retry:
      max_retries: 3
      base_delay_s: 1.0
      backoff_factor: 2.0
      jitter: true

  - name: openai-fallback
    type: llm
    enabled: true
    priority: 1
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY

  - name: flux
    type: image
    primary: true
    enabled: true
    model: flux-1.1-pro
    api_key_env: BFL_API_KEY

  - name: elevenlabs
    type: audio
    primary: true
    enabled: true
    api_key_env: ELEVENLABS_API_KEY

default_timeout_s: 60
fallback_enabled: true
health_check_interval_s: 300
```

### 3. Wire Everything Together

```python
import asyncio
from mythforge.providers import (
    ProviderRegistry, ProviderSDKConfig, ConfigLoader, ProviderFactory,
)
from mythforge.providers.manifest_hooks import ManifestBridge
from mythforge.engine.engine import ManifestEngine


async def main():
    # Load configuration
    config = ConfigLoader.from_file("config/providers.yaml")

    # Create Manifest Engine + bridge
    engine = ManifestEngine("project_manifest.json")
    bridge = ManifestBridge(engine)

    # Create registry with manifest integration
    registry = ProviderRegistry(config=config, manifest_hook=bridge.hook)

    # Register provider classes with factory
    registry.factory.register_class("gemini", GeminiLLM)
    registry.factory.register_class("openai-fallback", OpenAILLM)
    registry.factory.register_class("flux", FluxImage)
    registry.factory.register_class("elevenlabs", ElevenLabsAudio)

    # Create and register all providers from config
    for provider_config in config.providers:
        if provider_config.enabled:
            provider = await registry.factory.create(
                provider_config.name, provider_config
            )
            registry.register(provider)

    # Health check all
    health = await registry.health_check_all()
    for name, result in health.items():
        print(f"{name}: {'✓' if result.available else '✗'}")

    # Use providers
    llm = registry.get_llm()
    response = await llm.generate(LLMRequest(
        prompt="Write a scene description",
        system_prompt="You are a screenwriter.",
    ))
    print(response.text)

    # Generate image
    image = registry.get_image()
    img_response = await image.generate(ImageRequest(
        prompt="A futuristic city at sunset",
        width=1920,
        height=1080,
    ))
    print(f"Generated {len(img_response.assets)} image(s)")

    # Record transactions
    recorder = registry.transaction_recorder
    async with recorder.record("gemini", "generate", "llm") as txn:
        txn.set_response(
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            actual_cost=0.001,
        )

    # View costs
    print(f"Total cost: ${recorder.get_total_cost():.4f}")

    # Cleanup
    await registry.shutdown_all()


asyncio.run(main())
```

## Key Concepts

### Provider Capabilities

Every provider declares what it can do via the `ProviderCapability` enum:

| Capability | Interface     | Operations                          |
|-----------|---------------|-------------------------------------|
| `LLM`     | `LLMProvider` | Text generation, streaming, chat    |
| `IMAGE`   | `ImageProvider`| Image generation, editing, upscale |
| `AUDIO`   | `AudioProvider`| Narration, music, SFX              |

### Provider Chain (Primary + Fallbacks)

The registry supports automatic fallback when a provider fails:

```
Request → Primary Provider (gemini)
                ↓ (fails)
           Fallback 1 (openai-fallback)
                ↓ (fails)
           Fallback 2 (anthropic)
                ↓ (all fail)
           ProviderNotAvailableError
```

Fallback order is determined by the `priority` field in configuration (lower = higher priority).

### Health Checks

Providers are periodically health-checked. Results are cached with a configurable TTL:

- **Healthy**: Provider responded within latency threshold
- **Degraded**: Provider responded but above latency threshold
- **Unhealthy**: Provider failed health check (after failure threshold)

Unhealthy providers are automatically excluded from provider chains.

### Transaction Recording

Every provider interaction is recorded as a `Transaction`:

- **Cost tracking**: Per-provider, per-capability, per-stage
- **Manifest integration**: Automatically feeds cost and provider data into the Manifest Engine
- **Diagnostics**: Latency, retry counts, error tracking

### Retry Framework

Automatic retry with exponential backoff:

```python
from mythforge.providers import RetryConfig, with_retry

# Use a preset
result = await with_retry(RETRY_AGGRESSIVE, my_async_function, arg1, arg2)

# Or custom config
config = RetryConfig(
    max_retries=3,
    base_delay_s=1.0,
    max_delay_s=30.0,
    backoff_factor=2.0,
    jitter=True,  # add randomness to prevent thundering herd
)
result = await with_retry(config, my_async_function)
```

Presets:
- `RETRY_CONSERVATIVE`: 2 retries, 2s base delay
- `RETRY_AGGRESSIVE`: 5 retries, 1s base delay
- `RETRY_NONE`: 0 retries (fail immediately)

## Configuration Reference

### Provider Config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | required | Unique provider identifier |
| `type` | string | required | `llm`, `image`, or `audio` |
| `enabled` | bool | `true` | Whether the provider is active |
| `primary` | bool | `false` | Primary provider for its type |
| `priority` | int | `0` | Fallback order (lower = higher priority) |
| `model` | string | `null` | Default model name |
| `api_key_env` | string | `null` | Environment variable for API key |
| `base_url` | string | `null` | API base URL override |
| `timeout_s` | float | `60` | Per-request timeout |
| `max_concurrent` | int | `10` | Max concurrent requests |
| `rate_limit_rpm` | int | `null` | Requests per minute limit |
| `retry` | object | see below | Retry configuration |
| `health_check_enabled` | bool | `true` | Enable health checks |
| `options` | object | `{}` | Provider-specific options |

### Retry Config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_retries` | int | `3` | Maximum retry attempts |
| `base_delay_s` | float | `1.0` | Initial delay between retries |
| `max_delay_s` | float | `60.0` | Maximum delay cap |
| `backoff_factor` | float | `2.0` | Delay multiplier per retry |
| `jitter` | bool | `true` | Add random jitter to delays |
| `timeout_s` | float | `null` | Overall timeout for all retries |

### Global SDK Config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `providers` | list | `[]` | Provider configurations |
| `default_timeout_s` | float | `60` | Default timeout for all providers |
| `health_check_interval_s` | float | `300` | Health check cache TTL |
| `transaction_max_history` | int | `1000` | Max transactions to keep in memory |
| `fallback_enabled` | bool | `true` | Enable automatic fallback |

## Adding a New Provider

1. **Create the implementation class** — subclass `LLMProvider`, `ImageProvider`, or `AudioProvider`
2. **Implement required methods** — `generate()`, `health_check()`, `estimate_cost()`, etc.
3. **Register the class** — `registry.factory.register_class("my-provider", MyProvider)`
4. **Add configuration** — add an entry to `config/providers.yaml`
5. **That's it** — the registry handles the rest (instantiation, health, retry, transactions)

No existing code needs to be modified. The SDK is fully open for extension.

## Manifest Engine Integration

The Provider SDK automatically bridges into the Manifest Engine via `ManifestBridge`:

```
Provider Transaction → TransactionRecorder → ManifestHook → ManifestBridge → ManifestEngine
                                                                         ↓
                                                              CostRecord + ProviderRecord
```

This means every provider interaction automatically:
- Records cost in the manifest
- Tracks provider usage statistics
- Attributes costs to pipeline stages

To customise manifest integration, implement `ManifestHook`:

```python
from mythforge.providers import ManifestHook

class CustomHook(ManifestHook):
    def on_transaction_complete(self, transaction):
        # Custom logic: e.g. send to analytics
        analytics.track("provider_call", {
            "provider": transaction.provider,
            "cost": transaction.actual_cost_usd,
        })

    def on_transaction_failed(self, transaction):
        alerting.notify(f"Provider {transaction.provider} failed: {transaction.error}")
```

## Testing

```bash
# Run all provider SDK tests
pytest tests/test_providers/ -v

# Run specific test categories
pytest tests/test_providers/test_providers_sdk.py::TestRetry -v
pytest tests/test_providers/test_providers_sdk.py::TestRegistry -v
pytest tests/test_providers/test_providers_sdk.py::TestIntegration -v
```

## Files

| File | Purpose | Risk if Modified |
|------|---------|-----------------|
| `exceptions.py` | Exception hierarchy | LOW — adding is safe, renaming breaks imports |
| `models.py` | Request/response types | MEDIUM — changes affect all providers |
| `interfaces.py` | Abstract base classes | HIGH — changes break all provider implementations |
| `retry.py` | Retry framework | LOW — self-contained |
| `health.py` | Health checks | LOW — self-contained |
| `transaction.py` | Transaction recording | LOW — self-contained |
| `config.py` | Configuration | MEDIUM — schema changes need validation update |
| `registry.py` | Provider registry | HIGH — central orchestration point |
| `manifest_hooks.py` | Manifest integration | MEDIUM — depends on engine schema |