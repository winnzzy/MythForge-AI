"""
Cost estimation and tracking for OpenAI models.

Pricing is loaded from configuration — never hardcoded.
This module provides a registry of model pricing and utilities
for estimating costs before and after API calls.

All prices are per 1M tokens (input/output).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model pricing registry
# ---------------------------------------------------------------------------

@dataclass
class ModelPricing:
    """Pricing for a single model (per 1M tokens)."""

    input_per_mtok: float = 0.0     # USD per 1M input tokens
    output_per_mtok: float = 0.0    # USD per 1M output tokens
    cached_input_per_mtok: float = 0.0  # USD per 1M cached input tokens


# Default pricing — can be overridden at runtime via configuration.
# Prices in USD per 1M tokens.
MODEL_PRICING: Dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing(
        input_per_mtok=2.50,
        output_per_mtok=10.00,
        cached_input_per_mtok=1.25,
    ),
    "gpt-4o-mini": ModelPricing(
        input_per_mtok=0.15,
        output_per_mtok=0.60,
        cached_input_per_mtok=0.075,
    ),
    "gpt-4-turbo": ModelPricing(
        input_per_mtok=10.00,
        output_per_mtok=30.00,
        cached_input_per_mtok=5.00,
    ),
    "gpt-4": ModelPricing(
        input_per_mtok=30.00,
        output_per_mtok=60.00,
    ),
    "gpt-3.5-turbo": ModelPricing(
        input_per_mtok=0.50,
        output_per_mtok=1.50,
        cached_input_per_mtok=0.25,
    ),
    "o1": ModelPricing(
        input_per_mtok=15.00,
        output_per_mtok=60.00,
        cached_input_per_mtok=7.50,
    ),
    "o1-mini": ModelPricing(
        input_per_mtok=3.00,
        output_per_mtok=12.00,
        cached_input_per_mtok=1.50,
    ),
    "o1-pro": ModelPricing(
        input_per_mtok=150.00,
        output_per_mtok=600.00,
    ),
    "o3-mini": ModelPricing(
        input_per_mtok=1.10,
        output_per_mtok=4.40,
        cached_input_per_mtok=0.55,
    ),
}


# ---------------------------------------------------------------------------
# Cost Estimator
# ---------------------------------------------------------------------------

class CostEstimator:
    """Estimates and tracks costs for OpenAI API calls.

    Usage::

        estimator = CostEstimator()

        # Pre-call estimate (if you know approximate token counts)
        estimate = estimator.estimate("gpt-4o", tokens_in=1000, tokens_out=500)

        # Post-call cost calculation
        cost = estimator.calculate("gpt-4o", tokens_in=1042, tokens_out=537)

        # Register pricing for a new model
        estimator.register_pricing("my-model", ModelPricing(
            input_per_mtok=5.0,
            output_per_mtok=15.0,
        ))

        # Total cost tracking
        total = estimator.get_total_cost()
    """

    def __init__(self, pricing: Optional[Dict[str, ModelPricing]] = None) -> None:
        self._pricing: Dict[str, ModelPricing] = dict(pricing or MODEL_PRICING)
        self._total_cost: float = 0.0
        self._costs_by_model: Dict[str, float] = {}
        self._total_tokens_in: int = 0
        self._total_tokens_out: int = 0

    def register_pricing(self, model: str, pricing: ModelPricing) -> None:
        """Register or update pricing for a model.

        Parameters
        ----------
        model:
            Model name (must match API model name exactly).
        pricing:
            Pricing information.
        """
        self._pricing[model] = pricing
        logger.debug("Registered pricing for model '%s'", model)

    def register_pricing_from_dict(self, model: str, data: Dict[str, Any]) -> None:
        """Register pricing from a dict.

        Parameters
        ----------
        model:
            Model name.
        data:
            Dict with keys: input_per_mtok, output_per_mtok, cached_input_per_mtok.
        """
        self._pricing[model] = ModelPricing(
            input_per_mtok=data.get("input_per_mtok", 0.0),
            output_per_mtok=data.get("output_per_mtok", 0.0),
            cached_input_per_mtok=data.get("cached_input_per_mtok", 0.0),
        )

    def estimate(
        self,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> float:
        """Estimate cost before an API call.

        Parameters
        ----------
        model:
            Model name.
        tokens_in:
            Estimated input tokens.
        tokens_out:
            Estimated output tokens.

        Returns
        -------
        float
            Estimated cost in USD.
        """
        pricing = self._pricing.get(model)
        if not pricing:
            logger.warning("No pricing data for model '%s', returning 0.0", model)
            return 0.0

        cost = (
            (tokens_in / 1_000_000) * pricing.input_per_mtok
            + (tokens_out / 1_000_000) * pricing.output_per_mtok
        )
        return round(cost, 8)

    def calculate(
        self,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        *,
        cached_tokens: int = 0,
    ) -> float:
        """Calculate cost after an API call and update running totals.

        Parameters
        ----------
        model:
            Model name.
        tokens_in:
            Actual input tokens used.
        tokens_out:
            Actual output tokens generated.
        cached_tokens:
            Number of input tokens that were cached (cheaper rate).

        Returns
        -------
        float
            Actual cost in USD.
        """
        pricing = self._pricing.get(model)
        if not pricing:
            logger.warning("No pricing data for model '%s', returning 0.0", model)
            return 0.0

        # Calculate input cost (cached tokens at reduced rate)
        non_cached_in = tokens_in - cached_tokens
        input_cost = (non_cached_in / 1_000_000) * pricing.input_per_mtok
        if cached_tokens > 0 and pricing.cached_input_per_mtok > 0:
            input_cost += (cached_tokens / 1_000_000) * pricing.cached_input_per_mtok

        output_cost = (tokens_out / 1_000_000) * pricing.output_per_mtok
        cost = input_cost + output_cost

        # Update running totals
        self._total_cost += cost
        self._costs_by_model[model] = self._costs_by_model.get(model, 0.0) + cost
        self._total_tokens_in += tokens_in
        self._total_tokens_out += tokens_out

        return round(cost, 8)

    def get_total_cost(self) -> float:
        """Get the total accumulated cost in USD."""
        return round(self._total_cost, 8)

    def get_costs_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model name."""
        return {k: round(v, 8) for k, v in self._costs_by_model.items()}

    def get_total_tokens(self) -> Dict[str, int]:
        """Get total tokens consumed."""
        return {
            "tokens_in": self._total_tokens_in,
            "tokens_out": self._total_tokens_out,
        }

    def get_pricing(self, model: str) -> Optional[ModelPricing]:
        """Get pricing data for a model."""
        return self._pricing.get(model)

    def list_models(self) -> list:
        """List all models with registered pricing."""
        return list(self._pricing.keys())

    def reset(self) -> None:
        """Reset all cost tracking."""
        self._total_cost = 0.0
        self._costs_by_model.clear()
        self._total_tokens_in = 0
        self._total_tokens_out = 0