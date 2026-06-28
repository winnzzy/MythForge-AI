# Pipeline Stages — How Stages Interact with the Engine

> A guide for engineers implementing or extending pipeline stages.

---

## The Stage Contract

Every pipeline stage follows the same interaction pattern with the `ManifestEngine`:

```
1. engine.begin_stage("STAGE_NAME")
2. ... do work ...
3. engine.record_asset(...)        # optional, one or more
4. engine.record_cost(...)         # optional, one or more
5. engine.record_provider(...)     # optional
6. engine.complete_stage("STAGE_NAME", metadata={...})
```

On failure:

```
1. engine.begin_stage("STAGE_NAME")
2. ... do work ...
3. ... exception occurs ...
4. engine.fail_stage("STAGE_NAME", error_message, traceback=tb)
```

---

## Canonical Pipeline Order

```
CREATED ──→ RESEARCHING ──→ WRITING ──→ SCENE_BREAKDOWN ──→ PROMPT_GENERATION
                                                                    │
                                                                    ▼
READY ←── QA ←── RENDERING ←── MUSIC ←── SFX ←── NARRATION ←── IMAGE_GENERATION
```

### Stage Descriptions

| Stage | Purpose | Typical Inputs | Typical Outputs |
|-------|---------|---------------|-----------------|
| `RESEARCHING` | Gather topic information, context, references | Topic, settings | Research notes, source list |
| `WRITING` | Generate narration script | Research notes | Script text |
| `SCENE_BREAKDOWN` | Split script into scenes with timing | Script | Scene list with durations |
| `PROMPT_GENERATION` | Create image generation prompts per scene | Scene list | Prompt list |
| `IMAGE_GENERATION` | Generate images via AI providers | Prompts | Image files (PNG/JPG) |
| `NARRATION` | Generate narration audio via TTS | Script, timing | Audio files (MP3/WAV) |
| `SFX` | Generate or select sound effects | Scene list | SFX audio files |
| `MUSIC` | Generate background music | Settings, mood | Music audio files |
| `RENDERING` | Compose final video from all assets | All assets, scene list | Video file (MP4) |
| `QA` | Quality checks (sync, levels, etc.) | Rendered video | QA reports, pass/fail |

---

## Error Handling Pattern

```python
import traceback

engine.begin_stage("IMAGE_GENERATION")
try:
    for scene in scenes:
        image = generate_image(scene.prompt)
        engine.record_asset(AssetRecord(
            stage="IMAGE_GENERATION",
            kind="image",
            path=f"assets/images/{scene.id}.png",
            provider="gemini",
        ))
    engine.complete_stage("IMAGE_GENERATION")
except Exception as e:
    engine.fail_stage(
        "IMAGE_GENERATION",
        str(e),
        traceback=traceback.format_exc(),
    )
    raise  # or handle retry
```

---

## Skipping Stages

If a stage's outputs are already cached:

```python
if cached_assets_exist:
    engine.skip_stage("IMAGE_GENERATION", reason="all 12 images found in cache")
else:
    engine.begin_stage("IMAGE_GENERATION")
    # ... generate ...
    engine.complete_stage("IMAGE_GENERATION")
```

---

## Resume After Interruption

If the process exits mid-pipeline:

```python
engine = ManifestEngine(base_dir="projects")
engine.load_project("shango-rises")

next_stage = engine.resume()
if next_stage:
    engine.begin_stage(next_stage)
    execute_stage(next_stage)
    engine.complete_stage(next_stage)
```

The engine determines the next stage by examining `completed_stages` against `PIPELINE_ORDER`.

---

## Recording Costs

Every provider call should record its cost:

```python
engine.record_cost(CostRecord(
    stage="RESEARCHING",
    provider="gemini",
    operation="web_search",
    amount_usd=0.003,
    tokens_in=500,
    tokens_out=2000,
))
```

Costs are aggregated by `engine.get_total_cost()` and `engine.get_costs_by_stage()`.

---

## Recording Providers

Track which provider/model was used for each capability:

```python
engine.record_provider(ProviderRecord(
    capability="llm",
    provider="gemini",
    model="gemini-2.0-flash",
))
```

---

## Adding a New Stage

To add a custom stage to the pipeline:

1. Add the status to `ProjectStatus` enum in `schema.py`
2. Add it to `PIPELINE_ORDER` in the correct position
3. Implement the stage logic following the stage contract above
4. Add tests

**Example:** Adding a `SUBTITLE_GENERATION` stage between `NARRATION` and `SFX`:

```python
# In schema.py
class ProjectStatus(str, enum.Enum):
    ...
    NARRATION = "NARRATION"
    SUBTITLE_GENERATION = "SUBTITLE_GENERATION"  # NEW
    SFX = "SFX"
    ...

PIPELINE_ORDER = [
    ...
    ProjectStatus.NARRATION,
    ProjectStatus.SUBTITLE_GENERATION,  # NEW
    ProjectStatus.SFX,
    ...
]
```

The engine automatically handles the new stage — no changes to `engine.py` needed.