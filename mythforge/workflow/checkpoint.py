"""
Checkpoint Manager.

Creates and restores workflow execution snapshots so that workflows can be
paused and resumed without losing progress.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from mythforge.workflow.models import (
    CheckpointData,
    StageState,
    WorkflowStatus,
    _now_iso,
)

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages workflow checkpoints for pause/resume.

    Checkpoints can be stored in memory (default) or persisted to disk.

    Parameters
    ----------
    storage_dir:
        Optional directory for persisting checkpoints to disk.
        If ``None``, checkpoints are stored in memory only.
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._storage_dir: Optional[Path] = storage_dir
        self._checkpoints: Dict[str, CheckpointData] = {}  # checkpoint_id -> data
        self._workflow_checkpoints: Dict[str, List[str]] = {}  # workflow_id -> [checkpoint_ids]

        if self._storage_dir is not None:
            self._storage_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create_checkpoint(
        self,
        workflow_id: str,
        stage_states: Dict[str, StageState],
        context: Dict[str, Any],
        execution_order: List[str],
        workflow_status: str = WorkflowStatus.PAUSED.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CheckpointData:
        """Create a checkpoint of the current workflow state.

        Parameters
        ----------
        workflow_id:
            The workflow identifier.
        stage_states:
            Current execution state of every stage.
        context:
            The shared workflow context at this point.
        execution_order:
            The order in which stages have been executed so far.
        workflow_status:
            Status to record (typically ``"paused"``).
        metadata:
            Optional metadata to attach to the checkpoint.

        Returns
        -------
        CheckpointData
            The created checkpoint.
        """
        checkpoint = CheckpointData(
            workflow_id=workflow_id,
            workflow_status=workflow_status,
            stage_states={name: state.to_dict() for name, state in stage_states.items()},
            context=dict(context),
            execution_order=list(execution_order),
            metadata=metadata or {},
        )

        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        self._workflow_checkpoints.setdefault(workflow_id, []).append(
            checkpoint.checkpoint_id
        )

        # Persist to disk if configured
        if self._storage_dir is not None:
            self._persist(checkpoint)

        logger.info(
            "Created checkpoint '%s' for workflow '%s' (%d stages)",
            checkpoint.checkpoint_id,
            workflow_id,
            len(stage_states),
        )

        return checkpoint

    # ------------------------------------------------------------------
    # Restoration
    # ------------------------------------------------------------------

    def restore_checkpoint(self, checkpoint_id: str) -> CheckpointData:
        """Restore a checkpoint by its ID.

        Parameters
        ----------
        checkpoint_id:
            The checkpoint identifier.

        Returns
        -------
        CheckpointData
            The restored checkpoint data.

        Raises
        ------
        KeyError
            If the checkpoint does not exist.
        """
        # Try memory first
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]

        # Try disk
        if self._storage_dir is not None:
            path = self._storage_dir / f"{checkpoint_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                checkpoint = CheckpointData.from_dict(data)
                self._checkpoints[checkpoint_id] = checkpoint
                return checkpoint

        raise KeyError(f"Checkpoint '{checkpoint_id}' not found.")

    def get_latest_checkpoint(self, workflow_id: str) -> Optional[CheckpointData]:
        """Return the most recent checkpoint for a workflow.

        Returns ``None`` if no checkpoints exist for the workflow.
        """
        checkpoint_ids = self._workflow_checkpoints.get(workflow_id, [])
        if not checkpoint_ids:
            return None
        return self.restore_checkpoint(checkpoint_ids[-1])

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_checkpoints(self, workflow_id: Optional[str] = None) -> List[str]:
        """Return checkpoint IDs, optionally filtered by workflow.

        Parameters
        ----------
        workflow_id:
            If provided, return only checkpoints for this workflow.
        """
        if workflow_id is not None:
            return list(self._workflow_checkpoints.get(workflow_id, []))
        return list(self._checkpoints.keys())

    def has_checkpoint(self, checkpoint_id: str) -> bool:
        """Return ``True`` if the checkpoint exists."""
        if checkpoint_id in self._checkpoints:
            return True
        if self._storage_dir is not None:
            return (self._storage_dir / f"{checkpoint_id}.json").exists()
        return False

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint from memory and disk."""
        self._checkpoints.pop(checkpoint_id, None)

        # Remove from workflow index
        for wf_id, ids in self._workflow_checkpoints.items():
            if checkpoint_id in ids:
                ids.remove(checkpoint_id)
                break

        # Remove from disk
        if self._storage_dir is not None:
            path = self._storage_dir / f"{checkpoint_id}.json"
            if path.exists():
                path.unlink()

    def clear(self, workflow_id: Optional[str] = None) -> None:
        """Clear checkpoints.

        Parameters
        ----------
        workflow_id:
            If provided, clear only checkpoints for this workflow.
            Otherwise clear all.
        """
        if workflow_id is not None:
            ids = self._workflow_checkpoints.pop(workflow_id, [])
            for cid in ids:
                self._checkpoints.pop(cid, None)
                if self._storage_dir is not None:
                    path = self._storage_dir / f"{cid}.json"
                    if path.exists():
                        path.unlink()
        else:
            self._checkpoints.clear()
            self._workflow_checkpoints.clear()
            if self._storage_dir is not None:
                for f in self._storage_dir.glob("*.json"):
                    f.unlink()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, checkpoint: CheckpointData) -> None:
        """Write checkpoint to disk."""
        assert self._storage_dir is not None
        path = self._storage_dir / f"{checkpoint.checkpoint_id}.json"
        path.write_text(
            json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Persisted checkpoint '%s' to %s", checkpoint.checkpoint_id, path)