# ManifestEngine — API Reference

> Complete method-by-method documentation for `mythforge.engine.ManifestEngine`.

---

## Constructor

### `ManifestEngine(base_dir: str | Path = "projects")`

Create a new engine instance.  The engine does **not** load a project automatically —
call `create_project()` or `load_project()` before using any other method.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `base_dir` | `str \| Path` | `"projects"` | Root directory containing all project folders |

---

## Properties

### `manifest → Manifest`

Returns the currently-loaded manifest.  Raises `RuntimeError` if no project is loaded.

### `project_dir → Path`

Returns the project directory path.  Raises `RuntimeError` if no project is loaded.

### `stage_records → Dict[str, StageRecord]`

Returns a copy of all stage execution records.

---

## Project Lifecycle

### `create_project(title, slug, *, settings=None, configuration_snapshot=None, metadata=None) → Manifest`

Create a brand-new project and its on-disk directory structure.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `title` | `str` | *required* | Human-readable project title |
| `slug` | `str` | *required* | URL-safe identifier (used as directory name) |
| `settings` | `Dict[str, Any]` | `None` | Project settings (resolution, fps, etc.) |
| `configuration_snapshot` | `Dict[str, Any]` | `None` | Snapshot of provider/tool configuration |
| `metadata` | `Dict[str, Any]` | `None` | Arbitrary metadata (genre, audience, etc.) |

**Returns:** `Manifest`

**Raises:**
- `FileExistsError` — if a project with the same slug already exists

**Side effects:**
- Creates directory tree: `assets/images`, `assets/narration`, `assets/music`, `assets/sfx`, `assets/thumbnails`, `assets/renders/draft`, `assets/renders/final`, `logs`
- Writes `manifest.json` to disk

**Example:**
```python
manifest = engine.create_project(
    title="Shango Rises",
    slug="shango-rises",
    settings={"resolution": "4k", "fps": 30},
    metadata={"genre": "mythology"},
)
```

---

### `load_project(slug: str) → Manifest`

Load an existing project from disk.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `slug` | `str` | Project slug (directory name) |

**Returns:** `Manifest`

**Raises:**
- `FileNotFoundError` — if the project directory or manifest file does not exist

**Example:**
```python
engine2 = ManifestEngine(base_dir="projects")
manifest = engine2.load_project("shango-rises")
```

---

### `save() → None`

Persist the current manifest (and stage records) to disk.

Uses an atomic write pattern: write to temp file, then rename.
On Windows, falls back to copy-then-delete if `os.replace` raises `PermissionError`.

**Raises:**
- `RuntimeError` — if no project is loaded

---

## Stage Tracking

### `begin_stage(stage: str) → StageRecord`

Mark a stage as running.  Updates manifest status and creates/updates the stage record.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `stage` | `str` | Stage name (must be a valid `ProjectStatus` value) |

**Returns:** `StageRecord` with `status = "running"`

**Raises:**
- `RuntimeError` — if no project is loaded, or project is in immutable terminal state (`READY`, `PUBLISHED`)
- `ValueError` — if `stage` is not a known pipeline stage

**Note:** `FAILED` status is **not** immutable — it allows retry via `begin_stage`.

**Example:**
```python
engine.begin_stage("RESEARCHING")
# ... do research work ...
engine.complete_stage("RESEARCHING")
```

---

### `complete_stage(stage: str, *, metadata=None) → StageRecord`

Mark a stage as completed.  Adds it to `completed_stages` and advances the pipeline.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `stage` | `str` | *required* | Stage name |
| `metadata` | `Dict[str, Any]` | `None` | Arbitrary metadata to attach to the stage record |

**Returns:** `StageRecord` with `status = "completed"`

**Raises:**
- `ValueError` — if the stage was never started

**Side effects:**
- Adds stage to `completed_stages` (idempotent)
- Advances `current_stage` and `status` to the next pipeline stage
- Saves to disk

---

### `fail_stage(stage: str, error: str, *, traceback: str = "") → StageRecord`

Mark a stage as failed and record the error.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `stage` | `str` | *required* | Stage name |
| `error` | `str` | *required* | Error message |
| `traceback` | `str` | `""` | Optional traceback string |

**Returns:** `StageRecord` with `status = "failed"`

**Side effects:**
- Sets project status to `FAILED`
- Increments retry count
- Records error in manifest
- Saves to disk

**Example:**
```python
try:
    engine.begin_stage("IMAGE_GENERATION")
    generate_images()
    engine.complete_stage("IMAGE_GENERATION")
except Exception as e:
    engine.fail_stage("IMAGE_GENERATION", str(e), traceback=traceback.format_exc())
```

---

### `skip_stage(stage: str, *, reason: str = "") → StageRecord`

Mark a stage as skipped (e.g. cached assets already exist).

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `stage` | `str` | *required* | Stage name |
| `reason` | `str` | `""` | Reason for skipping |

**Returns:** `StageRecord` with `status = "skipped"`

**Side effects:**
- Adds stage to `completed_stages`
- Saves to disk

---

### `is_stage_completed(stage: str) → bool`

Return `True` if the stage has been marked completed or skipped.

---

### `get_stage_record(stage: str) → Optional[StageRecord]`

Return the `StageRecord` for the given stage, or `None` if it was never executed.

---

## Resume Logic

### `get_next_stage() → Optional[str]`

Return the next pipeline stage that needs to run, or `None` if the project is complete.

Skips:
- Terminal statuses (`READY`, `PUBLISHED`)
- Initial `CREATED` state (set automatically, never "executed")
- Already-completed stages

**Returns:** Stage name string, or `None`

---

### `resume() → Optional[str]`

Resume a project: determine the next stage and return it.

If the project is in `FAILED` status, resets the failed stage so it can be retried.

**Returns:** Stage name string to execute, or `None` if the project is already complete

**Example:**
```python
engine = ManifestEngine(base_dir="projects")
engine.load_project("shango-rises")
next_stage = engine.resume()
if next_stage:
    engine.begin_stage(next_stage)
    # ... execute stage ...
```

---

## Asset Tracking

### `record_asset(asset: AssetRecord) → None`

Add an asset record to the manifest.  Saves to disk.

---

### `get_assets(*, stage=None, kind=None) → List[AssetRecord]`

Return assets, optionally filtered by stage and/or kind.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `stage` | `Optional[str]` | `None` | Filter by pipeline stage |
| `kind` | `Optional[str]` | `None` | Filter by asset kind (`image`, `narration`, `music`, `sfx`, `thumbnail`, `render`) |

---

## Cost Tracking

### `record_cost(cost: CostRecord) → None`

Add a cost entry to the manifest.  Saves to disk.

---

### `get_total_cost() → float`

Return the sum of all recorded costs in USD.

---

### `get_costs_by_stage() → Dict[str, float]`

Return a breakdown of costs by stage name.

**Returns:** `{"RESEARCHING": 0.05, "WRITING": 0.12, ...}`

---

## Provider Tracking

### `record_provider(provider: ProviderRecord) → None`

Record which provider was selected for a capability.  Saves to disk.

---

### `get_providers(*, capability=None) → List[ProviderRecord]`

Return provider records, optionally filtered by capability.

---

## Error / Warning Tracking

### `record_error(stage, message, *, traceback="", metadata=None) → None`

Record an error in the manifest.  Saves to disk.

---

### `record_warning(stage, message, *, metadata=None) → None`

Record a warning in the manifest.  Saves to disk.

---

## Quality Checks

### `record_quality_check(qc: QualityCheck) → None`

Add a QA check result to the manifest.  Saves to disk.

---

## Render Tracking

### `record_render(render: RenderRecord) → None`

Add a render record to the manifest.  Saves to disk.

---

## Status Reporting

### `generate_summary() → Dict[str, Any]`

Return a concise summary dict suitable for CLI display or logging.

**Returns:**

```python
{
    "project_id": "a1b2c3d4e5f6",
    "title": "Shango Rises",
    "slug": "shango-rises",
    "status": "WRITING",
    "current_stage": "WRITING",
    "progress_pct": 27.3,
    "completed_stages": ["RESEARCHING", "WRITING"],
    "total_cost_usd": 0.17,
    "asset_count": 5,
    "error_count": 0,
    "warning_count": 1,
    "stage_timing_s": {"RESEARCHING": 12.5, "WRITING": 45.2},
    "retry_counts": {},
    "created_at": "2025-01-15T10:30:00+00:00",
    "updated_at": "2025-01-15T10:35:00+00:00",
}
```

---

## Directory Helpers

### `get_path(*parts: str) → Path`

Return an absolute path inside the project directory.

```python
engine.get_path("assets", "images", "001.png")
# → /path/to/projects/shango-rises/assets/images/001.png
```

---

### `ensure_subdir(*parts: str) → Path`

Ensure a sub-directory exists and return its path.  Creates parents as needed.

---

### `write_text(relative_path: str, content: str) → Path`

Write text content to a file inside the project directory.  Creates parent directories as needed.

---

### `read_text(relative_path: str) → str`

Read text content from a file inside the project directory.