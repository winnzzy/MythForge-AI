# MythForge AI — Product Requirements Document (V1)

## Overview

MythForge AI Version 1 is an automated video production platform that takes a single video title as input and produces a complete, publishable mythology video as output. The system handles every stage of production — research, scripting, visual asset generation, narration, sound design, rendering, and metadata — with zero human intervention beyond the initial title.

---

## End-to-End Data Flow

```
INPUT
  │
  ▼
┌─────────────────────┐
│   VIDEO TITLE       │  User provides: "The Legend of Shango, God of Thunder"
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   RESEARCH          │  AI researches the mythology using knowledge base + web
│                     │  Output: Research Brief (JSON)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SCRIPT            │  AI writes a cinematic narration script
│                     │  Output: Script Document (JSON)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SCENE BREAKDOWN   │  AI breaks script into visual scenes
│                     │  Output: Scene Plan (JSON)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   IMAGE GENERATION  │  AI generates images for each scene
│                     │  Output: PNG/JPG files per scene
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   NARRATION         │  AI generates voice narration for each scene
│                     │  Output: MP3/WAV files per scene
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SOUND DESIGN      │  AI selects/generates music and sound effects
│                     │  Output: Music track + SFX files
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   RENDERING         │  Remotion/FFmpeg composites all assets into video
│                     │  Output: MP4 video file
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   THUMBNAIL         │  AI generates a YouTube-optimized thumbnail
│                     │  Output: JPG/PNG thumbnail
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   METADATA          │  AI generates title, description, tags, SEO
│                     │  Output: Metadata JSON
└──────────┬──────────┘
           │
           ▼
OUTPUT
  │
  ├── final_video.mp4
  ├── thumbnail.jpg
  ├── metadata.json
  ├── subtitles.srt
  └── production_report.json
```

---

## In Scope (V1)

### Input Requirements

| Requirement | Specification |
|-------------|--------------|
| Input format | Plain text title (string) |
| Input source | CLI command or Python function call |
| Input validation | Non-empty string, minimum 5 characters |
| Optional input | Custom voice selection, custom style override, custom duration target |

### Research Stage

| Requirement | Specification |
|-------------|--------------|
| Knowledge base lookup | Search local knowledge base for mythology entries matching title keywords |
| Web research | Use AI to research mythology details not in knowledge base |
| Source verification | Cross-reference multiple sources for accuracy |
| Output format | Research Brief JSON with: deity/character info, story arc, cultural context, visual references, key scenes |
| Cultural sensitivity | Flag potentially sensitive content for review |

### Script Stage

| Requirement | Specification |
|-------------|--------------|
| Script format | Narration script with scene-by-scene breakdown |
| Script length | 10-15 minutes of narration (approximately 1,500-2,250 words) |
| Narrative structure | Three-act structure: Setup → Conflict/Development → Resolution |
| Tone | Cinematic documentary style — authoritative, dramatic, respectful |
| Dialogue handling | Characters speak in first person when quoted; narrator uses third person |
| Cultural voice | Language reflects the mythology's cultural origin (e.g., Yoruba proverbs for Yoruba stories) |
| Output format | Script JSON with: scene_id, narration_text, scene_description, visual_direction, duration_estimate |

### Scene Breakdown Stage

| Requirement | Specification |
|-------------|--------------|
| Scene count | 15-30 scenes per video |
| Scene types | Narration scene, action scene, transition scene, title card, outro |
| Scene duration | 15-45 seconds per scene |
| Visual direction | Each scene includes: image prompt, camera movement, text overlay, subtitle text |
| Output format | Scene Plan JSON with: scene_id, type, narration, image_prompt, duration, transitions, subtitles |

### Image Generation Stage

| Requirement | Specification |
|-------------|--------------|
| Provider | Gemini Image API (primary) |
| Image count | 15-30 images per video (one per scene, plus alternates) |
| Image resolution | Minimum 1920x1080 (landscape) for video; 1280x720 acceptable for B-roll |
| Art style | Consistent within a video; style defined by playbook |
| Character consistency | Same character appears visually consistent across scenes |
| Negative prompts | Exclude: text artifacts, watermarks, Western fantasy tropes, anachronistic elements |
| Output format | PNG files named: `{project_id}_scene_{scene_id}_{variant}.png` |

### Narration Stage

| Requirement | Specification |
|-------------|--------------|
| Provider | ElevenLabs (primary) |
| Voice | Deep, authoritative male voice with African accent (configurable) |
| Audio format | WAV, 44.1kHz, 16-bit |
| Audio levels | Normalized to -14 LUFS (broadcast standard) |
| Pacing | Natural pauses between scenes (0.5-1.5 seconds) |
| Pronunciation | Mythology-specific names must be pronounced correctly (pronunciation guide from knowledge base) |
| Output format | WAV files named: `{project_id}_scene_{scene_id}_narration.wav` |

### Sound Design Stage

| Requirement | Specification |
|-------------|--------------|
| Background music | Cinematic score appropriate to mythology's cultural origin |
| Music duration | Continuous throughout video, fading at intro and outro |
| Music levels | -20 LUFS under narration, -14 LUFS during pauses |
| Sound effects | Ambient sounds, impact sounds, transition sounds |
| SFX count | 5-15 per video |
| Output format | Music: `{project_id}_music.wav`, SFX: `{project_id}_sfx_{id}.wav` |

### Rendering Stage

| Requirement | Specification |
|-------------|--------------|
| Render engine | Remotion (primary), FFmpeg (fallback) |
| Output resolution | 1920x1080 (16:9) |
| Output frame rate | 30 fps |
| Output codec | H.264 |
| Output container | MP4 |
| Subtitles | Burned-in subtitles (SRT rendered onto video) |
| Transitions | Cross-dissolve (default), fade-to-black (scene breaks), wipe (optional) |
| Ken Burns effect | Slow pan/zoom on all static images (3-5% movement) |
| Text overlays | Title card at opening, credits at closing |
| Output format | `{project_id}_final.mp4` |

### Thumbnail Stage

| Requirement | Specification |
|-------------|--------------|
| Provider | Gemini Image API |
| Resolution | 1280x720 (YouTube standard) |
| Style | Bold, dramatic, high-contrast |
| Text | Minimal — character name and one power word (e.g., "SHANGO — THUNDER") |
| Face | Character face must be prominent and recognizable |
| Output format | `{project_id}_thumbnail.png` |

### Metadata Stage

| Requirement | Specification |
|-------------|--------------|
| Title | SEO-optimized, 60-70 characters |
| Description | 200-500 words with timestamps, mythology context, and call-to-action |
| Tags | 15-30 tags including mythology name, character names, cultural origin, "mythology", "story" |
| Category | Entertainment or Education |
| Language | English (V1) |
| Output format | `{project_id}_metadata.json` |

### Final Output Package

| File | Format | Purpose |
|------|--------|---------|
| `{project_id}_final.mp4` | MP4/H.264 | Publishable video |
| `{project_id}_thumbnail.png` | PNG | YouTube thumbnail |
| `{project_id}_metadata.json` | JSON | Title, description, tags |
| `{project_id}_subtitles.srt` | SRT | Subtitle file for upload |
| `{project_id}_production_report.json` | JSON | Cost, timing, quality scores |
| `{project_id}_assets/` | Directory | All generated assets (images, audio) |

---

## Out of Scope (V1)

| Feature | Reason | Planned Version |
|---------|--------|-----------------|
| YouTube upload automation | Requires OAuth setup and API review | V1.1 |
| TikTok/Instagram publishing | Different format requirements | V1.2 |
| Multi-language narration | Requires voice cloning per language | V2.0 |
| Series/playlist automation | Requires scheduling infrastructure | V1.2 |
| User authentication | Single-operator system for V1 | V2.0 |
| Web UI | CLI-based workflow for V1 | V2.0 |
| Real-time preview | Render is the preview | V2.0 |
| Custom voice cloning | Requires ElevenLabs voice design | V1.1 |
| Interactive video | Linear narrative only | V3.0 |
| Custom art style training | Use existing models | V2.0 |
| Multi-user collaboration | Single operator | V2.0 |
| Billing/subscription | Free for internal use | V2.0 |

---

## Future Enhancements (Post-V1)

### V1.1 (Month 2)
- YouTube upload with OAuth
- Custom ElevenLabs voice cloning
- Asset caching for repeated imagery
- Batch video production (multiple titles at once)

### V1.2 (Month 3)
- TikTok short-form video (vertical, 60 seconds)
- Instagram Reels format
- Series automation (produce 10+ episodes from a topic list)
- Thumbnail A/B testing

### V2.0 (Month 6)
- Web UI with React frontend
- Multi-user authentication
- Multi-language narration (Yoruba, Igbo, Swahili, French)
- Custom art style profiles
- Provider marketplace

### V3.0 (Year 2)
- Interactive choose-your-own-adventure videos
- API access for developers
- White-label licensing
- Custom model training for character consistency

---

## Quality Gates

Every video must pass these gates before being considered complete:

| Gate | Criteria | Measurement |
|------|----------|-------------|
| Audio quality | No clipping, no silence > 2s, levels at -14 LUFS | Automated (FFmpeg analysis) |
| Visual quality | No duplicate scenes, no blank frames, no text artifacts | Automated (image comparison) |
| Narration sync | Narration aligns with scene duration within 2s tolerance | Automated (duration check) |
| Subtitle accuracy | Subtitles match narration with >95% accuracy | Automated (comparison) |
| Cultural accuracy | No factual errors in mythology representation | Manual review (V1), automated (V2) |
| Narrative coherence | Story follows logical arc, no non-sequiturs | Manual review (V1), automated (V2) |
| Technical specs | 1920x1080, 30fps, H.264, -14 LUFS | Automated (FFprobe) |
| Cost | Total production cost under $5 | Automated (cost tracker) |
| Duration | 10-15 minutes | Automated (duration check) |