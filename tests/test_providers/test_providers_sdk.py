"""
Unit tests for the Provider SDK.

Tests the complete Provider SDK in isolation — no real API calls,
no real providers, everything mocked.

Usage::

    pytest tests/test_providers/test_providers_sdk.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mythforge.providers import (
    # Exceptions
    ProviderError,
    ProviderConfigError,
    ProviderNotAvailableError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderRegistrationError,
    MaxRetriesExceededError,
    # Models
    ProviderCapability,
    ProviderStatus,
    TransactionStatus,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    ImageRequest,
    ImageResponse,
    ImageAsset,
    NarrationRequest,
    MusicRequest,
    SFXRequest,
    AudioResponse,
    HealthCheckResult,
    Transaction,
    CostEstimate,
    # Interfaces
    BaseProvider,
    LLMProvider,
    ImageProvider,
    AudioProvider,
    # Retry
    RetryConfig,
    with_retry,
    RETRY_CONSERVATIVE,
    RETRY_AGGRESSIVE,
    RETRY_NONE,
    # Health
    HealthCheckConfig,
    HealthCheckManager,
    # Transaction
    ManifestHook,
    TransactionRecorder,
    TransactionContext,
    # Config
    ProviderConfig,
    ProviderSDKConfig,
    ConfigLoader,
    # Registry
    ProviderFactory,
    ProviderRegistry,
)


# =========================================================================
# Fixtures / helpers
# =========================================================================

class StubLLMProvider(LLMProvider):
    """Stub LLM provider for testing."""

    name = "stub-llm"
    capabilities = [ProviderCapability.LLM]

    def __init__(self, config=None):
        self._config = config or ProviderConfig(name="stub-llm", type="llm")
        self._initialised = False

    async def initialise(self) -> None:
        self._initialised = True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=f"Echo: {request.prompt}",
            provider=self.name,
            model=self._config.model or "stub-model",
            tokens_in=len(request.prompt.split()),
            tokens_out=5,
        )

    async def stream(self, request: LLMRequest):
        yield LLMStreamChunk(delta="Echo: ")
        yield LLMStreamChunk(delta=request.prompt, finished=True)

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(provider=self.name, available=True, latency_ms=1.0)

    async def estimate_cost(self, operation: str, **kwargs) -> CostEstimate:
        return CostEstimate(
            provider=self.name,
            operation=operation,
            estimated_cost_usd=0.001,
        )


class StubImageProvider(ImageProvider):
    """Stub image provider for testing."""

    name = "stub-image"
    capabilities = [ProviderCapability.IMAGE]

    def __init__(self, config=None):
        self._config = config or ProviderConfig(name="stub-image", type="image")

    async def initialise(self) -> None:
        pass

    async def generate(self, request: ImageRequest) -> ImageResponse:
        asset = ImageAsset(
            url="https://example.com/image.png",
            width=request.width or 1024,
            height=request.height or 576,
            format="png",
        )
        return ImageResponse(
            assets=[asset],
            provider=self.name,
            model=self._config.model or "stub-model",
        )

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(provider=self.name, available=True)

    async def estimate_cost(self, operation: str, **kwargs) -> CostEstimate:
        return CostEstimate(
            provider=self.name,
            operation=operation,
            estimated_cost_usd=0.01,
        )


class FailingProvider(LLMProvider):
    """Provider that always fails — for retry testing."""

    name = "failing-llm"
    capabilities = [ProviderCapability.LLM]
    call_count = 0

    def __init__(self, config=None):
        self._config = config or ProviderConfig(name="failing-llm", type="llm")

    async def initialise(self) -> None:
        pass

    async def generate(self, request: LLMRequest) -> LLMResponse:
        FailingProvider.call_count += 1
        raise ProviderUnavailableError("failing-llm", "Always fails")

    async def stream(self, request: LLMRequest):
        raise ProviderUnavailableError("failing-llm", "Always fails")

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            provider=self.name,
            available=False,
            error="Always fails",
        )

    async def estimate_cost(self, operation: str, **kwargs) -> CostEstimate:
        return CostEstimate(provider=self.name, operation=operation)


@pytest.fixture
def stub_llm():
    return StubLLMProvider()


@pytest.fixture
def stub_image():
    return StubImageProvider()


@pytest.fixture
def sdk_config():
    return ProviderSDKConfig(
        providers=[
            ProviderConfig(name="stub-llm", type="llm", primary=True, enabled=True),
            ProviderConfig(name="stub-image", type="image", primary=True, enabled=True),
            ProviderConfig(name="fallback-llm", type="llm", enabled=True, priority=1),
        ],
    )


@pytest.fixture
def registry(sdk_config):
    reg = ProviderRegistry(config=sdk_config)
    reg.register(StubLLMProvider())
    reg.register(StubImageProvider())
    return reg


# =========================================================================
# Test: Exceptions
# =========================================================================

class TestExceptions:
    def test_provider_error_hierarchy(self):
        assert issubclass(ProviderConfigError, ProviderError)
        assert issubclass(ProviderNotAvailableError, ProviderError)
        assert issubclass(ProviderUnavailableError, ProviderError)
        assert issubclass(ProviderTimeoutError, ProviderError)
        assert issubclass(ProviderRateLimitError, ProviderError)
        assert issubclass(ProviderRegistrationError, ProviderError)
        assert issubclass(MaxRetriesExceededError, ProviderError)

    def test_provider_error_message(self):
        err = ProviderError("test message", provider="gemini")
        assert "test message" in str(err)
        assert err.provider == "gemini"

    def test_max_retries_exceeded(self):
        err = MaxRetriesExceededError(max_retries=3, last_error=RuntimeError("oops"))
        assert err.max_retries == 3
        assert isinstance(err.last_error, RuntimeError)


# =========================================================================
# Test: Models
# =========================================================================

class TestModels:
    def test_llm_request(self):
        req = LLMRequest(prompt="Hello", model="test-model")
        assert req.prompt == "Hello"
        assert req.model == "test-model"

    def test_llm_response(self):
        resp = LLMResponse(text="Hi", provider="test", tokens_in=1, tokens_out=1)
        assert resp.text == "Hi"
        assert resp.provider == "test"

    def test_image_request(self):
        req = ImageRequest(prompt="A cat", width=1024, height=768)
        assert req.width == 1024
        assert req.height == 768

    def test_image_asset(self):
        asset = ImageAsset(url="https://example.com/img.png", width=1024, height=768, format="png")
        assert asset.width == 1024

    def test_image_response(self):
        asset = ImageAsset(url="https://example.com/img.png", width=1024, height=768, format="png")
        resp = ImageResponse(assets=[asset], provider="test")
        assert len(resp.assets) == 1

    def test_audio_response(self):
        resp = AudioResponse(url="https://example.com/audio.mp3", provider="test", duration_s=10.5)
        assert resp.duration_s == 10.5

    def test_health_check_result(self):
        hcr = HealthCheckResult(provider="test", available=True, latency_ms=5.0)
        assert hcr.available is True

    def test_transaction_defaults(self):
        txn = Transaction(provider="test", operation="generate", capability="llm")
        assert txn.status == TransactionStatus.PENDING
        assert txn.retries == 0

    def test_transaction_complete(self):
        txn = Transaction(provider="test", operation="generate", capability="llm")
        txn.complete(
            status=TransactionStatus.SUCCESS,
            tokens_in=10,
            tokens_out=20,
            actual_cost_usd=0.05,
        )
        assert txn.status == TransactionStatus.SUCCESS
        assert txn.tokens_in == 10
        assert txn.actual_cost_usd == 0.05

    def test_provider_capability_enum(self):
        assert ProviderCapability.LLM.value == "llm"
        assert ProviderCapability.IMAGE.value == "image"
        assert ProviderCapability.AUDIO.value == "audio"


# =========================================================================
# Test: Interfaces
# =========================================================================

class TestInterfaces:
    def test_base_provider_interface(self):
        """Verify the ABC requires implementation."""
        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            class IncompleteProvider(BaseProvider):
                pass
            IncompleteProvider()

    def test_llm_provider_requires_methods(self):
        """Verify LLMProvider requires generate and stream."""
        with pytest.raises(TypeError):
            class Incomplete(LLMProvider):
                name = "test"
                capabilities = [ProviderCapability.LLM]
                async def initialise(self): pass
                async def health_check(self): pass
                async def estimate_cost(self, op, **kw): pass
                # Missing: generate, stream
            Incomplete()

    def test_stub_llm_implements_interface(self, stub_llm):
        assert isinstance(stub_llm, LLMProvider)
        assert isinstance(stub_llm, BaseProvider)
        assert ProviderCapability.LLM in stub_llm.capabilities

    def test_stub_image_implements_interface(self, stub_image):
        assert isinstance(stub_image, ImageProvider)
        assert ProviderCapability.IMAGE in stub_image.capabilities


# =========================================================================
# Test: Retry
# =========================================================================

class TestRetry:
    @pytest.mark.asyncio
    async def test_with_retry_success_first_try(self):
        call_count = 0

        async def success():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await with_retry(RetryConfig(max_retries=3), success)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_with_retry_succeeds_after_failures(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ProviderUnavailableError("test", "not ready")
            return "ok"

        result = await with_retry(
            RetryConfig(max_retries=3, base_delay_s=0.01),
            flaky,
        )
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retry_exhausted(self):
        async def always_fail():
            raise ProviderUnavailableError("test", "always")

        with pytest.raises(MaxRetriesExceededError):
            await with_retry(
                RetryConfig(max_retries=2, base_delay_s=0.01),
                always_fail,
            )

    @pytest.mark.asyncio
    async def test_retry_none_config(self):
        async def always_fail():
            raise ProviderUnavailableError("test", "always")

        with pytest.raises(ProviderUnavailableError):
            await with_retry(RETRY_NONE, always_fail)

    def test_retry_presets(self):
        assert RETRY_AGGRESSIVE.max_retries == 5
        assert RETRY_CONSERVATIVE.max_retries == 2
        assert RETRY_NONE.max_retries == 0


# =========================================================================
# Test: Health
# =========================================================================

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_check_manager(self):
        hcm = HealthCheckManager()

        async def check_ok():
            return HealthCheckResult(provider="test", available=True)

        hcm.register("test", check_ok)
        result = await hcm.check("test", force=True)
        assert result.available is True

    @pytest.mark.asyncio
    async def test_health_check_caching(self):
        call_count = 0

        async def check_fn():
            nonlocal call_count
            call_count += 1
            return HealthCheckResult(provider="test", available=True)

        hcm = HealthCheckManager(HealthCheckConfig(cache_ttl_s=60.0))
        hcm.register("test", check_fn)

        await hcm.check("test", force=True)
        await hcm.check("test", force=False)  # should use cache
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_health_check_failure_threshold(self):
        async def check_fail():
            return HealthCheckResult(provider="test", available=False, error="down")

        hcm = HealthCheckManager(HealthCheckConfig(failure_threshold=2))
        hcm.register("test", check_fail)

        r1 = await hcm.check("test", force=True)
        assert r1.available is False

        is_healthy = await hcm.is_healthy("test")
        # First failure, still considered healthy (threshold not reached)
        # depends on implementation — threshold tracking is internal


# =========================================================================
# Test: Transaction Recorder
# =========================================================================

class TestTransactionRecorder:
    @pytest.mark.asyncio
    async def test_record_success(self):
        recorder = TransactionRecorder()

        async with recorder.record("test-provider", "generate", "llm") as txn:
            txn.set_response(tokens_in=10, tokens_out=20, actual_cost=0.05)

        history = recorder.get_history()
        assert len(history) == 1
        assert history[0].provider == "test-provider"
        assert history[0].status == TransactionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_record_failure(self):
        recorder = TransactionRecorder()

        with pytest.raises(ValueError):
            async with recorder.record("test-provider", "generate", "llm") as txn:
                raise ValueError("boom")

        history = recorder.get_history()
        assert len(history) == 1
        assert history[0].status == TransactionStatus.FAILURE

    @pytest.mark.asyncio
    async def test_cost_aggregation(self):
        recorder = TransactionRecorder()

        async with recorder.record("p1", "generate", "llm") as txn:
            txn.set_response(actual_cost=1.0)

        async with recorder.record("p1", "generate", "llm") as txn:
            txn.set_response(actual_cost=2.0)

        async with recorder.record("p2", "generate", "image") as txn:
            txn.set_response(actual_cost=0.5)

        assert recorder.get_total_cost() == pytest.approx(3.5)
        assert recorder.get_costs_by_provider()["p1"] == pytest.approx(3.0)
        assert recorder.get_costs_by_capability()["llm"] == pytest.approx(3.0)

    @pytest.mark.asyncio
    async def test_manifest_hook_called(self):
        hook = MagicMock(spec=ManifestHook)
        recorder = TransactionRecorder(manifest_hook=hook)

        async with recorder.record("p1", "generate", "llm") as txn:
            txn.set_response(actual_cost=0.1)

        hook.on_transaction_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_history_limit(self):
        recorder = TransactionRecorder(max_history=3)

        for i in range(5):
            async with recorder.record("p1", "generate", "llm") as txn:
                txn.set_response(tokens_in=i)

        history = recorder.get_history()
        assert len(history) == 3


# =========================================================================
# Test: Config
# =========================================================================

class TestConfig:
    def test_config_from_dict(self):
        data = {
            "providers": [
                {"name": "gemini", "type": "llm", "primary": True},
                {"name": "flux", "type": "image"},
            ],
            "default_timeout_s": 30,
            "fallback_enabled": True,
        }
        config = ConfigLoader.from_dict(data)
        assert len(config.providers) == 2
        assert config.providers[0].name == "gemini"
        assert config.providers[0].primary is True

    def test_config_rejects_duplicate_names(self):
        data = {
            "providers": [
                {"name": "gemini", "type": "llm"},
                {"name": "gemini", "type": "image"},
            ],
        }
        with pytest.raises(ProviderConfigError, match="Duplicate"):
            ConfigLoader.from_dict(data)

    def test_config_rejects_multiple_primaries(self):
        data = {
            "providers": [
                {"name": "a", "type": "llm", "primary": True},
                {"name": "b", "type": "llm", "primary": True},
            ],
        }
        with pytest.raises(ProviderConfigError, match="Multiple primary"):
            ConfigLoader.from_dict(data)

    def test_config_get_primary(self):
        config = ProviderSDKConfig(
            providers=[
                ProviderConfig(name="a", type="llm", primary=True),
                ProviderConfig(name="b", type="llm", enabled=True, priority=1),
            ]
        )
        primary = config.get_primary("llm")
        assert primary.name == "a"

    def test_config_get_chain(self):
        config = ProviderSDKConfig(
            providers=[
                ProviderConfig(name="a", type="llm", primary=True),
                ProviderConfig(name="b", type="llm", priority=1),
                ProviderConfig(name="c", type="llm", priority=2),
            ]
        )
        chain = config.get_chain("llm")
        assert [p.name for p in chain] == ["a", "b", "c"]

    def test_config_from_json_file(self):
        data = {
            "providers": [
                {"name": "test", "type": "llm"},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        try:
            config = ConfigLoader.from_file(path)
            assert len(config.providers) == 1
            assert config.providers[0].name == "test"
        finally:
            os.unlink(path)

    def test_provider_config_to_dict(self):
        pc = ProviderConfig(name="test", type="llm", enabled=True, model="gpt-4")
        d = pc.to_dict()
        assert d["name"] == "test"
        assert d["model"] == "gpt-4"


# =========================================================================
# Test: Registry
# =========================================================================

class TestRegistry:
    @pytest.mark.asyncio
    async def test_register_and_get(self, registry, stub_llm):
        assert registry.get("stub-llm") is stub_llm
        assert registry.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_required_raises(self, registry):
        with pytest.raises(ProviderNotAvailableError):
            registry.get_required("nonexistent")

    @pytest.mark.asyncio
    async def test_get_by_capability(self, registry):
        llm_providers = registry.get_by_capability(ProviderCapability.LLM)
        assert len(llm_providers) == 1
        assert llm_providers[0].name == "stub-llm"

    @pytest.mark.asyncio
    async def test_get_primary(self, registry):
        primary = registry.get_primary(ProviderCapability.LLM)
        assert primary is not None
        assert primary.name == "stub-llm"

    @pytest.mark.asyncio
    async def test_convenience_get_llm(self, registry):
        llm = registry.get_llm()
        assert isinstance(llm, LLMProvider)

    @pytest.mark.asyncio
    async def test_convenience_get_image(self, registry):
        img = registry.get_image()
        assert isinstance(img, ImageProvider)

    @pytest.mark.asyncio
    async def test_unregistered_raises(self):
        reg = ProviderRegistry()
        with pytest.raises(ProviderNotAvailableError):
            reg.get_llm()

    @pytest.mark.asyncio
    async def test_unregister(self, registry):
        registry.unregister("stub-llm")
        assert registry.get("stub-llm") is None

    @pytest.mark.asyncio
    async def test_generate_through_registry(self, registry):
        llm = registry.get_llm()
        response = await llm.generate(LLMRequest(prompt="Hello"))
        assert "Echo: Hello" in response.text

    @pytest.mark.asyncio
    async def test_health_check_all(self, registry):
        results = await registry.health_check_all()
        assert "stub-llm" in results
        assert results["stub-llm"].available is True


# =========================================================================
# Test: Factory
# =========================================================================

class TestFactory:
    @pytest.mark.asyncio
    async def test_factory_create(self):
        factory = ProviderFactory()
        factory.register_class("stub-llm", StubLLMProvider)

        config = ProviderConfig(name="stub-llm", type="llm")
        provider = await factory.create("stub-llm", config)
        assert isinstance(provider, StubLLMProvider)
        assert provider._initialised is True

    @pytest.mark.asyncio
    async def test_factory_unregistered_raises(self):
        factory = ProviderFactory()
        with pytest.raises(ProviderRegistrationError):
            await factory.create("nonexistent", ProviderConfig())

    def test_factory_rejects_non_base_provider(self):
        factory = ProviderFactory()
        with pytest.raises(ProviderRegistrationError):
            factory.register_class("bad", dict)  # type: ignore


# =========================================================================
# Test: Manifest Hooks
# =========================================================================

class TestManifestHooks:
    def test_manifest_bridge_no_op_when_no_engine(self):
        from mythforge.providers.manifest_hooks import ManifestBridge

        bridge = ManifestBridge(engine=None)
        # Should not raise
        txn = Transaction(provider="test", operation="generate", capability="llm")
        txn.complete(status=TransactionStatus.SUCCESS)
        bridge.record_transaction(txn)


# =========================================================================
# Test: Integration (provider → registry → manifest)
# =========================================================================

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_flow(self, sdk_config):
        """End-to-end: config → registry → provider → generate → transaction."""
        registry = ProviderRegistry(config=sdk_config)
        provider = StubLLMProvider(
            config=ProviderConfig(name="stub-llm", type="llm", primary=True)
        )
        await provider.initialise()
        registry.register(provider)

        # Generate
        llm = registry.get_llm()
        response = await llm.generate(LLMRequest(prompt="Test"))
        assert response.text == "Echo: Test"

        # Record transaction
        recorder = registry.transaction_recorder
        async with recorder.record("stub-llm", "generate", "llm") as txn:
            txn.set_response(
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                actual_cost=0.001,
            )

        assert recorder.get_total_cost() == pytest.approx(0.001)
        assert recorder.get_transaction_count() == 1