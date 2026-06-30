"""
Unit tests for the MythForge Workflow Engine.

Covers:
- Stage definitions & models
- Stage registry
- Dependency graph (DAG)
- Execution planner
- Resume planner
- Retry planner
- Lifecycle events & event dispatcher
- Checkpoint manager
- Workflow executor (full integration)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from mythforge.workflow.checkpoint import CheckpointManager
from mythforge.workflow.dag import CyclicDependencyError, DependencyGraph
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
from mythforge.workflow.executor import (
    ExecutionPlanner,
    ResumePlanner,
    RetryPlanner,
    WorkflowEngine,
)
from mythforge.workflow.models import (
    CheckpointData,
    CostEstimate,
    RetryPolicy,
    StageDefinition,
    StageState,
    StageStatus,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
    _now_iso,
)
from mythforge.workflow.registry import StageRegistry


# ===========================================================================
# Helpers
# ===========================================================================

def _make_stage(
    name: str,
    deps: Optional[List[str]] = None,
    handler=None,
    max_retries: int = 0,
    parallel_eligible: bool = False,
    produced_outputs: Optional[List[str]] = None,
    **kwargs,
) -> StageDefinition:
    """Helper to create a StageDefinition for tests."""
    return StageDefinition(
        name=name,
        dependencies=deps or [],
        handler=handler,
        parallel_eligible=parallel_eligible,
        retry_policy=RetryPolicy(max_retries=max_retries),
        produced_outputs=produced_outputs or [],
        **kwargs,
    )


def _collect_events(dispatcher: EventDispatcher) -> List[WorkflowEvent]:
    """Collect all events dispatched during a test."""
    events: List[WorkflowEvent] = []
    dispatcher.on(None, lambda e: events.append(e))
    return events


# ===========================================================================
# Tests: Stage Definitions & Models
# ===========================================================================

class TestStageDefinition:
    """Tests for StageDefinition model."""

    def test_minimal_definition(self):
        s = _make_stage("RESEARCH")
        assert s.name == "RESEARCH"
        assert s.dependencies == []
        assert s.retry_policy.max_retries == 0
        assert s.parallel_eligible is False
        assert s.cost_estimate == CostEstimate()

    def test_full_definition(self):
        s = _make_stage(
            "IMAGE_GENERATION",
            deps=["PROMPT_GENERATION"],
            max_retries=3,
            parallel_eligible=True,
            produced_outputs=["image_paths"],
        )
        assert s.name == "IMAGE_GENERATION"
        assert s.dependencies == ["PROMPT_GENERATION"]
        assert s.retry_policy.max_retries == 3
        assert s.parallel_eligible is True
        assert s.produced_outputs == ["image_paths"]

    def test_to_dict_roundtrip(self):
        s = _make_stage("RESEARCH", deps=[], max_retries=2)
        d = s.to_dict()
        assert "handler" not in d
        s2 = StageDefinition.from_dict(d)
        assert s2.name == "RESEARCH"
        assert s2.retry_policy.max_retries == 2


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_no_retries_delay(self):
        p = RetryPolicy(max_retries=0)
        assert p.max_retries == 0
        # delay_for_attempt still computes based on backoff formula
        assert p.delay_for_attempt(0) == 1.0

    def test_default_delay(self):
        p = RetryPolicy(max_retries=3)
        assert p.delay_for_attempt(0) == 1.0
        assert p.delay_for_attempt(1) == 2.0
        assert p.delay_for_attempt(2) == 4.0

    def test_custom_backoff(self):
        p = RetryPolicy(max_retries=3, backoff_base_s=2.0, backoff_multiplier=3.0)
        assert p.delay_for_attempt(0) == 2.0
        assert p.delay_for_attempt(1) == 6.0
        assert p.delay_for_attempt(2) == 18.0

    def test_max_backoff_cap(self):
        p = RetryPolicy(max_retries=10, backoff_base_s=1.0, backoff_multiplier=2.0, max_backoff_s=5.0)
        assert p.delay_for_attempt(0) == 1.0
        assert p.delay_for_attempt(1) == 2.0
        assert p.delay_for_attempt(2) == 4.0
        assert p.delay_for_attempt(3) == 5.0  # capped
        assert p.delay_for_attempt(10) == 5.0  # still capped


class TestStageState:
    """Tests for StageState model."""

    def test_initial_state(self):
        s = StageState(stage_name="RESEARCH")
        assert s.status == StageStatus.PENDING.value
        assert s.attempt == 0
        assert s.error is None
        assert s.result == {}

    def test_to_dict_roundtrip(self):
        s = StageState(stage_name="RESEARCH", status=StageStatus.COMPLETED.value)
        d = s.to_dict()
        s2 = StageState.from_dict(d)
        assert s2.stage_name == "RESEARCH"
        assert s2.status == StageStatus.COMPLETED.value


class TestWorkflowResult:
    """Tests for WorkflowResult model."""

    def test_is_terminal_property(self):
        r = WorkflowResult(workflow_id="wf1", status=WorkflowStatus.COMPLETED.value)
        assert r.is_terminal is True

        r2 = WorkflowResult(workflow_id="wf1", status=WorkflowStatus.FAILED.value)
        assert r2.is_terminal is True

        r3 = WorkflowResult(workflow_id="wf1", status=WorkflowStatus.RUNNING.value)
        assert r3.is_terminal is False

    def test_duration_defaults_to_zero(self):
        r = WorkflowResult(workflow_id="wf1", status=WorkflowStatus.COMPLETED.value)
        assert r.duration_s == 0.0
        assert r.completed_stage_count == 0


# ===========================================================================
# Tests: Stage Registry
# ===========================================================================

class TestStageRegistry:
    """Tests for StageRegistry."""

    def test_register_and_get(self):
        reg = StageRegistry()
        s = _make_stage("RESEARCH")
        reg.register(s)
        assert reg.get("RESEARCH") is s
        assert "RESEARCH" in reg

    def test_register_duplicate_raises(self):
        reg = StageRegistry()
        s = _make_stage("RESEARCH")
        reg.register(s)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(s)

    def test_get_unknown_returns_none(self):
        reg = StageRegistry()
        assert reg.get("UNKNOWN") is None

    def test_names(self):
        reg = StageRegistry()
        reg.register(_make_stage("A"))
        reg.register(_make_stage("B"))
        names = reg.names()
        assert "A" in names
        assert "B" in names

    def test_clear(self):
        reg = StageRegistry()
        reg.register(_make_stage("A"))
        reg.clear()
        assert len(reg.names()) == 0

    def test_register_handler(self):
        reg = StageRegistry()

        def my_handler(input_data, context):
            return {"result": "ok"}

        defn = reg.register_handler("TEST", my_handler, dependencies=["A", "B"])
        assert defn.name == "TEST"
        assert defn.handler is my_handler
        assert defn.dependencies == ["A", "B"]

    def test_decorator_registration(self):
        reg = StageRegistry()

        @reg.stage("RESEARCH", dependencies=[], parallel_eligible=True)
        def do_research(input_data, context):
            return {"data": "research"}

        assert "RESEARCH" in reg
        defn = reg.get("RESEARCH")
        assert defn is not None
        assert defn.parallel_eligible is True
        assert defn.handler is do_research

    def test_unregister(self):
        reg = StageRegistry()
        reg.register(_make_stage("A"))
        assert "A" in reg
        reg.unregister("A")
        assert "A" not in reg

    def test_unregister_unknown_raises(self):
        reg = StageRegistry()
        with pytest.raises(KeyError, match="not registered"):
            reg.unregister("UNKNOWN")

    def test_definitions(self):
        reg = StageRegistry()
        reg.register(_make_stage("A"))
        reg.register(_make_stage("B"))
        defs = reg.definitions()
        assert len(defs) == 2

    def test_to_workflow_stages(self):
        reg = StageRegistry()
        reg.register(_make_stage("A"))
        stages = reg.to_workflow_stages()
        assert len(stages) == 1
        assert stages[0].name == "A"


# ===========================================================================
# Tests: Dependency Graph (DAG)
# ===========================================================================

class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def test_empty_graph(self):
        dag = DependencyGraph([])
        assert dag.stage_names == []

    def test_single_stage(self):
        stages = [_make_stage("A")]
        dag = DependencyGraph(stages)
        assert dag.stage_names == ["A"]
        assert dag.get_stage("A").name == "A"

    def test_linear_chain(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
            _make_stage("C", deps=["B"]),
        ]
        dag = DependencyGraph(stages)

        topo = dag.topological_order()
        assert topo.index("A") < topo.index("B")
        assert topo.index("B") < topo.index("C")

    def test_diamond_dependency(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
            _make_stage("C", deps=["A"]),
            _make_stage("D", deps=["B", "C"]),
        ]
        dag = DependencyGraph(stages)

        topo = dag.topological_order()
        assert topo.index("A") < topo.index("B")
        assert topo.index("A") < topo.index("C")
        assert topo.index("B") < topo.index("D")
        assert topo.index("C") < topo.index("D")

    def test_ready_stages_initial(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
        ]
        dag = DependencyGraph(stages)
        ready = dag.ready_stages(completed=set())
        assert ready == ["A"]

    def test_ready_stages_after_completion(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
        ]
        dag = DependencyGraph(stages)
        ready = dag.ready_stages(completed={"A"})
        assert ready == ["B"]

    def test_ready_stages_excludes_completed(self):
        stages = [
            _make_stage("A"),
            _make_stage("B"),
        ]
        dag = DependencyGraph(stages)
        ready = dag.ready_stages(completed={"A"})
        assert ready == ["B"]

    def test_ready_stages_exclude_set(self):
        stages = [
            _make_stage("A"),
            _make_stage("B"),
        ]
        dag = DependencyGraph(stages)
        ready = dag.ready_stages(completed=set(), exclude={"B"})
        assert ready == ["A"]

    def test_cyclic_dependency_detected(self):
        stages = [
            _make_stage("A", deps=["C"]),
            _make_stage("B", deps=["A"]),
            _make_stage("C", deps=["B"]),
        ]
        with pytest.raises(CyclicDependencyError):
            DependencyGraph(stages)

    def test_missing_dependency_detected(self):
        stages = [_make_stage("A", deps=["MISSING"])]
        with pytest.raises(ValueError, match="not defined"):
            DependencyGraph(stages)

    def test_self_dependency_detected(self):
        stages = [_make_stage("A", deps=["A"])]
        with pytest.raises(CyclicDependencyError):
            DependencyGraph(stages)

    def test_get_unknown_stage_returns_none(self):
        stages = [_make_stage("A")]
        dag = DependencyGraph(stages)
        assert dag.get_stage("UNKNOWN") is None

    def test_dependencies_of(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
        ]
        dag = DependencyGraph(stages)
        assert dag.dependencies_of("B") == ["A"]
        assert dag.dependencies_of("A") == []

    def test_dependants_of(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
            _make_stage("C", deps=["A"]),
        ]
        dag = DependencyGraph(stages)
        dependants = dag.dependants_of("A")
        assert "B" in dependants
        assert "C" in dependants

    def test_parallel_groups(self):
        stages = [
            _make_stage("A"),
            _make_stage("B"),
            _make_stage("C", deps=["A", "B"]),
        ]
        dag = DependencyGraph(stages)
        groups = dag.parallel_groups()
        assert len(groups) == 2
        assert set(groups[0]) == {"A", "B"}
        assert groups[1] == ["C"]

    def test_ancestors(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
            _make_stage("C", deps=["B"]),
        ]
        dag = DependencyGraph(stages)
        assert dag.ancestors("C") == {"A", "B"}
        assert dag.ancestors("A") == set()


# ===========================================================================
# Tests: Execution Planner
# ===========================================================================

class TestExecutionPlanner:
    """Tests for ExecutionPlanner."""

    def test_plan_next_initial(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
        ]
        dag = DependencyGraph(stages)
        planner = ExecutionPlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A"),
            "B": StageState(stage_name="B"),
        }
        ready = planner.plan_next(stage_states)
        assert ready == ["A"]

    def test_plan_next_after_completion(self):
        stages = [
            _make_stage("A"),
            _make_stage("B", deps=["A"]),
        ]
        dag = DependencyGraph(stages)
        planner = ExecutionPlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.COMPLETED.value),
            "B": StageState(stage_name="B"),
        }
        ready = planner.plan_next(stage_states)
        assert ready == ["B"]

    def test_is_complete(self):
        stages = [_make_stage("A"), _make_stage("B")]
        dag = DependencyGraph(stages)
        planner = ExecutionPlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.COMPLETED.value),
            "B": StageState(stage_name="B", status=StageStatus.COMPLETED.value),
        }
        assert planner.is_complete(stage_states) is True

        stage_states["B"] = StageState(stage_name="B", status=StageStatus.PENDING.value)
        assert planner.is_complete(stage_states) is False

    def test_can_progress(self):
        stages = [_make_stage("A"), _make_stage("B")]
        dag = DependencyGraph(stages)
        planner = ExecutionPlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A"),
            "B": StageState(stage_name="B"),
        }
        assert planner.can_progress(stage_states) is True


# ===========================================================================
# Tests: Resume Planner
# ===========================================================================

class TestResumePlanner:
    """Tests for ResumePlanner."""

    def test_plan_resume_identifies_failed(self):
        stages = [_make_stage("A"), _make_stage("B", deps=["A"])]
        dag = DependencyGraph(stages)
        planner = ResumePlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.COMPLETED.value),
            "B": StageState(stage_name="B", status=StageStatus.FAILED.value),
        }
        resume = planner.plan_resume(stage_states)
        assert "B" in resume
        assert "A" not in resume

    def test_plan_resume_identifies_pending(self):
        stages = [_make_stage("A"), _make_stage("B")]
        dag = DependencyGraph(stages)
        planner = ResumePlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.COMPLETED.value),
            "B": StageState(stage_name="B", status=StageStatus.PENDING.value),
        }
        resume = planner.plan_resume(stage_states)
        assert "B" in resume

    def test_plan_resume_preserves_completed(self):
        stages = [_make_stage("A"), _make_stage("B")]
        dag = DependencyGraph(stages)
        planner = ResumePlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.COMPLETED.value),
            "B": StageState(stage_name="B", status=StageStatus.COMPLETED.value),
        }
        resume = planner.plan_resume(stage_states)
        assert resume == []

    def test_reset_failed_stages(self):
        stages = [_make_stage("A")]
        dag = DependencyGraph(stages)
        planner = ResumePlanner(dag)

        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.FAILED.value, attempt=2),
        }
        reset = planner.reset_failed_stages(stage_states)
        assert reset["A"].status == StageStatus.PENDING.value
        assert reset["A"].attempt == 2  # attempt count preserved


# ===========================================================================
# Tests: Retry Planner
# ===========================================================================

class TestRetryPlanner:
    """Tests for RetryPlanner."""

    def test_should_retry_within_limit(self):
        planner = RetryPlanner()
        defn = _make_stage("A", max_retries=3)
        state = StageState(stage_name="A", attempt=0)
        assert planner.should_retry(defn, state) is True

    def test_should_not_retry_at_limit(self):
        planner = RetryPlanner()
        defn = _make_stage("A", max_retries=3)
        state = StageState(stage_name="A", attempt=3)
        assert planner.should_retry(defn, state) is False

    def test_delay_exponential(self):
        planner = RetryPlanner()
        defn = _make_stage("A", max_retries=3)
        state = StageState(stage_name="A", attempt=0)
        assert planner.next_delay(defn, state) == 1.0
        state.attempt = 1
        assert planner.next_delay(defn, state) == 2.0


# ===========================================================================
# Tests: Event Dispatcher
# ===========================================================================

class TestEventDispatcher:
    """Tests for EventDispatcher."""

    def test_subscribe_and_dispatch(self):
        dispatcher = EventDispatcher()
        received = []
        dispatcher.on(None, lambda e: received.append(e))
        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        assert len(received) == 1
        assert isinstance(received[0], StageStarted)

    def test_wildcard_subscription(self):
        """Global handler (on(None, ...)) receives all event types."""
        dispatcher = EventDispatcher()
        received = []
        dispatcher.on(None, lambda e: received.append(e))

        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        dispatcher.dispatch(StageCompleted(workflow_id="wf1", stage_name="A"))
        dispatcher.dispatch(WorkflowCompleted(workflow_id="wf1"))

        assert len(received) == 3

    def test_multiple_subscribers(self):
        dispatcher = EventDispatcher()
        received_a = []
        received_b = []
        dispatcher.on(None, lambda e: received_a.append(e))
        dispatcher.on(None, lambda e: received_b.append(e))

        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_unsubscribe(self):
        dispatcher = EventDispatcher()
        received = []
        handler = lambda e: received.append(e)
        dispatcher.on(None, handler)
        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        assert len(received) == 1

        dispatcher.off(None, handler)
        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="B"))
        assert len(received) == 1  # not incremented

    def test_specific_event_subscription(self):
        dispatcher = EventDispatcher()
        received = []
        dispatcher.on(StageStarted, lambda e: received.append(e))

        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        dispatcher.dispatch(StageCompleted(workflow_id="wf1", stage_name="A"))

        assert len(received) == 1  # only StageStarted

    def test_error_in_handler_does_not_break_dispatch(self):
        dispatcher = EventDispatcher()

        def bad_handler(e):
            raise RuntimeError("boom")

        received = []
        dispatcher.on(None, bad_handler)
        dispatcher.on(None, lambda e: received.append(e))

        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        assert len(received) == 1

    def test_clear_handlers(self):
        dispatcher = EventDispatcher()
        received = []
        dispatcher.on(None, lambda e: received.append(e))
        dispatcher.clear_handlers()

        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        assert len(received) == 0

    def test_event_log(self):
        dispatcher = EventDispatcher()
        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        log = dispatcher.event_log
        assert len(log) == 1
        assert log[0]["event_type"] == "StageStarted"

    def test_clear_log(self):
        dispatcher = EventDispatcher()
        dispatcher.dispatch(StageStarted(workflow_id="wf1", stage_name="A"))
        assert len(dispatcher.event_log) == 1
        dispatcher.clear_log()
        assert len(dispatcher.event_log) == 0


# ===========================================================================
# Tests: Workflow Events
# ===========================================================================

class TestWorkflowEvents:
    """Tests for individual event types."""

    def test_workflow_started_event(self):
        e = WorkflowStarted(workflow_id="wf1", workflow_name="Test", total_stages=5)
        d = e.to_dict()
        assert d["event_type"] == "WorkflowStarted"
        assert d["workflow_id"] == "wf1"
        assert d["workflow_name"] == "Test"
        assert d["total_stages"] == 5

    def test_stage_started_event(self):
        e = StageStarted(workflow_id="wf1", stage_name="RESEARCH", attempt=1)
        d = e.to_dict()
        assert d["stage_name"] == "RESEARCH"
        assert d["attempt"] == 1

    def test_stage_completed_event(self):
        e = StageCompleted(workflow_id="wf1", stage_name="RESEARCH", duration_s=1.5, result_keys=["data"])
        d = e.to_dict()
        assert d["stage_name"] == "RESEARCH"
        assert d["duration_s"] == 1.5
        assert d["result_keys"] == ["data"]

    def test_stage_failed_event(self):
        e = StageFailed(workflow_id="wf1", stage_name="RESEARCH", error="boom", attempt=2, will_retry=True)
        d = e.to_dict()
        assert d["error"] == "boom"
        assert d["will_retry"] is True

    def test_retry_scheduled_event(self):
        e = RetryScheduled(workflow_id="wf1", stage_name="RESEARCH", attempt=3, delay_s=4.0)
        d = e.to_dict()
        assert d["attempt"] == 3
        assert d["delay_s"] == 4.0

    def test_workflow_paused_event(self):
        e = WorkflowPaused(workflow_id="wf1", checkpoint_id="cp1", reason="manual")
        d = e.to_dict()
        assert d["checkpoint_id"] == "cp1"
        assert d["reason"] == "manual"

    def test_workflow_resumed_event(self):
        e = WorkflowResumed(workflow_id="wf1", checkpoint_id="cp1", remaining_stages=3)
        d = e.to_dict()
        assert d["remaining_stages"] == 3

    def test_workflow_completed_event(self):
        e = WorkflowCompleted(workflow_id="wf1", duration_s=10.0, completed_stages=5)
        d = e.to_dict()
        assert d["duration_s"] == 10.0
        assert d["completed_stages"] == 5

    def test_workflow_cancelled_event(self):
        e = WorkflowCancelled(workflow_id="wf1", reason="user", completed_stages=2)
        d = e.to_dict()
        assert d["reason"] == "user"

    def test_stage_skipped_event(self):
        e = StageSkipped(workflow_id="wf1", stage_name="RESEARCH", reason="not needed")
        d = e.to_dict()
        assert d["stage_name"] == "RESEARCH"
        assert d["reason"] == "not needed"

    def test_events_are_frozen(self):
        e = StageStarted(workflow_id="wf1", stage_name="A")
        with pytest.raises(AttributeError):
            e.stage_name = "B"


# ===========================================================================
# Tests: Checkpoint Manager
# ===========================================================================

class TestCheckpointManager:
    """Tests for CheckpointManager."""

    def test_create_and_restore(self):
        mgr = CheckpointManager()
        states = {"A": StageState(stage_name="A", status=StageStatus.COMPLETED.value)}
        cp = mgr.create_checkpoint(
            workflow_id="wf1",
            stage_states=states,
            context={"key": "value"},
            execution_order=["A"],
        )
        restored = mgr.restore_checkpoint(cp.checkpoint_id)
        assert restored.workflow_id == "wf1"
        assert restored.context == {"key": "value"}

    def test_restore_unknown_raises(self):
        mgr = CheckpointManager()
        with pytest.raises(KeyError, match="not found"):
            mgr.restore_checkpoint("nonexistent")

    def test_latest_checkpoint(self):
        mgr = CheckpointManager()
        states = {"A": StageState(stage_name="A")}
        mgr.create_checkpoint("wf1", states, {}, [])
        cp2 = mgr.create_checkpoint("wf1", states, {"x": 1}, [])
        latest = mgr.get_latest_checkpoint("wf1")
        assert latest.checkpoint_id == cp2.checkpoint_id

    def test_latest_checkpoint_none_if_empty(self):
        mgr = CheckpointManager()
        assert mgr.get_latest_checkpoint("wf1") is None

    def test_list_checkpoints(self):
        mgr = CheckpointManager()
        states = {"A": StageState(stage_name="A")}
        mgr.create_checkpoint("wf1", states, {}, [])
        mgr.create_checkpoint("wf1", states, {}, [])
        ids = mgr.list_checkpoints("wf1")
        assert len(ids) == 2

    def test_has_checkpoint(self):
        mgr = CheckpointManager()
        states = {"A": StageState(stage_name="A")}
        cp = mgr.create_checkpoint("wf1", states, {}, [])
        assert mgr.has_checkpoint(cp.checkpoint_id) is True
        assert mgr.has_checkpoint("nonexistent") is False

    def test_delete_checkpoint(self):
        mgr = CheckpointManager()
        states = {"A": StageState(stage_name="A")}
        cp = mgr.create_checkpoint("wf1", states, {}, [])
        mgr.delete_checkpoint(cp.checkpoint_id)
        assert mgr.has_checkpoint(cp.checkpoint_id) is False

    def test_clear_specific_workflow(self):
        mgr = CheckpointManager()
        states = {"A": StageState(stage_name="A")}
        mgr.create_checkpoint("wf1", states, {}, [])
        mgr.create_checkpoint("wf2", states, {}, [])
        mgr.clear("wf1")
        assert len(mgr.list_checkpoints("wf1")) == 0
        assert len(mgr.list_checkpoints("wf2")) == 1

    def test_clear_all(self):
        mgr = CheckpointManager()
        states = {"A": StageState(stage_name="A")}
        mgr.create_checkpoint("wf1", states, {}, [])
        mgr.create_checkpoint("wf2", states, {}, [])
        mgr.clear()
        assert len(mgr.list_checkpoints()) == 0

    def test_persist_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(storage_dir=Path(tmpdir))
            states = {"A": StageState(stage_name="A", status=StageStatus.COMPLETED.value)}
            cp = mgr.create_checkpoint("wf1", states, {"data": 42}, ["A"])

            # Verify file exists
            path = Path(tmpdir) / f"{cp.checkpoint_id}.json"
            assert path.exists()

            # Verify content
            data = json.loads(path.read_text())
            assert data["workflow_id"] == "wf1"
            assert data["context"]["data"] == 42

            # Verify restore works from disk
            mgr2 = CheckpointManager(storage_dir=Path(tmpdir))
            restored = mgr2.restore_checkpoint(cp.checkpoint_id)
            assert restored.workflow_id == "wf1"


# ===========================================================================
# Tests: Workflow Engine (Integration)
# ===========================================================================

class TestWorkflowEngine:
    """Integration tests for WorkflowEngine."""

    def test_simple_linear_workflow(self):
        """A → B → C linear chain."""
        call_order = []

        def handler_a(data, ctx):
            call_order.append("A")
            return {"a_result": 1}

        def handler_b(data, ctx):
            call_order.append("B")
            return {"b_result": 2}

        def handler_c(data, ctx):
            call_order.append("C")
            return {"c_result": 3}

        stages = [
            _make_stage("A", handler=handler_a),
            _make_stage("B", deps=["A"], handler=handler_b),
            _make_stage("C", deps=["B"], handler=handler_c),
        ]

        wf = WorkflowDefinition(name="test-linear", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.COMPLETED.value
        assert call_order == ["A", "B", "C"]
        assert result.completed_stage_count == 3

    def test_parallel_independent_stages(self):
        """A and B are independent, C depends on both."""
        call_order = []

        def handler_a(data, ctx):
            call_order.append("A")
            return {"a": 1}

        def handler_b(data, ctx):
            call_order.append("B")
            return {"b": 2}

        def handler_c(data, ctx):
            call_order.append("C")
            return {"c": 3}

        stages = [
            _make_stage("A", handler=handler_a),
            _make_stage("B", handler=handler_b),
            _make_stage("C", deps=["A", "B"], handler=handler_c),
        ]

        wf = WorkflowDefinition(name="test-parallel", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.COMPLETED.value
        assert call_order[-1] == "C"  # C must be last
        assert "A" in call_order and "B" in call_order

    def test_diamond_workflow(self):
        """A → B, A → C, B+C → D diamond pattern."""
        call_order = []

        def h_a(d, c):
            call_order.append("A")
            return {"a": 1}

        def h_b(d, c):
            call_order.append("B")
            return {"b": 2}

        def h_c(d, c):
            call_order.append("C")
            return {"c": 3}

        def h_d(d, c):
            call_order.append("D")
            return {"d": 4}

        stages = [
            _make_stage("A", handler=h_a),
            _make_stage("B", deps=["A"], handler=h_b),
            _make_stage("C", deps=["A"], handler=h_c),
            _make_stage("D", deps=["B", "C"], handler=h_d),
        ]

        wf = WorkflowDefinition(name="test-diamond", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.COMPLETED.value
        assert call_order.index("A") < call_order.index("B")
        assert call_order.index("A") < call_order.index("C")
        assert call_order.index("D") == 3  # D is last

    def test_stage_failure_marks_workflow_failed(self):
        """A fails → workflow fails."""
        def handler_a(data, ctx):
            raise RuntimeError("boom")

        stages = [
            _make_stage("A", handler=handler_a),
            _make_stage("B", deps=["A"], handler=lambda d, c: {}),
        ]

        wf = WorkflowDefinition(name="test-fail", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.FAILED.value
        assert result.failed_stage_count == 1
        assert "boom" in result.stage_states["A"]["error"]

    def test_stage_retry_on_failure(self):
        """Stage fails twice then succeeds on third attempt."""
        attempt_count = {"count": 0}

        def handler_a(data, ctx):
            attempt_count["count"] += 1
            if attempt_count["count"] < 3:
                raise RuntimeError(f"fail #{attempt_count['count']}")
            return {"result": "ok"}

        stages = [
            _make_stage("A", handler=handler_a, max_retries=3),
        ]

        wf = WorkflowDefinition(name="test-retry", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.COMPLETED.value
        assert attempt_count["count"] == 3

    def test_stage_retry_exhausted(self):
        """Stage fails more times than max_retries."""
        attempt_count = {"count": 0}

        def handler_a(data, ctx):
            attempt_count["count"] += 1
            raise RuntimeError(f"fail #{attempt_count['count']}")

        stages = [
            _make_stage("A", handler=handler_a, max_retries=2),
        ]

        wf = WorkflowDefinition(name="test-retry-exhaust", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.FAILED.value
        assert attempt_count["count"] == 3  # 1 initial + 2 retries

    def test_no_handler_marks_stage_failed(self):
        """Stage with no handler is marked as failed."""
        stages = [
            _make_stage("A"),  # no handler
        ]

        wf = WorkflowDefinition(name="test-no-handler", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.FAILED.value
        assert "No handler" in result.stage_states["A"]["error"]

    def test_context_passing_between_stages(self):
        """Results from earlier stages are available in context."""
        def handler_a(data, ctx):
            return {"shared_key": "hello"}

        def handler_b(data, ctx):
            assert ctx.get("shared_key") == "hello"
            return {"b": True}

        stages = [
            _make_stage("A", handler=handler_a),
            _make_stage("B", deps=["A"], handler=handler_b),
        ]

        wf = WorkflowDefinition(name="test-context", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.COMPLETED.value
        assert result.context["shared_key"] == "hello"

    def test_dependency_outputs_passed_to_dependants(self):
        """Dependency outputs are passed as input_data to dependant handlers."""
        def handler_a(data, ctx):
            return {"a_output": 42}

        def handler_b(data, ctx):
            # data should contain A's result
            assert "A" in data
            assert data["A"]["a_output"] == 42
            return {"b_output": "done"}

        stages = [
            _make_stage("A", handler=handler_a),
            _make_stage("B", deps=["A"], handler=handler_b),
        ]

        wf = WorkflowDefinition(name="test-dep-output", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)
        assert result.status == WorkflowStatus.COMPLETED.value

    def test_lifecycle_events_emitted(self):
        """All lifecycle events are emitted during execution."""
        def handler_a(data, ctx):
            return {}

        stages = [_make_stage("A", handler=handler_a)]

        wf = WorkflowDefinition(name="test-events", stages=stages)
        engine = WorkflowEngine()
        events = _collect_events(engine.dispatcher)
        engine.execute(wf)

        event_types = [type(e).__name__ for e in events]
        assert "WorkflowStarted" in event_types
        assert "StageStarted" in event_types
        assert "StageCompleted" in event_types
        assert "WorkflowCompleted" in event_types

    def test_pause_and_resume(self):
        """Workflow can be paused and resumed from checkpoint."""
        call_order = []

        def handler_a(data, ctx):
            call_order.append("A")
            return {"a": 1}

        def handler_b(data, ctx):
            call_order.append("B")
            return {"b": 2}

        stages = [
            _make_stage("A", handler=handler_a),
            _make_stage("B", deps=["A"], handler=handler_b),
        ]

        wf = WorkflowDefinition(name="test-pause-resume", stages=stages)
        engine = WorkflowEngine()

        # Execute first stage manually to get states
        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.PENDING.value),
            "B": StageState(stage_name="B", status=StageStatus.PENDING.value),
        }
        context = {}
        execution_order = []

        # Execute A
        result_a = handler_a({}, context)
        stage_states["A"].status = StageStatus.COMPLETED.value
        stage_states["A"].result = result_a
        context.update(result_a)
        execution_order.append("A")

        # Pause
        checkpoint_id = engine.pause("wf1", stage_states, context, execution_order)
        assert checkpoint_id

        # Resume
        result = engine.resume(wf, checkpoint_id)
        assert result.status == WorkflowStatus.COMPLETED.value
        assert "B" in call_order

    def test_resume_from_failure(self):
        """Workflow can resume from a failed result."""
        call_count = {"count": 0}

        def handler_a(data, ctx):
            return {"a": 1}

        def handler_b(data, ctx):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise RuntimeError("first attempt fails")
            return {"b": 2}

        stages = [
            _make_stage("A", handler=handler_a),
            _make_stage("B", deps=["A"], handler=handler_b, max_retries=1),
        ]

        wf = WorkflowDefinition(name="test-resume-fail", stages=stages)
        engine = WorkflowEngine()

        # First execution - B fails
        result1 = engine.execute(wf)
        assert result1.status == WorkflowStatus.FAILED.value

        # Resume from failure
        result2 = engine.resume_from_failure(wf, result1)
        assert result2.status == WorkflowStatus.COMPLETED.value

    def test_engine_register_stage_handler(self):
        """Handlers can be registered on the engine."""
        def my_handler(data, ctx):
            return {"done": True}

        stages = [_make_stage("A")]
        wf = WorkflowDefinition(name="test-external-handler", stages=stages)

        engine = WorkflowEngine()
        engine.register_stage_handler("A", my_handler)

        result = engine.execute(wf)
        assert result.status == WorkflowStatus.COMPLETED.value

    def test_cancel_workflow(self):
        """Workflow can be cancelled."""
        engine = WorkflowEngine()
        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.COMPLETED.value),
            "B": StageState(stage_name="B", status=StageStatus.PENDING.value),
        }
        events = _collect_events(engine.dispatcher)
        engine.cancel("wf1", stage_states, reason="user requested")

        cancel_events = [e for e in events if isinstance(e, WorkflowCancelled)]
        assert len(cancel_events) == 1
        assert cancel_events[0].reason == "user requested"

    def test_skip_stage(self):
        """A stage can be skipped."""
        engine = WorkflowEngine()
        stage_states = {
            "A": StageState(stage_name="A", status=StageStatus.PENDING.value),
        }
        events = _collect_events(engine.dispatcher)
        engine.skip_stage("A", stage_states, reason="not needed")

        assert stage_states["A"].status == StageStatus.SKIPPED.value
        skip_events = [e for e in events if isinstance(e, StageSkipped)]
        assert len(skip_events) == 1

    def test_empty_workflow(self):
        """An empty workflow completes immediately."""
        wf = WorkflowDefinition(name="test-empty", stages=[])
        engine = WorkflowEngine()
        result = engine.execute(wf)

        assert result.status == WorkflowStatus.COMPLETED.value
        assert result.completed_stage_count == 0

    def test_manifest_engine_property(self):
        """Manifest engine can be set and retrieved."""
        engine = WorkflowEngine()
        assert engine.manifest_engine is None

        mock_manifest = MagicMock()
        engine.manifest_engine = mock_manifest
        assert engine.manifest_engine is mock_manifest

    def test_workflow_result_serialization(self):
        """WorkflowResult can be serialized and deserialized."""
        stages = [
            _make_stage("A", handler=lambda d, c: {"x": 1}),
        ]
        wf = WorkflowDefinition(name="test-serial", stages=stages)
        engine = WorkflowEngine()
        result = engine.execute(wf)

        d = result.to_dict()
        assert d["workflow_id"] == result.workflow_id
        assert d["status"] == WorkflowStatus.COMPLETED.value

    def test_workflow_definition_serialization(self):
        """WorkflowDefinition can be serialized and deserialized."""
        stages = [
            _make_stage("A", max_retries=2),
            _make_stage("B", deps=["A"]),
        ]
        wf = WorkflowDefinition(name="test-serial", stages=stages, metadata={"key": "val"})
        d = wf.to_dict()

        wf2 = WorkflowDefinition.from_dict(d)
        assert wf2.name == "test-serial"
        assert len(wf2.stages) == 2
        assert wf2.metadata == {"key": "val"}