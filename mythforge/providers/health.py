"""
Health check framework.

Tracks the health status of registered providers over time.
Results are cached with a configurable TTL so that frequent checks
don't overwhelm provider APIs.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .models import HealthCheckResult, ProviderStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class HealthCheckConfig:
    """Configuration for the health check system."""

    enabled: bool = True
    check_interval_s: float = 300.0          # background check interval
    cache_ttl_s: float = 60.0                # how long a cached result is valid
    timeout_s: float = 10.0                  # per-check timeout
    failure_threshold: int = 3               # consecutive failures before UNHEALTHY
    degraded_threshold_ms: float = 5000.0    # latency above this → DEGRADED


# ---------------------------------------------------------------------------
# Health Check Manager
# ---------------------------------------------------------------------------

class HealthCheckManager:
    """Manages health checks for all registered providers.

    Caches results, tracks consecutive failures, and provides
    aggregate health status.

    Usage::

        manager = HealthCheckManager(config)

        # Register a check function for a provider
        manager.register("gemini", provider.health_check)

        # Run a check
        result = await manager.check("gemini")

        # Get cached status
        status = manager.get_status("gemini")
    """

    def __init__(self, config: Optional[HealthCheckConfig] = None) -> None:
        self._config = config or HealthCheckConfig()
        self._checks: Dict[str, Callable[..., Coroutine[Any, Any, HealthCheckResult]]] = {}
        self._cache: Dict[str, _CachedResult] = {}
        self._consecutive_failures: Dict[str, int] = {}
        self._last_success: Dict[str, str] = {}

    @property
    def config(self) -> HealthCheckConfig:
        return self._config

    def register(
        self,
        provider_name: str,
        check_fn: Callable[..., Coroutine[Any, Any, HealthCheckResult]],
    ) -> None:
        """Register a health-check coroutine for a provider.

        Parameters
        ----------
        provider_name:
            Unique provider identifier.
        check_fn:
            An async callable that returns a :class:`HealthCheckResult`.
        """
        self._checks[provider_name] = check_fn
        self._consecutive_failures[provider_name] = 0
        logger.debug("Registered health check for provider '%s'", provider_name)

    def unregister(self, provider_name: str) -> None:
        """Remove a provider's health check registration."""
        self._checks.pop(provider_name, None)
        self._cache.pop(provider_name, None)
        self._consecutive_failures.pop(provider_name, None)
        self._last_success.pop(provider_name, None)

    async def check(self, provider_name: str, force: bool = False) -> HealthCheckResult:
        """Run a health check for a provider.

        Returns a cached result if available and not expired.
        Use ``force=True`` to bypass the cache.

        Parameters
        ----------
        provider_name:
            The provider to check.
        force:
            If ``True``, ignore cached results and run a fresh check.

        Returns
        -------
        HealthCheckResult
            The health check result.

        Raises
        ------
        KeyError
            If no check function is registered for the provider.
        """
        if provider_name not in self._checks:
            return HealthCheckResult(
                provider=provider_name,
                status=ProviderStatus.UNKNOWN,
                available=False,
                failure_reason="No health check registered",
            )

        # Check cache
        if not force and provider_name in self._cache:
            cached = self._cache[provider_name]
            if (time.monotonic() - cached.created_at) < self._config.cache_ttl_s:
                return cached.result

        # Run check with timeout
        result = await self._run_check(provider_name)

        # Update cache
        self._cache[provider_name] = _CachedResult(
            result=result,
            created_at=time.monotonic(),
        )

        # Track consecutive failures
        if result.status == ProviderStatus.HEALTHY:
            self._consecutive_failures[provider_name] = 0
            self._last_success[provider_name] = result.checked_at
            result.last_success_at = result.checked_at
        else:
            self._consecutive_failures[provider_name] = (
                self._consecutive_failures.get(provider_name, 0) + 1
            )

        # Apply degradation logic
        result = self._apply_thresholds(provider_name, result)

        return result

    async def check_all(self, force: bool = False) -> Dict[str, HealthCheckResult]:
        """Run health checks for all registered providers concurrently.

        Returns
        -------
        Dict[str, HealthCheckResult]
            Map of provider name to health check result.
        """
        if not self._checks:
            return {}

        tasks = {
            name: self.check(name, force=force)
            for name in self._checks
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        output: Dict[str, HealthCheckResult] = {}
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                output[name] = HealthCheckResult(
                    provider=name,
                    status=ProviderStatus.UNHEALTHY,
                    available=False,
                    failure_reason=str(result),
                )
            else:
                output[name] = result

        return output

    def get_status(self, provider_name: str) -> ProviderStatus:
        """Get the cached status of a provider without running a new check.

        Returns
        -------
        ProviderStatus
            The cached status, or UNKNOWN if no check has been run.
        """
        if provider_name in self._cache:
            return self._cache[provider_name].result.status
        return ProviderStatus.UNKNOWN

    def get_last_success(self, provider_name: str) -> Optional[str]:
        """Get the timestamp of the provider's last successful health check."""
        return self._last_success.get(provider_name)

    def get_consecutive_failures(self, provider_name: str) -> int:
        """Get the number of consecutive health-check failures."""
        return self._consecutive_failures.get(provider_name, 0)

    def is_healthy(self, provider_name: str) -> bool:
        """Check if a provider is considered healthy based on cached status."""
        return self.get_status(provider_name) == ProviderStatus.HEALTHY

    def get_all_statuses(self) -> Dict[str, ProviderStatus]:
        """Get cached statuses for all registered providers."""
        return {
            name: self.get_status(name)
            for name in self._checks
        }

    def invalidate_cache(self, provider_name: Optional[str] = None) -> None:
        """Invalidate cached health check results.

        Parameters
        ----------
        provider_name:
            If provided, only invalidate this provider's cache.
            If ``None``, invalidate all cached results.
        """
        if provider_name:
            self._cache.pop(provider_name, None)
        else:
            self._cache.clear()

    # -- internal --

    async def _run_check(self, provider_name: str) -> HealthCheckResult:
        """Execute the health check with timeout."""
        check_fn = self._checks[provider_name]
        try:
            return await asyncio.wait_for(
                check_fn(),
                timeout=self._config.timeout_s,
            )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                provider=provider_name,
                status=ProviderStatus.UNHEALTHY,
                available=False,
                failure_reason=f"Health check timed out after {self._config.timeout_s}s",
            )
        except Exception as exc:
            return HealthCheckResult(
                provider=provider_name,
                status=ProviderStatus.UNHEALTHY,
                available=False,
                failure_reason=str(exc),
            )

    def _apply_thresholds(
        self,
        provider_name: str,
        result: HealthCheckResult,
    ) -> HealthCheckResult:
        """Apply failure-count and latency thresholds."""
        # Consecutive failure threshold
        if (
            result.status != ProviderStatus.UNHEALTHY
            and self._consecutive_failures.get(provider_name, 0) >= self._config.failure_threshold
        ):
            result.status = ProviderStatus.UNHEALTHY
            result.available = False
            result.failure_reason = (
                f"Consecutive failures ({self._consecutive_failures[provider_name]}) "
                f"exceed threshold ({self._config.failure_threshold})"
            )

        # Latency threshold
        if (
            result.status == ProviderStatus.HEALTHY
            and result.latency_ms > self._config.degraded_threshold_ms
        ):
            result.status = ProviderStatus.DEGRADED

        return result


# ---------------------------------------------------------------------------
# Internal cache entry
# ---------------------------------------------------------------------------

@dataclass
class _CachedResult:
    """A cached health check result with timestamp."""

    result: HealthCheckResult
    created_at: float = field(default_factory=time.monotonic)