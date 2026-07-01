"""
OpenAI provider configuration.

Configuration-driven model selection — no hardcoded model names.
Supports role-based model mapping (default, reasoning, fast, vision).
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from mythforge.providers.exceptions import ProviderConfigError


# ---------------------------------------------------------------------------
# Model roles
# ---------------------------------------------------------------------------

class ModelRole(str, enum.Enum):
    """Semantic model roles for configuration-driven selection."""

    DEFAULT = "default"
    REASONING = "reasoning"
    FAST = "fast"
    VISION = "vision"


# ---------------------------------------------------------------------------
# OpenAI-specific configuration
# ---------------------------------------------------------------------------

@dataclass
class OpenAIConfig:
    """Configuration for the OpenAI provider.

    All model names come from configuration — never hardcoded.
    """

    # Authentication
    api_key: Optional[str] = None               # explicit key (overrides env)
    api_key_env: str = "OPENAI_API_KEY"          # env var name

    # Base URL (for proxies / Azure)
    base_url: Optional[str] = None
    organization: Optional[str] = None

    # Model selection by role — all from config, no defaults
    default_model: Optional[str] = None
    reasoning_model: Optional[str] = None
    fast_model: Optional[str] = None
    vision_model: Optional[str] = None

    # Generation defaults
    max_output_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    timeout_s: float = 60.0

    # Retry
    max_retries: int = 3

    # Structured output
    structured_output_enabled: bool = True

    # Streaming
    streaming_enabled: bool = True

    # Provider-specific options
    options: Dict[str, Any] = field(default_factory=dict)

    def resolve_api_key(self) -> str:
        """Resolve the API key from explicit value or environment variable.

        Returns
        -------
        str
            The resolved API key.

        Raises
        ------
        ProviderConfigError
            If no API key can be resolved.
        """
        key = self.api_key or os.environ.get(self.api_key_env, "")
        if not key:
            raise ProviderConfigError(
                f"No API key found. Set '{self.api_key_env}' environment variable "
                f"or pass api_key directly."
            )
        return key

    def resolve_model(self, role: Optional[ModelRole] = None) -> str:
        """Resolve the model name for a given role.

        Parameters
        ----------
        role:
            The semantic role. If None, uses default_model.

        Returns
        -------
        str
            The resolved model name.

        Raises
        ------
        ProviderConfigError
            If no model is configured for the requested role.
        """
        role = role or ModelRole.DEFAULT
        model_map = {
            ModelRole.DEFAULT: self.default_model,
            ModelRole.REASONING: self.reasoning_model,
            ModelRole.FAST: self.fast_model,
            ModelRole.VISION: self.vision_model,
        }
        model = model_map.get(role)
        if not model:
            # Fall back to default_model for any role
            model = self.default_model
        if not model:
            raise ProviderConfigError(
                f"No model configured for role '{role.value}'. "
                f"Set 'default_model' in provider configuration."
            )
        return model

    def get_model_for_request(self, request_model: Optional[str] = None) -> str:
        """Get the model to use for a request.

        Priority: request-level model > config default_model.

        Parameters
        ----------
        request_model:
            Model specified in the request. If provided, takes priority.

        Returns
        -------
        str
            The model name to use.
        """
        if request_model:
            return request_model
        return self.resolve_model(ModelRole.DEFAULT)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to dict (masks API key)."""
        return {
            "api_key_env": self.api_key_env,
            "base_url": self.base_url,
            "organization": self.organization,
            "default_model": self.default_model,
            "reasoning_model": self.reasoning_model,
            "fast_model": self.fast_model,
            "vision_model": self.vision_model,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "timeout_s": self.timeout_s,
            "max_retries": self.max_retries,
            "structured_output_enabled": self.structured_output_enabled,
            "streaming_enabled": self.streaming_enabled,
            "options": self.options,
        }

    @classmethod
    def from_provider_config(cls, pc: Any) -> "OpenAIConfig":
        """Build from a generic :class:`ProviderConfig` object.

        Parameters
        ----------
        pc:
            A :class:`mythforge.providers.config.ProviderConfig` instance.

        Returns
        -------
        OpenAIConfig
            Populated configuration.
        """
        opts = pc.options or {}
        return cls(
            api_key_env=pc.api_key_env or "OPENAI_API_KEY",
            base_url=pc.base_url,
            organization=opts.get("organization"),
            default_model=pc.model or opts.get("default_model"),
            reasoning_model=opts.get("reasoning_model"),
            fast_model=opts.get("fast_model"),
            vision_model=opts.get("vision_model"),
            max_output_tokens=opts.get("max_output_tokens", 4096),
            temperature=opts.get("temperature", 0.7),
            top_p=opts.get("top_p", 1.0),
            timeout_s=pc.timeout_s,
            max_retries=pc.retry.max_retries if pc.retry else 3,
            structured_output_enabled=opts.get("structured_output_enabled", True),
            streaming_enabled=opts.get("streaming_enabled", True),
            options={k: v for k, v in opts.items() if k not in {
                "organization", "default_model", "reasoning_model",
                "fast_model", "vision_model", "max_output_tokens",
                "temperature", "top_p", "structured_output_enabled",
                "streaming_enabled",
            }},
        )