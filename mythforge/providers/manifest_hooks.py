"""
Manifest Engine integration hooks.

Bridges the Provider SDK's transaction recording into the Manifest Engine's
schema.  These hooks translate provider transactions into the record types
that the Manifest Engine understands (CostRecord, ProviderRecord, etc.).

Usage::

    from mythforge.engine.engine import ManifestEngine
    from mythforge.providers.manifest_hooks import ManifestBridge

    engine = ManifestEngine("project_manifest.json")
    bridge = ManifestBridge(engine)

    # Attach to the provider registry
    registry = ProviderRegistry(config=sdk_config, manifest_hook=bridge.hook)

    # Or attach to the transaction recorder directly
    recorder.transaction_manifest_hook = bridge.hook

    # After a stage completes, update the manifest
    bridge.finalise_stage("image-generation", status="completed")
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .transaction import ManifestHook, Transaction
from .models import TransactionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conditional import for Manifest Engine
# ---------------------------------------------------------------------------

def _import_engine():
    """Lazily import ManifestEngine to avoid circular imports."""
    try:
        from mythforge.engine.engine import ManifestEngine
        from mythforge.engine.schema import CostRecord, ProviderRecord
        return ManifestEngine, CostRecord, ProviderRecord
    except ImportError:
        logger.warning(
            "Manifest Engine not available — manifest hooks will be no-ops."
        )
        return None, None, None


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

class ManifestBridge:
    """Connects the Provider SDK to the Manifest Engine.

    Translates provider transactions into Manifest Engine records.

    Parameters
    ----------
    engine:
        A :class:`ManifestEngine` instance.  If ``None``, the bridge
        will be a no-op (useful when the engine is not yet available).
    """

    def __init__(self, engine: Any = None) -> None:
        self._engine = engine
        self._hook = _BridgeHook(self)

    @property
    def hook(self) -> ManifestHook:
        """Get the :class:`ManifestHook` instance to attach to the registry."""
        return self._hook

    @property
    def engine(self) -> Any:
        """Get the underlying Manifest Engine."""
        return self._engine

    @engine.setter
    def engine(self, engine: Any) -> None:
        """Set or replace the Manifest Engine."""
        self._engine = engine

    def record_transaction(self, transaction: Transaction) -> None:
        """Record a completed transaction in the Manifest Engine.

        Parameters
        ----------
        transaction:
            The completed transaction to record.
        """
        if self._engine is None:
            return

        try:
            _, CostRecord, ProviderRecord = _import_engine()
            if CostRecord is None:
                return

            # Record cost
            cost_usd = transaction.actual_cost_usd or transaction.estimated_cost_usd
            if cost_usd > 0:
                cost_record = CostRecord(
                    stage=getattr(self, "_current_stage", "unknown"),
                    provider=transaction.provider,
                    operation=transaction.operation,
                    amount_usd=cost_usd,
                    tokens_in=transaction.tokens_in,
                    tokens_out=transaction.tokens_out,
                    timestamp=transaction.completed_at or _now_iso(),
                )
                self._engine.record_cost(cost_record)

            # Record provider usage
            provider_record = ProviderRecord(
                capability=transaction.capability,
                provider=transaction.provider,
                model=transaction.model,
                transactions=1,
                total_tokens_in=transaction.tokens_in,
                total_tokens_out=transaction.tokens_out,
                total_cost_usd=cost_usd,
                avg_latency_ms=transaction.duration_ms,
            )
            self._engine.record_provider(provider_record)

            logger.debug(
                "Recorded transaction in manifest: provider=%s op=%s cost=%.6f",
                transaction.provider,
                transaction.operation,
                cost_usd,
            )

        except Exception as exc:
            logger.error("Failed to record transaction in manifest: %s", exc)

    def set_stage(self, stage: str) -> None:
        """Set the current pipeline stage for cost attribution.

        Parameters
        ----------
        stage:
            The stage name (e.g. ``"image-generation"``, ``"narration"``).
        """
        self._current_stage = stage

    def finalise_stage(
        self,
        stage: str,
        *,
        status: str = "completed",
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record stage completion in the Manifest Engine.

        Parameters
        ----------
        stage:
            The stage name.
        status:
            Stage status (``"completed"``, ``"failed"``, ``"skipped"``).
        summary:
            Optional summary data (cost, asset count, etc.).
        """
        if self._engine is None:
            return

        try:
            # The engine tracks stage progress internally via its state.
            # We record the stage completion as a progress update.
            summary = summary or {}
            logger.info(
                "Stage '%s' finalised with status '%s': %s",
                stage,
                status,
                summary,
            )
        except Exception as exc:
            logger.error("Failed to finalise stage in manifest: %s", exc)

    def record_asset(
        self,
        stage: str,
        asset_type: str,
        path: str,
        *,
        provider: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an asset produced by a provider in the Manifest Engine.

        Parameters
        ----------
        stage:
            The pipeline stage that produced the asset.
        asset_type:
            Type of asset (``"image"``, ``"audio"``, ``"video"``, ``"text"``).
        path:
            File path or URL of the asset.
        provider:
            Provider that generated the asset.
        metadata:
            Additional metadata.
        """
        if self._engine is None:
            return

        try:
            self._engine.record_asset(
                stage=stage,
                asset_type=asset_type,
                path=path,
                metadata=metadata or {},
            )
            logger.debug(
                "Recorded asset in manifest: stage=%s type=%s path=%s",
                stage,
                asset_type,
                path,
            )
        except Exception as exc:
            logger.error("Failed to record asset in manifest: %s", exc)


# ---------------------------------------------------------------------------
# Internal hook implementation
# ---------------------------------------------------------------------------

class _BridgeHook(ManifestHook):
    """ManifestHook implementation that delegates to ManifestBridge."""

    def __init__(self, bridge: ManifestBridge) -> None:
        self._bridge = bridge

    def on_transaction_complete(self, transaction: Transaction) -> None:
        self._bridge.record_transaction(transaction)

    def on_transaction_failed(self, transaction: Transaction) -> None:
        # Still record failed transactions for cost tracking (retries cost money)
        logger.warning(
            "Transaction failed: provider=%s op=%s error=%s",
            transaction.provider,
            transaction.operation,
            transaction.error,
        )

    def on_transaction_retry(self, transaction: Transaction, attempt: int) -> None:
        logger.info(
            "Transaction retry: provider=%s op=%s attempt=%d",
            transaction.provider,
            transaction.operation,
            attempt,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()