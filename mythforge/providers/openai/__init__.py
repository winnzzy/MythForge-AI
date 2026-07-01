"""
OpenAI provider — implements the Responses API for MythForge.

This module exposes the :class:`OpenAIProvider` which implements
:class:`LLMProvider` using the official OpenAI Python SDK and the
recommended Responses API.

Usage::

    from mythforge.providers.openai import OpenAIProvider, OpenAIConfig

    config = OpenAIConfig(
        api_key="sk-...",
        default_model="gpt-4o",
    )
    provider = OpenAIProvider(config)
    await provider.initialise()
    response = await provider.generate(request)
"""

from .config import OpenAIConfig, ModelRole
from .provider import OpenAIProvider
from .mapper import OpenAIRequestMapper, OpenAIResponseMapper
from .cost import CostEstimator, MODEL_PRICING
from .metrics import ProviderMetrics

__all__ = [
    "OpenAIConfig",
    "OpenAIProvider",
    "ModelRole",
    "OpenAIRequestMapper",
    "OpenAIResponseMapper",
    "CostEstimator",
    "MODEL_PRICING",
    "ProviderMetrics",
]