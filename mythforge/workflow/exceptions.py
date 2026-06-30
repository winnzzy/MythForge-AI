"""
Workflow Engine exceptions.

All custom exceptions for the workflow orchestration engine.
"""

from __future__ import annotations


class WorkflowError(Exception):
    """Base exception for all workflow engine errors."""

    def __init__(self, message: str, *, workflow_id: str = "") -> None:
        super().__init__(message)
        self.workflow_id = workflow_id


class StageExecutionError(WorkflowError):
    """A stage handler raised an exception during execution."""

    def __init__(
        self,
        message: str,
        *,
        stage_name: str = "",
        workflow_id: str = "",
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, workflow_id=workflow_id)
        self.stage_name = stage_name
        if cause is not None:
            self.__cause__ = cause


class DependencyError(WorkflowError):
    """A dependency constraint was violated."""

    def __init__(
        self,
        message: str,
        *,
        stage_name: str = "",
        missing_dependencies: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.stage_name = stage_name
        self.missing_dependencies = missing_dependencies or []


class CheckpointError(WorkflowError):
    """Checkpoint creation or restoration failed."""

    def __init__(self, message: str, *, checkpoint_id: str = "") -> None:
        super().__init__(message)
        self.checkpoint_id = checkpoint_id


class PlannerError(WorkflowError):
    """The execution planner could not produce a valid plan."""

    pass