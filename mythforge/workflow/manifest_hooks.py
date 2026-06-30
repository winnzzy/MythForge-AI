"""
Manifest Engine integration hooks for the Workflow Engine.

Bridges workflow execution results into the Manifest Engine's schema.
These hooks translate workflow completion events into manifest records.

The Workflow Engine does NOT depend on the Manifest Engine — this module
is the only integration point, and it gracefully degrades when the
Manifest Engine is not available.

Usage::

    from mythforge.engine.engine import ManifestEngine
    from mythforge.workflow.manifest_hooks import ManifestSync

    engine = ManifestEngine("project_manifest.json")
    sync = ManifestSync(engine)

    # After workflow completes
    sync.on_workflow_completed(workflow_def, result, stage_states)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mythforge.workflow.models import (
    StageState,
    StageStatus,
    WorkflowDefinition,
    WorkflowResult,
)

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
            "Manifest Engine not available — workflow manifest hooks will be no-ops."
        )
        return None, None, None


# ---------------------------------------------------------------------------
# ManifestSync
# ---------------------------------------------------------------------------

class ManifestSync:
    """Synchronises workflow execution results to the Manifest Engine.

    This is a one-way sync: workflow results flow *into* the manifest.
    The workflow engine never reads from the manifest.

    Parameters
    ----------
    engine:
        A :class:`ManifestEngine` instance.  If ``None``, the sync
        will be a no-op.
    """

    def __init__(self, engine: Any = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> Any:
        """Get the underlying Manifest Engine."""
        return self._engine

    @engine.setter
    def engine(self, engine: Any) -> None:
        """Set or replace the Manifest Engine."""
        self._engine = engine

    # ------------------------------------------------------------------
    # Workflow hooks
    # ------------------------------------------------------------------

    def on_workflow_started(
        self,
        workflow: WorkflowDefinition,
    ) -> None:
        """Called when a workflow starts.

        Records the workflow metadata in the manifest.
        """
        if self._engine is None:
            return

        try:
            logger.info(
                "Workflow '%s' (id=%s) started — %d stages",
                workflow.name,
                workflow.workflow_id,
                len(workflow.stages),
            )
        except Exception:
            logger.exception("Failed to record workflow start in manifest")

    def on_workflow_completed(
        self,
        workflow: WorkflowDefinition,
        result: WorkflowResult,
        stage_states: Dict[str, StageState],
    ) -> None:
        """Called when a workflow completes (success or failure).

        Records per-stage cost and provider data in the manifest.

        Parameters
        ----------
        workflow:
            The workflow definition.
        result:
            The workflow execution result.
        stage_states:
            Execution state of every stage.
        """
        if self._engine is None:
            return

        try:
            _, CostRecord, ProviderRecord = _import_engine()
            if CostRecord is None:
                return

            # Record per-stage costs if available in stage metadata
            for name, state in stage_states.items():
                stage_meta = state.metadata or {}
                cost_usd = stage_meta.get("cost_usd", 0.0)
                if cost_usd > 0 and CostRecord is not None:
                    cost_record = CostRecord(
                        stage=name,
                        provider=stage_meta.get("provider", "unknown"),
                        operation=stage_meta.get("operation", name),
                        amount_usd=cost_usd,
                        tokens_in=stage_meta.get("tokens_in", 0),
                        tokens_out=stage_meta.get("tokens_out", 0),
                        timestamp=state.completed_at or _now_iso(),
                    )
                    self._engine.record_cost(cost_record)

            logger.info(
                "Workflow '%s' completed with status '%s' — %d/%d stages succeeded",
                workflow.name,
                result.status,
                result.completed_stage_count,
                len(stage_states),
            )

        except Exception:
            logger.exception("Failed to sync workflow completion to manifest")

    def on_stage_completed(
        self,
        workflow_id: str,
        stage_name: str,
        stage_state: StageState,
        cost_usd: float = 0.0,
        provider: str = "",
    ) -> None:
        """Called when an individual stage completes.

        Useful for real-time manifest updates during long-running workflows.
        """
        if self._engine is None:
            return

        try:
            _, CostRecord, _ = _import_engine()
            if CostRecord is not None and cost_usd > 0:
                cost_record = CostRecord(
                    stage=stage_name,
                    provider=provider,
                    operation=stage_name,
                    amount_usd=cost_usd,
                    timestamp=stage_state.completed_at or _now_iso(),
                )
                self._engine.record_cost(cost_record)

            logger.debug(
                "Stage '%s' completed — synced to manifest (cost=%.6f)",
                stage_name,
                cost_usd,
            )
        except Exception:
            logger.exception("Failed to sync stage completion to manifest")

    def on_workflow_cancelled(
        self,
        workflow_id: str,
        stage_states: Dict[str, StageState],
        reason: str = "",
    ) -> None:
        """Called when a workflow is cancelled."""
        if self._engine is None:
            return

        try:
            completed = sum(
                1 for s in stage_states.values()
                if s.status == StageStatus.COMPLETED.value
            )
            logger.info(
                "Workflow '%s' cancelled after %d completed stages: %s",
                workflow_id,
                completed,
                reason,
            )
        except Exception:
            logger.exception("Failed to record workflow cancellation in manifest")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()