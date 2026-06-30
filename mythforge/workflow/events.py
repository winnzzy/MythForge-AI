"""
Workflow Engine lifecycle events and event dispatcher.

Strongly-typed events are emitted at every significant point in the
workflow lifecycle.  External consumers (logging, manifest sync, UI)
subscribe to these events without coupling to the engine internals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowEvent:
    """Base class for all workflow lifecycle events."""

    workflow_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a dict (suitable for JSON)."""
        d = {
            "event_type": type(self).__name__,
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d


# ---------------------------------------------------------------------------
# Concrete events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkflowStarted(WorkflowEvent):
    """Emitted when a workflow begins execution."""

    workflow_name: str = ""
    total_stages: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"workflow_name": self.workflow_name, "total_stages": self.total_stages})
        return d


@dataclass(frozen=True)
class StageStarted(WorkflowEvent):
    """Emitted when a stage begins execution."""

    stage_name: str = ""
    attempt: int = 1

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"stage_name": self.stage_name, "attempt": self.attempt})
        return d


@dataclass(frozen=True)
class StageCompleted(WorkflowEvent):
    """Emitted when a stage completes successfully."""

    stage_name: str = ""
    duration_s: float = 0.0
    result_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "stage_name": self.stage_name,
            "duration_s": self.duration_s,
            "result_keys": self.result_keys,
        })
        return d


@dataclass(frozen=True)
class StageFailed(WorkflowEvent):
    """Emitted when a stage fails."""

    stage_name: str = ""
    error: str = ""
    attempt: int = 1
    will_retry: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "stage_name": self.stage_name,
            "error": self.error,
            "attempt": self.attempt,
            "will_retry": self.will_retry,
        })
        return d


@dataclass(frozen=True)
class RetryScheduled(WorkflowEvent):
    """Emitted when a failed stage is scheduled for retry."""

    stage_name: str = ""
    attempt: int = 1
    delay_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "stage_name": self.stage_name,
            "attempt": self.attempt,
            "delay_s": self.delay_s,
        })
        return d


@dataclass(frozen=True)
class WorkflowPaused(WorkflowEvent):
    """Emitted when a workflow is paused (checkpoint created)."""

    checkpoint_id: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"checkpoint_id": self.checkpoint_id, "reason": self.reason})
        return d


@dataclass(frozen=True)
class WorkflowResumed(WorkflowEvent):
    """Emitted when a workflow resumes from a checkpoint."""

    checkpoint_id: str = ""
    remaining_stages: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "checkpoint_id": self.checkpoint_id,
            "remaining_stages": self.remaining_stages,
        })
        return d


@dataclass(frozen=True)
class WorkflowCompleted(WorkflowEvent):
    """Emitted when a workflow completes successfully."""

    duration_s: float = 0.0
    completed_stages: int = 0
    total_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "duration_s": self.duration_s,
            "completed_stages": self.completed_stages,
            "total_cost_usd": self.total_cost_usd,
        })
        return d


@dataclass(frozen=True)
class WorkflowCancelled(WorkflowEvent):
    """Emitted when a workflow is cancelled."""

    reason: str = ""
    completed_stages: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"reason": self.reason, "completed_stages": self.completed_stages})
        return d


@dataclass(frozen=True)
class StageSkipped(WorkflowEvent):
    """Emitted when a stage is skipped."""

    stage_name: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"stage_name": self.stage_name, "reason": self.reason})
        return d


# ---------------------------------------------------------------------------
# Event handler type
# ---------------------------------------------------------------------------

EventHandler = Callable[[WorkflowEvent], None]


# ---------------------------------------------------------------------------
# Event dispatcher
# ---------------------------------------------------------------------------

class EventDispatcher:
    """Dispatches :class:`WorkflowEvent` instances to registered handlers.

    Handlers are keyed by event type.  A special ``"*"`` key receives all
    events (useful for logging).

    Usage::

        dispatcher = EventDispatcher()

        def on_stage_completed(event: WorkflowEvent):
            print(f"Stage {event.stage_name} done")

        dispatcher.on(StageCompleted, on_stage_completed)
        dispatcher.dispatch(StageCompleted(workflow_id="abc", stage_name="RESEARCH"))
    """

    def __init__(self) -> None:
        self._handlers: Dict[type, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._event_log: List[Dict[str, Any]] = []

    def on(
        self,
        event_type: Optional[type],
        handler: EventHandler,
    ) -> None:
        """Register a handler for a specific event type.

        Parameters
        ----------
        event_type:
            The event class to listen for, or ``None`` to listen for all events.
        handler:
            Callable that receives a :class:`WorkflowEvent`.
        """
        if event_type is None:
            self._global_handlers.append(handler)
        else:
            self._handlers.setdefault(event_type, []).append(handler)

    def off(
        self,
        event_type: Optional[type],
        handler: EventHandler,
    ) -> None:
        """Remove a previously registered handler."""
        if event_type is None:
            self._global_handlers.remove(handler)
        else:
            handlers = self._handlers.get(event_type, [])
            handlers.remove(handler)

    def dispatch(self, event: WorkflowEvent) -> None:
        """Dispatch an event to all matching handlers.

        Handlers for the specific event type are called first, followed
        by global handlers.
        """
        event_type = type(event)

        # Type-specific handlers
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Event handler error for %s", event_type.__name__
                )

        # Global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Global event handler error for %s", event_type.__name__
                )

        # Append to internal log
        self._event_log.append(event.to_dict())

    @property
    def event_log(self) -> List[Dict[str, Any]]:
        """Return the full event log as a list of dicts."""
        return list(self._event_log)

    def clear_log(self) -> None:
        """Clear the event log."""
        self._event_log.clear()

    def clear_handlers(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()
        self._global_handlers.clear()