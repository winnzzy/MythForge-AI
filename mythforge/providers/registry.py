"""
Provider registry and factory.

Central registry for provider instances.  Providers are registered by name
and resolved by name or capability.  The factory creates provider instances
from configuration.

Usage::

    # Register a provider class
    registry = ProviderRegistry()
    registry.register_class("gemini-llm", GeminiLLMProvider)

    # Create and retrieve
    provider = await registry.create("gemini-llm", config=my_config)
    llm = registry.get("gemini-llm")

    # Get all providers for a capability
    image_providers = registry.get_by_capability(ProviderCapability.IMAGE)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from .config import ProviderConfig, ProviderSDKConfig
from .exceptions import ProviderNotAvailableError, ProviderRegistrationError
from .health import HealthCheckConfig, HealthCheckManager
from .interfaces import BaseProvider, LLMProvider, ImageProvider, AudioProvider
from .models import ProviderCapability
from .retry import RetryConfig, with_retry
from .transaction import ManifestHook, TransactionRecorder

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider Factory
# ---------------------------------------------------------------------------

class ProviderFactory:
    """Creates provider instances from configuration.

    The factory maintains a class registry mapping provider names to
    their implementation classes.  When ``create()`` is called, it
    instantiates the class with the provided configuration.

    Usage::

        factory = ProviderFactory()
        factory.register_class("gemini-llm", GeminiLLMProvider)

        provider = await factory.create("gemini-llm", config=provider_config)
    """

    def __init__(self) -> None:
        self._classes: Dict[str, Type[BaseProvider]] = {}

    def register_class(
        self,
        name: str,
        cls: Type[BaseProvider],
    ) -> None:
        """Register a provider implementation class.

        Parameters
        ----------
        name:
            Unique name for this provider type.
        cls:
            The provider class (must subclass :class:`BaseProvider`).
        """
        if not (isinstance(cls, type) and issubclass(cls, BaseProvider)):
            raise ProviderRegistrationError(
                f"'{cls}' is not a subclass of BaseProvider."
            )
        self._classes[name] = cls
        logger.debug("Registered provider class: %s -> %s", name, cls.__name__)

    def unregister_class(self, name: str) -> None:
        """Remove a registered provider class."""
        self._classes.pop(name, None)

    def get_class(self, name: str) -> Optional[Type[BaseProvider]]:
        """Get a registered provider class by name."""
        return self._classes.get(name)

    def list_classes(self) -> Dict[str, Type[BaseProvider]]:
        """List all registered provider classes."""
        return dict(self._classes)

    async def create(
        self,
        name: str,
        config: ProviderConfig,
    ) -> BaseProvider:
        """Create a provider instance from configuration.

        Parameters
        ----------
        name:
            The registered provider class name.
        config:
            Provider configuration.

        Returns
        -------
        BaseProvider
            Instantiated and initialised provider.

        Raises
        ------
        ProviderRegistrationError
            If no class is registered for the given name.
        """
        cls = self._classes.get(name)
        if cls is None:
            raise ProviderRegistrationError(
                f"No provider class registered for '{name}'."
            )

        # Instantiate
        provider = cls(config)

        # Initialise if it has an initialise method
        if hasattr(provider, "initialise"):
            await provider.initialise()

        return provider


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------

class ProviderRegistry:
    """Central registry for provider instances.

    Manages the full lifecycle of providers:
    * Registration (by name)
    * Retrieval (by name or capability)
    * Health monitoring
    * Transaction recording
    * Retry configuration

    Usage::

        registry = ProviderRegistry()

        # Register a provider instance
        registry.register(my_llm_provider)

        # Use it
        llm = registry.get_llm()
        image = registry.get_image()

        # Get provider with retry
        result = await registry.call_with_retry(
            "gemini-llm",
            provider.generate,
            request,
        )
    """

    def __init__(
        self,
        config: Optional[ProviderSDKConfig] = None,
        manifest_hook: Optional[ManifestHook] = None,
    ) -> None:
        self._config = config or ProviderSDKConfig()
        self._providers: Dict[str, BaseProvider] = {}
        self._health_manager = HealthCheckManager(
            HealthCheckConfig(
                cache_ttl_s=self._config.health_check_interval_s,
            )
        )
        self._transaction_recorder = TransactionRecorder(
            manifest_hook=manifest_hook,
            max_history=self._config.transaction_max_history,
        )
        self._factory = ProviderFactory()
        self._primary_by_capability: Dict[ProviderCapability, str] = {}

    # -- properties --

    @property
    def config(self) -> ProviderSDKConfig:
        return self._config

    @property
    def factory(self) -> ProviderFactory:
        return self._factory

    @property
    def health_manager(self) -> HealthCheckManager:
        return self._health_manager

    @property
    def transaction_recorder(self) -> TransactionRecorder:
        return self._transaction_recorder

    # -- registration --

    def register(self, provider: BaseProvider) -> None:
        """Register a provider instance.

        Parameters
        ----------
        provider:
            Instantiated provider with ``name`` set.
        """
        if not provider.name:
            raise ProviderRegistrationError("Provider must have a 'name'.")

        self._providers[provider.name] = provider

        # Register health check
        if hasattr(provider, "health_check"):
            self._health_manager.register(provider.name, provider.health_check)

        # Register as primary for its capabilities if configured
        provider_config = self._config.get_provider(provider.name)
        if provider_config and provider_config.primary:
            for cap in provider.capabilities:
                self._primary_by_capability[cap] = provider.name
                logger.info(
                    "Registered '%s' as primary for %s",
                    provider.name,
                    cap.value,
                )

        logger.info("Registered provider: %s", provider.name)

    def unregister(self, name: str) -> None:
        """Unregister a provider and clean up."""
        provider = self._providers.pop(name, None)
        if provider:
            self._health_manager.unregister(name)
            # Remove from primary mappings
            for cap, pname in list(self._primary_by_capability.items()):
                if pname == name:
                    del self._primary_by_capability[cap]
            logger.info("Unregistered provider: %s", name)

    async def shutdown_all(self) -> None:
        """Shut down all registered providers."""
        for name, provider in list(self._providers.items()):
            try:
                await provider.shutdown()
                logger.debug("Shut down provider: %s", name)
            except Exception as exc:
                logger.warning("Error shutting down provider '%s': %s", name, exc)

    # -- retrieval --

    def get(self, name: str) -> Optional[BaseProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def get_required(self, name: str) -> BaseProvider:
        """Get a provider by name, raising if not found."""
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderNotAvailableError(name)
        return provider

    def get_by_capability(self, capability: ProviderCapability) -> List[BaseProvider]:
        """Get all providers that support a given capability."""
        return [
            p for p in self._providers.values()
            if capability in p.capabilities
        ]

    def get_primary(self, capability: ProviderCapability) -> Optional[BaseProvider]:
        """Get the primary provider for a capability.

        Looks up the primary by registered primary mapping, then
        falls back to the first enabled provider from config.
        """
        # Check explicit primary mapping
        name = self._primary_by_capability.get(capability)
        if name and name in self._providers:
            return self._providers[name]

        # Fall back to config
        cap_str = capability.value
        provider_config = self._config.get_primary(cap_str)
        if provider_config and provider_config.name in self._providers:
            return self._providers[provider_config.name]

        return None

    def get_chain(self, capability: ProviderCapability) -> List[BaseProvider]:
        """Get the provider chain for a capability (primary + fallbacks)."""
        cap_str = capability.value
        chain_configs = self._config.get_chain(cap_str)
        return [
            self._providers[pc.name]
            for pc in chain_configs
            if pc.name in self._providers
        ]

    def list_all(self) -> Dict[str, BaseProvider]:
        """List all registered providers."""
        return dict(self._providers)

    # -- retry-aware execution --

    async def call_with_retry(
        self,
        provider_name: str,
        operation: str,
        capability: str,
        coro_fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a provider operation with retry logic and transaction recording.

        Parameters
        ----------
        provider_name:
            Provider name (for logging and transaction recording).
        operation:
            Operation name (e.g. ``"generate"``).
        capability:
            Provider capability (e.g. ``"image"``).
        coro_fn:
            The async callable to execute.
        *args, **kwargs:
            Arguments to ``coro_fn``.

        Returns
        -------
        Any
            The result of ``coro_fn``.
        """
        provider_config = self._config.get_provider(provider_name)
        retry_config = provider_config.retry if provider_config else RetryConfig()

        async with self._transaction_recorder.record(
            provider_name, operation, capability
        ) as txn:
            result = await with_retry(retry_config, coro_fn, *args, **kwargs)

            # Try to extract token/cost info from the result
            if hasattr(result, "tokens_in"):
                txn.set_response(
                    tokens_in=getattr(result, "tokens_in", 0),
                    tokens_out=getattr(result, "tokens_out", 0),
                    estimated_cost=getattr(result, "estimated_cost_usd", 0.0),
                )
            return result

    # -- health --

    async def health_check_all(self) -> Dict[str, Any]:
        """Run health checks for all registered providers."""
        return await self._health_manager.check_all(force=True)

    async def health_check(self, provider_name: str) -> Any:
        """Run a health check for a specific provider."""
        return await self._health_manager.check(provider_name, force=True)

    # -- convenience accessors --

    def get_llm(self, name: Optional[str] = None) -> BaseProvider:
        """Get an LLM provider.  If no name, returns the primary."""
        if name:
            return self.get_required(name)
        primary = self.get_primary(ProviderCapability.LLM)
        if primary:
            return primary
        raise ProviderNotAvailableError("No LLM provider available")

    def get_image(self, name: Optional[str] = None) -> BaseProvider:
        """Get an image provider.  If no name, returns the primary."""
        if name:
            return self.get_required(name)
        primary = self.get_primary(ProviderCapability.IMAGE)
        if primary:
            return primary
        raise ProviderNotAvailableError("No image provider available")

    def get_audio(self, name: Optional[str] = None) -> BaseProvider:
        """Get an audio provider.  If no name, returns the primary."""
        if name:
            return self.get_required(name)
        primary = self.get_primary(ProviderCapability.AUDIO)
        if primary:
            return primary
        raise ProviderNotAvailableError("No audio provider available")