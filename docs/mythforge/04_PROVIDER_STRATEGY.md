# MythForge AI — Provider Strategy

## Overview

MythForge AI depends on external providers for five core capabilities: research/intelligence, visual generation, audio generation, sound design, and rendering. This document defines the official provider decisions, abstraction requirements, fallback strategy, and configuration approach.

---

## Provider Matrix

| Capability | Primary Provider | Secondary Provider | Fallback Provider | Status |
|-----------|-----------------|-------------------|-------------------|--------|
| Research & Scripting | ChatGPT (OpenAI) | Claude (Anthropic) | Gemini (Google) | Active |
| Image Generation | Gemini Image API | Replicate (FLUX) | DALL-E (OpenAI) | Active |
| Narration (TTS) | ElevenLabs | OpenAI TTS | Edge TTS | Active |
| Music Generation | ElevenLabs (future) | Local Asset Cache | Replicate | Planned |
| Sound Effects | ElevenLabs SFX | Local Asset Cache | Freesound.org | Active |
| Video Rendering | Remotion | FFmpeg | — | Active |
| Web Search | Google Custom Search | Tavily | — | Active |
| Storage | Local Filesystem | — | — | Active |

---

## Detailed Provider Specifications

### 1. Research — ChatGPT (OpenAI)

**Purpose**: Research mythology topics, generate scripts, analyze content, and provide cultural context.

**Model Selection**:
- Research Agent: `gpt-4o` (best reasoning for mythology research)
- Script Writer: `gpt-4o` (creative writing quality)
- QA Agent: `gpt-4o-mini` (analysis tasks, cost-efficient)
- Metadata Generator: `gpt-4o-mini` (structured output, cost-efficient)

**Why ChatGPT**:
- Best general knowledge of world mythology
- Strong creative writing capabilities
- Reliable structured JSON output
- Proven reliability in production

**Configuration**:
```yaml
# config/providers/chatgpt.yaml
provider: openai
model_default: gpt-4o
model_fast: gpt-4o-mini
temperature_research: 0.3
temperature_creative: 0.8
temperature_structured: 0.1
max_tokens_research: 4000
max_tokens_script: 6000
```

**Cost Estimate per Video**:
- Research: ~$0.10-0.20
- Script: ~$0.15-0.30
- QA: ~$0.05-0.10
- Metadata: ~$0.02-0.05
- **Total**: ~$0.32-0.65

**Fallback Strategy**:
1. If OpenAI returns 429 (rate limit): wait 30s, retry with exponential backoff
2. If OpenAI returns 500/503: retry once, then switch to Claude
3. If Claude unavailable: switch to Gemini
4. If all LLMs unavailable: checkpoint and pause production

---

### 2. Image Generation — Gemini Image API (Google)

**Purpose**: Generate all visual assets for scenes, thumbnails, and B-roll.

**Why Gemini Image API**:
- Native image generation (no model loading delay)
- High quality cinematic output
- Good character consistency with proper prompting
- Cost-effective at scale
- Fast generation times

**Configuration**:
```yaml
# config/providers/gemini_images.yaml
provider: gemini
model: gemini-2.0-flash-exp
aspect_ratio: 16:9
style: cinematic
safety_filter: block_only_high
number_of_images: 1  # per prompt
```

**Prompt Engineering Strategy**:
- Every image prompt includes: character identity (from Character Bible), art style (from Playbook), cultural context (from Knowledge Base), scene description (from Scene Director)
- Negative prompts exclude: text artifacts, watermarks, Western fantasy tropes, anachronistic elements, low quality
- Style consistency maintained through Playbook injection

**Cost Estimate per Video**:
- 20-30 scene images: ~$0.50-1.00
- 1 thumbnail: ~$0.05
- Alternates/retries: ~$0.10-0.20
- **Total**: ~$0.65-1.25

**Fallback Strategy**:
1. If Gemini returns 429: wait 60s (Gemini has generous quotas)
2. If Gemini returns content policy violation: rephrase prompt, retry
3. If Gemini unavailable: switch to Replicate (FLUX model)
4. If Replicate unavailable: switch to DALL-E 3
5. If all image providers unavailable: checkpoint and pause

**Character Consistency Approach**:
- Inject character visual identity from Character Bible into every prompt
- Use consistent art style keywords from Playbook
- Reference specific visual attributes (skin tone, clothing, accessories, build)
- Maintain a "style anchor" sentence that appears in every image prompt for a given video

---

### 3. Narration — ElevenLabs

**Purpose**: Generate natural-sounding voice narration for all scenes.

**Why ElevenLabs**:
- Best-in-class voice quality and naturalness
- Voice cloning capability for consistent narration
- Multiple voice profiles for different storytelling styles
- SSML support for pronunciation control
- High-quality African-accented English voices available

**Voice Selection**:
```yaml
# config/providers/elevenlabs.yaml
provider: elevenlabs
default_voice: "mythforge-narrator"  # Custom cloned voice
backup_voice: "Josh"  # ElevenLabs preset voice
model: eleven_multilingual_v2
stability: 0.65
similarity_boost: 0.80
style: 0.40
output_format: mp3_44100_128
```

**Pronunciation Handling**:
- Knowledge base includes pronunciation guides for all mythology names
- SSML phoneme tags used for correct pronunciation
- Example: `<phoneme alphabet="ipa" p="ʃæŋˈɡoʊ">Shango</phoneme>`

**Cost Estimate per Video**:
- 12-15 minutes of narration: ~$0.50-1.00
- Retries/regenerations: ~$0.10-0.20
- **Total**: ~$0.60-1.20

**Fallback Strategy**:
1. If ElevenLabs returns 429: wait 60s, retry
2. If ElevenLabs unavailable: switch to OpenAI TTS (alloy voice)
3. If OpenAI TTS unavailable: switch to Edge TTS (free, good quality)
4. If all TTS unavailable: checkpoint and pause

---

### 4. Music — ElevenLabs (Future) / Local Asset Cache

**Purpose**: Provide cinematic background music appropriate to the mythology's cultural origin.

**Current Strategy (V1)**:
- Use a curated local library of royalty-free cinematic music
- Music categorized by cultural origin (West African, East African, North African, Egyptian, etc.)
- Music categorized by mood (epic, mysterious, sorrowful, triumphant, etc.)
- AI selects appropriate tracks based on scene mood analysis

**Future Strategy (V1.1+)**:
- ElevenLabs music generation API (when available)
- AI-generated music tailored to specific scenes
- Cultural instrument integration (djembe, kora, shekere, balafon, mbira)

**Configuration**:
```yaml
# config/providers/music.yaml
provider: local_cache
cache_path: assets/music/
fallback_provider: replicate
replicate_model: musicgen-large
```

**Cost Estimate per Video**:
- V1 (local cache): $0.00
- V1.1+ (AI generation): ~$0.50-1.00

---

### 5. Sound Effects — ElevenLabs SFX / Local Asset Cache

**Purpose**: Provide ambient sounds, impact effects, transition sounds, and environmental audio.

**Strategy**:
- Primary: ElevenLabs SFX generation API
- Secondary: Local curated SFX library
- SFX generated on-demand based on scene content
- Local library provides: thunder, rain, fire, crowd, nature, combat, magic

**Configuration**:
```yaml
# config/providers/sfx.yaml
provider: elevenlabs_sfx
cache_path: assets/sfx/
fallback_provider: local_cache
local_categories:
  - nature
  - weather
  - combat
  - magic
  - crowd
  - ambient
```

**Cost Estimate per Video**:
- AI-generated SFX (10-15): ~$0.20-0.40
- Local cache SFX: $0.00
- **Total**: ~$0.20-0.40

---

### 6. Rendering — Remotion / FFmpeg

**Purpose**: Composite all assets (images, narration, music, subtitles) into final video.

**Primary: Remotion**
- Timeline-based rendering
- React component-based scene composition
- Ken Burns effect on static images
- Smooth transitions (cross-dissolve, fade, wipe)
- Subtitle overlay
- Text overlay (titles, credits)

**Fallback: FFmpeg**
- Direct command-line video assembly
- No Node.js dependency
- Faster for simple compositions
- Used when Remotion fails or is unavailable

**Configuration**:
```yaml
# config/providers/rendering.yaml
primary_engine: remotion
fallback_engine: ffmpeg
resolution: 1920x1080
fps: 30
codec: h264
container: mp4
crf: 18
audio_codec: aac
audio_bitrate: 192k
```

---

### 7. Web Search — Google Custom Search

**Purpose**: Research mythology topics not covered in the knowledge base.

**Configuration**:
```yaml
# config/providers/web_search.yaml
provider: google_custom_search
max_results: 5
safe_search: moderate
language: en
fallback_provider: tavily
```

---

## Provider Abstraction Requirements

All providers must implement a common interface to enable hot-swapping:

```
Provider Interface Requirements:
├── initialize() → Load config, validate API key
├── health_check() → Verify provider availability
├── generate(input) → Produce output
├── get_cost() → Return cost of last operation
├── get_latency() → Return time of last operation
└── get_quota_status() → Return remaining quota/credits
```

**Why This Matters**:
- Any provider can be replaced without changing agent code
- Cost tracking works uniformly across all providers
- Health checks enable automatic failover
- Quota monitoring prevents unexpected service interruptions

---

## Fallback Strategy Summary

```
┌─────────────────────────────────────────────────────┐
│              PROVIDER FALLBACK CHAIN                  │
│                                                       │
│  RESEARCH:                                            │
│  ChatGPT → Claude → Gemini → Checkpoint & Pause      │
│                                                       │
│  IMAGES:                                              │
│  Gemini → Replicate (FLUX) → DALL-E → Checkpoint     │
│                                                       │
│  NARRATION:                                           │
│  ElevenLabs → OpenAI TTS → Edge TTS → Checkpoint     │
│                                                       │
│  MUSIC:                                               │
│  Local Cache → ElevenLabs (future) → Replicate       │
│                                                       │
│  SFX:                                                 │
│  ElevenLabs SFX → Local Cache → Generate Silent      │
│                                                       │
│  RENDERING:                                           │
│  Remotion → FFmpeg → Error                            │
│                                                       │
│  RULE: Every fallback chain ends with either          │
│  a working provider or a checkpoint save.             │
│  No production run is ever lost.                      │
└─────────────────────────────────────────────────────┘
```

---

## Configuration Strategy

### Provider Configuration Layers

```
Layer 1: Default Config (config/default.yaml)
  │  Sensible defaults for all providers
  │
  ▼
Layer 2: Profile Config (config/mythforge.yaml)
  │  MythForge-specific provider selections
  │
  ▼
Layer 3: Environment Variables (.env)
  │  API keys and secrets
  │
  ▼
Layer 4: Runtime Overrides (CLI flags)
     Per-run provider overrides
```

### API Key Management

| Provider | Environment Variable | Required |
|----------|---------------------|----------|
| OpenAI | `OPENAI_API_KEY` | Yes |
| Google/Gemini | `GOOGLE_API_KEY` | Yes |
| ElevenLabs | `ELEVENLABS_API_KEY` | Yes |
| Replicate | `REPLICATE_API_TOKEN` | No (fallback only) |
| Anthropic | `ANTHROPIC_API_KEY` | No (fallback only) |
| Google Search | `GOOGLE_SEARCH_API_KEY` | No (for web research) |
| YouTube | `YOUTUBE_API_KEY` | No (future publishing) |

### Cost Budget per Production Run

| Stage | Budget | Provider |
|-------|--------|----------|
| Research | $0.30 | ChatGPT |
| Script | $0.40 | ChatGPT |
| Images | $1.50 | Gemini |
| Narration | $1.20 | ElevenLabs |
| Music | $0.00 | Local Cache |
| SFX | $0.40 | ElevenLabs |
| Thumbnail | $0.10 | Gemini |
| Metadata | $0.10 | ChatGPT |
| Rendering | $0.00 | Local (Remotion/FFmpeg) |
| **Total** | **$4.00** | — |

Budget tracker enforces a hard limit of $5.00 per production run.

---

## Provider Risk Assessment

| Provider | Risk Level | Mitigation |
|----------|-----------|------------|
| ChatGPT (OpenAI) | Low | Claude and Gemini as fallbacks |
| Gemini Image API | Medium | Replicate and DALL-E as fallbacks |
| ElevenLabs | Medium | OpenAI TTS and Edge TTS as fallbacks |
| Remotion | Low | FFmpeg as fallback |
| Local Music Cache | Low | No external dependency |

---

## Summary

The provider strategy follows three principles:

1. **No single point of failure**: Every provider has at least one fallback
2. **Cost discipline**: Total production cost stays under $5 per video
3. **Hot-swappable**: Any provider can be replaced without changing agent or pipeline code