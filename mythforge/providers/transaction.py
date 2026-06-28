"""
Transaction recorder.

Records every provider interaction as a :class:`Transaction` object.
Provides hooks for writing transactions to the Manifest Engine,
cost aggregation, and diagnostics.

Usage::

    recorder = TransactionRecorder(manifest_hook=my_manifest_hook)

    async with recorder.record("gemini", "generate", "image") as txn:
        response = await provider.generate(request)
        txn.set_response(tokens_in=100, tokens_out=500, cost=0.02)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from .models import (
    Transaction,
    TransactionStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Manifest hook protocol
# ---------------------------------------------------------------------------

class ManifestHook:
    """Interface for recording transactions in the Manifest Engine.

    Implement this to bridge transactions into your manifest.
    The Manifest Engine does NOT need to know about providers directly —
    it receives already-formatted records via these hooks.

    Usage::

        class MyManifestHook(ManifestHook):
            def __init__(self, engine):
                self.engine = engine

            def on_transaction_complete(self, transaction):
                self.engine.record_cost(CostRecord(
                    stage=self.current_stage,
                    provider=transaction.provider,
                    operation=transaction.operation,
                    amount_usd=transaction.actual_cost_usd,
                    tokens_in=transaction.tokens_in,
                    tokens_out=transaction.tokens_out,
                ))
                self.engine.record_provider(ProviderRecord(
                    capability=transaction.capability,
                    provider=transaction.provider,
                    model=transaction.model,
                ))
    """

    def on_transaction_complete(self, transaction: Transaction) -> None:
        """Called when a transaction completes successfully."""
        pass

    def on_transaction_failed(self, transaction: Transaction) -> None:
        """Called when a transaction fails."""
        pass

    def on_transaction_retry(self, transaction: Transaction, attempt: int) -> None:
        """Called when a transaction is being retried."""
        pass


# ---------------------------------------------------------------------------
# Transaction Recorder
# ---------------------------------------------------------------------------

class TransactionRecorder:
    """Records provider interactions as :class:`Transaction` objects.

    Features:
    * Context manager for automatic start/complete/fail lifecycle
    * Aggregated cost tracking per provider and capability
    * Pluggable manifest hooks for persistence
    * In-memory transaction history with configurable limits

    Usage::

        recorder = TransactionRecorder()

        # Record a transaction
        async with recorder.record("gemini", "generate", "image") as txn:
            response = await provider.generate(request)
            txn.set_response(
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                estimated_cost=response.estimated_cost_usd,
            )

        # Query history
        costs = recorder.get_costs_by_provider()
        total = recorder.get_total_cost()
    """

    def __init__(
        self,
        manifest_hook: Optional[ManifestHook] = None,
        max_history: int = 1000,
    ) -> None:
        self._manifest_hook = manifest_hook
        self._max_history = max_history
        self._history: List[Transaction] = []
        self._costs_by_provider: Dict[str, float] = {}
        self._costs_by_capability: Dict[str, float] = {}
        self._costs_by_stage: Dict[str, float] = {}
        self._current_stage: str = ""

    @property
    def manifest_hook(self) -> Optional[ManifestHook]:
        return self._manifest_hook

    @manifest_hook.setter
    def manifest_hook(self, hook: Optional[ManifestHook]) -> None:
        self._manifest_hook = hook

    def set_stage(self, stage: str) -> None:
        """Set the current pipeline stage for cost attribution."""
        self._current_stage = stage

    @asynccontextmanager
    async def record(
        self,
        provider: str,
        operation: str,
        capability: str,
        *,
        model: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[TransactionContext]:
        """Context manager that records a provider transaction.

        Yields a :class:`TransactionContext` that the caller uses to
        set response details.  The transaction is automatically completed
        (or failed) when the context exits.

        Parameters
        ----------
        provider:
            Provider name (e.g. ``"gemini"``).
        operation:
            Operation name (e.g. ``"generate"``, ``"narrate"``).
        capability:
            Provider capability (e.g. ``"llm"``, ``"image"``).
        model:
            Model name (optional).
        metadata:
            Additional metadata to attach.

        Yields
        ------
        TransactionContext
            Use to set response details before the context exits.
        """
        txn = Transaction(
            provider=provider,
            operation=operation,
            capability=capability,
            model=model,
            metadata=metadata or {},
        )
        ctx = TransactionContext(txn)

        try:
            yield ctx
        except Exception as exc:
            # Failure path
            txn.complete(
                status=TransactionStatus.FAILURE,
                error=str(exc),
                error_type=type(exc).__name__,
                tokens_in=ctx.tokens_in,
                tokens_out=ctx.tokens_out,
                estimated_cost_usd=ctx.estimated_cost,
                actual_cost_usd=ctx.actual_cost,
                input_size_bytes=ctx.input_size,
                output_size_bytes=ctx.output_size,
            )
            self._record_transaction(txn, failed=True)
            raise
        else:
            # Success path
            if txn.status == TransactionStatus.SUCCESS:
                pass  # already completed by TransactionContext.set_response
            txn.complete(
                status=ctx.status or TransactionStatus.SUCCESS,
                tokens_in=ctx.tokens_in,
                tokens_out=ctx.tokens_out,
                estimated_cost_usd=ctx.estimated_cost,
                actual_cost_usd=ctx.actual_cost,
                input_size_bytes=ctx.input_size,
                output_size_bytes=ctx.output_size,
                metadata=ctx.extra_metadata,
            )
            self._record_transaction(txn, failed=False)

    def _record_transaction(self, txn: Transaction, *, failed: bool) -> None:
        """Store the transaction and notify hooks."""
        # Add to history
        self._history.append(txn)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Aggregate costs (only on success)
        if not failed:
            cost = txn.actual_cost_usd or txn.estimated_cost_usd
            if cost > 0:
                self._costs_by_provider[txn.provider] = (
                    self._costs_by_provider.get(txn.provider, 0.0) + cost
                )
                self._costs_by_capability[txn.capability] = (
                    self._costs_by_capability.get(txn.capability, 0.0) + cost
                )
                if self._current_stage:
                    self._costs_by_stage[self._current_stage] = (
                        self._costs_by_stage.get(self._current_stage, 0.0) + cost
                    )

        # Notify manifest hook
        if self._manifest_hook:
            try:
                if failed:
                    self._manifest_hook.on_transaction_failed(txn)
                else:
                    self._manifest_hook.on_transaction_complete(txn)
            except Exception as exc:
                logger.error("Manifest hook error: %s", exc)

        logger.debug(
            "Transaction recorded: provider=%s op=%s status=%s cost=%.6f retries=%d",
            txn.provider,
            txn.operation,
            txn.status.value,
            txn.actual_cost_usd or txn.estimated_cost_usd,
            txn.retries,
        )

    # -- query methods --

    def get_history(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get recent transaction history.

        Parameters
        ----------
        limit:
            Maximum number of transactions to return.
            If ``None``, returns all.
        """
        if limit:
            return list(self._history[-limit:])
        return list(self._history)

    def get_total_cost(self) -> float:
        """Get the total cost across all providers."""
        return sum(self._costs_by_provider.values())

    def get_costs_by_provider(self) -> Dict[str, float]:
        """Get cost breakdown by provider name."""
        return dict(self._costs_by_provider)

    def get_costs_by_capability(self) -> Dict[str, float]:
        """Get cost breakdown by capability (llm, image, audio)."""
        return dict(self._costs_by_capability)

    def get_costs_by_stage(self) -> Dict[str, float]:
        """Get cost breakdown by pipeline stage."""
        return dict(self._costs_by_stage)

    def get_transaction_count(self) -> int:
        """Get total number of recorded transactions."""
        return len(self._history)

    def get_failure_count(self) -> int:
        """Get number of failed transactions."""
        return sum(
            1 for txn in self._history
            if txn.status == TransactionStatus.FAILURE
        )

    def clear(self) -> None:
        """Clear all recorded transactions and cost aggregates."""
        self._history.clear()
        self._costs_by_provider.clear()
        self._costs_by_capability.clear()
        self._costs_by_stage.clear()


# ---------------------------------------------------------------------------
# Transaction Context (mutable helper inside the context manager)
# ---------------------------------------------------------------------------

class TransactionContext:
    """Mutable context for setting transaction response details.

    Passed to the caller inside ``TransactionRecorder.record()``.
    The caller sets response fields before the context exits.
    """

    def __init__(self, txn: Transaction) -> None:
        self._txn = txn
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.estimated_cost: float = 0.0
        self.actual_cost: float = 0.0
        self.input_size: int = 0
        self.output_size: int = 0
        self.status: Optional[TransactionStatus] = None
        self.extra_metadata: Dict[str, Any] = {}

    @property
    def transaction(self) -> Transaction:
        """Access the underlying transaction."""
        return self._txn

    def set_response(
        self,
        *,
        tokens_in: int = 0,
        tokens_out: int = 0,
        estimated_cost: float = 0.0,
        actual_cost: float = 0.0,
        input_size_bytes: int = 0,
        output_size_bytes: int = 0,
        status: Optional[TransactionStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set response details for the transaction.

        Call this before the context manager exits to record the
        outcome of the provider interaction.
        """
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.estimated_cost = estimated_cost
        self.actual_cost = actual_cost
        self.input_size = input_size_bytes
        self.output_size = output_size_bytes
        if status:
            self.status = status
        if metadata:
            self.extra_metadata.update(metadata)

    def set_retry(self) -> None:
        """Increment the retry counter on the transaction."""
        self._txn.retries += 1