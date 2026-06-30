# Workflow Engine

## Overview

The Workflow Engine is MythForge's deterministic orchestration system. It coordinates production stages (Research, Script, Image Generation, Narration, etc.) without containing any business logic or AI provider knowledge.

## Key Features

- **Deterministic execution** — Stages execute only when dependencies are satisfied, in a reproducible order.
- **Dependency graph (DAG)** — Stages declare inputs, outputs, and dependencies; the engine builds and validates a directed acyclic graph.
- **Parallel execution** — Independent stages at the same dependency frontier execute concurrently (when handlers are async).
- **Retry with backoff** — Each stage can declare a retry policy (max retries, exponential backoff, max delay).
- **Checkpoints** — Pause/resume workflows at any point. Checkpoints serialise the full execution state.
- **Lifecycle events** — Strongly-typed events for every state transition (started, completed, failed, retried, paused, resumed, cancelled, skipped).
- **Manifest integration** — Optional hooks to synchronise workflow results with the Manifest Engine.
- **Extensible** — New stages are registered without changing engine code.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   WorkflowEngine                      │
│                                                      │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ Execution   │  │   Retry     │  │   Resume     │  │
│  │ Planner     │  │   Planner   │  │   Planner    │  │
│  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘  │
│        │                │                │           │
│  ┌─────┴────────────────┴────────────────┴───────┐   │
│  │            DependencyGraph (DAG)               │   │
│  └────────────────────┬──────────────────────────┘   │
│                       │                              │
│  ┌────────────────────┴──────────────────────────┐   │
│  │          Stage Registry + Handlers             │   │
│  └───────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │   Event       │  │  Checkpoint  │                  │
│  │   Dispatcher  │  │  Manager     │                  │
│  └──────────────┘  └──────────────┘                  │
│                                                      │
│  ┌───────────────────────────────────────────────┐   │
│  │         Manifest Sync (optional)               │   │
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

## Quick Start

```python
from mythforge.workflow import (
    WorkflowEngine,
    WorkflowDefinition,
    StageDefinition,
    RetryPolicy,
)
from mythforge.workflow.events import EventDispatcher, WorkflowCompleted

# Define stages
research = StageDefinition(
    name="RESEARCH",
    handler=lambda inp, ctx: {"research_data": {"topic": "mythology"}},
    produced_outputs=["research_data"],
)

script = StageDefinition(
    name="SCRIPT",
    handler=lambda inp, ctx: {"script": {"scenes": 5}},
    dependencies=["RESEARCH"],
    produced_outputs=["script"],
)

# Build workflow
workflow = WorkflowDefinition(
    name="My Production",
    stages=[research, script],
)

# Create engine and execute
engine = WorkflowEngine()

# Optional: subscribe to events
engine.dispatcher.subscribe("WorkflowCompleted", lambda e: print(f"Done! {e.completed_stages} stages"))

result = engine.execute(workflow, context={"project_id": "demo-001"})

print(result.status)       # "completed"
print(result.duration_s)   # execution time
```

## Module Structure

| Module | Purpose |
|---|---|
| `models.py` | Data classes: `StageDefinition`, `WorkflowDefinition`, `StageState`, `WorkflowResult`, `RetryPolicy`, `CostEstimate`, `CheckpointData` |
| `registry.py` | `StageRegistry` — register, discover, and manage stage definitions |
| `dag.py` | `DependencyGraph` — build and validate the DAG, compute ready stages, topological order |
| `events.py` | `EventDispatcher` + strongly-typed event classes |
| `checkpoint.py` | `CheckpointManager` — create, restore, list, and persist checkpoints |
| `executor.py` | `WorkflowEngine`, `ExecutionPlanner`, `ResumePlanner`, `RetryPlanner` |
| `manifest_hooks.py` | `ManifestSync` — optional integration with the Manifest Engine |
| `exceptions.py` | Exception hierarchy |

## Built-in Stages

The engine ships with standard MythForge production stage names:

| Stage | Dependencies | Description |
|---|---|---|
| `RESEARCH` | — | Gather source material |
| `SCRIPT` | RESEARCH | Write the script |
| `SCENE_BREAKDOWN` | SCRIPT | Break script into scenes |
| `PROMPT_GENERATION` | SCENE_BREAKDOWN | Generate AI prompts |
| `IMAGE_GENERATION` | PROMPT_GENERATION | Generate images |
| `NARRATION` | SCRIPT | Generate voice narration |
| `MUSIC` | SCRIPT | Generate background music |
| `SOUND_EFFECTS` | SCENE_BREAKDOWN | Generate sound effects |
| `RENDERING` | IMAGE_GENERATION, NARRATION, MUSIC, SOUND_EFFECTS | Compose final output |
| `QUALITY_ASSURANCE` | RENDERING | Review quality |
| `PUBLISHING` | QUALITY_ASSURANCE | Publish final product |

## Further Reading

- [Architecture](architecture.md) — Detailed design and data flow
- [Events](events.md) — All event types and subscription patterns
- [Developer Guide](developer-guide.md) — How to register custom stages, extend the engine