"""
Provider SDK exceptions.

All provider-related errors inherit from ``ProviderError``.
Each exception carries enough context for logging, retry decisions,
and manifest error recording.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ProviderError(Exception):
    """Base exception for all provider-related failures."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        operation: str = "",
        is_retryable: bool = False,
        status_code: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.operation = operation
        self.is_retryable = is_retryable
        self.status_code = status_code
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": type(self).__name__,
            "message": str(self),
            "provider": self.provider,
            "operation": self.operation,
            "is_retryable": self.is_retryable,
            "status_code": self.status_code,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Configuration & Registration
# ---------------------------------------------------------------------------

class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not registered."""

    def __init__(self, provider_name: str, **kwargs: Any) -> None:
        super().__init__(
            f"Provider '{provider_name}' is not registered.",
            provider=provider_name,
            is_retryable=False,
            **kwargs,
        )


class ProviderNotAvailableError(ProviderError):
    """Raised when a provider is requested but unavailable."""

    def __init__(self, provider_name: str, **kwargs: Any) -> None:
        super().__init__(
            f"Provider '{provider_name}' is not available.",
            provider=provider_name,
            is_retryable=False,
            **kwargs,
        )


class ProviderRegistrationError(ProviderError):
    """Raised when provider registration fails."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, is_retryable=False, **kwargs)


class ProviderConfigError(ProviderError):
    """Raised when provider configuration is invalid or missing."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, is_retryable=False, **kwargs)


class DuplicateProviderError(ProviderError):
    """Raised when attempting to register a provider that already exists."""

    def __init__(self, provider_name: str, **kwargs: Any) -> None:
        super().__init__(
            f"Provider '{provider_name}' is already registered.",
            provider=provider_name,
            is_retryable=False,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Runtime / Network
# ---------------------------------------------------------------------------

class ProviderUnavailableError(ProviderError):
    """Raised when a provider is temporarily unavailable (e.g. rate-limited)."""

    def __init__(
        self,
        provider_or_message: str,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if message is None:
            msg = provider_or_message
            provider = kwargs.pop("provider", "")
        else:
            msg = message
            provider = provider_or_message
        super().__init__(msg, provider=provider, is_retryable=True, **kwargs)


class ProviderTimeoutError(ProviderError):
    """Raised when a provider call exceeds the configured timeout."""

    def __init__(
        self,
        provider: str,
        operation: str,
        timeout_s: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            f"Provider '{provider}' timed out after {timeout_s}s on '{operation}'.",
            provider=provider,
            operation=operation,
            is_retryable=True,
            **kwargs,
        )


class ProviderRateLimitError(ProviderUnavailableError):
    """Raised when a provider returns a rate-limit response (HTTP 429)."""

    def __init__(
        self,
        provider: str,
        retry_after_s: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        self.retry_after_s = retry_after_s
        super().__init__(
            f"Provider '{provider}' rate-limited."
            + (f" Retry after {retry_after_s}s." if retry_after_s else ""),
            provider=provider,
            status_code=429,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class ProviderUnhealthyError(ProviderError):
    """Raised when a provider fails its health check."""

    def __init__(self, provider: str, reason: str, **kwargs: Any) -> None:
        super().__init__(
            f"Provider '{provider}' is unhealthy: {reason}",
            provider=provider,
            is_retryable=True,
            **kwargs,
        )


class MaxRetriesExceededError(ProviderError):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        provider: str = "",
        operation: str = "",
        attempts: Optional[int] = None,
        last_error: Optional[Exception] = None,
        max_retries: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        if attempts is None:
            attempts = (max_retries or 0) + 1
        self.attempts = attempts
        self.max_retries = max_retries if max_retries is not None else attempts - 1
        self.last_error = last_error
        last_msg = f": {last_error}" if last_error else ""
        super().__init__(
            f"Provider '{provider}' failed after {attempts} attempts on '{operation}'{last_msg}",
            provider=provider,
            operation=operation,
            is_retryable=False,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Non-retryable API errors
# ---------------------------------------------------------------------------

class ProviderAuthError(ProviderError):
    """Raised on authentication/authorisation failures (HTTP 401/403)."""

    def __init__(self, provider: str, **kwargs: Any) -> None:
        super().__init__(
            f"Provider '{provider}' authentication failed.",
            provider=provider,
            is_retryable=False,
            status_code=401,
            **kwargs,
        )


class ProviderBadRequestError(ProviderError):
    """Raised on invalid request parameters (HTTP 400/422)."""

    def __init__(self, provider: str, message: str, **kwargs: Any) -> None:
        super().__init__(
            f"Provider '{provider}' rejected request: {message}",
            provider=provider,
            is_retryable=False,
            status_code=400,
            **kwargs,
        )


class ProviderAPIError(ProviderError):
    """Raised on non-authentication provider API failures."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, is_retryable=True, **kwargs)


class ProviderContentPolicyError(ProviderError):
    """Raised when content violates the provider's usage policy."""

    def __init__(self, provider: str, message: str, **kwargs: Any) -> None:
        super().__init__(
            f"Provider '{provider}' content policy violation: {message}",
            provider=provider,
            is_retryable=False,
            **kwargs,
        )