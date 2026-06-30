"""
Workflow Engine — Executor.

The central orchestrator.  Combines the DAG, event dispatcher, checkpoint
manager and manifest sync into a single deterministic execution loop.

The engine itself contains no business logic — it delegates to stage handlers.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set

from mythforge.workflow.checkpoint import CheckpointManager
from mythforge.workflow.dag import DependencyGraph
from mythforge.workflow.events import (
    EventDispatcher,
    RetryScheduled,
    StageCompleted,
    StageFailed,
    StageSkipped,
    StageStarted,
    WorkflowCancelled,
    WorkflowCompleted,
    WorkflowEvent,
    WorkflowPaused,
    WorkflowResumed,
    WorkflowStarted,
)
from mythforge.workflow.exceptions import (
    DependencyError,
    StageExecutionError,
    PlannerError,
    WorkflowError,
)
from mythforge.workflow.models import (
    StageDefinition,
    StageState,
    StageStatus,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
    _now_iso,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# Execution Planner
# ===========================================================================

class ExecutionPlanner:
    """Determines the next stages to execute based on the DAG and current state.

    The planner is *pure* — it reads state and returns decisions without
    mutating anything.
    """

    def __init__(self, dag: DependencyGraph) -> None:
        self._dag = dag

    def plan_next(
        self,
        stage_states: Dict[str, StageState],
        exclude: Optional[Set[str]] = None,
    ) -> List[str]:
        """Return the next stages whose dependencies are satisfied.

        Parameters
        ----------
        stage_states:
            Current execution state of every stage.
        exclude:
            Stages to exclude (e.g. currently running or permanently failed).

        Returns
        -------
        list[str]
            Sorted list of stage names ready to execute.
        """
        completed = {
            name
            for name, state in stage_states.items()
            if state.status == StageStatus.COMPLETED.value
            or state.status == StageStatus.SKIPPED.value
        }
        return self._dag.ready_stages(completed, exclude=exclude)

    def remaining_stages(
        self,
        stage_states: Dict[str, StageState],
    ) -> List[str]:
        """Return stages that are not yet completed or skipped."""
        return [
            name
            for name in self._dag.stage_names
            if stage_states[name].status
            in {StageStatus.PENDING.value, StageStatus.FAILED.value, StageStatus.WAITING_RETRY.value}
        ]

    def is_complete(self, stage_states: Dict[str, StageState]) -> bool:
        """Return ``True`` if all stages are completed or skipped."""
        return all(
            state.status in {StageStatus.COMPLETED.value, StageStatus.SKIPPED.value}
            for state in stage_states.values()
        )

    def can_progress(self, stage_states: Dict[str, StageState]) -> bool:
        """Return ``True`` if there are stages that can still be executed."""
        ready = self.plan_next(stage_states)
        pending = [
            n for n, s in stage_states.items()
            if s.status in {StageStatus.PENDING.value, StageStatus.WAITING_RETRY.value}
        ]
        return len(ready) > 0 or len(pending) > 0


# ===========================================================================
# Resume Planner
# ===========================================================================

class ResumePlanner:
    """Determines which stages need to be (re-)executed when resuming from a
    checkpoint or after a failure.
    """

    def __init__(self, dag: DependencyGraph) -> None:
        self._dag = dag

    def plan_resume(
        self,
        stage_states: Dict[str, StageState],
    ) -> List[str]:
        """Plan stages to re-execute when resuming.

        Stages that are PENDING, FAILED, or WAITING_RETRY need to run.
        Stages that are COMPLETED or SKIPPED are kept.

        Returns
        -------
        list[str]
            Topologically sorted list of stage names to execute.
        """
        need_execution: Set[str] = set()
        for name, state in stage_states.items():
            if state.status in {
                StageStatus.PENDING.value,
                StageStatus.FAILED.value,
                StageStatus.WAITING_RETRY.value,
                StageStatus.CANCELLED.value,
            }:
                need_execution.add(name)

        # Return in topological order for determinism
        topo = self._dag.topological_order()
        return [n for n in topo if n in need_execution]

    def reset_failed_stages(
        self,
        stage_states: Dict[str, StageState],
    ) -> Dict[str, StageState]:
        """Reset failed/waiting_retry stages to PENDING for re-execution.

        Returns a new dict with updated states (does not mutate input).
        """
        updated: Dict[str, StageState] = {}
        for name, state in stage_states.items():
            if state.status in {
                StageStatus.FAILED.value,
                StageStatus.WAITING_RETRY.value,
                StageStatus.CANCELLED.value,
            }:
                new_state = StageState(
                    stage_name=name,
                    status=StageStatus.PENDING.value,
                    attempt=state.attempt,
                )
                updated[name] = new_state
            else:
                updated[name] = state
        return updated


# ===========================================================================
# Retry Planner
# ===========================================================================

class RetryPlanner:
    """Decides whether to retry a failed stage and computes the backoff delay."""

    def should_retry(self, stage_defn: StageDefinition, state: StageState) -> bool:
        """Return ``True`` if the stage should be retried.

        Parameters
        ----------
        stage_defn:
            The stage definition (contains retry policy).
        state:
            The current execution state (contains attempt count).
        """
        return state.attempt < stage_defn.retry_policy.max_retries

    def next_delay(self, stage_defn: StageDefinition, state: StageState) -> float:
        """Compute the backoff delay for the next retry attempt.

        Returns the delay in seconds.
        """
        return stage_defn.retry_policy.delay_for_attempt(state.attempt)

    def next_attempt(self, state: StageState) -> int:
        """Return the next attempt number (0-indexed)."""
        return state.attempt


# ===========================================================================
# Workflow Engine
# ===========================================================================

class WorkflowEngine:
    """Deterministic workflow orchestrator.

    Coordinates the Manifest Engine, Provider SDK, and Prompt Engine
    without knowing anything about AI providers.

    Parameters
    ----------
    manifest_engine:
        Optional :class:`ManifestEngine` instance for manifest synchronisation.
    checkpoint_manager:
        Optional :class:`CheckpointManager`.  If ``None``, an in-memory
        manager is created.
    dispatcher:
        Optional :class:`EventDispatcher`.  If ``None``, a new one is created.
    """

    def __init__(
        self,
        manifest_engine: Any = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        dispatcher: Optional[EventDispatcher] = None,
    ) -> None:
        self._manifest_engine = manifest_engine
        self._checkpoint_manager = checkpoint_manager or CheckpointManager()
        self._dispatcher = dispatcher or EventDispatcher()

        # Lazy import to avoid circular dependency
        self._manifest_sync: Any = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def dispatcher(self) -> EventDispatcher:
        """The event dispatcher."""
        return self._dispatcher

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        """The checkpoint manager."""
        return self._checkpoint_manager

    @property
    def manifest_engine(self) -> Any:
        """The manifest engine (if set)."""
        return self._manifest_engine

    @manifest_engine.setter
    def manifest_engine(self, engine: Any) -> None:
        """Set the manifest engine."""
        self._manifest_engine = engine

    # ------------------------------------------------------------------
    # Stage handler registration
    # ------------------------------------------------------------------

    def register_stage_handler(
        self,
        stage_name: str,
        handler: Callable[..., Dict[str, Any]],
    ) -> None:
        """Register a stage handler.

        This is the primary extension point for future engineers.
        External modules (e.g. prompt_engine, providers) call this to
        attach their logic to specific stage names.

        Parameters
        ----------
        stage_name:
            The stage name to handle.
        handler:
            Callable ``(input_data, context) -> result_dict``.
        """
        # Store handlers on the engine for later use during execution
        if not hasattr(self, "_stage_handlers"):
            self._stage_handlers: Dict[str, Callable] = {}
        self._stage_handlers[stage_name] = handler
        logger.debug("Registered handler for stage '%s'", stage_name)

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(
        self,
        workflow: WorkflowDefinition,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Execute a workflow.

        Parameters
        ----------
        workflow:
            The workflow definition to execute.
        context:
            Initial context (shared state) for the workflow.

        Returns
        -------
        WorkflowResult
            The outcome of the execution.
        """
        context = dict(context or {})
        workflow_id = workflow.workflow_id

        # Build DAG
        dag = DependencyGraph(workflow.stages)
        planner = ExecutionPlanner(dag)
        retry_planner = RetryPlanner()

        # Initialise stage states
        stage_states: Dict[str, StageState] = {}
        for defn in workflow.stages:
            stage_states[defn.name] = StageState(
                stage_name=defn.name,
                status=StageStatus.PENDING.value,
            )

        execution_order: List[str] = []
        started_at = _now_iso()

        # Build handler map: merge workflow handlers with engine handlers
        handlers = self._resolve_handlers(workflow)

        # Emit WorkflowStarted
        self._dispatcher.dispatch(WorkflowStarted(
            workflow_id=workflow_id,
            workflow_name=workflow.name,
            total_stages=len(workflow.stages),
        ))

        # Main execution loop
        while not planner.is_complete(stage_states):
            ready = planner.plan_next(stage_states)
            if not ready:
                # No stages ready — check if we can still progress
                if not planner.can_progress(stage_states):
                    break
                # There are stages waiting for retry; in a real async system
                # we'd wait.  For deterministic sync execution, we break.
                break

            for stage_name in ready:
                self._execute_stage(
                    workflow_id=workflow_id,
                    stage_name=stage_name,
                    stage_states=stage_states,
                    context=context,
                    handlers=handlers,
                    dag=dag,
                    retry_planner=retry_planner,
                    execution_order=execution_order,
                )

        # Determine final status
        completed_at = _now_iso()
        all_completed = planner.is_complete(stage_states)
        any_failed = any(
            s.status == StageStatus.FAILED.value for s in stage_states.values()
        )

        if all_completed:
            status = WorkflowStatus.COMPLETED.value
        elif any_failed:
            status = WorkflowStatus.FAILED.value
        else:
            status = WorkflowStatus.PAUSED.value

        meta = dict(workflow.metadata)
        meta["execution_order"] = execution_order

        result = WorkflowResult(
            workflow_id=workflow_id,
            status=status,
            stage_states={name: state.to_dict() for name, state in stage_states.items()},
            context=context,
            started_at=started_at,
            completed_at=completed_at,
            metadata=meta,
        )

        # Emit completion event
        if status == WorkflowStatus.COMPLETED.value:
            self._dispatcher.dispatch(WorkflowCompleted(
                workflow_id=workflow_id,
                duration_s=result.duration_s,
                completed_stages=result.completed_stage_count,
            ))

        # Sync to manifest
        if self._manifest_engine is not None:
            self._sync_manifest(workflow, result, stage_states)

        return result

    # ------------------------------------------------------------------
    # Pause / Resume
    # ------------------------------------------------------------------

    def pause(
        self,
        workflow_id: str,
        stage_states: Dict[str, StageState],
        context: Dict[str, Any],
        execution_order: List[str],
        reason: str = "",
    ) -> str:
        """Pause a workflow and create a checkpoint.

        Returns the checkpoint ID.
        """
        checkpoint = self._checkpoint_manager.create_checkpoint(
            workflow_id=workflow_id,
            stage_states=stage_states,
            context=context,
            execution_order=execution_order,
        )

        self._dispatcher.dispatch(WorkflowPaused(
            workflow_id=workflow_id,
            checkpoint_id=checkpoint.checkpoint_id,
            reason=reason,
        ))

        return checkpoint.checkpoint_id

    def resume(
        self,
        workflow: WorkflowDefinition,
        checkpoint_id: str,
    ) -> WorkflowResult:
        """Resume a workflow from a checkpoint.

        Parameters
        ----------
        workflow:
            The workflow definition.
        checkpoint_id:
            The checkpoint to resume from.

        Returns
        -------
        WorkflowResult
            The outcome of the resumed execution.
        """
        checkpoint = self._checkpoint_manager.restore_checkpoint(checkpoint_id)
        resume_planner = ResumePlanner(DependencyGraph(workflow.stages))

        # Restore stage states
        stage_states: Dict[str, StageState] = {}
        for name, state_dict in checkpoint.stage_states.items():
            stage_states[name] = StageState.from_dict(state_dict)

        # Reset failed stages for retry
        stage_states = resume_planner.reset_failed_stages(stage_states)

        context = dict(checkpoint.context)
        execution_order = list(checkpoint.execution_order)

        self._dispatcher.dispatch(WorkflowResumed(
            workflow_id=workflow.workflow_id,
            checkpoint_id=checkpoint_id,
            remaining_stages=len(resume_planner.plan_resume(stage_states)),
        ))

        # Build remaining workflow (only stages that need execution)
        return self._continue_execution(
            workflow=workflow,
            stage_states=stage_states,
            context=context,
            execution_order=execution_order,
        )

    def resume_from_failure(
        self,
        workflow: WorkflowDefinition,
        result: WorkflowResult,
    ) -> WorkflowResult:
        """Resume a workflow from its last failed result (no explicit checkpoint).

        Parameters
        ----------
        workflow:
            The workflow definition.
        result:
            The previous :class:`WorkflowResult` containing failure state.

        Returns
        -------
        WorkflowResult
            The outcome of the resumed execution.
        """
        resume_planner = ResumePlanner(DependencyGraph(workflow.stages))

        # Restore stage states
        stage_states: Dict[str, StageState] = {}
        for name, state_dict in result.stage_states.items():
            stage_states[name] = StageState.from_dict(state_dict)

        # Reset failed stages for retry
        stage_states = resume_planner.reset_failed_stages(stage_states)

        context = dict(result.context)
        execution_order = list(result.metadata.get("execution_order", []))

        return self._continue_execution(
            workflow=workflow,
            stage_states=stage_states,
            context=context,
            execution_order=execution_order,
        )

    # ------------------------------------------------------------------
    # Skip
    # ------------------------------------------------------------------

    def skip_stage(
        self,
        stage_name: str,
        stage_states: Dict[str, StageState],
        reason: str = "",
    ) -> None:
        """Mark a stage as skipped."""
        state = stage_states.get(stage_name)
        if state is None:
            raise ValueError(f"Stage '{stage_name}' not found in workflow.")
        state.status = StageStatus.SKIPPED.value
        state.completed_at = _now_iso()
        state.metadata["skip_reason"] = reason

        self._dispatcher.dispatch(StageSkipped(
            workflow_id="",
            stage_name=stage_name,
            reason=reason,
        ))

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def cancel(
        self,
        workflow_id: str,
        stage_states: Dict[str, StageState],
        reason: str = "",
    ) -> None:
        """Cancel a workflow."""
        completed = sum(
            1 for s in stage_states.values()
            if s.status == StageStatus.COMPLETED.value
        )
        self._dispatcher.dispatch(WorkflowCancelled(
            workflow_id=workflow_id,
            reason=reason,
            completed_stages=completed,
        ))

    # ------------------------------------------------------------------
    # Internal: execute a single stage
    # ------------------------------------------------------------------

    def _execute_stage(
        self,
        workflow_id: str,
        stage_name: str,
        stage_states: Dict[str, StageState],
        context: Dict[str, Any],
        handlers: Dict[str, Callable],
        dag: DependencyGraph,
        retry_planner: RetryPlanner,
        execution_order: List[str],
    ) -> None:
        """Execute a single stage with retry logic."""
        state = stage_states[stage_name]
        defn = dag.get_stage(stage_name)

        # Resolve handler
        handler = handlers.get(stage_name)
        if handler is None:
            # No handler — treat as stage that can't be executed
            state.status = StageStatus.FAILED.value
            state.error = f"No handler registered for stage '{stage_name}'"
            self._dispatcher.dispatch(StageFailed(
                workflow_id=workflow_id,
                stage_name=stage_name,
                error=state.error,
                will_retry=False,
            ))
            return

        # Prepare input data from dependencies' outputs
        input_data: Dict[str, Any] = {}
        for dep_name in defn.dependencies:
            dep_state = stage_states.get(dep_name)
            if dep_state and dep_state.result:
                input_data[dep_name] = dep_state.result

        # Retry loop
        max_attempts = defn.retry_policy.max_retries + 1
        for attempt in range(state.attempt, max_attempts):
            state.status = StageStatus.RUNNING.value
            state.started_at = _now_iso()
            state.attempt = attempt

            self._dispatcher.dispatch(StageStarted(
                workflow_id=workflow_id,
                stage_name=stage_name,
                attempt=attempt + 1,
            ))

            try:
                result = handler(input_data, context)
                if result is None:
                    result = {}

                # Success
                state.status = StageStatus.COMPLETED.value
                state.completed_at = _now_iso()
                state.duration_s = _elapsed(state.started_at, state.completed_at)
                state.result = result
                state.error = None

                # Merge result into context
                if defn.produced_outputs:
                    for key in defn.produced_outputs:
                        if key in result:
                            context[key] = result[key]
                else:
                    context.update(result)

                execution_order.append(stage_name)

                self._dispatcher.dispatch(StageCompleted(
                    workflow_id=workflow_id,
                    stage_name=stage_name,
                    duration_s=state.duration_s,
                    result_keys=list(result.keys()),
                ))
                return

            except Exception as exc:
                state.completed_at = _now_iso()
                state.duration_s = _elapsed(state.started_at, state.completed_at)
                state.error = str(exc)

                will_retry = retry_planner.should_retry(defn, state)

                self._dispatcher.dispatch(StageFailed(
                    workflow_id=workflow_id,
                    stage_name=stage_name,
                    error=str(exc),
                    attempt=attempt + 1,
                    will_retry=will_retry,
                ))

                if will_retry:
                    delay = retry_planner.next_delay(defn, state)
                    state.status = StageStatus.WAITING_RETRY.value
                    state.attempt = attempt + 1

                    self._dispatcher.dispatch(RetryScheduled(
                        workflow_id=workflow_id,
                        stage_name=stage_name,
                        attempt=attempt + 2,
                        delay_s=delay,
                    ))
                    # In a sync system, we continue the loop immediately.
                    # In an async system, we'd await the delay.
                    continue
                else:
                    state.status = StageStatus.FAILED.value
                    state.attempt = attempt + 1
                    return

    # ------------------------------------------------------------------
    # Internal: continue execution with existing state
    # ------------------------------------------------------------------

    def _continue_execution(
        self,
        workflow: WorkflowDefinition,
        stage_states: Dict[str, StageState],
        context: Dict[str, Any],
        execution_order: List[str],
    ) -> WorkflowResult:
        """Continue executing a workflow from existing state."""
        dag = DependencyGraph(workflow.stages)
        planner = ExecutionPlanner(dag)
        retry_planner = RetryPlanner()
        handlers = self._resolve_handlers(workflow)
        workflow_id = workflow.workflow_id

        while not planner.is_complete(stage_states):
            ready = planner.plan_next(stage_states)
            if not ready:
                if not planner.can_progress(stage_states):
                    break
                break

            for stage_name in ready:
                self._execute_stage(
                    workflow_id=workflow_id,
                    stage_name=stage_name,
                    stage_states=stage_states,
                    context=context,
                    handlers=handlers,
                    dag=dag,
                    retry_planner=retry_planner,
                    execution_order=execution_order,
                )

        completed_at = _now_iso()
        all_completed = planner.is_complete(stage_states)
        any_failed = any(
            s.status == StageStatus.FAILED.value for s in stage_states.values()
        )

        if all_completed:
            status = WorkflowStatus.COMPLETED.value
        elif any_failed:
            status = WorkflowStatus.FAILED.value
        else:
            status = WorkflowStatus.PAUSED.value

        meta = dict(workflow.metadata)
        meta["execution_order"] = execution_order

        result = WorkflowResult(
            workflow_id=workflow_id,
            status=status,
            stage_states={name: state.to_dict() for name, state in stage_states.items()},
            context=context,
            started_at=_now_iso(),
            completed_at=completed_at,
            metadata=meta,
        )

        if status == WorkflowStatus.COMPLETED.value:
            self._dispatcher.dispatch(WorkflowCompleted(
                workflow_id=workflow_id,
                duration_s=result.duration_s,
                completed_stages=result.completed_stage_count,
            ))

        return result

    # ------------------------------------------------------------------
    # Internal: resolve handlers
    # ------------------------------------------------------------------

    def _resolve_handlers(
        self,
        workflow: WorkflowDefinition,
    ) -> Dict[str, Callable]:
        """Build a map of stage_name -> handler from workflow definitions
        and engine-registered handlers.
        """
        handlers: Dict[str, Callable] = {}

        # From workflow definitions
        for defn in workflow.stages:
            if defn.handler is not None:
                handlers[defn.name] = defn.handler

        # From engine-registered handlers (override workflow handlers)
        engine_handlers = getattr(self, "_stage_handlers", {})
        handlers.update(engine_handlers)

        return handlers

    # ------------------------------------------------------------------
    # Internal: manifest sync
    # ------------------------------------------------------------------

    def _sync_manifest(
        self,
        workflow: WorkflowDefinition,
        result: WorkflowResult,
        stage_states: Dict[str, StageState],
    ) -> None:
        """Synchronise workflow results to the manifest engine."""
        try:
            sync = self._get_manifest_sync()
            sync.on_workflow_completed(workflow, result, stage_states)
        except Exception:
            logger.exception("Failed to sync workflow to manifest")

    def _get_manifest_sync(self) -> Any:
        """Lazy-create the manifest sync hook."""
        if self._manifest_sync is None:
            from mythforge.workflow.manifest_hooks import ManifestSync
            self._manifest_sync = ManifestSync(self._manifest_engine)
        return self._manifest_sync


# ===========================================================================
# Helpers
# ===========================================================================

def _elapsed(start_iso: str, end_iso: str) -> float:
    """Compute elapsed seconds between two ISO timestamps.

    Returns 0.0 if parsing fails.
    """
    try:
        from datetime import datetime
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        return (end - start).total_seconds()
    except Exception:
        return 0.0