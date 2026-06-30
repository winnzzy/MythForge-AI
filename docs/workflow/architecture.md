# Workflow Engine — Architecture

## Design Principles

1. **Separation of concerns** — The engine orchestrates; it does not implement stage logic.
2. **Determinism** — Given the same workflow definition and context, execution order is reproducible.
3. **Immutability of definitions** — `StageDefinition` and `WorkflowDefinition` are declarative blueprints. Execution state lives in `StageState`.
4. **Event-driven observability** — Every state transition emits a strongly-typed event.
5. **Fail-safe** — Failures are contained per-stage. The engine retries according to policy, then marks the workflow as failed without corrupting completed stages.

## Component Overview

### 1. Models (`models.py`)

All data classes are JSON-serialisable via `to_dict()` / `from_dict()`. This enables checkpointing, manifest sync, and cross-process communication.

**Key types:**

- `StageDefinition` — Blueprint for a stage (name, handler, dependencies, retry policy, cost estimate).
- `WorkflowDefinition` — Collection of stage definitions + metadata.
- `StageState` — Mutable execution state for one stage (status, attempt, error, result, timestamps).
- `WorkflowResult` — Immutable outcome of a workflow execution.
- `RetryPolicy` — Per-stage retry configuration with exponential backoff.
- `CostEstimate` — Estimated cost and duration for a stage.
- `CheckpointData` — Serialisable snapshot of the entire execution state.

**Enums:**

- `StageStatus` — `PENDING | RUNNING | COMPLETED | FAILED | SKIPPED | CANCELLED | WAITING_RETRY`
- `WorkflowStatus` — `CREATED | RUNNING | PAUSED | COMPLETED | FAILED | CANCELLED`

### 2. Stage Registry (`registry.py`)

Centralised registry for stage definitions. Supports:

- Register/unregister stage definitions
- Handler registration (separate from definitions)
- Decorator-based registration (`@registry.register(...)`)
- Building `WorkflowDefinition` from registered stages
- Filtering by metadata (e.g., parallel-eligible stages)

```python
registry = StageRegistry()

@registry.register("RESEARCH", produced_outputs=["research_data"])
def do_research(input_data, context):
    return {"research_data": {...}}
```

### 3. Dependency Graph (`dag.py`)

`DependencyGraph` builds a DAG from a list of `StageDefinition` objects.

**Validation:**

- Rejects cyclic dependencies (topological sort with Kahn's algorithm)
- Rejects missing dependencies (stage references non-existent stage)
- Rejects self-dependencies

**Queries:**

- `ready_stages(completed, exclude)` — Stages whose dependencies are all in `completed`
- `topological_order()` — Deterministic execution order
- `parallel_groups()` — Groups of stages that can execute in parallel
- `dependencies_of(name)` / `dependants_of(name)` — Direct dependency queries
- `ancestors(name)` — All transitive dependencies

### 4. Execution Planner (`executor.py`)

`ExecutionPlanner` is **pure** — it reads state and returns decisions without mutating anything.

- `plan_next(stage_states)` — Returns the next batch of stages ready to execute
- `is_complete(stage_states)` — All stages completed or skipped
- `can_progress(stage_states)` — Whether any stages can still be executed

### 5. Resume Planner (`executor.py`)

`ResumePlanner` handles resumption from checkpoints or after failures.

- `plan_resume(stage_states)` — Identifies stages that need re-execution (PENDING, FAILED, WAITING_RETRY, CANCELLED)
- `reset_failed_stages(stage_states)` — Resets failed/cancelled stages to PENDING (returns new dict, does not mutate)

### 6. Retry Planner (`executor.py`)

`RetryPlanner` decides whether to retry a failed stage.

- `should_retry(stage_defn, state)` — Returns `True` if `attempt < max_retries`
- `next_delay(stage_defn, state)` — Computes backoff delay using `RetryPolicy.delay_for_attempt()`

### 7. Event Dispatcher (`events.py`)

Pub/sub event system with:

- **Specific subscriptions** — `dispatcher.subscribe("StageFailed", handler)`
- **Wildcard subscriptions** — `dispatcher.subscribe("*", handler)`
- **Event log** — Automatic recording of all dispatched events (configurable max size)
- **Error isolation** — Handler exceptions are logged but don't break dispatch
- **Type safety** — All events are frozen dataclasses inheriting from `WorkflowEvent`

### 8. Checkpoint Manager (`checkpoint.py`)

Creates and restores execution snapshots.

- In-memory storage by default
- Optional disk persistence via `persist_to_disk(workflow_id, filepath)` / `load_from_disk(filepath)`
- Supports latest-checkpoint lookup, listing, and cleanup

### 9. Workflow Engine / Executor (`executor.py`)

The central orchestrator that combines all components.

**Execution flow:**

```
1. Build DependencyGraph from workflow.stages
2. Initialise StageState for each stage (PENDING)
3. Merge handlers (workflow definitions + engine-registered)
4. Emit WorkflowStarted event
5. Loop:
   a. Ask planner for ready stages
   b. For each ready stage:
      - Set status → RUNNING
      - Emit StageStarted
      - Call handler(input_data, context)
      - On success: set COMPLETED, merge outputs, emit StageCompleted
      - On failure: check retry policy
        - If retryable: set WAITING_RETRY, emit RetryScheduled, continue loop
        - If exhausted: set FAILED, emit StageFailed
   c. Repeat until complete or stuck
6. Determine final status (COMPLETED / FAILED / PAUSED)
7. Emit WorkflowCompleted (if completed)
8. Sync to manifest (if configured)
9. Return WorkflowResult
```

**Pause / Resume flow:**

```
Pause:
1. Create checkpoint from current stage_states + context
2. Emit WorkflowPaused

Resume:
1. Restore checkpoint
2. Reset failed stages to PENDING
3. Continue execution from restored state
```

### 10. Manifest Hooks (`manifest_hooks.py`)

Optional integration with the Manifest Engine. The `ManifestSync` class:

- Receives workflow results on completion
- Writes pipeline metadata to the manifest
- Does not modify the Manifest Engine — only reads/writes through its public API

## Data Flow

```
WorkflowDefinition
       │
       ▼
DependencyGraph ──→ ExecutionPlanner ──→ ready stages
       │                                       │
       │                                       ▼
       │                              stage handlers
       │                                       │
       │                                       ▼
       │                              context (shared state)
       │                                       │
       ▼                                       ▼
CheckpointManager ◄──── pause/resume ◄─── WorkflowResult
       │
       ▼
ManifestSync (optional)
```

## State Machine

### Stage State Machine

```
PENDING ──→ RUNNING ──→ COMPLETED
                │
                ├──→ WAITING_RETRY ──→ RUNNING (retry)
                │
                └──→ FAILED
                
PENDING ──→ SKIPPED
PENDING ──→ CANCELLED
```

### Workflow State Machine

```
CREATED ──→ RUNNING ──→ COMPLETED
                │
                ├──→ FAILED
                │
                ├──→ PAUSED ──→ RUNNING (resume)
                │
                └──→ CANCELLED
```

## Thread Safety

The current implementation is single-threaded and synchronous. For production use with async handlers:

- The executor loop can be extended to use `asyncio.gather()` for parallel stages
- The `EventDispatcher` and `CheckpointManager` use simple dicts — add locks for concurrent access
- `StageState` mutations are isolated per-stage, so parallel stage execution is safe as long as context merges are synchronised