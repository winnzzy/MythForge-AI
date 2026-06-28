# OpenMontage — Rendering Analysis

## Overview

OpenMontage supports **three rendering runtimes**, selected at the proposal stage and locked for the duration of the pipeline. The choice of runtime determines how the final video is composed and rendered.

```
┌─────────────────────────────────────────────────────────────┐
│                    RENDER RUNTIME SELECTION                  │
│                    (Locked at Proposal Stage)                │
├─────────────────┬─────────────────┬─────────────────────────┤
│    REMOTION     │   HYPERFRAMES   │        FFMPEG           │
│  (TypeScript)   │   (HTML/GSAP)   │      (CLI/Python)       │
├─────────────────┼─────────────────┼─────────────────────────┤
│ Motion graphics │ Kinetic type    │ Simple concat           │
│ Data viz        │ Product promos  │ Subtitle burn           │
│ Explainer vids  │ Website-to-vid  │ Audio mux               │
│ Charts/tables   │ GSAP animations │ Video trimming          │
│ Transitions     │                 │ Format conversion       │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## Runtime 1: Remotion

### Architecture

```
remotion-composer/
├── package.json              # Dependencies (Remotion v4.x, React)
├── src/
│   ├── index.tsx             # Remotion entry point
│   ├── Root.tsx              # Root composition registry
│   ├── Explainer.tsx         # Main explainer composition
│   ├── CinematicRenderer.tsx # Cinematic B-roll composition
│   ├── TalkingHead.tsx       # Talking head composition
│   ├── scenes/               # Individual scene components
│   │   ├── TextCard.tsx      # Text overlay scene
│   │   ├── StatCard.tsx      # Statistics/data scene
│   │   ├── ChartScene.tsx    # Chart visualization
│   │   ├── CalloutScene.tsx  # Callout/highlight scene
│   │   ├── ImageScene.tsx    # Image with effects
│   │   ├── VideoScene.tsx    # Video clip scene
│   │   └── CodeScene.tsx     # Code snippet scene
│   ├── components/           # Shared UI components
│   │   ├── Subtitles.tsx     # Word-level caption overlay
│   │   ├── Transitions.tsx   # Scene transitions
│   │   └── MusicBed.tsx      # Background music mixing
│   └── utils/                # Utility functions
│       ├── timeline.ts       # Timeline math
│       └── colors.ts         # Color utilities
├── public/
│   └── demo-props/           # Demo JSON props for testing
└── tsconfig.json             # TypeScript configuration
```

### Timeline Generation

The AI agent (compose-director) generates a JSON props object from `edit_decisions`:

```json
{
  "scenes": [
    {
      "type": "text_card",
      "text": "What is Quantum Computing?",
      "durationInFrames": 90,
      "style": { "bg": "#1a1a2e", "color": "#eee" }
    },
    {
      "type": "stat_card",
      "value": "4,000x",
      "label": "faster than classical",
      "durationInFrames": 120
    }
  ],
  "subtitles": {
    "words": [...],
    "style": { "font": "Inter", "size": 24 }
  },
  "audio": {
    "narration": "assets/narration.mp3",
    "music": "assets/bgmusic.mp3",
    "musicVolume": 0.15
  }
}
```

### Rendering Command

```bash
npx remotion render src/index.tsx Explainer output.mp4 --props=props.json
```

### Key Features
- **Frame-accurate timing**: Each scene has exact `durationInFrames` (30fps default)
- **Word-level captions**: Subtitles sync to WhisperX word timestamps
- **Scene transitions**: CSS/React transitions between scenes
- **Dynamic components**: Scene type determines which React component renders
- **Webpack bundling**: TypeScript compiled at render time

### Extension Points
- Add new scene types by creating React components in `src/scenes/`
- Register new compositions in `src/Root.tsx`
- Customize transitions in `src/components/Transitions.tsx`

### Risk Level: **HIGH**
- TypeScript/React changes require Node.js build pipeline
- Remotion version upgrades may break scene components
- Performance depends on scene complexity

---

## Runtime 2: HyperFrames

### Architecture

```
tools/video/hyperframes_compose.py
  ├── Generates HTML/GSAP composition from edit_decisions
  ├── Invokes: npx hyperframes render composition.html output.mp4
  └── Handles: kinetic typography, product promos, website-to-video
```

### How It Works

1. The compose-director generates an HTML file with GSAP animations
2. HyperFrames renders the HTML to video frames
3. Audio is muxed via FFmpeg

### Key Features
- **GSAP animations**: Professional motion graphics via GreenSock
- **HTML/CSS layout**: Familiar web development paradigm
- **Kinetic typography**: Text animation specialist
- **Product promos**: Optimized for marketing content

### Extension Points
- Add new HTML templates for different animation styles
- Extend GSAP animation presets

### Risk Level: **MEDIUM**
- Depends on HyperFrames CLI tool availability
- Less flexible than Remotion for complex compositions

---

## Runtime 3: FFmpeg

### Architecture

```
tools/video/video_stitch.py
  ├── Trim video segments (in/out seconds)
  ├── Concatenate segments
  ├── Burn subtitles (ASS format)
  ├── Mux audio tracks
  └── Encode to target profile

tools/audio/audio_mixer.py
  ├── Mix narration + music
  ├── Apply ducking (reduce music volume during speech)
  ├── Normalize audio levels
  └── Export to target format

tools/subtitle/subtitle_gen.py
  ├── Generate SRT/ASS subtitle files
  ├── Apply word-level timing from WhisperX
  └── Style subtitles (font, size, position)
```

### FFmpeg Command Patterns

**Concat**:
```bash
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
```

**Subtitle Burn**:
```bash
ffmpeg -i input.mp4 -vf "ass=subtitles.ass" -c:a copy output.mp4
```

**Audio Mux**:
```bash
ffmpeg -i video.mp4 -i narration.mp3 -i music.mp3 \
  -filter_complex "[1:a]volume=1.0[narr];[2:a]volume=0.15[music];[narr][music]amix=inputs=2" \
  -c:v copy output.mp4
```

**Trim**:
```bash
ffmpeg -i input.mp4 -ss 10 -to 30 -c copy segment.mp4
```

### Subtitle Handling

Subtitle formats supported:
- **SRT** (SubRip): Simple timestamp + text
- **ASS** (Advanced SubStation Alpha): Full styling (font, color, position, effects)

Subtitle styling is driven by the playbook:
```json
{
  "subtitles": {
    "font": "Inter Bold",
    "size": 24,
    "color": "#FFFFFF",
    "outline": "#000000",
    "outlineWidth": 2,
    "position": "bottom_center",
    "wordHighlight": true,
    "highlightColor": "#FFD700"
  }
}
```

### Audio Handling

**Narration**:
- Generated by TTS tools (ElevenLabs, Google TTS, etc.)
- Output: WAV or MP3 file
- Duration drives scene timing

**Background Music**:
- Generated by music tools (Suno, Freesound, Pixabay)
- Ducking: Volume reduced to 10-20% during narration segments
- Fade in/out at start/end of video

**Audio Mixing** (via `audio_mixer.py`):
```
Narration track ─────┐
                      ├──▶ Mix ──▶ Normalize ──▶ Output
Music track ─────────┘
```

### Extension Points
- Add new FFmpeg filter chains for effects
- Extend subtitle styling options
- Add multi-track audio support

### Risk Level: **MEDIUM**
- FFmpeg is a mature, stable dependency
- Command-line interface is well-documented
- Version compatibility is generally good

---

## Scene Handling

### Scene Types (Remotion)

| Scene Type | Component | Purpose | Typical Duration |
|------------|-----------|---------|------------------|
| `text_card` | `TextCard.tsx` | Text overlay with background | 3-5 seconds |
| `stat_card` | `StatCard.tsx` | Large number/statistic display | 3-5 seconds |
| `chart_scene` | `ChartScene.tsx` | Chart/graph visualization | 5-8 seconds |
| `callout_scene` | `CalloutScene.tsx` | Highlighted callout box | 3-5 seconds |
| `image_scene` | `ImageScene.tsx` | Image with Ken Burns/zoom | 4-6 seconds |
| `video_scene` | `VideoScene.tsx` | Video clip playback | 3-10 seconds |
| `code_scene` | `CodeScene.tsx` | Code snippet with syntax highlight | 5-8 seconds |
| `diagram_scene` | `DiagramScene.tsx` | Diagram/flowchart display | 5-8 seconds |

### Scene JSON Structure

Each scene in `edit_decisions.cuts[]`:
```json
{
  "scene_id": "scene_001",
  "type": "text_card",
  "start_second": 0.0,
  "end_second": 4.5,
  "duration_seconds": 4.5,
  "asset_path": "assets/scene_001.png",
  "text": "What is Quantum Computing?",
  "style": {
    "bg_color": "#1a1a2e",
    "text_color": "#ffffff",
    "font_size": 48,
    "alignment": "center"
  },
  "transition": {
    "type": "fade",
    "duration_seconds": 0.5
  }
}
```

---

## Asset Loading

### Asset Flow

```
Scene Plan (JSON)
    │
    ▼
Asset Director generates assets
    │
    ├── TTS → assets/narration.mp3
    ├── Images → assets/scene_001.png, scene_002.png, ...
    ├── Videos → assets/scene_003.mp4, ...
    ├── Music → assets/bgmusic.mp3
    └── Diagrams → assets/diagram_001.svg, ...
    │
    ▼
Edit Director creates edit_decisions with asset paths
    │
    ▼
Compose Director passes asset paths to render runtime
    │
    ▼
Render runtime loads assets from filesystem
```

### Asset Path Resolution

All asset paths in `edit_decisions` are **relative to the project directory**:
```
projects/<project_name>/
├── assets/
│   ├── narration.mp3
│   ├── bgmusic.mp3
│   ├── scene_001.png
│   ├── scene_002.png
│   └── scene_003.mp4
├── artifacts/
│   ├── research_brief.json
│   ├── proposal_packet.json
│   ├── script.json
│   ├── scene_plan.json
│   └── edit_decisions.json
└── renders/
    └── output.mp4
```

---

## Export Process

### Final Output Pipeline

```
Render Runtime
    │
    ├── Remotion: npx remotion render → output.mp4
    ├── HyperFrames: npx hyperframes render → output.mp4
    └── FFmpeg: ffmpeg concat+mux → output.mp4
    │
    ▼
Final Review (compose-director)
    │
    ├── Technical validation (duration, resolution, codec)
    ├── Transcript comparison (narration vs script)
    ├── A/V sync check (audio duration vs video duration)
    └── Quality score (scoring.py)
    │
    ▼
Render Report
    │
    ├── output_path: renders/output.mp4
    ├── duration_seconds: 60.5
    ├── file_size_mb: 45.2
    ├── resolution: 1920x1080
    ├── fps: 30
    ├── codec: h264
    └── final_review: { passed: true, issues: [] }
    │
    ▼
Publish Director
    │
    ├── SEO metadata (title, description, tags)
    ├── Chapter markers
    ├── Thumbnail concept
    └── Export package structure
```

### Target Profiles (from `lib/media_profiles.py`)

| Profile | Resolution | FPS | Codec | Bitrate | Use Case |
|---------|------------|-----|-------|---------|----------|
| `youtube_1080p` | 1920×1080 | 30 | h264 | 8 Mbps | YouTube upload |
| `youtube_4k` | 3840×2160 | 30 | h264 | 35 Mbps | YouTube 4K |
| `tiktok_vertical` | 1080×1920 | 30 | h264 | 6 Mbps | TikTok/Reels |
| `instagram_square` | 1080×1080 | 30 | h264 | 5 Mbps | Instagram feed |
| `twitter_video` | 1280×720 | 30 | h264 | 5 Mbps | Twitter/X |
| `linkedin_video` | 1920×1080 | 30 | h264 | 8 Mbps | LinkedIn |

---

## Key Observations

1. **Remotion is the primary runtime** — most capable, handles all scene types
2. **HyperFrames is specialized** — best for kinetic typography and product promos
3. **FFmpeg is the fallback** — simple but reliable for basic concat/mux operations
4. **Runtime is locked at proposal** — cannot be changed mid-pipeline
5. **Subtitle handling is split** — Remotion burns via React components, FFmpeg burns via ASS filter
6. **Audio mixing is consistent** — same `audio_mixer.py` tool across all runtimes
7. **Asset loading is filesystem-based** — no streaming or CDN integration