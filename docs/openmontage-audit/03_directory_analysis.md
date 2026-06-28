# OpenMontage — Directory Analysis

## Root Directory (`/`)

| File | Purpose |
|------|---------|
| `AGENT_GUIDE.md` | Layer 1 instructions for AI agents — core operating rules |
| `PROJECT_CONTEXT.md` | Layer 2 context — philosophy, design principles |
| `README.md` | Human-facing documentation and setup guide |
| `ROADMAP.md` | Feature roadmap and future plans |
| `SECURITY.md` | Security policy and responsible disclosure |
| `Makefile` | Build/test/setup orchestration |
| `config.yaml` | Global configuration (LLM, budget, output, models) |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python core dependencies |
| `requirements-dev.txt` | Python dev/test dependencies |
| `requirements-gpu.txt` | GPU-accelerated dependencies |
| `render_demo.py` | CLI demo video renderer |

**Risk Level**: LOW — These are configuration and documentation files. Modifications should be deliberate and documented.

---

## `tools/` — Tool Implementations

**Purpose**: Contains all tool implementations — the executable capabilities the AI agent invokes.

**Dependencies**: `base_tool.py` (abstract base), external APIs, FFmpeg, Remotion, various Python packages.

**Responsibilities**:
- Implement the `BaseTool` contract (`execute()`, `get_info()`, `estimate_cost()`, `dry_run()`)
- Handle provider-specific API calls
- Return standardized `ToolResult` objects

**Extension Points**: Add new tool modules following the `BaseTool` pattern. Auto-discovered by `tool_registry.py`.

**Risk Level**: HIGH — Core business logic. Changes can break pipeline execution.

### Subdirectories

| Directory | Purpose | Tools | Risk |
|-----------|---------|-------|------|
| `tools/analysis/` | Video/audio analysis (transcription, scene detection) | `transcriber`, `scene_detect`, `video_understand` | MEDIUM |
| `tools/audio/` | TTS, music generation, audio mixing | `piper_tts`, `elevenlabs_tts`, `google_tts`, `openai_tts`, `doubao_tts`, `music_gen`, `audio_mixer`, `freesound_music`, `pixabay_music`, `suno_music` | HIGH |
| `tools/avatar/` | Lip sync, talking head generation | `wav2lip_avatar`, `heygen_avatar`, `hedra_avatar` | MEDIUM |
| `tools/capture/` | Screen recording | `screen_record` | LOW |
| `tools/character/` | Character animation | `animate_image`, `runway_video` (character-specific) | MEDIUM |
| `tools/enhancement/` | Image/video enhancement | `upscale`, `denoise`, `face_restore`, `bg_remove` | LOW |
| `tools/graphics/` | Image generation (11+ providers) | `flux_image`, `google_imagen`, `grok_image`, `openai_image`, `recraft_image`, `pexels_image`, `pixabay_image`, `stable_diffusion_local`, `sd35_local`, `segmind_real`, `cogview4_local`, `image_selector` | HIGH |
| `tools/publishers/` | Publishing (placeholder) | Empty/stub | LOW |
| `tools/subtitle/` | Subtitle generation | `subtitle_gen` | MEDIUM |
| `tools/video/` | Video generation (16+ providers), composition, stitching | `video_compose`, `hyperframes_compose`, `video_stitch`, `video_selector`, `pexels_video`, `pixabay_video`, `kling_video`, `runway_video`, `veo_video`, `seedance_video`, `heygen_video`, `grok_video`, `minimax_video`, `hunyuan_video`, `cogvideo_video`, `wan_video`, `ltx_video_local`, `ltx_video_modal` | HIGH |

### Key Files in `tools/`

| File | Purpose | Risk |
|------|---------|------|
| `base_tool.py` | Abstract base class defining the tool contract | **CRITICAL** — All tools depend on this |
| `tool_registry.py` | Auto-discovery registry using `pkgutil.walk_packages` | **CRITICAL** — Tool resolution depends on this |
| `cost_tracker.py` | Budget tracking and approval gates | HIGH |
| `google_credentials.py` | Google Cloud authentication helper | MEDIUM |

---

## `skills/` — LLM Prompt Documents

**Purpose**: Markdown files that define the AI agent's behavior at each pipeline stage. This is the "brain" of the system.

**Dependencies**: None (pure Markdown). Referenced by pipeline YAML definitions.

**Responsibilities**:
- Define how the agent approaches each task
- Provide creative direction, technical guidelines, quality checklists
- Serve as reusable prompt templates

**Extension Points**: Add new skill files and reference them in pipeline YAML. No code changes needed.

**Risk Level**: MEDIUM — Changes alter agent behavior but don't break the framework.

### Subdirectories

| Directory | Purpose | Files | Risk |
|-----------|---------|-------|------|
| `skills/core/` | Technical skills (FFmpeg, Remotion, WhisperX, subtitle-sync, color-grading, hyperframes) | 6 files | MEDIUM |
| `skills/creative/` | Creative direction (storytelling, typography, animation, lip-sync, video editing, sound design, etc.) | 30+ files | LOW |
| `skills/creative/prompting/` | Image/video generation prompting guides | Per-provider guides | LOW |
| `skills/meta/` | Meta-skills (reviewer, checkpoint, onboarding, skill-creator, capability-extension) | 8 files | MEDIUM |
| `skills/pipelines/` | Pipeline-specific director skills | 12 pipeline subdirectories | HIGH |

### Pipeline Skill Directories

Each pipeline has its own set of stage-director skills:

| Directory | Pipeline | Skills |
|-----------|----------|--------|
| `skills/pipelines/explainer/` | Animated Explainer | executive-producer, research-director, proposal-director, script-director, scene-director, asset-director, edit-director, compose-director |
| `skills/pipelines/talking-head/` | Talking Head | Similar stage directors |
| `skills/pipelines/documentary-montage/` | Documentary | Similar stage directors |
| `skills/pipelines/podcast-repurpose/` | Podcast Repurpose | Similar stage directors |
| `skills/pipelines/screen-demo/` | Screen Demo | Similar stage directors |
| `skills/pipelines/cinematic/` | Cinematic | Similar stage directors |
| `skills/pipelines/localization-dub/` | Localization | Similar stage directors |
| `skills/pipelines/avatar-spokesperson/` | Avatar | Similar stage directors |
| `skills/pipelines/character-animation/` | Character Animation | Similar stage directors |
| `skills/pipelines/clip-factory/` | Clip Factory | Similar stage directors |
| `skills/pipelines/hybrid/` | Hybrid | Similar stage directors |
| `skills/pipelines/animation/` | Animation | Similar stage directors |

---

## `pipeline_defs/` — Pipeline Definitions

**Purpose**: YAML files defining the stages, skills, tools, checkpoints, and schemas for each production pipeline.

**Dependencies**: References skills, schemas, playbooks, and tools by name.

**Responsibilities**:
- Declaratively define pipeline structure
- Specify stage order, review focus, success criteria
- Reference required skills and tools

**Extension Points**: Add new YAML files to define custom pipelines.

**Risk Level**: MEDIUM — Changes alter pipeline behavior but are declarative and auditable.

**Files**: 11 pipeline definitions (animated-explainer, cinematic-broll, talking-head, podcast-repurpose, screen-demo, documentary-montage, localization-dub, avatar-spokesperson, character-animation, clip-factory, hybrid-live-animated)

---

## `playbooks/` — Visual Style Playbooks

**Purpose**: JSON files defining visual style constraints (color palettes, typography, motion patterns, quality budgets).

**Dependencies**: Referenced by pipeline YAML and agent skills.

**Responsibilities**:
- Enforce visual consistency across scenes
- Define color schemes, font stacks, motion curves
- Set quality/cost tradeoff preferences

**Extension Points**: Add new JSON playbook files.

**Risk Level**: LOW — Pure configuration, no code dependencies.

---

## `schemas/` — JSON Schema Definitions

**Purpose**: JSON Schema files that validate artifacts produced at each pipeline stage.

**Dependencies**: Used by pipeline validation logic.

**Responsibilities**:
- Validate research_brief, proposal_packet, script, scene_plan, asset_manifest, edit_decisions, etc.
- Enforce contract between pipeline stages

**Extension Points**: Add new schema files for new artifact types.

**Risk Level**: LOW — Schema changes are backwards-compatible if additive.

---

## `remotion-composer/` — Remotion Rendering Backend

**Purpose**: TypeScript/React project that renders video compositions using Remotion.

**Dependencies**: Remotion v4.x, React, Node.js, npm.

**Responsibilities**:
- Define scene components (text_card, stat_card, chart, callout, etc.)
- Render video frames from JSON props
- Handle transitions, animations, captions

**Extension Points**: Add new scene components, register in Root.tsx.

**Risk Level**: HIGH — Core rendering pipeline. TypeScript/React changes require careful testing.

**Key Files**:
| File | Purpose |
|------|---------|
| `package.json` | Dependencies (Remotion, React) |
| `src/index.tsx` | Remotion entry point |
| `src/Root.tsx` | Root composition registry |
| `src/Explainer.tsx` | Main explainer composition |
| `src/CinematicRenderer.tsx` | Cinematic composition |
| `src/TalkingHead.tsx` | Talking head composition |
| `public/demo-props/` | Demo JSON props |

---

## `lib/` — Shared Python Libraries

**Purpose**: Shared utility code used across tools.

**Files**:
| File | Purpose | Risk |
|------|---------|------|
| `scoring.py` | Tool quality scoring engine | MEDIUM |
| `media_profiles.py` | Media profile definitions (resolution, fps, codec) | MEDIUM |

**Risk Level**: MEDIUM — Changes can affect multiple tools.

---

## `library/` — Reusable Asset Library

**Purpose**: Storage for reusable assets (templates, stock elements). Currently empty/template.

**Risk Level**: LOW

---

## `output/` — Render Output Directory

**Purpose**: Default directory for rendered video outputs.

**Risk Level**: LOW — Runtime output, not source code.

---

## `pipeline/` — Pipeline State Storage

**Purpose**: Stores checkpoint state for pipeline resume capability.

**Risk Level**: LOW — Runtime state, not source code.

---

## `projects/` — Project Working Directories

**Purpose**: Per-project working directories containing artifacts, assets, and renders.

**Risk Level**: LOW — Runtime data, not source code.

---

## `tests/` — Test Suite

**Purpose**: Contract tests and unit tests for tools.

**Subdirectory**: `tests/contracts/` — Tests that verify tools implement the `BaseTool` contract correctly.

**Risk Level**: LOW — Tests should be extended, not modified.