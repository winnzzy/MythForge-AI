# Workflow Engine — Events

## Overview

The Workflow Engine emits strongly-typed events for every state transition. Events are immutable frozen dataclasses that enable observability, logging, monitoring, and integration with external systems.

## Event Dispatcher

```python
from mythforge.workflow.events import EventDispatcher

dispatcher = EventDispatcher()

# Subscribe to a specific event type
dispatcher.subscribe("StageFailed", my_handler)

# Subscribe to all events
dispatcher.subscribe("*", my_catchall_handler)

# Unsubscribe
dispatcher.unsubscribe("StageFailed", my_handler)

# Access the event log
recent_events = dispatcher.get_log(limit=50)
dispatcher.clear_log()
```

### Handler Signature

Event handlers receive a single argument — the event object:

```python
def on_stage_failed(event):
    print(f"Stage {event.stage_name} failed: {event.error}")
```

### Error Isolation

If a handler raises an exception, the dispatcher logs the error and continues delivering to remaining handlers. One bad handler cannot break the event system.

## Event Types

### WorkflowStarted

Emitted when a workflow begins execution.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"WorkflowStarted"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Unique workflow identifier |
| `workflow_name` | `str` | Human-readable workflow name |
| `total_stages` | `int` | Number of stages in the workflow |

### StageStarted

Emitted when a stage begins execution.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"StageStarted"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `stage_name` | `str` | Stage being executed |
| `attempt` | `int` | Attempt number (1-indexed) |

### StageCompleted

Emitted when a stage completes successfully.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"StageCompleted"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `stage_name` | `str` | Stage that completed |
| `duration_s` | `float` | Execution duration in seconds |
| `result_keys` | `list[str]` | Keys written to the result |

### StageFailed

Emitted when a stage execution fails.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"StageFailed"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `stage_name` | `str` | Stage that failed |
| `error` | `str` | Error message |
| `attempt` | `int` | Attempt number (1-indexed) |
| `will_retry` | `bool` | Whether the engine will retry |

### RetryScheduled

Emitted when a failed stage is scheduled for retry.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"RetryScheduled"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `stage_name` | `str` | Stage being retried |
| `attempt` | `int` | Next attempt number (1-indexed) |
| `delay_s` | `float` | Backoff delay in seconds |

### StageSkipped

Emitted when a stage is explicitly skipped.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"StageSkipped"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `stage_name` | `str` | Stage that was skipped |
| `reason` | `str` | Why the stage was skipped |

### WorkflowPaused

Emitted when a workflow is paused and a checkpoint is created.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"WorkflowPaused"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `checkpoint_id` | `str` | ID of the created checkpoint |
| `reason` | `str` | Why the workflow was paused |

### WorkflowResumed

Emitted when a workflow resumes from a checkpoint.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"WorkflowResumed"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `checkpoint_id` | `str` | Checkpoint being resumed from |
| `remaining_stages` | `int` | Number of stages left to execute |

### WorkflowCompleted

Emitted when all stages complete successfully.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"WorkflowCompleted"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `duration_s` | `float` | Total execution duration |
| `completed_stages` | `int` | Number of completed stages |

### WorkflowCancelled

Emitted when a workflow is cancelled.

| Field | Type | Description |
|---|---|---|
| `event_type` | `str` | `"WorkflowCancelled"` |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `workflow_id` | `str` | Workflow identifier |
| `reason` | `str` | Why the workflow was cancelled |
| `completed_stages` | `int` | Number of stages completed before cancellation |

## Event Log

The dispatcher maintains an in-memory event log:

```python
dispatcher = EventDispatcher()

# ... dispatch events ...

# Get recent events (newest first)
events = dispatcher.get_log(limit=100)

# Get events filtered by type
failed_events = dispatcher.get_log(event_type="StageFailed")

# Clear the log
dispatcher.clear_log()
```

The log has a configurable maximum size (default: 10,000 events). Older events are discarded when the limit is reached.

## Usage Patterns

### Logging Integration

```python
import logging

logger = logging.getLogger("workflow")

def log_event(event):
    logger.info(f"[{event.event_type}] {event}")

engine.dispatcher.subscribe("*", log_event)
```

### Metrics Collection

```python
def track_stage_duration(event):
    if event.event_type == "StageCompleted":
        metrics.histogram("stage.duration", event.duration_s, tags={"stage": event.stage_name})

engine.dispatcher.subscribe("StageCompleted", track_stage_duration)
```

### Failure Alerting

```python
def alert_on_failure(event):
    if not event.will_retry:
        send_alert(f"Stage {event.stage_name} failed permanently: {event.error}")

engine.dispatcher.subscribe("StageFailed", alert_on_failure)
```

### Checkpoint on Pause

```python
def save_checkpoint_to_s3(event):
    checkpoint = engine.checkpoint_manager.restore_checkpoint(event.checkpoint_id)
    # Upload to S3...

engine.dispatcher.subscribe("WorkflowPaused", save_checkpoint_to_s3)