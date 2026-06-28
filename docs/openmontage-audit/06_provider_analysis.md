# OpenMontage — Provider Analysis

## Overview

OpenMontage implements a **tool-based provider pattern** rather than a formal provider interface. Each external service (LLM, TTS, image API, video API) is wrapped as a Python tool that extends `BaseTool`. Tools are auto-discovered by `tool_registry.py` and selected at runtime by the AI agent based on user preferences and pipeline requirements.

There is **no formal provider registry** — the agent selects tools by name, and the registry resolves them.

---

## Provider Registration & Discovery

```
tools/
  └── <category>/
       └── <tool_name>.py    # Must extend BaseTool
            └── get_info()   # Returns ToolResult with name, description, capabilities

tool_registry.py
  └── discover()
       └── pkgutil.walk_packages(tools.__path__, prefix="tools.")
            └── Scans all Python modules for BaseTool subclasses
                 └── Registers by class name
```

**How providers are registered**: Automatic — any Python file in `tools/` that defines a class extending `BaseTool` is discovered on startup.

**How providers are selected**: The AI agent reads tool descriptions from `tool_registry.discover()` and selects based on:
1. User preferences (from Provider Menu)
2. Pipeline requirements (from YAML definition)
3. Budget constraints (from cost_tracker)
4. Quality requirements (from scoring.py)

**How providers can be replaced**: Drop a new tool file in the same category directory, or create a new category directory. The registry will discover it automatically.

---

## LLM Providers

LLMs are **not wrapped as tools** — they are configured in `config.yaml` under `agent.model` and used by the AI agent runtime itself. The OpenMontage framework does not manage LLM calls directly; it relies on the host AI agent (Claude, GPT, Cursor) to be the reasoning engine.

| Provider | Configuration | Usage |
|----------|--------------|-------|
| Anthropic (Claude) | `config.yaml → agent.model` | Primary reasoning agent |
| OpenAI (GPT) | `config.yaml → agent.model` | Alternative reasoning agent |
| Google Gemini | `config.yaml → agent.model` | Alternative reasoning agent |
| Local LLM (Ollama) | `config.yaml → agent.model` | Privacy-focused alternative |

**Note**: LLM providers are external to the framework. The framework assumes an AI agent is already running and consuming skill documents.

---

## TTS (Text-to-Speech) Providers

| Provider | Tool File | API Key | Cost | Quality | Languages |
|----------|-----------|---------|------|---------|-----------|
| **ElevenLabs** | `tools/audio/elevenlabs_tts.py` | `ELEVENLABS_API_KEY` | $0.10-0.30/min | Highest | 29+ |
| **Google Cloud TTS** | `tools/audio/google_tts.py` | Google credentials | $0.04/min | High | 40+ |
| **OpenAI TTS** | `tools/audio/openai_tts.py` | `OPENAI_API_KEY` | $0.06/min | High | 50+ |
| **Doubao TTS** | `tools/audio/doubao_tts.py` | Doubao credentials | Low | Medium | Chinese-focused |
| **Piper TTS** | `tools/audio/piper_tts.py` | None (local) | $0.00 | Medium | English-focused |

**Selection Logic**:
```
tts_selector tool (if exists)
  → Routes based on: language, quality requirements, budget
  → Fallback: configured default in config.yaml
```

---

## Image Generation Providers

| Provider | Tool File | API Key | Cost | Quality | Style |
|----------|-----------|---------|------|---------|-------|
| **FLUX** | `tools/graphics/flux_image.py` | FLUX API | $0.03-0.06/img | Highest | Photorealistic, artistic |
| **Google Imagen** | `tools/graphics/google_imagen.py` | Google credentials | $0.02-0.04/img | High | Versatile |
| **Grok Image** | `tools/graphics/grok_image.py` | X/Grok API | $0.02/img | High | Realistic |
| **OpenAI DALL-E** | `tools/graphics/openai_image.py` | `OPENAI_API_KEY` | $0.04-0.08/img | High | Versatile |
| **Recraft** | `tools/graphics/recraft_image.py` | Recraft API | $0.02/img | High | Design-focused |
| **Pexels** | `tools/graphics/pexels_image.py` | `PEXELS_API_KEY` | $0.00 | Varies | Stock photos |
| **Pixabay** | `tools/graphics/pixabay_image.py` | Pixabay API | $0.00 | Varies | Stock photos |
| **Stable Diffusion (local)** | `tools/graphics/stable_diffusion_local.py` | None (local) | $0.00 | Medium | Artistic |
| **SD 3.5 (local)** | `tools/graphics/sd35_local.py` | None (local) | $0.00 | High | Versatile |
| **Segmind Real** | `tools/graphics/segmind_real.py` | Segmind API | $0.01/img | High | Photorealistic |
| **CogView4 (local)** | `tools/graphics/cogview4_local.py` | None (local) | $0.00 | High | Versatile |

**Selection Logic**:
```
image_selector tool
  → Routes based on: scene type, style requirements, budget
  → Prefers stock (Pexels/Pixabay) for B-roll
  → Prefers generative (FLUX/Imagen/DALL-E) for custom scenes
```

---

## Video Generation Providers

| Provider | Tool File | API Key | Cost | Quality | Type |
|----------|-----------|---------|------|---------|------|
| **Google Veo** | `tools/video/veo_video.py` | Google credentials | $0.10-0.50/clip | Highest | Text-to-video |
| **Kling** | `tools/video/kling_video.py` | Kling API | $0.05-0.20/clip | High | Text/image-to-video |
| **Runway** | `tools/video/runway_video.py` | Runway API | $0.10-0.30/clip | High | Image-to-video, character |
| **Seedance** | `tools/video/seedance_video.py` | Seedance API | $0.05/clip | High | Dance/motion |
| **HeyGen** | `tools/video/heygen_video.py` | `HEYGEN_API_KEY` | $0.10-0.50/clip | High | Avatar/spokesperson |
| **Grok Video** | `tools/video/grok_video.py` | X/Grok API | $0.05/clip | Medium | Text-to-video |
| **MiniMax** | `tools/video/minimax_video.py` | MiniMax API | $0.05/clip | Medium | Text-to-video |
| **Hunyuan** | `tools/video/hunyuan_video.py` | Hunyuan API | $0.05/clip | High | Text-to-video |
| **CogVideo** | `tools/video/cogvideo_video.py` | CogVideo API | $0.05/clip | Medium | Text-to-video |
| **Wan** | `tools/video/wan_video.py` | Wan API | $0.05/clip | Medium | Text-to-video |
| **LTX (local)** | `tools/video/ltx_video_local.py` | None (local) | $0.00 | Medium | Text-to-video |
| **LTX (Modal)** | `tools/video/ltx_video_modal.py` | Modal API | $0.05/clip | Medium | Cloud text-to-video |
| **Pexels Video** | `tools/video/pexels_video.py` | `PEXELS_API_KEY` | $0.00 | Varies | Stock footage |
| **Pixabay Video** | `tools/video/pixabay_video.py` | Pixabay API | $0.00 | Varies | Stock footage |

**Selection Logic**:
```
video_selector tool
  → Routes based on: scene requirements, motion type, budget
  → Prefers stock (Pexels/Pixabay) for B-roll
  → Prefers generative (Veo/Kling/Runway) for custom scenes
```

---

## Music Providers

| Provider | Tool File | API Key | Cost | Quality |
|----------|-----------|---------|------|---------|
| **Suno** | `tools/audio/suno_music.py` | Suno API | $0.05/track | High |
| **Freesound** | `tools/audio/freesound_music.py` | Freesound API | $0.00 | Varies |
| **Pixabay Music** | `tools/audio/pixabay_music.py` | Pixabay API | $0.00 | Varies |

---

## Avatar Providers

| Provider | Tool File | API Key | Cost | Quality |
|----------|-----------|---------|------|---------|
| **HeyGen Avatar** | `tools/avatar/heygen_avatar.py` | `HEYGEN_API_KEY` | $0.10-0.50/min | High |
| **Hedra Avatar** | `tools/avatar/hedra_avatar.py` | Hedra API | $0.05-0.20/min | Medium |
| **Wav2Lip** | `tools/avatar/wav2lip_avatar.py` | None (local) | $0.00 | Medium |

---

## Rendering Providers (Runtimes)

| Runtime | Technology | File | Use Case |
|---------|------------|------|----------|
| **Remotion** | TypeScript/React | `remotion-composer/` | Motion graphics, explainer videos, data visualization |
| **HyperFrames** | HTML/GSAP | `tools/video/hyperframes_compose.py` | Kinetic typography, product promos, website-to-video |
| **FFmpeg** | C CLI tool | Used via `video_stitch.py`, `audio_mixer.py` | Simple concat, subtitle burn, audio mux |

---

## Analysis Providers

| Provider | Tool File | Purpose |
|----------|-----------|---------|
| **WhisperX** | `tools/analysis/transcriber.py` | Speech-to-text with word-level alignment |
| **Scene Detect** | `tools/analysis/scene_detect.py` | Detect scene changes in video |
| **Video Understand** | `tools/analysis/video_understand.py` | AI-powered video content analysis |

---

## Enhancement Providers

| Provider | Tool File | Purpose |
|----------|-----------|---------|
| **Upscale** | `tools/enhancement/upscale.py` | Image/video upscaling |
| **Denoise** | `tools/enhancement/denoise.py` | Noise reduction |
| **Face Restore** | `tools/enhancement/face_restore.py` | Face enhancement |
| **BG Remove** | `tools/enhancement/bg_remove.py` | Background removal |

---

## Provider Cost Matrix

| Category | Cheapest | Most Expensive | Free Options |
|----------|----------|----------------|--------------|
| TTS | Piper ($0) | ElevenLabs ($0.30/min) | Piper (local) |
| Image | Pexels ($0) | DALL-E ($0.08/img) | Pexels, Pixabay, local SD |
| Video | Pexels ($0) | Veo ($0.50/clip) | Pexels, Pixabay, local LTX |
| Music | Freesound ($0) | Suno ($0.05/track) | Freesound, Pixabay |
| Avatar | Wav2Lip ($0) | HeyGen ($0.50/min) | Wav2Lip (local) |

---

## Key Observations

1. **No formal provider interface** — each tool implements `BaseTool` independently
2. **Selector tools** (`image_selector`, `video_selector`, `tts_selector`) provide routing logic
3. **Free alternatives exist** for every category (stock media, local models)
4. **Provider count is high** — 40+ external service integrations
5. **API key management** is via `.env` file — no secret rotation mechanism
6. **No provider health checks** — agent discovers availability at preflight time
7. **Cost tracking** is per-tool via `ToolResult.cost_usd` field