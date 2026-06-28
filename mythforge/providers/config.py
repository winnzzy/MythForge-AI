"""
Provider configuration loader.

Reads provider configuration from dict/YAML sources and produces
structured :class:`ProviderConfig` objects.  No hardcoded provider names —
everything is configuration-driven.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import ProviderConfigError
from .retry import RetryConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

@dataclass
class ProviderConfig:
    """Configuration for a single provider instance.

    All fields are generic — no provider-specific logic.
    """

    name: str = ""                          # unique provider identifier
    type: str = ""                          # llm | image | audio
    enabled: bool = True
    primary: bool = False                   # is this the primary provider for its type?
    priority: int = 0                       # lower = higher priority (for fallback ordering)
    model: Optional[str] = None             # default model
    api_key_env: Optional[str] = None       # environment variable name for API key
    base_url: Optional[str] = None          # API base URL override
    timeout_s: float = 60.0                 # per-request timeout
    max_concurrent: int = 10                # max concurrent requests
    rate_limit_rpm: Optional[int] = None    # requests per minute limit
    retry: RetryConfig = field(default_factory=RetryConfig)
    health_check_enabled: bool = True
    options: Dict[str, Any] = field(default_factory=dict)  # provider-specific options

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled,
            "primary": self.primary,
            "priority": self.priority,
            "model": self.model,
            "api_key_env": self.api_key_env,
            "base_url": self.base_url,
            "timeout_s": self.timeout_s,
            "max_concurrent": self.max_concurrent,
            "rate_limit_rpm": self.rate_limit_rpm,
            "retry": self.retry.to_dict(),
            "health_check_enabled": self.health_check_enabled,
            "options": self.options,
        }


@dataclass
class ProviderSDKConfig:
    """Top-level configuration for the Provider SDK.

    Contains all provider configurations and global settings.
    """

    providers: List[ProviderConfig] = field(default_factory=list)
    default_retry: RetryConfig = field(default_factory=RetryConfig)
    default_timeout_s: float = 60.0
    health_check_interval_s: float = 300.0
    transaction_max_history: int = 1000
    fallback_enabled: bool = True
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "providers": [p.to_dict() for p in self.providers],
            "default_retry": self.default_retry.to_dict(),
            "default_timeout_s": self.default_timeout_s,
            "health_check_interval_s": self.health_check_interval_s,
            "transaction_max_history": self.transaction_max_history,
            "fallback_enabled": self.fallback_enabled,
            "options": self.options,
        }

    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """Get a provider config by name."""
        for p in self.providers:
            if p.name == name:
                return p
        return None

    def get_primary(self, provider_type: str) -> Optional[ProviderConfig]:
        """Get the primary provider for a given type (llm, image, audio)."""
        # First look for explicitly marked primary
        for p in self.providers:
            if p.type == provider_type and p.primary and p.enabled:
                return p
        # Fall back to highest priority enabled provider of that type
        candidates = [
            p for p in self.providers
            if p.type == provider_type and p.enabled
        ]
        if candidates:
            return min(candidates, key=lambda p: p.priority)
        return None

    def get_fallbacks(self, provider_type: str) -> List[ProviderConfig]:
        """Get fallback providers ordered by priority (excluding primary)."""
        primary = self.get_primary(provider_type)
        candidates = [
            p for p in self.providers
            if p.type == provider_type and p.enabled and p != primary
        ]
        return sorted(candidates, key=lambda p: p.priority)

    def get_chain(self, provider_type: str) -> List[ProviderConfig]:
        """Get the full provider chain: primary first, then fallbacks by priority."""
        primary = self.get_primary(provider_type)
        fallbacks = self.get_fallbacks(provider_type)
        if primary:
            return [primary] + fallbacks
        return fallbacks


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class ConfigLoader:
    """Loads and validates provider configuration from a dict source.

    Expected format::

        {
            "providers": [
                {
                    "name": "gemini",
                    "type": "llm",
                    "enabled": true,
                    "primary": true,
                    "model": "gemini-2.0-flash",
                    "api_key_env": "GEMINI_API_KEY",
                    "timeout_s": 30,
                    "retry": {
                        "max_retries": 3,
                        "base_delay_s": 1.0,
                    },
                    "options": {}
                }
            ],
            "default_timeout_s": 60,
            "fallback_enabled": true,
        }
    """

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProviderSDKConfig:
        """Load configuration from a dict.

        Parameters
        ----------
        data:
            Configuration dict (e.g. parsed from YAML/JSON).

        Returns
        -------
        ProviderSDKConfig
            Validated configuration object.

        Raises
        ------
        ProviderConfigError
            If the configuration is invalid.
        """
        if not isinstance(data, dict):
            raise ProviderConfigError("Configuration must be a dict.")

        config = ProviderSDKConfig()

        # Global settings
        config.default_timeout_s = data.get("default_timeout_s", 60.0)
        config.health_check_interval_s = data.get("health_check_interval_s", 300.0)
        config.transaction_max_history = data.get("transaction_max_history", 1000)
        config.fallback_enabled = data.get("fallback_enabled", True)
        config.options = data.get("options", {})

        # Default retry
        if "default_retry" in data:
            config.default_retry = cls._parse_retry(data["default_retry"])

        # Providers
        raw_providers = data.get("providers", [])
        if not isinstance(raw_providers, list):
            raise ProviderConfigError("'providers' must be a list.")

        seen_names: set = set()
        for raw in raw_providers:
            provider_config = cls._parse_provider(raw, config.default_retry)

            if provider_config.name in seen_names:
                raise ProviderConfigError(
                    f"Duplicate provider name: '{provider_config.name}'"
                )
            seen_names.add(provider_config.name)

            config.providers.append(provider_config)

        cls._validate(config)
        return config

    @classmethod
    def from_file(cls, path: str) -> ProviderSDKConfig:
        """Load configuration from a JSON or YAML file.

        Parameters
        ----------
        path:
            Path to the configuration file.

        Returns
        -------
        ProviderSDKConfig
            Validated configuration object.
        """
        import json

        with open(path, "r") as f:
            if path.endswith((".yaml", ".yml")):
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ProviderConfigError(
                        "PyYAML is required to load YAML configuration files."
                    )
            else:
                data = json.load(f)

        return cls.from_dict(data)

    # -- internal parsers --

    @classmethod
    def _parse_provider(
        cls,
        raw: Dict[str, Any],
        default_retry: RetryConfig,
    ) -> ProviderConfig:
        """Parse a single provider configuration dict."""
        if not isinstance(raw, dict):
            raise ProviderConfigError("Each provider entry must be a dict.")

        name = raw.get("name", "")
        if not name:
            raise ProviderConfigError("Provider must have a 'name'.")

        provider_type = raw.get("type", "")
        if provider_type not in ("llm", "image", "audio", ""):
            raise ProviderConfigError(
                f"Provider '{name}': invalid type '{provider_type}'. "
                f"Must be 'llm', 'image', or 'audio'."
            )

        retry_config = default_retry
        if "retry" in raw:
            retry_config = cls._parse_retry(raw["retry"])

        return ProviderConfig(
            name=name,
            type=provider_type,
            enabled=raw.get("enabled", True),
            primary=raw.get("primary", False),
            priority=raw.get("priority", 0),
            model=raw.get("model"),
            api_key_env=raw.get("api_key_env"),
            base_url=raw.get("base_url"),
            timeout_s=raw.get("timeout_s", 60.0),
            max_concurrent=raw.get("max_concurrent", 10),
            rate_limit_rpm=raw.get("rate_limit_rpm"),
            retry=retry_config,
            health_check_enabled=raw.get("health_check_enabled", True),
            options=raw.get("options", {}),
        )

    @classmethod
    def _parse_retry(cls, raw: Dict[str, Any]) -> RetryConfig:
        """Parse a retry configuration dict."""
        return RetryConfig(
            max_retries=raw.get("max_retries", 3),
            base_delay_s=raw.get("base_delay_s", 1.0),
            max_delay_s=raw.get("max_delay_s", 60.0),
            backoff_factor=raw.get("backoff_factor", 2.0),
            jitter=raw.get("jitter", True),
            timeout_s=raw.get("timeout_s"),
        )

    @classmethod
    def _validate(cls, config: ProviderSDKConfig) -> None:
        """Post-parse validation."""
        # Check for multiple primaries of the same type
        primaries_by_type: Dict[str, List[str]] = {}
        for p in config.providers:
            if p.primary:
                primaries_by_type.setdefault(p.type, []).append(p.name)

        for ptype, names in primaries_by_type.items():
            if len(names) > 1:
                raise ProviderConfigError(
                    f"Multiple primary providers for type '{ptype}': {names}. "
                    f"Only one primary is allowed per type."
                )