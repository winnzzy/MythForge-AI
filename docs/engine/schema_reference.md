# Schema Reference

> All dataclasses defined in `mythforge/engine/schema.py` and their fields.

Every dataclass is JSON-serialisable via `to_dict()` / `from_dict()` helpers.
The schema is intentionally extensible: add optional fields at the end of each
dataclass and bump `ManifestVersion.CURRENT` when the shape changes.

---

## Enums

### `ProjectStatus`

Lifecycle states for a MythForge project.

| Value | Description |
|-------|-------------|
| `CREATED` | Project created, no stages executed |
| `RESEARCHING` | Research stage in progress |
| `WRITING` | Script writing in progress |
| `SCENE_BREAKDOWN` | Scene breakdown in progress |
| `PROMPT_GENERATION` | Image prompt generation in progress |
| `IMAGE_GENERATION` | Image generation in progress |
| `NARRATION` | Narration/TTS in progress |
| `SFX` | Sound effects in progress |
| `MUSIC` | Music generation in progress |
| `RENDERING` | Video rendering in progress |
| `QA` | Quality assurance in progress |
| `READY` | Terminal — project ready for publishing |
| `FAILED` | Terminal — project failed (retryable) |
| `PUBLISHED` | Terminal — project published |

### `ManifestVersion`

| Value | Description |
|-------|-------------|
| `V1` / `CURRENT` | `"1.0"` — current schema version |

---

## Constants

### `PIPELINE_ORDER`

Canonical pipeline order used by resume logic to determine "next stage":

```python
[
    ProjectStatus.CREATED,
    ProjectStatus.RESEARCHING,
    ProjectStatus.WRITING,
    ProjectStatus.SCENE_BREAKDOWN,
    ProjectStatus.PROMPT_GENERATION,
    ProjectStatus.IMAGE_GENERATION,
    ProjectStatus.NARRATION,
    ProjectStatus.SFX,
    ProjectStatus.MUSIC,
    ProjectStatus.RENDERING,
    ProjectStatus.QA,
    ProjectStatus.READY,
    ProjectStatus.PUBLISHED,
]
```

---

## Core Dataclass: `Manifest`

The root document.  Represents an entire video project.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `project_id` | `str` | `uuid.uuid4().hex[:12]` | Unique 12-char hex identifier |
| `version` | `str` | `ManifestVersion.CURRENT.value` | Schema version |
| `title` | `str` | `""` | Human-readable project title |
| `slug` | `str` | `""` | URL-safe identifier |
| `status` | `str` | `ProjectStatus.CREATED.value` | Current project status |
| `current_stage` | `str` | `ProjectStatus.CREATED.value` | Currently executing stage |
| `completed_stages` | `List[str]` | `[]` | Stages that have completed or been skipped |
| `retry_counts` | `Dict[str, int]` | `{}` | Per-stage retry counts |
| `providers` | `List[Dict]` | `[]` | Provider records (see `ProviderRecord`) |
| `costs` | `List[Dict]` | `[]` | Cost records (see `CostRecord`) |
| `assets` | `List[Dict]` | `[]` | Asset records (see `AssetRecord`) |
| `render_history` | `List[Dict]` | `[]` | Render records (see `RenderRecord`) |
| `quality_checks` | `List[Dict]` | `[]` | QA check results (see `QualityCheck`) |
| `errors` | `List[Dict]` | `[]` | Error records (see `ErrorRecord`) |
| `warnings` | `List[Dict]` | `[]` | Warning records (see `WarningRecord`) |
| `settings` | `Dict[str, Any]` | `{}` | Project settings (resolution, fps, etc.) |
| `configuration_snapshot` | `Dict[str, Any]` | `{}` | Snapshot of provider/tool config |
| `metadata` | `Dict[str, Any]` | `{` | Arbitrary metadata (genre, audience, etc.) |
| `created_at` | `str` | ISO 8601 timestamp | Project creation time |
| `updated_at` | `str` | ISO 8601 timestamp | Last modification time |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_terminal` | `bool` | `True` if status is `READY`, `PUBLISHED`, or `FAILED` |
| `total_cost_usd` | `float` | Sum of all `amount_usd` in costs |
| `asset_count` | `int` | Number of assets |
| `error_count` | `int` | Number of errors |

---

## Sub-Records

### `AssetRecord`

One asset (image, audio file, thumbnail, etc.) produced by a stage.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `asset_id` | `str` | `uuid.uuid4().hex[:12]` | Unique asset identifier |
| `stage` | `str` | `""` | Pipeline stage that created it |
| `kind` | `str` | `""` | `image` / `narration` / `music` / `sfx` / `thumbnail` / `render` |
| `path` | `str` | `""` | Relative path inside project directory |
| `provider` | `str` | `""` | Provider name (e.g. `"gemini"`, `"elevenlabs"`) |
| `created_at` | `str` | ISO 8601 | Creation timestamp |
| `metadata` | `Dict[str, Any]` | `{}` | Arbitrary metadata |

---

### `CostRecord`

One cost entry for a provider operation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stage` | `str` | `""` | Pipeline stage |
| `provider` | `str` | `""` | Provider name |
| `operation` | `str` | `""` | Operation description |
| `amount_usd` | `float` | `0.0` | Cost in USD |
| `tokens_in` | `int` | `0` | Input tokens |
| `tokens_out` | `int` | `0` | Output tokens |
| `created_at` | `str` | ISO 8601 | Timestamp |

---

### `ProviderRecord`

Records which provider was selected for a capability.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `capability` | `str` | `""` | Capability name (`llm`, `tts`, `image`, `video`, `music`, `sfx`) |
| `provider` | `str` | `""` | Provider name |
| `model` | `str` | `""` | Model name |
| `selected_at` | `str` | ISO 8601 | Selection timestamp |
| `metadata` | `Dict[str, Any]` | `{}` | Arbitrary metadata |

---

### `ErrorRecord`

An error that occurred during a pipeline stage.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `error_id` | `str` | `uuid.uuid4().hex[:12]` | Unique error identifier |
| `stage` | `str` | `""` | Pipeline stage |
| `message` | `str` | `""` | Error message |
| `traceback` | `str` | `""` | Optional traceback |
| `occurred_at` | `str` | ISO 8601 | Timestamp |
| `metadata` | `Dict[str, Any]` | `{}` | Arbitrary metadata |

---

### `WarningRecord`

A warning that occurred during a pipeline stage.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `warning_id` | `str` | `uuid.uuid4().hex[:12]` | Unique warning identifier |
| `stage` | `str` | `""` | Pipeline stage |
| `message` | `str` | `""` | Warning message |
| `occurred_at` | `str` | ISO 8601 | Timestamp |
| `metadata` | `Dict[str, Any]` | `{}` | Arbitrary metadata |

---

### `QualityCheck`

A QA check result.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `check_id` | `str` | `uuid.uuid4().hex[:12]` | Unique check identifier |
| `stage` | `str` | `""` | Pipeline stage |
| `check_type` | `str` | `""` | Check type (e.g. `"subtitle_sync"`, `"audio_levels"`) |
| `passed` | `bool` | `True` | Whether the check passed |
| `score` | `float` | `0.0` | Numeric score (0.0–1.0) |
| `details` | `str` | `""` | Human-readable details |
| `checked_at` | `str` | ISO 8601 | Timestamp |

---

### `RenderRecord`

A render output record.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `render_id` | `str` | `uuid.uuid4().hex[:12]` | Unique render identifier |
| `kind` | `str` | `""` | `draft` / `final` |
| `path` | `str` | `""` | Relative path to rendered file |
| `resolution` | `str` | `""` | Resolution (e.g. `"1080p"`, `"4k"`) |
| `duration_s` | `float` | `0.0` | Duration in seconds |
| `file_size_bytes` | `int` | `0` | File size |
| `rendered_at` | `str` | ISO 8601 | Timestamp |
| `metadata` | `Dict[str, Any]` | `{}` | Arbitrary metadata |

---

### `StageRecord`

Execution record for a single pipeline stage.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stage` | `str` | `""` | Stage name |
| `status` | `str` | `"pending"` | `pending` / `running` / `completed` / `failed` / `skipped` |
| `started_at` | `str` | `""` | ISO 8601 start timestamp |
| `completed_at` | `str` | `""` | ISO 8601 completion timestamp |
| `duration_s` | `float` | `0.0` | Duration in seconds |
| `retry_count` | `int` | `0` | Number of retries |
| `error` | `str` | `""` | Error message (if failed) |
| `metadata` | `Dict[str, Any]` | `{}` | Arbitrary metadata |

---

## Extending the Schema

To add a new field to any dataclass:

1. Add the field at the **end** of the dataclass with a default value
2. Update `to_dict()` and `from_dict()` if the field is not a simple type
3. Bump `ManifestVersion.CURRENT` if the shape change is breaking
4. Existing manifests will load correctly (unknown fields are ignored by `from_dict`)