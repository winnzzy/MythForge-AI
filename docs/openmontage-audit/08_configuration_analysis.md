# OpenMontage — Configuration Analysis

## Overview

OpenMontage uses a layered configuration system with multiple sources of truth. Configuration is spread across YAML files, environment variables, JSON playbooks, and pipeline definitions. There is no single configuration manager — the AI agent reads configuration from multiple locations as needed.

---

## Configuration Hierarchy

```
Priority (highest to lowest):
  1. Environment variables (.env)
  2. Global config (config.yaml)
  3. Pipeline config (pipeline_defs/*.yaml)
  4. Playbook config (playbooks/*.json)
  5. Skill-embedded defaults (skills/*.md)
```

---

## Environment Variables (`.env`)

**Template**: `.env.example`
**Purpose**: API keys, credentials, and runtime secrets
**Management**: Manual copy from `.env.example`, fill in values

### Required Variables

| Variable | Purpose | Used By |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API access | `openai_image.py`, `openai_tts.py` |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS | `elevenlabs_tts.py` |
| `PEXELS_API_KEY` | Pexels stock media | `pexels_image.py`, `pexels_video.py` |
| `HEYGEN_API_KEY` | HeyGen avatar/spokesperson | `heygen_avatar.py`, `heygen_video.py` |
| `FREESOUND_API_KEY` | Freesound music | `freesound_music.py` |

### Optional Variables

| Variable | Purpose | Used By |
|----------|---------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud service account | `google_credentials.py`, `google_imagen.py`, `google_tts.py`, `veo_video.py` |
| `FLUX_API_KEY` | FLUX image generation | `flux_image.py` |
| `GROK_API_KEY` | Grok image/video | `grok_image.py`, `grok_video.py` |
| `REPLICATE_API_TOKEN` | Replicate models | Various local diffusion tools |
| `RUNWAY_API_KEY` | Runway video generation | `runway_video.py` |
| `KLING_API_KEY` | Kling video generation | `kling_video.py` |
| `SUNO_API_KEY` | Suno music generation | `suno_music.py` |
| `RECRRAFT_API_KEY` | Recraft image generation | `recraft_image.py` |
| `SEGMIND_API_KEY` | Segmind image generation | `segmind_real.py` |
| `MINIMAX_API_KEY` | MiniMax video generation | `minimax_video.py` |
| `MODAL_TOKEN_ID` | Modal cloud GPU | `ltx_video_modal.py` |
| `MODAL_TOKEN_SECRET` | Modal cloud GPU | `ltx_video_modal.py` |
| `HEDRA_API_KEY` | Hedra avatar | `hedra_avatar.py` |
| `SEEDANCE_API_KEY` | Seedance video | `seedance_video.py` |
| `DOUBAO_API_KEY` | Doubao TTS (Chinese) | `doubao_tts.py` |

### Loading Mechanism

```python
# tools/base_tool.py
def _load_dotenv():
    """Load .env file from project root"""
    from dotenv import load_dotenv
    load_dotenv()  # Searches from CWD upward
```

**Risk**: No validation of required keys at startup. Missing keys cause runtime failures when tools are invoked.

---

## Global Configuration (`config.yaml`)

**Purpose**: Core framework settings
**Format**: YAML

### Structure

```yaml
# Agent configuration
agent:
  model: "claude-sonnet-4-20250514"  # LLM model for the AI agent
  # Alternatives: "gpt-4o", "gemini-pro", "ollama/llama3"

# Output configuration
output:
  default_directory: "./output"
  default_resolution: "1920x1080"
  default_fps: 30
  default_codec: "h264"

# Budget configuration
budget:
  default_limit_usd: 2.00
  mode: "warn"  # observe | warn | cap

# Model/provider defaults
models:
  tts_default: "elevenlabs"
  image_default: "flux"
  video_default: "pexels"
  music_default: "freesound"
  avatar_default: "heygen"

# Pipeline defaults
pipeline:
  checkpoint_policy: "guided"  # guided | manual_all | auto_noncreative
  max_revisions_per_stage: 3
  approval_required: true
```

### Key Settings

| Setting | Purpose | Default | Options |
|---------|---------|---------|---------|
| `agent.model` | LLM for AI reasoning | `claude-sonnet-4-20250514` | Any supported model |
| `output.default_resolution` | Video resolution | `1920x1080` | Any valid resolution |
| `output.default_fps` | Frames per second | `30` | 24, 30, 60 |
| `budget.default_limit_usd` | Default budget cap | `$2.00` | Any amount |
| `budget.mode` | Budget enforcement | `warn` | observe, warn, cap |
| `pipeline.checkpoint_policy` | Resume behavior | `guided` | guided, manual_all, auto_noncreative |
| `pipeline.max_revisions_per_stage` | Revision limit | `3` | Any integer |

---

## Pipeline Configuration (`pipeline_defs/*.yaml`)

**Purpose**: Define stage structure, required skills, tools, and schemas per pipeline
**Format**: YAML

### Pipeline YAML Schema

```yaml
name: animated-explainer
description: "Motion-graphics explainer video"
version: "1.0.0"

stages:
  - name: research
    skill: research-director
    required_skills:
      - skills/pipelines/explainer/research-director.md
    required_tools: []
    schema: schemas/research_brief.json
    review_focus: "coverage, source quality, angle uniqueness"
    success_criteria:
      - "3+ unique angles identified"
      - "5+ data points gathered"

  - name: proposal
    skill: proposal-director
    required_skills:
      - skills/pipelines/explainer/proposal-director.md
    required_tools: []
    schema: schemas/proposal_packet.json
    review_focus: "concept quality, cost accuracy"
    success_criteria:
      - "3+ concept options presented"
      - "production plan with tool selections"
    gate: "approval"  # HUMAN APPROVAL REQUIRED

  - name: script
    skill: script-director
    # ... similar structure

  - name: scene_plan
    skill: scene-director
    # ...

  - name: assets
    skill: asset-director
    required_tools:
      - tts_selector
      - image_selector
      - video_selector
      - music_gen
    # ...

  - name: edit
    skill: edit-director
    # ...

  - name: compose
    skill: compose-director
    required_tools:
      - video_compose
      - hyperframes_compose
      - audio_mixer
    # ...

  - name: publish
    skill: publish-director
    # ...

render_runtime: remotion  # default runtime
renderer_family:
  - explainer-data
  - explainer-teacher
  - product-reveal
  - screen-demo
  - animation-first
checkpoint_policy: guided
```

---

## Playbook Configuration (`playbooks/*.json`)

**Purpose**: Visual style constraints for consistent video aesthetics
**Format**: JSON

### Playbook Schema

```json
{
  "name": "clean-professional",
  "description": "Corporate/professional style",
  "colors": {
    "primary": "#1a1a2e",
    "secondary": "#16213e",
    "accent": "#0f3460",
    "text": "#e0e0e0",
    "background": "#0a0a0a"
  },
  "typography": {
    "heading_font": "Inter Bold",
    "body_font": "Inter Regular",
    "heading_size": 48,
    "body_size": 24,
    "caption_size": 18
  },
  "motion": {
    "default_transition": "fade",
    "transition_duration_ms": 500,
    "ease_curve": "ease-in-out",
    "parallax_enabled": true,
    "zoom_intensity": 0.1
  },
  "subtitles": {
    "font": "Inter Bold",
    "size": 24,
    "color": "#FFFFFF",
    "outline": "#000000",
    "outline_width": 2,
    "position": "bottom_center",
    "word_highlight": true,
    "highlight_color": "#FFD700"
  },
  "quality_budget": {
    "max_images_per_10s": 2,
    "max_video_clips_per_10s": 1,
    "prefer_stock_for_broll": true,
    "prefer_generative_for_hero": true
  }
}
```

### Available Playbooks

| Playbook | Style | Best For |
|----------|-------|----------|
| `clean-professional.json` | Corporate, minimal | Business explainer, SaaS demo |
| `cinematic-dark.json` | Dark, dramatic | Documentary, thriller |
| `vibrant-social.json` | Bright, energetic | Social media, TikTok |
| `educational-light.json` | Light, friendly | Tutorial, educational |
| `tech-futuristic.json` | Neon, tech | AI, blockchain, tech |

---

## Feature Flags

OpenMontage does **not have a formal feature flag system**. However, several configuration values function as implicit feature flags:

| Config | Effect When Changed |
|--------|-------------------|
| `pipeline.checkpoint_policy` | Changes resume behavior |
| `budget.mode` | Changes cost enforcement |
| `render_runtime` (in pipeline YAML) | Switches rendering backend |
| `models.tts_default` | Switches TTS provider |
| `models.image_default` | Switches image provider |

---

## Provider Configuration

Provider configuration is handled through environment variables and tool-specific settings. There is no centralized provider configuration file.

### Provider Registration Flow

```
.env file
    │
    ▼
base_tool._load_dotenv()
    │
    ▼
Tool reads API key from os.environ
    │
    ▼
Tool validates key exists (or raises error)
    │
    ▼
Tool registers with tool_registry via get_info()
```

### Provider Selection Flow

```
config.yaml → models.tts_default
    │
    ▼
Agent presents Provider Menu to user
    │
    ▼
User selects providers (or accepts defaults)
    │
    ▼
Selected providers stored in proposal_packet.production_plan
    │
    ▼
Asset director uses production_plan to select tools
```

---

## Pipeline State Configuration

Pipeline checkpoint state is stored in `pipeline/` directory:

```
pipeline/
├── <project_name>/
│   ├── state.json          # Current pipeline state
│   ├── checkpoint.json     # Last checkpoint
│   └── stage_outputs/      # Per-stage artifact snapshots
│       ├── research.json
│       ├── proposal.json
│       ├── script.json
│       └── ...
```

---

## Makefile Targets

The `Makefile` provides CLI commands for common operations:

| Target | Command | Purpose |
|--------|---------|---------|
| `make setup` | Install dependencies | `pip install -r requirements.txt && cd remotion-composer && npm install` |
| `make preflight` | Discover available tools | `python -c "from tools.tool_registry import discover; discover()"` |
| `make test` | Run test suite | `pytest tests/` |
| `make render-demo` | Render demo video | `python render_demo.py` |
| `make install-hooks` | Install git hooks | Pre-commit hooks for linting |

---

## Key Observations

1. **No centralized config manager** — configuration is spread across multiple files
2. **Secret management is basic** — `.env` file only, no rotation mechanism
3. **No config validation** — missing values cause runtime errors, not startup errors
4. **Playbooks are powerful** — they drive visual consistency but are optional
5. **Pipeline YAML is the real config** — it defines what skills and tools are needed
6. **No feature flag system** — implicit flags exist but aren't centrally managed
7. **No environment profiles** — same config for dev/staging/production