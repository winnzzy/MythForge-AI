"""
MythForge Workflow Engine.

Deterministic orchestration engine for MythForge production stages.
Coordinates the Manifest Engine, Provider SDK, and Prompt Engine without
knowing anything about AI providers.

Usage::

    from mythforge.workflow import WorkflowEngine, StageDefinition, WorkflowDefinition

    # Define stages
    stages = [
        StageDefinition(name="RESEARCH", handler=my_research_fn, ...),
        StageDefinition(name="SCRIPT", handler=my_script_fn, dependencies=["RESEARCH"], ...),
    ]

    # Create workflow
    wf = WorkflowDefinition(name="video-production", stages=stages)
    engine = WorkflowEngine(manifest_engine=my_manifest_engine)
    result = engine.execute(wf, context={...})
"""

from mythforge.workflow.models import (
    StageDefinition,
    StageState,
    StageStatus,
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowResult,
    CheckpointData,
    RetryPolicy,
    CostEstimate,
)
from mythforge.workflow.registry import StageRegistry
from mythforge.workflow.dag import DependencyGraph, CyclicDependencyError
from mythforge.workflow.events import (
    WorkflowEvent,
    WorkflowStarted,
    StageStarted,
    StageCompleted,
    StageFailed,
    StageSkipped,
    RetryScheduled,
    WorkflowPaused,
    WorkflowResumed,
    WorkflowCompleted,
    WorkflowCancelled,
    EventDispatcher,
)
from mythforge.workflow.checkpoint import CheckpointManager
from mythforge.workflow.executor import (
    WorkflowEngine,
    ExecutionPlanner,
    ResumePlanner,
    RetryPlanner,
)
from mythforge.workflow.exceptions import (
    WorkflowError,
    StageExecutionError,
    DependencyError,
    CheckpointError,
    PlannerError,
)
from mythforge.workflow.manifest_hooks import ManifestSync

__all__ = [
    # Models
    "StageDefinition",
    "StageState",
    "StageStatus",
    "WorkflowDefinition",
    "WorkflowStatus",
    "WorkflowResult",
    "CheckpointData",
    "RetryPolicy",
    "CostEstimate",
    # Registry
    "StageRegistry",
    # DAG
    "DependencyGraph",
    "CyclicDependencyError",
    # Events
    "WorkflowEvent",
    "WorkflowStarted",
    "StageStarted",
    "StageCompleted",
    "StageFailed",
    "StageSkipped",
    "RetryScheduled",
    "WorkflowPaused",
    "WorkflowResumed",
    "WorkflowCompleted",
    "WorkflowCancelled",
    "EventDispatcher",
    # Checkpoint
    "CheckpointManager",
    # Planners
    "ExecutionPlanner",
    "ResumePlanner",
    "RetryPlanner",
    # Executor
    "WorkflowEngine",
    # Manifest hooks
    "ManifestSync",
    # Exceptions
    "WorkflowError",
    "StageExecutionError",
    "DependencyError",
    "CheckpointError",
    "PlannerError",
]