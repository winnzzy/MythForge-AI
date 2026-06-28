# OpenMontage — Pipeline Analysis

## Overview

OpenMontage defines **11 production pipelines** as YAML files in `pipeline_defs/`. Each pipeline is a declarative definition of stages, required skills, tools, checkpoints, and success criteria. The AI agent reads these definitions and orchestrates execution accordingly.

Pipelines are **not executable code** — they are data consumed by the AI agent.

---

## Pipeline 1: Animated Explainer

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/animated-explainer.yaml` |
| **Purpose** | Create motion-graphics explainer videos from a topic |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Executive Producer** | Yes — `skills/pipelines/explainer/executive-producer.md` |
| **Render Runtime** | remotion (default), hyperframes, ffmpeg |
| **Renderer Family** | explainer-data, explainer-teacher, product-reveal, screen-demo, animation-first |
| **Inputs** | User topic/idea |
| **Outputs** | MP4 video file, publish_log |
| **Cost Range** | $0.00 - $5.00+ (depends on provider choices) |
| **Duration** | 30s - 5min typical |
| **Dependencies** | TTS tool, image/video generation tool, Remotion or HyperFrames |
| **Reuse Suitability** | HIGH — Most general-purpose pipeline |

**Stage Skills**:
1. `research-director` — Gather data, identify angles
2. `proposal-director` — Present concepts, get approval
3. `script-director` — Write narration with enhancement cues
4. `scene-director` — Map script to visual scenes
5. `asset-director` — Generate TTS, images, videos
6. `edit-director` — Create timeline and edit decisions
7. `compose-director` — Render via Remotion/HyperFrames/FFmpeg
8. `publish-director` — Generate metadata and export

---

## Pipeline 2: Talking Head

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/talking-head.yaml` |
| **Purpose** | Create talking-head videos with lip-synced avatars |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | ffmpeg (default — video concat) |
| **Renderer Family** | presenter |
| **Inputs** | User topic/idea + avatar image/video |
| **Outputs** | MP4 video with lip-synced avatar |
| **Dependencies** | TTS, lip-sync tool (wav2lip/heygen/hedra), FFmpeg |
| **Reuse Suitability** | MEDIUM — Specialized for avatar content |

---

## Pipeline 3: Cinematic B-Roll

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/cinematic-broll.yaml` |
| **Purpose** | Cinematic-style video with stock B-roll footage |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | remotion or ffmpeg |
| **Renderer Family** | cinematic-trailer, documentary-montage |
| **Inputs** | User topic/idea |
| **Outputs** | Cinematic MP4 with stock footage, narration, music |
| **Dependencies** | TTS, stock video (Pexels/Pixabay), Remotion CinematicRenderer |
| **Reuse Suitability** | HIGH — Good template for documentary-style content |

---

## Pipeline 4: Podcast Repurpose

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/podcast-repurpose.yaml` |
| **Purpose** | Convert podcast audio into short-form video clips |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | remotion or ffmpeg |
| **Inputs** | Podcast audio file |
| **Outputs** | Short video clips with waveform, captions, highlights |
| **Dependencies** | Transcriber (WhisperX), subtitle generator, Remotion |
| **Reuse Suitability** | HIGH — Common workflow for content repurposing |

---

## Pipeline 5: Screen Demo

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/screen-demo.yaml` |
| **Purpose** | Create screen recording demos with narration |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | remotion or ffmpeg |
| **Renderer Family** | screen-demo |
| **Inputs** | Screen recording + narration script |
| **Outputs** | Polished demo video with captions, zoom effects |
| **Dependencies** | screen_record tool, TTS, subtitle generator, Remotion |
| **Reuse Suitability** | HIGH — Standard demo workflow |

---

## Pipeline 6: Documentary Montage

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/documentary-montage.yaml` |
| **Purpose** | Long-form documentary-style video with montage editing |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | remotion |
| **Renderer Family** | documentary-montage |
| **Inputs** | User topic/idea |
| **Outputs** | Documentary MP4 with B-roll, narration, music |
| **Dependencies** | TTS, stock video, music, Remotion CinematicRenderer |
| **Reuse Suitability** | MEDIUM — Specialized for longer content |

---

## Pipeline 7: Localization / Dubbing

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/localization-dub.yaml` |
| **Purpose** | Translate and dub existing videos into target languages |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | ffmpeg |
| **Inputs** | Source video + target language |
| **Outputs** | Dubbed video with translated narration and subtitles |
| **Dependencies** | Transcriber, TTS (multi-language), subtitle generator, FFmpeg |
| **Reuse Suitability** | HIGH — Standard localization workflow |

---

## Pipeline 8: Avatar Spokesperson

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/avatar-spokesperson.yaml` |
| **Purpose** | AI avatar spokesperson videos (HeyGen-style) |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | ffmpeg |
| **Renderer Family** | presenter |
| **Inputs** | Script + avatar selection |
| **Outputs** | Avatar spokesperson video |
| **Dependencies** | TTS, avatar tool (heygen/hedra), FFmpeg |
| **Reuse Suitability** | MEDIUM — Depends on avatar provider availability |

---

## Pipeline 9: Character Animation

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/character-animation.yaml` |
| **Purpose** | Animate character images with motion |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | remotion or ffmpeg |
| **Inputs** | Character images + script |
| **Outputs** | Animated character video |
| **Dependencies** | Character animation tools, TTS, Remotion |
| **Reuse Suitability** | LOW — Highly specialized |

---

## Pipeline 10: Clip Factory

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/clip-factory.yaml` |
| **Purpose** | Batch-produce multiple short clips from a single topic |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | remotion or ffmpeg |
| **Inputs** | Topic + clip count |
| **Outputs** | Multiple short video clips |
| **Dependencies** | TTS, image/video generation, Remotion |
| **Reuse Suitability** | HIGH — Useful for social media content |

---

## Pipeline 11: Hybrid Live-Animated

| Attribute | Value |
|-----------|-------|
| **File** | `pipeline_defs/hybrid-live-animated.yaml` |
| **Purpose** | Combine live-action footage with animated overlays |
| **Stages** | research → proposal → script → scene_plan → assets → edit → compose → publish |
| **Render Runtime** | remotion |
| **Inputs** | Live footage + animation requirements |
| **Outputs** | Hybrid video with live + animated elements |
| **Dependencies** | TTS, video generation, Remotion, FFmpeg |
| **Reuse Suitability** | MEDIUM — Complex but valuable for certain content types |

---

## Common Pipeline Structure

All 11 pipelines share the same 8-stage structure:

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE STAGES                           │
├─────────┬─────────┬─────────┬─────────┬─────────┬──────────┤
│ Stage 1 │ Stage 2 │ Stage 3 │ Stage 4 │ Stage 5 │ Stage 6  │
│Research │Proposal │ Script  │ Scene   │ Assets  │  Edit    │
│ (free)  │ (free)  │ (free)  │ (free)  │ (cost)  │ (free)   │
│         │ APPROVAL│         │         │         │          │
├─────────┴─────────┴─────────┴─────────┴─────────┴──────────┤
│                    Stage 7: Compose (compute)                │
│                    Stage 8: Publish (free)                   │
└─────────────────────────────────────────────────────────────┘
```

**Key Observations**:
- Stages 1-4 and 6, 8 are zero-cost (agent reasoning only)
- Stage 5 (Assets) is the primary cost-bearing stage
- Stage 7 (Compose) is CPU-intensive but free (local compute)
- The approval gate at Stage 2 is mandatory for all pipelines
- All pipelines use the same Executive Producer orchestration pattern

---

## Pipeline Differentiation

Pipelines differ primarily in:

1. **Default render runtime** (remotion vs ffmpeg vs hyperframes)
2. **Renderer family** (explainer, cinematic, presenter, etc.)
3. **Primary tools** (TTS provider, image provider, video provider)
4. **Scene types** (text cards vs video clips vs avatar frames)
5. **Skill specialization** (each pipeline has its own director skills)

The underlying orchestration pattern is identical — only the content and tool selection vary.

---

## Execution Order

All pipelines execute stages in the same order:

```
1. research  → 2. proposal → [APPROVAL] → 3. script → 4. scene_plan → 5. assets → 6. edit_decisions → 7. compose → 8. publish
```

No parallel stage execution is supported. The Executive Producer enforces serial execution with review gates between each stage.