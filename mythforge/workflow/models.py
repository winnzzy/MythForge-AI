"""
Workflow Engine data models.

All dataclasses are JSON-serialisable via ``to_dict`` / ``from_dict`` helpers.
Models follow the same pattern as ``mythforge.engine.schema``.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StageStatus(str, enum.Enum):
    """Execution status for a single stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    WAITING_RETRY = "waiting_retry"


class WorkflowStatus(str, enum.Enum):
    """Execution status for a workflow."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

class StageHandler(Protocol):
    """Protocol for stage handler callables.

    A stage handler receives the stage's input data and a shared context
    dict, and returns a result dict that becomes part of the workflow output.
    """

    def __call__(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

@dataclass
class RetryPolicy:
    """Retry configuration for a stage."""

    max_retries: int = 3
    backoff_base_s: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_s: float = 60.0

    def delay_for_attempt(self, attempt: int) -> float:
        """Return the backoff delay in seconds for *attempt* (0-indexed)."""
        delay = self.backoff_base_s * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_backoff_s)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RetryPolicy":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Cost estimate
# ---------------------------------------------------------------------------

@dataclass
class CostEstimate:
    """Estimated cost and duration for a stage."""

    estimated_cost_usd: float = 0.0
    estimated_duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CostEstimate":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Stage definition
# ---------------------------------------------------------------------------

@dataclass
class StageDefinition:
    """Declarative definition of a single workflow stage.

    This is the blueprint — it does not hold execution state.

    Parameters
    ----------
    name:
        Unique stage identifier (e.g. ``"RESEARCH"``).
    handler:
        Callable that executes the stage logic.
    dependencies:
        List of stage names that must complete before this stage can start.
    required_inputs:
        Keys that must exist in ``context`` before the handler runs.
    produced_outputs:
        Keys the handler promises to write into ``context``.
    parallel_eligible:
        If ``True``, this stage may run concurrently with other stages
        that share the same dependency frontier.
    retry_policy:
        Retry configuration for this stage.
    cost_estimate:
        Estimated cost and duration.
    """

    name: str
    handler: Optional[Callable[..., Dict[str, Any]]] = None
    dependencies: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    produced_outputs: List[str] = field(default_factory=list)
    parallel_eligible: bool = False
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    cost_estimate: CostEstimate = field(default_factory=CostEstimate)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise (excluding the handler callable)."""
        d = asdict(self)
        d.pop("handler", None)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StageDefinition":
        """Deserialise (handler will be ``None``)."""
        known = {k for k in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in known and k != "handler"}
        # Handle nested dataclass fields
        if "retry_policy" in filtered and isinstance(filtered["retry_policy"], dict):
            filtered["retry_policy"] = RetryPolicy.from_dict(filtered["retry_policy"])
        if "cost_estimate" in filtered and isinstance(filtered["cost_estimate"], dict):
            filtered["cost_estimate"] = CostEstimate.from_dict(filtered["cost_estimate"])
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Stage execution state
# ---------------------------------------------------------------------------

@dataclass
class StageState:
    """Mutable execution state for a single stage."""

    stage_name: str = ""
    status: str = StageStatus.PENDING.value
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_s: float = 0.0
    attempt: int = 0
    error: Optional[str] = None
    result: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StageState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Workflow definition
# ---------------------------------------------------------------------------

@dataclass
class WorkflowDefinition:
    """Declarative definition of a workflow (a collection of stages).

    Parameters
    ----------
    name:
        Human-readable workflow name.
    workflow_id:
        Unique identifier (auto-generated if omitted).
    stages:
        List of stage definitions.
    metadata:
        Arbitrary metadata.
    """

    name: str = ""
    workflow_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stages: List[StageDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "workflow_id": self.workflow_id,
            "stages": [s.to_dict() for s in self.stages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowDefinition":
        stages = [StageDefinition.from_dict(s) for s in d.get("stages", [])]
        return cls(
            name=d.get("name", ""),
            workflow_id=d.get("workflow_id", uuid.uuid4().hex[:12]),
            stages=stages,
            metadata=d.get("metadata", {}),
        )

    def get_stage(self, name: str) -> Optional[StageDefinition]:
        """Return the stage definition with *name*, or ``None``."""
        for s in self.stages:
            if s.name == name:
                return s
        return None


# ---------------------------------------------------------------------------
# Workflow result
# ---------------------------------------------------------------------------

@dataclass
class WorkflowResult:
    """Outcome of a workflow execution."""

    workflow_id: str = ""
    status: str = WorkflowStatus.CREATED.value
    stage_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_s: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowResult":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            WorkflowStatus.COMPLETED.value,
            WorkflowStatus.FAILED.value,
            WorkflowStatus.CANCELLED.value,
        }

    @property
    def completed_stage_count(self) -> int:
        return sum(
            1 for s in self.stage_states.values()
            if s.get("status") == StageStatus.COMPLETED.value
        )

    @property
    def failed_stage_count(self) -> int:
        return sum(
            1 for s in self.stage_states.values()
            if s.get("status") == StageStatus.FAILED.value
        )


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

@dataclass
class CheckpointData:
    """Serialisable snapshot of workflow execution state."""

    checkpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_id: str = ""
    created_at: str = field(default_factory=lambda: _now_iso())
    workflow_status: str = WorkflowStatus.PAUSED.value
    stage_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CheckpointData":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """UTC now as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()