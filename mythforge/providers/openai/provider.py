"""
OpenAI provider — implements :class:`LLMProvider` using the Responses API.

This is the production implementation that the pipeline interacts with.
It delegates to :class:`OpenAIRequestMapper` / :class:`OpenAIResponseMapper`
for all OpenAI-specific translation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from mythforge.providers.exceptions import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderAPIError,
)
from mythforge.providers.health import HealthCheckManager
from mythforge.providers.interfaces import LLMProvider
from mythforge.providers.models import (
    CostEstimate,
    HealthCheckResult,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    ProviderCapability,
    ProviderStatus,
)
from mythforge.providers.retry import RetryConfig, with_retry
from mythforge.providers.transaction import TransactionRecorder

from .config import OpenAIConfig
from .cost import CostEstimator
from .mapper import OpenAIRequestMapper, OpenAIResponseMapper
from .metrics import ProviderMetrics

logger = logging.getLogger(__name__)


async def _to_async_iter(value: Any) -> AsyncIterator[Any]:
    for item in value:
        yield item


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    """OpenAI provider using the Responses API.

    Implements :class:`LLMProvider` with:

    * Responses API (``client.responses.create``)
    * Streaming support
    * Automatic cost tracking
    * Built-in metrics
    * Structured output via JSON schema
    * Health checks

    Usage::

        config = OpenAIConfig(
            api_key="sk-...",
            default_model="gpt-4o",
        )
        provider = OpenAIProvider(config)
        await provider.initialise()

        request = LLMRequest(prompt="Hello, world!")
        response = await provider.generate(request)

        # Streaming
        async for chunk in provider.stream(request):
            print(chunk.delta, end="")
    """

    def __init__(
        self,
        config: OpenAIConfig,
        *,
        health_manager: Optional[HealthCheckManager] = None,
        transaction_recorder: Optional[TransactionRecorder] = None,
    ) -> None:
        self._config = config
        self._client: Any = None              # openai.AsyncOpenAI
        self._initialised = False
        self._health_manager = health_manager
        self._transaction_recorder = transaction_recorder
        self._metrics = ProviderMetrics()
        self._cost_estimator = CostEstimator()

    # -- LLMProvider interface ------------------------------------------

    @property
    def name(self) -> str:
        return "openai"

    @property
    def version(self) -> str:
        return "2.0.0"  # SDK version

    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [ProviderCapability.LLM]

    async def initialise(self) -> None:
        """Initialise the OpenAI client.

        Raises
        ------
        ProviderConfigError
            If the API key cannot be resolved or the SDK is not installed.
        """
        if self._initialised:
            return

        try:
            import openai
        except ImportError:
            raise ProviderConfigError(
                "The 'openai' package is required. Install it with: pip install openai"
            )

        api_key = self._config.resolve_api_key()

        kwargs: Dict[str, Any] = {"api_key": api_key}
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url
        if self._config.organization:
            kwargs["organization"] = self._config.organization
        if self._config.timeout_s:
            kwargs["timeout"] = self._config.timeout_s
        if self._config.max_retries:
            kwargs["max_retries"] = self._config.max_retries

        self._client = openai.AsyncOpenAI(**kwargs)
        self._initialised = True

        # Register health check
        if self._health_manager:
            self._health_manager.register("openai", self.health_check)

        logger.info(
            "OpenAI provider initialised (model=%s, base_url=%s)",
            self._config.default_model,
            self._config.base_url or "default",
        )

    async def shutdown(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.close()
            self._client = None
        self._initialised = False
        logger.info("OpenAI provider shut down")

    async def generate(
        self,
        request: LLMRequest,
        *,
        _retry_manager: Optional[Any] = None,
    ) -> LLMResponse:
        """Generate a response synchronously (non-streaming).

        Parameters
        ----------
        request:
            MythForge generic LLM request.

        Returns
        -------
        LLMResponse
            The generated response.

        Raises
        ------
        ProviderAuthError
            If authentication fails.
        ProviderRateLimitError
            If rate limited.
        ProviderTimeoutError
            If the request times out.
        ProviderAPIError
            For other API errors.
        """
        self._ensure_initialised()

        model = self._config.get_model_for_request(request.model)
        body = OpenAIRequestMapper.to_responses_api(
            request,
            model=model,
            max_output_tokens=self._config.max_output_tokens,
            stream=False,
        )

        retry_config = RetryConfig(
            max_retries=self._config.max_retries,
            base_delay_s=0.25,
            timeout_s=self._config.timeout_s,
        )

        # Remove internal metadata before sending
        request_metadata = body.pop("_mythforge_metadata", {})
        request_metadata["provider"] = self.name
        request_metadata["model"] = model

        async def _call_api() -> Any:
            return await self._client.responses.create(**body)

        t0 = time.monotonic()
        try:
            if self._transaction_recorder is not None:
                async with self._transaction_recorder.record(
                    self.name,
                    "generate",
                    "llm",
                    model=model,
                    metadata={"request": request.to_dict()},
                ) as txn:
                    api_response = await with_retry(retry_config, _call_api)
                    latency_ms = (time.monotonic() - t0) * 1000
                    response = OpenAIResponseMapper.from_responses_api(
                        api_response,
                        provider=self.name,
                        latency_ms=latency_ms,
                        request_metadata=request_metadata,
                    )
                    self._cost_estimator.calculate(
                        model,
                        tokens_in=response.tokens_in,
                        tokens_out=response.tokens_out,
                    )
                    txn.set_response(
                        tokens_in=response.tokens_in,
                        tokens_out=response.tokens_out,
                        estimated_cost=response.estimated_cost_usd,
                        actual_cost=self._cost_estimator.get_total_cost(),
                        metadata={"response": response.to_dict()},
                    )
                    self._metrics.record_request(
                        latency_ms=latency_ms,
                        tokens_in=response.tokens_in,
                        tokens_out=response.tokens_out,
                        model=model,
                        success=True,
                    )
                    return response

            api_response = await with_retry(retry_config, _call_api)
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            self._metrics.record_request(
                latency_ms=latency_ms,
                model=model,
                success=False,
                error_type=type(exc).__name__,
            )
            raise self._map_error(exc) from exc

        latency_ms = (time.monotonic() - t0) * 1000

        response = OpenAIResponseMapper.from_responses_api(
            api_response,
            provider=self.name,
            latency_ms=latency_ms,
            request_metadata=request_metadata,
        )

        self._cost_estimator.calculate(
            model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )

        self._metrics.record_request(
            latency_ms=latency_ms,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            model=model,
            success=True,
        )

        return response

    async def stream(
        self,
        request: LLMRequest,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a response token-by-token.

        Parameters
        ----------
        request:
            MythForge generic LLM request.

        Yields
        ------
        LLMStreamChunk
            Incremental response chunks.
        """
        self._ensure_initialised()

        model = self._config.get_model_for_request(request.model)
        body = OpenAIRequestMapper.to_responses_api(
            request,
            model=model,
            max_output_tokens=self._config.max_output_tokens,
            stream=True,
        )
        body.pop("_mythforge_metadata", {})

        retry_config = RetryConfig(
            max_retries=self._config.max_retries,
            base_delay_s=0.25,
            timeout_s=self._config.timeout_s,
        )

        async def _open_stream() -> Any:
            return await self._client.responses.create(**body)

        t0 = time.monotonic()
        try:
            if self._transaction_recorder is not None:
                async with self._transaction_recorder.record(
                    self.name,
                    "stream",
                    "llm",
                    model=model,
                    metadata={"request": request.to_dict()},
                ) as txn:
                    stream = await with_retry(retry_config, _open_stream)
                    async for event in stream:
                        chunk = OpenAIResponseMapper.from_stream_event(event, provider=self.name)
                        if chunk:
                            yield chunk
                    latency_ms = (time.monotonic() - t0) * 1000
                    txn.set_response(
                        tokens_out=0,
                        estimated_cost=0.0,
                        actual_cost=0.0,
                        metadata={"streamed": True},
                    )
                    self._metrics.record_request(
                        latency_ms=latency_ms,
                        model=model,
                        success=True,
                        streamed=True,
                    )
                    return

            stream = await with_retry(retry_config, _open_stream)
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            self._metrics.record_request(
                latency_ms=latency_ms,
                model=model,
                success=False,
                error_type=type(exc).__name__,
            )
            raise self._map_error(exc) from exc

        if hasattr(stream, "__aiter__"):
            async_iter = stream
        else:
            async_iter = _to_async_iter(stream)

        async for event in async_iter:
            chunk = OpenAIResponseMapper.from_stream_event(event, provider=self.name)
            if chunk:
                yield chunk

        latency_ms = (time.monotonic() - t0) * 1000
        self._metrics.record_request(
            latency_ms=latency_ms,
            model=model,
            success=True,
            streamed=True,
        )

    async def health_check(self) -> HealthCheckResult:
        """Perform a health check by listing models.

        Returns
        -------
        HealthCheckResult
            Current health status.
        """
        self._ensure_initialised()

        t0 = time.monotonic()
        try:
            # Lightweight call — list available models
            models = await self._client.models.list()
            latency_ms = (time.monotonic() - t0) * 1000

            # Verify our default model exists
            model_ids = {m.id for m in models.data} if hasattr(models, "data") else set()
            default_model = self._config.default_model
            if default_model and default_model not in model_ids:
                return HealthCheckResult(
                    provider=self.name,
                    status=ProviderStatus.DEGRADED,
                    available=True,
                    latency_ms=latency_ms,
                    failure_reason=f"Default model '{default_model}' not found in available models",
                )

            return HealthCheckResult(
                provider=self.name,
                status=ProviderStatus.HEALTHY,
                available=True,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            status = ProviderStatus.UNHEALTHY
            if "auth" in str(exc).lower() or "401" in str(exc):
                status = ProviderStatus.UNHEALTHY
            return HealthCheckResult(
                provider=self.name,
                status=status,
                available=False,
                latency_ms=latency_ms,
                failure_reason=str(exc),
            )

    async def estimate_cost(self, operation: str, **kwargs: Any) -> CostEstimate:
        """Estimate cost for an operation before execution."""
        model = kwargs.get("model") or self._config.default_model or ""
        tokens_in = int(kwargs.get("tokens_in", 0) or 0)
        tokens_out = int(kwargs.get("tokens_out", 0) or 0)
        estimated_cost = self._cost_estimator.estimate(
            model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        return CostEstimate(
            provider=self.name,
            operation=operation,
            estimated_cost_usd=estimated_cost,
            estimated_tokens_in=tokens_in,
            estimated_tokens_out=tokens_out,
            confidence=0.8 if model else 0.0,
            metadata={"model": model},
        )

    def capability_report(self) -> Dict[str, Any]:
        """Expose capability metadata for the provider."""
        return {
            "streaming": self._config.streaming_enabled,
            "structured_outputs": self._config.structured_output_enabled,
            "reasoning": bool(self._config.reasoning_model),
            "vision": bool(self._config.vision_model),
            "json": self._config.structured_output_enabled,
            "max_context": int(self._config.options.get("max_context", 128000)),
            "token_limits": {
                "input": int(self._config.options.get("input_token_limit", 128000)),
                "output": int(self._config.options.get("output_token_limit", 4096)),
            },
        }

    # -- Public accessors ------------------------------------------------

    @property
    def metrics(self) -> ProviderMetrics:
        """Access operational metrics."""
        return self._metrics

    @property
    def cost_estimator(self) -> CostEstimator:
        """Access cost estimator."""
        return self._cost_estimator

    @property
    def config(self) -> OpenAIConfig:
        """Access configuration."""
        return self._config

    # -- Internal --------------------------------------------------------

    def _ensure_initialised(self) -> None:
        """Raise if the provider has not been initialised."""
        if not self._initialised:
            raise ProviderConfigError(
                "OpenAI provider not initialised. Call await provider.initialise() first."
            )

    @staticmethod
    def _map_error(exc: Exception) -> Exception:
        """Map an OpenAI SDK exception to a MythForge provider exception."""
        exc_str = str(exc).lower()
        exc_type = type(exc).__name__

        # Import openai exceptions if available
        try:
            import openai
            if isinstance(exc, openai.AuthenticationError):
                return ProviderAuthError(str(exc), provider="openai")
            if isinstance(exc, openai.RateLimitError):
                return ProviderRateLimitError(str(exc), provider="openai")
            if isinstance(exc, openai.APITimeoutError):
                return ProviderTimeoutError(str(exc), provider="openai")
            if isinstance(exc, openai.APIError):
                return ProviderAPIError(
                    str(exc),
                    provider="openai",
                    status_code=getattr(exc, "status_code", None),
                )
        except ImportError:
            pass

        # Fallback string matching
        if "auth" in exc_str or "401" in exc_str:
            return ProviderAuthError(str(exc), provider="openai")
        if "rate" in exc_str or "429" in exc_str:
            return ProviderRateLimitError(str(exc), provider="openai")
        if "timeout" in exc_str:
            return ProviderTimeoutError(str(exc), provider="openai")

        return ProviderAPIError(str(exc), provider="openai")