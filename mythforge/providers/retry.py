"""
Retry framework with exponential backoff.

Provides a generic, configurable retry wrapper that can be applied to any
async provider operation.  Retry decisions are based on exception types.

Usage::

    config = RetryConfig(max_retries=3, base_delay_s=1.0)
    result = await with_retry(config, my_operation, arg1, arg2)
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional, Set, Tuple, Type

from .exceptions import (
    MaxRetriesExceededError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class RetryConfig:
    """Configuration for the retry framework."""

    max_retries: int = 3
    base_delay_s: float = 1.0
    max_delay_s: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.5           # ±50 % of computed delay
    timeout_s: Optional[float] = None   # per-attempt timeout

    # Exception types that should be retried
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ProviderUnavailableError,
        ProviderTimeoutError,
        ProviderRateLimitError,
    )

    # Exception types that should NEVER be retried
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (
        ProviderError,  # catch-all non-retryable; specific retryable types checked first
    )

    def to_dict(self) -> dict:
        return {
            "max_retries": self.max_retries,
            "base_delay_s": self.base_delay_s,
            "max_delay_s": self.max_delay_s,
            "backoff_factor": self.backoff_factor,
            "jitter": self.jitter,
            "timeout_s": self.timeout_s,
        }


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

def compute_delay(config: RetryConfig, attempt: int) -> float:
    """Compute the delay before the next retry attempt.

    Uses exponential backoff with optional jitter.

    Parameters
    ----------
    config:
        Retry configuration.
    attempt:
        Zero-based attempt number (0 = first retry).

    Returns
    -------
    float
        Delay in seconds.
    """
    delay = config.base_delay_s * (config.backoff_factor ** attempt)
    delay = min(delay, config.max_delay_s)

    if config.jitter:
        jitter_amount = delay * config.jitter_range
        delay += random.uniform(-jitter_amount, jitter_amount)
        delay = max(0.0, delay)

    return delay


def is_retryable(config: RetryConfig, exc: Exception) -> bool:
    """Determine whether an exception is retryable.

    Checks against the retryable and non-retryable exception lists.
    Retryable exceptions are checked first (more specific).

    Parameters
    ----------
    config:
        Retry configuration.
    exc:
        The exception to classify.

    Returns
    -------
    bool
        ``True`` if the operation should be retried.
    """
    # If the exception has an explicit is_retryable flag, honour it
    if isinstance(exc, ProviderError):
        # Check specific retryable subtypes first
        for retryable_type in config.retryable_exceptions:
            if isinstance(exc, retryable_type):
                return True
        # If it's a ProviderError but not a retryable subtype
        return False

    # Check non-retryable types
    for non_retryable_type in config.non_retryable_exceptions:
        if isinstance(exc, non_retryable_type):
            return False

    # Unknown exception — default to retryable for network/transient errors
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


async def with_retry(
    config: RetryConfig,
    coro_fn: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute an async callable with retry logic.

    Parameters
    ----------
    config:
        Retry configuration.
    coro_fn:
        An async callable (coroutine function).
    *args:
        Positional arguments forwarded to ``coro_fn``.
    **kwargs:
        Keyword arguments forwarded to ``coro_fn``.

    Returns
    -------
    Any
        The return value of ``coro_fn``.

    Raises
    ------
    MaxRetriesExceededError
        If all retry attempts are exhausted.
    Exception
        Any non-retryable exception is re-raised immediately.
    """
    last_error: Optional[Exception] = None

    for attempt in range(config.max_retries + 1):
        try:
            if config.timeout_s:
                return await asyncio.wait_for(
                    coro_fn(*args, **kwargs),
                    timeout=config.timeout_s,
                )
            return await coro_fn(*args, **kwargs)

        except Exception as exc:
            last_error = exc

            # Check if non-retryable
            if not is_retryable(config, exc):
                logger.debug(
                    "Non-retryable error on attempt %d: %s",
                    attempt + 1,
                    exc,
                )
                raise

            # Check if we have retries left
            if attempt >= config.max_retries:
                break

            # Compute delay and log
            delay = compute_delay(config, attempt)
            logger.warning(
                "Retryable error on attempt %d/%d for '%s': %s — retrying in %.2fs",
                attempt + 1,
                config.max_retries + 1,
                getattr(coro_fn, "__name__", str(coro_fn)),
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    # All retries exhausted
    raise MaxRetriesExceededError(
        provider=getattr(last_error, "provider", "unknown"),
        operation=getattr(last_error, "operation", getattr(coro_fn, "__name__", "unknown")),
        attempts=config.max_retries + 1,
        last_error=last_error,
    )


# ---------------------------------------------------------------------------
# Pre-built configurations
# ---------------------------------------------------------------------------

RETRY_CONSERVATIVE = RetryConfig(
    max_retries=2,
    base_delay_s=2.0,
    max_delay_s=30.0,
    backoff_factor=2.0,
    jitter=True,
)

RETRY_AGGRESSIVE = RetryConfig(
    max_retries=5,
    base_delay_s=0.5,
    max_delay_s=120.0,
    backoff_factor=3.0,
    jitter=True,
)

RETRY_NONE = RetryConfig(
    max_retries=0,
    base_delay_s=0.0,
    backoff_factor=1.0,
    jitter=False,
)