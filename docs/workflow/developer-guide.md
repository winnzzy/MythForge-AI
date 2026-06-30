# Workflow Engine — Developer Guide

## Adding a New Stage

The engine is designed so that new stages can be registered without modifying engine code. There are two approaches:

### Approach 1: Define at Workflow Creation Time

```python
from mythforge.workflow.models import StageDefinition, RetryPolicy, CostEstimate

my_stage = StageDefinition(
    name="CUSTOM_ANALYSIS",
    handler=my_analysis_function,
    dependencies=["SCRIPT"],
    required_inputs=["script"],
    produced_outputs=["analysis"],
    parallel_eligible=True,
    retry_policy=RetryPolicy(max_retries=5, backoff_base_s=2.0),
    cost_estimate=CostEstimate(estimated_cost_usd=0.50, estimated_duration_s=30.0),
    metadata={"category": "ai_generation"},
)
```

### Approach 2: Use the Stage Registry

```python
from mythforge.workflow.registry import StageRegistry

registry = StageRegistry()

# Decorator style
@registry.register(
    "CUSTOM_ANALYSIS",
    dependencies=["SCRIPT"],
    required_inputs=["script"],
    produced_outputs=["analysis"],
)
def run_analysis(input_data, context):
    script = context["script"]
    # ... perform analysis ...
    return {"analysis": {"sentiment": "positive", "score": 0.85}}

# Register handler separately
registry.register_handler("CUSTOM_ANALYSIS", run_analysis)

# Build workflow from registry
workflow = registry.to_workflow(
    name="My Production",
    stage_filter=lambda defn: defn.name in {"SCRIPT", "CUSTOM_ANALYSIS"},
)
```

### Approach 3: Engine-Level Registration

```python
engine = WorkflowEngine()

# Register a handler that applies to any workflow using this stage name
engine.register_stage_handler("CUSTOM_ANALYSIS", my_handler)
```

Handler registration priority (highest to lowest):
1. Engine-registered handlers (`engine.register_stage_handler()`)
2. Stage definition handlers (`StageDefinition(handler=...)`)

## Handler Contract

Stage handlers follow a simple contract:

```python
def my_handler(input_data: dict, context: dict) -> dict:
    """
    Parameters
    ----------
    input_data:
        Results from dependency stages, keyed by stage name.
        e.g. {"RESEARCH": {"data": ...}, "SCRIPT": {"text": ...}}
    context:
        Shared mutable context for the entire workflow.
        Contains initial context + outputs from completed stages.

    Returns
    -------
    dict:
        Result dict. Keys listed in `produced_outputs` will be
        merged into context. If `produced_outputs` is empty,
        the entire result is merged.
    """
    ...
```

### Handler Rules

1. **Pure side effects** — Handlers should not modify the filesystem or external systems directly. Use context to pass data.
2. **Idempotent** — Handlers may be retried. Ensure repeated calls produce the same result.
3. **Raise on failure** — Raise an exception to signal failure. The engine handles retry logic.
4. **Return a dict** — Always return a dict (or `None` for no-op stages).

## Defining Retry Policies

```python
from mythforge.workflow.models import RetryPolicy

# Aggressive retry for flaky API calls
api_retry = RetryPolicy(
    max_retries=5,
    backoff_base_s=2.0,
    backoff_multiplier=1.5,
    max_backoff_s=120.0,
)

# No retry for deterministic operations
deterministic_retry = RetryPolicy(max_retries=0)

# Default policy (3 retries, 1s base, 2x multiplier, 60s max)
default_retry = RetryPolicy()
```

Backoff formula: `delay = backoff_base_s * (backoff_multiplier ^ attempt)`, capped at `max_backoff_s`.

## Defining Dependencies

Stages declare dependencies by listing the names of stages that must complete first:

```python
rendering = StageDefinition(
    name="RENDERING",
    dependencies=["IMAGE_GENERATION", "NARRATION", "MUSIC", "SOUND_EFFECTS"],
)
```

The engine validates:
- All dependency names exist in the workflow
- No cycles (A → B → A)
- No self-dependencies

## Working with Checkpoints

### Creating a Checkpoint

```python
checkpoint_id = engine.pause(
    workflow_id="wf-001",
    stage_states=stage_states,
    context=current_context,
    execution_order=["RESEARCH", "SCRIPT"],
    reason="User requested pause",
)
```

### Resuming from a Checkpoint

```python
result = engine.resume(workflow, checkpoint_id)
```

### Resuming from a Failed Result

```python
# If the workflow failed, resume without an explicit checkpoint
result = engine.resume_from_failure(workflow, previous_result)
```

### Persisting Checkpoints to Disk

```python
# Save
engine.checkpoint_manager.persist_to_disk("wf-001", "/tmp/checkpoint.json")

# Load
engine.checkpoint_manager.load_from_disk("/tmp/checkpoint.json")
```

## Subscribing to Events

```python
from mythforge.workflow.events import EventDispatcher

# Track all events
def on_any_event(event):
    print(f"[{event.event_type}] at {event.timestamp}")

engine.dispatcher.subscribe("*", on_any_event)

# Track specific events
def on_failure(event):
    if not event.will_retry:
        print(f"PERMANENT FAILURE: {event.stage_name} — {event.error}")

engine.dispatcher.subscribe("StageFailed", on_failure)

# Access event log
events = engine.dispatcher.get_log(limit=100)
```

## Using the Stage Registry

```python
from mythforge.workflow.registry import StageRegistry

registry = StageRegistry()

# Register stages with metadata
registry.register(StageDefinition(
    name="RESEARCH",
    parallel_eligible=True,
    metadata={"category": "data_gathering"},
))

registry.register(StageDefinition(
    name="SCRIPT",
    dependencies=["RESEARCH"],
    metadata={"category": "content_creation"},
))

# Get parallel-eligible stages
parallel_stages = registry.get_parallel_eligible()

# Build a workflow with specific stages
workflow = registry.to_workflow(
    name="Content Pipeline",
    stage_filter=lambda d: d.metadata.get("category") == "content_creation",
)

# Clear the registry
registry.clear()
```

## Integrating with the Manifest Engine

```python
from mythforge.engine.engine import ManifestEngine

manifest = ManifestEngine(...)
engine = WorkflowEngine(manifest_engine=manifest)

# On workflow completion, results are automatically synced
result = engine.execute(workflow)
# Manifest now contains pipeline metadata
```

The manifest sync is a one-way hook — it writes workflow results to the manifest but does not read from it during execution.

## Complete Example: Custom Production Pipeline

```python
from mythforge.workflow import WorkflowEngine, WorkflowDefinition, StageDefinition
from mythforge.workflow.models import RetryPolicy, CostEstimate
from mythforge.workflow.events import EventDispatcher

# Define stage handlers
def gather_sources(inp, ctx):
    topic = ctx.get("topic", "mythology")
    return {"sources": [{"title": "Source A", "url": "..."}]}

def write_script(inp, ctx):
    sources = ctx.get("sources", [])
    return {"script": {"title": "My Script", "scenes": 10}}

def generate_images(inp, ctx):
    script = ctx.get("script", {})
    return {"images": [f"img_{i}.png" for i in range(script.get("scenes", 0))]}

def render_video(inp, ctx):
    images = ctx.get("images", [])
    return {"video": "output.mp4", "duration_s": 300}

# Build workflow
workflow = WorkflowDefinition(
    name="Custom Video Production",
    stages=[
        StageDefinition(
            name="GATHER_SOURCES",
            handler=gather_sources,
            produced_outputs=["sources"],
            cost_estimate=CostEstimate(estimated_cost_usd=0.10, estimated_duration_s=5),
        ),
        StageDefinition(
            name="WRITE_SCRIPT",
            handler=write_script,
            dependencies=["GATHER_SOURCES"],
            produced_outputs=["script"],
            retry_policy=RetryPolicy(max_retries=2),
            cost_estimate=CostEstimate(estimated_cost_usd=0.50, estimated_duration_s=15),
        ),
        StageDefinition(
            name="GENERATE_IMAGES",
            handler=generate_images,
            dependencies=["WRITE_SCRIPT"],
            produced_outputs=["images"],
            parallel_eligible=True,
            retry_policy=RetryPolicy(max_retries=3),
            cost_estimate=CostEstimate(estimated_cost_usd=5.00, estimated_duration_s=120),
        ),
        StageDefinition(
            name="RENDER_VIDEO",
            handler=render_video,
            dependencies=["GENERATE_IMAGES"],
            produced_outputs=["video"],
            cost_estimate=CostEstimate(estimated_cost_usd=1.00, estimated_duration_s=60),
        ),
    ],
)

# Execute
engine = WorkflowEngine()

# Subscribe to lifecycle events
engine.dispatcher.subscribe("*", lambda e: print(f"  {e.event_type}: {e.stage_name if hasattr(e, 'stage_name') else ''}"))

result = engine.execute(workflow, context={"topic": "Greek Mythology"})

print(f"\nStatus: {result.status}")
print(f"Duration: {result.duration_s:.2f}s")
print(f"Video: {result.context.get('video')}")
print(f"Execution order: {result.metadata.get('execution_order')}")
```

## Exception Hierarchy

```
WorkflowError (base)
├── DependencyError     — Invalid dependency graph (cycles, missing deps)
├── StageExecutionError — Stage handler raised an exception
└── PlannerError        — Execution planner cannot make progress
```

## Testing Tips

```python
# Use simple lambdas for test handlers
stage = StageDefinition(
    name="TEST_STAGE",
    handler=lambda inp, ctx: {"result": "ok"},
)

# Use side-effect handlers to track call order
call_log = []

def tracking_handler(name):
    def handler(inp, ctx):
        call_log.append(name)
        return {}
    return handler

# Verify execution order
assert call_log == ["A", "B", "C"]

# Test failure and retry
call_count = 0
def flaky_handler(inp, ctx):
    global call_count
    call_count += 1
    if call_count < 3:
        raise RuntimeError("transient error")
    return {"result": "ok"}