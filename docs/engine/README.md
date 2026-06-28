# MythForge Engine — Manifest Engine

> **Single source of truth for every MythForge video project.**

The Manifest Engine (`mythforge.engine`) is the foundational layer that tracks the
entire lifecycle of a video project.  Every pipeline stage — from research through
rendering — interacts with the project manifest exclusively through this module.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Pipeline Stages                    │
│  (Research → Writing → Scenes → Images → Audio → …) │
└──────────────────────┬──────────────────────────────┘
                       │  engine.begin_stage / complete_stage / …
                       ▼
┌─────────────────────────────────────────────────────┐
│               ManifestEngine  (API)                  │
│                                                      │
│  • create_project / load_project / save              │
│  • begin_stage / complete_stage / fail_stage / skip  │
│  • record_asset / record_cost / record_provider      │
│  • get_next_stage / resume                           │
│  • generate_summary                                  │
└──────────────────────┬──────────────────────────────┘
                       │  JSON read/write
                       ▼
┌─────────────────────────────────────────────────────┐
│              manifest.json  (on disk)                │
│                                                      │
│  Schema: Manifest → StageRecord, AssetRecord, …      │
│  Defined in: mythforge/engine/schema.py              │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

```python
from mythforge.engine import ManifestEngine

engine = ManifestEngine(base_dir="projects")

# 1. Create a project
manifest = engine.create_project(title="Shango Rises", slug="shango-rises")

# 2. Run a pipeline stage
engine.begin_stage("RESEARCHING")
# ... do work ...
engine.complete_stage("RESEARCHING", metadata={"sources": 12})

# 3. Record assets and costs
from mythforge.engine import AssetRecord, CostRecord
engine.record_asset(AssetRecord(stage="IMAGE_GENERATION", kind="image", path="assets/images/001.png"))
engine.record_cost(CostRecord(stage="RESEARCHING", provider="gemini", amount_usd=0.05))

# 4. Resume later
engine2 = ManifestEngine(base_dir="projects")
engine2.load_project("shango-rises")
next_stage = engine2.resume()  # → "WRITING"
```

---

## Module Structure

```
mythforge/engine/
├── __init__.py      # Public API re-exports
├── schema.py        # Data models (Manifest, StageRecord, AssetRecord, …)
└── engine.py        # ManifestEngine class (the only API pipeline stages use)
```

---

## Key Concepts

### Project Lifecycle

A project moves through a deterministic pipeline:

```
CREATED → RESEARCHING → WRITING → SCENE_BREAKDOWN → PROMPT_GENERATION
→ IMAGE_GENERATION → NARRATION → SFX → MUSIC → RENDERING → QA → READY
```

Terminal states: `READY`, `PUBLISHED`, `FAILED` (retryable).

### Manifest

The `Manifest` dataclass holds **everything** about a project:

- Identity (id, title, slug, version)
- Status (current stage, completed stages, retry counts)
- Assets (images, audio, thumbnails, renders)
- Costs (per-operation, per-provider)
- Providers (which LLM / TTS / image service was used)
- Errors and warnings
- Quality checks
- Render history
- Settings and metadata

### Stage Tracking

Each stage goes through: `pending → running → completed | failed | skipped`

The engine records timing, retry counts, and errors for every execution.

### Resume Capability

If a project fails or the process exits, `resume()` picks up exactly where
it left off by examining `completed_stages` against `PIPELINE_ORDER`.

---

## Files

| File | Description |
|------|-------------|
| [API Reference](api_reference.md) | Complete method-by-method documentation |
| [Schema Reference](schema_reference.md) | All dataclasses and their fields |
| [Pipeline Stages](pipeline_stages.md) | How stages interact with the engine |
| [Design Decisions](design_decisions.md) | Why the engine was built this way |