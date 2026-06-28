# MythForge AI — Pipeline Design

## Overview

The MythForge Production Pipeline is a multi-stage, checkpoint-enabled, fault-tolerant pipeline that transforms a video title into a complete, publishable mythology video. Each stage is an independent agent execution with defined inputs, outputs, artifacts, and failure handling.

---

## Pipeline Identity

| Property | Value |
|----------|-------|
| Pipeline ID | `mythforge_production` |
| Pipeline Name | MythForge Cinematic Production |
| Inherits From | `PipelineBase` (OpenMontage) |
| Stages | 11 |
| Estimated Duration | 15-30 minutes |
| Estimated Cost | $3.00-4.50 per video |
| Checkpoint Frequency | After every stage |
| Max Retries per Stage | 3 |

---

## Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MYTHFORGE PRODUCTION PIPELINE                         │
│                                                                          │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │
│  │  S1  │─▶│  S2  │─▶│  S3  │─▶│  S4  │─▶│  S5  │─▶│  S6  │          │
│  │Resrch│  │Script│  │Scenes│  │Prompt│  │Image │  │Narrat│          │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘          │
│     │         │         │         │         │         │                  │
│     ▼         ▼         ▼         ▼         ▼         ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    CHECKPOINT STORE                            │       │
│  │  .mythforge/projects/{project_id}/checkpoints/               │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                     │
│  │  S7  │─▶│  S8  │─▶│  S9  │─▶│ S10  │─▶│ S11  │                     │
│  │Music │  │ SFX  │  │Render│  │  QA  │  │Thmbl│                     │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘                     │
│     │         │         │         │         │                           │
│     ▼         ▼         ▼         ▼         ▼                           │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    FINAL OUTPUT                                │       │
│  │  .mythforge/projects/{project_id}/output/                    │       │
│  └──────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Stage Specifications

### Stage 1: Research

| Property | Value |
|----------|-------|
| Stage ID | `research` |
| Agent | `mythforge_researcher` |
| Input | Video title (string) |
| Output | `research.json` |
| Provider | ChatGPT (gpt-4o) |
| Budget | $0.30 |
| Timeout | 120 seconds |
| Retries | 3 |

**Responsibilities**:
- Parse the video title to identify mythology topic, characters, and cultural origin
- Search the local Knowledge Base for matching entries
- Supplement with web research if Knowledge Base coverage is insufficient
- Identify the story arc: Setup, Conflict, Resolution
- Flag cultural sensitivities or content warnings
- Produce a structured Research Brief

**Output Artifact** (`research.json`):
```json
{
  "project_id": "shango_thunder_20260628",
  "title": "The Legend of Shango, God of Thunder",
  "mythology_origin": "yoruba",
  "main_characters": [
    {
      "id": "shango",
      "name": "Shango",
      "role": "protagonist",
      "domain": "Thunder, Lightning, Fire, Justice",
      "personality": "Powerful, just, dramatic, proud"
    }
  ],
  "story_arc": {
    "setup": "Shango rises as the fourth Alafin of Oyo...",
    "conflict": "His generals plot against him, questioning his divine power...",
    "resolution": "Shango proves his divinity by calling thunder from the sky..."
  },
  "cultural_context": {
    "tradition": "Yoruba",
    "region": "West Africa (Nigeria, Benin, Togo)",
    "sacred_elements": ["thunderstones (edun ara)", "double-headed axe", "Oshe"],
    "sensitivity_notes": "Shango is actively worshipped in Yoruba religion; avoid mockery"
  },
  "key_scenes": [
    "Shango ascending the throne of Oyo",
    "The generals plotting in shadow",
    "Shango calling lightning from the heavens"
  ],
  "sources": [
    "Knowledge Base: characters/shango.json",
    "Web: Britannica - Shango",
    "Web: Mythology.net - Yoruba Gods"
  ]
}
```

**Failure Handling**:
- Knowledge Base miss: Log warning, continue with web research only
- Web search failure: Continue with Knowledge Base only
- LLM failure: Retry with exponential backoff (5s, 15s, 45s)
- All retries exhausted: Checkpoint, save partial research, pause pipeline

---

### Stage 2: Script Writing

| Property | Value |
|----------|-------|
| Stage ID | `script` |
| Agent | `mythforge_scriptwriter` |
| Input | `research.json` |
| Output | `script.json` |
| Provider | ChatGPT (gpt-4o) |
| Budget | $0.40 |
| Timeout | 180 seconds |
| Retries | 3 |

**Responsibilities**:
- Transform the Research Brief into a cinematic narration script
- Write in a documentary storytelling style (authoritative, dramatic, respectful)
- Structure as three acts with clear scene breaks
- Include character dialogue in first person where appropriate
- Weave in cultural elements (proverbs, idioms, cultural references)
- Target 1,500-2,250 words (10-15 minutes of narration at ~150 words/minute)

**Output Artifact** (`script.json`):
```json
{
  "project_id": "shango_thunder_20260628",
  "title": "The Legend of Shango, God of Thunder",
  "total_word_count": 1850,
  "estimated_duration_seconds": 740,
  "acts": [
    {
      "act": 1,
      "title": "The Rise of Shango",
      "scenes": [
        {
          "scene_id": "scene_01",
          "narration": "In the ancient city of Oyo, where the empire stretched beyond the horizon, a king sat upon a throne unlike any other...",
          "duration_estimate": 30,
          "mood": "epic",
          "tone": "establishing"
        }
      ]
    }
  ],
  "cultural_notes": [
    "Use 'Alafin' not 'King' for Yoruba royalty",
    "Reference 'Ogun' as Shango's ally, not rival"
  ]
}
```

**Failure Handling**:
- Script too short (< 1,000 words): Regenerate with "expand" instruction
- Script too long (> 3,000 words): Regenerate with "condense" instruction
- Cultural accuracy concern: Flag for manual review, continue with caveat
- LLM failure: Same retry strategy as Stage 1

---

### Stage 3: Scene Director

| Property | Value |
|----------|-------|
| Stage ID | `scene_director` |
| Agent | `mythforge_scene_director` |
| Input | `script.json` + `research.json` |
| Output | `scenes.json` |
| Provider | ChatGPT (gpt-4o) |
| Budget | $0.20 |
| Timeout | 120 seconds |
| Retries | 2 |

**Responsibilities**:
- Break the script into individual scenes with visual direction
- Define scene types (narration, action, transition, title card, outro)
- Specify camera movement for Ken Burns effect
- Define text overlays and subtitle timing
- Specify transitions between scenes
- Ensure no two consecutive scenes have similar visual composition

**Output Artifact** (`scenes.json`):
```json
{
  "project_id": "shango_thunder_20260628",
  "total_scenes": 22,
  "scenes": [
    {
      "scene_id": "scene_01",
      "type": "title_card",
      "title_text": "THE LEGEND OF SHANGO",
      "subtitle_text": "God of Thunder — Yoruba Mythology",
      "duration": 5.0,
      "transition_out": "fade_to_black",
      "audio": {
        "music_mood": "epic_opening",
        "sfx": ["distant_thunder"]
      }
    },
    {
      "scene_id": "scene_02",
      "type": "narration",
      "narration_text": "In the ancient city of Oyo...",
      "duration": 25.0,
      "visual": {
        "composition": "wide_shot",
        "subject": "Ancient city of Oyo at dawn, sprawling Yoruba kingdom",
        "camera_movement": "slow_zoom_in",
        "movement_intensity": 3
      },
      "transition_in": "cross_dissolve",
      "transition_out": "cross_dissolve",
      "subtitle": "In the ancient city of Oyo, where the empire stretched beyond the horizon...",
      "audio": {
        "music_mood": "mysterious",
        "sfx": ["morning_birds", "distant_drums"]
      }
    }
  ]
}
```

---

### Stage 4: Prompt Engineering

| Property | Value |
|----------|-------|
| Stage ID | `prompt_engineering` |
| Agent | `mythforge_prompt_agent` |
| Input | `scenes.json` + `research.json` + Character Bible + Playbook |
| Output | `prompts.json` |
| Provider | ChatGPT (gpt-4o-mini) |
| Budget | $0.15 |
| Timeout | 90 seconds |
| Retries | 2 |

**Responsibilities**:
- Transform scene descriptions into optimized image generation prompts
- Inject character identity from the Character Bible into every prompt containing characters
- Apply art style from the active Playbook
- Include negative prompts to avoid common generation failures
- Ensure cultural accuracy in visual descriptions (skin tone, clothing, architecture)
- Generate prompt variations for quality selection

**Output Artifact** (`prompts.json`):
```json
{
  "project_id": "shango_thunder_20260628",
  "playbook": "dark_fantasy",
  "style_anchor": "Cinematic dark fantasy art style inspired by African mythology, dramatic lighting, rich earth tones, highly detailed, 8K quality",
  "prompts": [
    {
      "scene_id": "scene_02",
      "positive_prompt": "Cinematic wide shot of the ancient Yoruba city of Oyo at dawn, sprawling mud-brick architecture with ornate carvings, golden sunlight breaking through morning mist, bustling marketplace in the distance, palm trees lining the horizon, dark fantasy art style inspired by African mythology, dramatic lighting, rich earth tones, highly detailed, 8K quality",
      "negative_prompt": "text, watermark, logo, european architecture, modern buildings, low quality, blurry, western fantasy castle",
      "character_ids": [],
      "aspect_ratio": "16:9"
    },
    {
      "scene_id": "scene_05",
      "positive_prompt": "Shango, the Yoruba god of thunder, standing powerfully with his double-headed axe (oshe), muscular dark-skinned man with intricate facial scarification marks, wearing royal white and red agbada robes with golden embroidery, crown of thunder stones on his head, lightning crackling around him, dark stormy sky background, dark fantasy art style inspired by African mythology, dramatic lighting, rich earth tones, highly detailed, 8K quality",
      "negative_prompt": "text, watermark, logo, european armor, medieval style, low quality, blurry, western fantasy",
      "character_ids": ["shango"],
      "aspect_ratio": "16:9"
    }
  ]
}
```

---

### Stage 5: Image Generation

| Property | Value |
|----------|-------|
| Stage ID | `image_generation` |
| Agent | `mythforge_image_agent` |
| Input | `prompts.json` |
| Output | Image files in `assets/images/` |
| Provider | Gemini Image API |
| Budget | $1.50 |
| Timeout | 600 seconds |
| Retries | 3 (per image) |

**Responsibilities**:
- Generate one image per scene using the prepared prompts
- Validate generated images for quality (no text artifacts, no blank frames)
- Store images with consistent naming convention
- Log generation cost per image
- If an image fails quality check, regenerate with adjusted prompt (up to 2 retries)

**Output Artifacts**:
- `{project_id}_scene_01.png`
- `{project_id}_scene_02.png`
- ... (one per scene)

**Failure Handling**:
- Single image failure: Retry with same prompt (up to 3 times)
- Quality check failure: Adjust prompt, retry (up to 2 times)
- Provider failure: Switch to fallback (Replicate FLUX)
- All providers exhausted: Checkpoint, save generated images, pause

---

### Stage 6: Narration

| Property | Value |
|----------|-------|
| Stage ID | `narration` |
| Agent | `mythforge_narrator` |
| Input | `scenes.json` + Knowledge Base pronunciation guide |
| Output | Audio files in `assets/narration/` |
| Provider | ElevenLabs |
| Budget | $1.20 |
| Timeout | 600 seconds |
| Retries | 3 (per scene) |

**Responsibilities**:
- Generate narration audio for each scene using the narration text
- Apply correct pronunciation for mythology names (from Knowledge Base)
- Normalize audio levels to -14 LUFS
- Generate silence gaps between scenes (0.5-1.5 seconds)
- Concatenate individual scene narrations into a single narration track

**Output Artifacts**:
- Individual: `{project_id}_scene_01_narration.mp3`
- Combined: `{project_id}_narration_full.mp3`

**Failure Handling**:
- Pronunciation error: Regenerate with SSML phoneme tags
- Audio quality issue: Regenerate with adjusted voice settings
- Provider failure: Switch to OpenAI TTS fallback

---

### Stage 7: Music

| Property | Value |
|----------|-------|
| Stage ID | `music` |
| Agent | `mythforge_music_agent` |
| Input | `scenes.json` + `research.json` (cultural context) |
| Output | Music file in `assets/music/` |
| Provider | Local Asset Cache |
| Budget | $0.00 |
| Timeout | 60 seconds |
| Retries | 1 |

**Responsibilities**:
- Analyze scene moods and cultural origin to select appropriate music
- Search the local music library for matching tracks
- If multiple tracks needed (e.g., different moods for different acts), create a playlist
- Ensure music duration covers the full video
- Apply fade-in at start and fade-out at end

**Output Artifacts**:
- `{project_id}_music_track.mp3`

**Music Selection Logic**:
```
Cultural Origin: Yoruba → Category: west_african
Mood Sequence: [epic, mysterious, tense, triumphant, reflective]
→ Select tracks matching cultural_origin + mood
→ If no exact match, use closest mood within cultural origin
→ If no cultural match, use generic cinematic music
```

---

### Stage 8: Sound Effects

| Property | Value |
|----------|-------|
| Stage ID | `sfx` |
| Agent | `mythforge_sfx_agent` |
| Input | `scenes.json` + `research.json` |
| Output | SFX files in `assets/sfx/` |
| Provider | ElevenLabs SFX / Local Cache |
| Budget | $0.40 |
| Timeout | 300 seconds |
| Retries | 2 (per effect) |

**Responsibilities**:
- Analyze each scene for appropriate sound effects
- Generate or select SFX for: ambient sounds, impact effects, transitions, environmental audio
- Layer SFX with appropriate volume levels relative to narration
- Produce a combined SFX track synchronized to scene timing

**Output Artifacts**:
- Individual: `{project_id}_sfx_thunder.wav`, `{project_id}_sfx_drums.wav`, ...
- Combined: `{project_id}_sfx_track.wav`

---

### Stage 9: Rendering

| Property | Value |
|----------|-------|
| Stage ID | `rendering` |
| Agent | `mythforge_renderer` |
| Input | All assets (images, narration, music, SFX, scenes) |
| Output | `render/final.mp4` |
| Provider | Remotion (primary) / FFmpeg (fallback) |
| Budget | $0.00 (local compute) |
| Timeout | 900 seconds |
| Retries | 1 |

**Responsibilities**:
- Compose all assets into a timeline-based video
- Apply Ken Burns effect to all static images
- Render transitions between scenes
- Overlay subtitles synchronized with narration
- Mix audio tracks (narration + music + SFX)
- Add title card and credits
- Encode to H.264 MP4 at 1920x1080, 30fps
- Normalize final audio to -14 LUFS

**Output Artifacts**:
- `{project_id}_final.mp4`
- `{project_id}_subtitles.srt`

**Rendering Process**:
```
1. Build Remotion timeline JSON from scenes.json
2. Load all assets into Remotion project
3. Render each composition:
   a. Apply Ken Burns to images
   b. Overlay subtitles
   c. Mix audio layers
   d. Apply transitions
4. Encode final output
5. Validate: duration, resolution, audio levels
6. If Remotion fails → FFmpeg fallback rendering
```

---

### Stage 10: Quality Assurance

| Property | Value |
|----------|-------|
| Stage ID | `qa` |
| Agent | `mythforge_qa` |
| Input | `render/final.mp4` + all artifacts |
| Output | `qa_report.json` |
| Provider | ChatGPT (gpt-4o-mini) + FFprobe |
| Budget | $0.10 |
| Timeout | 120 seconds |
| Retries | 1 |

**Responsibilities**:
- Validate video technical specifications (resolution, fps, codec, audio levels)
- Check for visual issues (blank frames, duplicates, artifacts)
- Verify narration-to-scene synchronization
- Check subtitle accuracy against narration
- Validate cultural accuracy against research notes
- Generate a quality score (0-100)
- Recommend: PASS, REVISE, or FAIL

**Quality Gates**:
| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Resolution | 1920x1080 | Re-render |
| Audio levels | -14 LUFS ± 2 | Re-mix audio |
| Silence gaps | < 2 seconds | Add ambient audio |
| Visual artifacts | 0 blank frames | Re-generate affected scenes |
| Subtitle sync | < 2s drift | Re-sync subtitles |
| Duration | 10-15 minutes | Adjust scene pacing |
| Cultural score | ≥ 7/10 | Flag for review |
| Overall score | ≥ 70/100 | REVISE; < 50 → FAIL |

**QA Report Output** (`qa_report.json`):
```json
{
  "project_id": "shango_thunder_20260628",
  "overall_score": 82,
  "recommendation": "PASS",
  "gates": {
    "resolution": {"status": "PASS", "value": "1920x1080"},
    "audio_levels": {"status": "PASS", "value": "-14.1 LUFS"},
    "duration": {"status": "PASS", "value": "724 seconds"},
    "cultural_accuracy": {"status": "PASS", "value": "8/10"}
  },
  "issues": [],
  "cost_tracking": {
    "total_cost": 3.47,
    "breakdown": {
      "research": 0.18,
      "script": 0.25,
      "images": 0.89,
      "narration": 0.72,
      "sfx": 0.31,
      "other": 0.12
    }
  }
}
```

---

### Stage 11: Thumbnail & Metadata

| Property | Value |
|----------|-------|
| Stage ID | `thumbnail_metadata` |
| Agent | `mythforge_publisher` |
| Input | `research.json` + `script.json` + primary character image |
| Output | `thumbnail.png` + `metadata.json` |
| Provider | Gemini (thumbnail) + ChatGPT (metadata) |
| Budget | $0.15 |
| Timeout | 120 seconds |
| Retries | 2 |

**Responsibilities**:
- Generate a YouTube-optimized thumbnail image
- Write SEO-optimized title, description, and tags
- Generate timestamps for video chapters
- Create production report summarizing the entire pipeline run

**Output Artifacts**:
- `{project_id}_thumbnail.png`
- `{project_id}_metadata.json`
- `{project_id}_production_report.json`

---

## Checkpoint System

### Checkpoint Architecture

Every stage saves a checkpoint upon completion. The checkpoint enables the pipeline to resume from the last successful stage if interrupted.

```
.mythforge/projects/{project_id}/
├── checkpoints/
│   ├── stage_01_research.json        # Completed
│   ├── stage_02_script.json          # Completed
│   ├── stage_03_scene_director.json  # Completed
│   ├── stage_04_prompt_engineering.json  # ← RESUME FROM HERE
│   └── pipeline_state.json           # Overall pipeline state
```

### Checkpoint Data

```json
{
  "pipeline_id": "mythforge_production",
  "project_id": "shango_thunder_20260628",
  "current_stage": "prompt_engineering",
  "completed_stages": ["research", "script", "scene_director"],
  "failed_stages": [],
  "start_time": "2026-06-28T20:00:00Z",
  "last_checkpoint": "2026-06-28T20:05:30Z",
  "total_cost_so_far": 0.63,
  "artifacts": {
    "research": "artifacts/research.json",
    "script": "artifacts/script.json",
    "scenes": "artifacts/scenes.json"
  }
}
```

### Resume Logic

```
IF checkpoint exists for project_id:
    LOAD pipeline_state.json
    SKIP all completed stages
    RESUME from current_stage
    PRESERVE all existing artifacts
ELSE:
    START from stage_01 (research)
```

---

## Caching Strategy

### What Gets Cached

| Asset Type | Cache Key | TTL | Storage |
|-----------|-----------|-----|---------|
| Generated Images | Hash of (prompt + style + model) | 30 days | `cache/images/` |
| Narration Audio | Hash of (text + voice + model) | 30 days | `cache/narration/` |
| Music Tracks | Track ID | Permanent | `cache/music/` |
| SFX | Effect ID | Permanent | `cache/sfx/` |
| Research Results | Hash of (title + date) | 7 days | `cache/research/` |

### Cache Hit Logic

```
Before generating any asset:
1. Compute cache key from input parameters
2. Check cache for matching key
3. IF cache hit:
   a. Validate cached asset (file exists, size > 0)
   b. Use cached asset, skip generation
   c. Log cache hit (cost savings)
4. IF cache miss:
   a. Generate asset normally
   b. Store in cache after successful generation
   c. Log generation cost
```

### Cache Invalidation

- Manual invalidation via CLI: `mythforge cache clear --type images --older-than 7d`
- Automatic invalidation on provider change (e.g., switching from Gemini to Replicate)
- Quality-triggered invalidation: If QA flags an image, cache entry is removed

---

## Failure Handling Matrix

| Failure Type | Detection | Response | Max Retries |
|-------------|-----------|----------|-------------|
| LLM timeout | Timeout exceeded | Retry with backoff (5s, 15s, 45s) | 3 |
| LLM rate limit (429) | HTTP status | Wait + retry with backoff | 5 |
| LLM invalid output | JSON parse failure | Retry with clarified prompt | 3 |
| Image generation failure | Empty/error response | Retry, then fallback provider | 3+2 |
| Image quality failure | QA check fails | Regenerate with adjusted prompt | 2 |
| Audio generation failure | Empty/error response | Retry, then fallback provider | 3+2 |
| Audio quality failure | Level check fails | Re-normalize, regenerate if needed | 2 |
| Rendering failure | FFmpeg/Remotion error | Switch renderer, retry | 1+1 |
| Disk space | Write failure | Clean cache, retry | 1 |
| Budget exceeded | Budget tracker | Checkpoint, pause, notify | 0 |
| Unknown error | Exception | Log, checkpoint, pause | 0 |

---

## Pipeline Configuration

```yaml
# config/pipelines/mythforge_production.yaml
pipeline:
  id: mythforge_production
  name: MythForge Cinematic Production
  version: 1.0.0

stages:
  - id: research
    agent: mythforge_researcher
    timeout: 120
    budget: 0.30
    retries: 3
    checkpoint: true

  - id: script
    agent: mythforge_scriptwriter
    timeout: 180
    budget: 0.40
    retries: 3
    checkpoint: true
    depends_on: [research]

  - id: scene_director
    agent: mythforge_scene_director
    timeout: 120
    budget: 0.20
    retries: 2
    checkpoint: true
    depends_on: [script]

  - id: prompt_engineering
    agent: mythforge_prompt_agent
    timeout: 90
    budget: 0.15
    retries: 2
    checkpoint: true
    depends_on: [scene_director]

  - id: image_generation
    agent: mythforge_image_agent
    timeout: 600
    budget: 1.50
    retries: 3
    checkpoint: true
    depends_on: [prompt_engineering]

  - id: narration
    agent: mythforge_narrator
    timeout: 600
    budget: 1.20
    retries: 3
    checkpoint: true
    depends_on: [scene_director]

  - id: music
    agent: mythforge_music_agent
    timeout: 60
    budget: 0.00
    retries: 1
    checkpoint: true
    depends_on: [scene_director]

  - id: sfx
    agent: mythforge_sfx_agent
    timeout: 300
    budget: 0.40
    retries: 2
    checkpoint: true
    depends_on: [scene_director]

  - id: rendering
    agent: mythforge_renderer
    timeout: 900
    budget: 0.00
    retries: 1
    checkpoint: true
    depends_on: [image_generation, narration, music, sfx]

  - id: qa
    agent: mythforge_qa
    timeout: 120
    budget: 0.10
    retries: 1
    checkpoint: true
    depends_on: [rendering]

  - id: thumbnail_metadata
    agent: mythforge_publisher
    timeout: 120
    budget: 0.15
    retries: 2
    checkpoint: true
    depends_on: [qa]

budget:
  total: 5.00
  warning_threshold: 0.80
  hard_limit: true

output:
  directory: .mythforge/projects/{project_id}/output/
  cleanup_temp: true
```

---

## Parallel Execution Opportunities

Some stages can run in parallel because they have the same dependency:

```
Stage 3 (Scene Director) completes
         │
         ├──▶ Stage 4 (Prompt Engineering) ──▶ Stage 5 (Images)
         │
         ├──▶ Stage 6 (Narration)    ──┐
         │                              │
         ├──▶ Stage 7 (Music)         ──┼──▶ Stage 9 (Rendering)
         │                              │
         └──▶ Stage 8 (SFX)           ──┘

Stages 4-8 can partially overlap:
- Stage 4 must complete before Stage 5 (images depend on prompts)
- Stages 6, 7, 8 only depend on Stage 3 (scenes) and can run in parallel
- Stage 9 (rendering) waits for ALL of 5, 6, 7, 8 to complete
```

---

## Summary

The MythForge Production Pipeline is designed for reliability, cost-efficiency, and quality. Every stage is independent, checkpointed, and retry-enabled. The pipeline can survive any single provider failure and resume from where it left off. Parallel execution of independent stages minimizes total production time.