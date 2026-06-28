# OpenMontage — Execution Flow

## Overview

OpenMontage does not follow a traditional programmatic execution model. There is no single `main()` function or CLI command that runs the entire pipeline. Instead, the system is orchestrated by an **AI agent** (e.g., Cursor, Claude, GPT) that reads skill documents, follows pipeline definitions, and invokes tools programmatically.

## High-Level Execution Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER                                                               │
│  "Make me a 60-second explainer about quantum computing"            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: AGENT INITIALIZATION                                       │
│  ─────────────────────────────                                      │
│  • Agent reads AGENT_GUIDE.md (Layer 1 instructions)                │
│  • Agent reads PROJECT_CONTEXT.md (Layer 2 philosophy)              │
│  • Agent loads .env via base_tool._load_dotenv()                    │
│  • Agent runs make preflight → tool_registry.discover()             │
│  • Agent presents Provider Menu to user                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: PIPELINE SELECTION                                         │
│  ────────────────────────────                                       │
│  • Agent reads pipeline_defs/*.yaml to find matching pipeline       │
│  • Example: animated-explainer.yaml matches "explainer" request     │
│  • Agent loads required_skills from pipeline YAML                   │
│  • Agent selects a playbook (e.g., clean-professional.json)         │
│  • Agent initializes EP_STATE (cumulative state object)             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: EXECUTIVE PRODUCER MODE (EP)                               │
│  ──────────────────────────────────────                             │
│  • Agent enters Executive Producer role (skill-driven)              │
│  • EP orchestrates stages serially with review gates                │
│  • EP maintains cumulative state across all stages                  │
│  • EP enforces budget, style consistency, A/V sync                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│ PRE-PROD     │  │ PRODUCTION   │  │ POST-PRODUCTION      │
│ ──────────── │  │ ──────────── │  │ ──────────────────── │
│ 1. Research  │  │ 3. Script    │  │ 6. Edit Decisions    │
│ 2. Proposal  │  │ 4. Scene Plan│  │ 7. Compose/Render    │
│    (APPROVAL │  │ 5. Assets    │  │ 8. Publish           │
│     GATE)    │  │              │  │                      │
└──────────────┘  └──────────────┘  └──────────────────────┘
```

## Detailed Stage-by-Stage Flow

### Stage 1: Research (Zero Cost)

```
Input:  User topic/idea
Agent:  research-director skill
Process:
  • Web search for existing content landscape
  • Gather data points, statistics, sources
  • Identify audience questions from forums
  • Discover 3+ unique angles
Output: research_brief (JSON)
Cost:   $0.00
Tools:  None (agent reasoning only)
```

### Stage 2: Proposal (Zero Cost, Approval Gate)

```
Input:  research_brief
Agent:  proposal-director skill
Process:
  • Generate 3+ concept options with different structures/hooks
  • Each concept includes: title, hook, structure, duration target
  • Create production plan with tool selections and cost estimates
  • Present quality/cost tradeoffs
  • SELECT PLAYBOOK (visual style)
  • SELECT RENDER RUNTIME (remotion | hyperframes | ffmpeg)
Output: proposal_packet (JSON), decision_log
Cost:   $0.00
Tools:  None (agent reasoning only)
Gate:   HUMAN APPROVAL REQUIRED — pipeline cannot proceed without approval
```

**Critical Decision Point**: The proposal stage locks:
- `render_runtime` (remotion | hyperframes | ffmpeg) — cannot be silently swapped later
- `renderer_family` (explainer-data, cinematic-trailer, presenter, etc.)
- `playbook` (visual style constraints)
- `budget` (approved spend cap)

### Stage 3: Script (Zero Cost)

```
Input:  proposal_packet, research_brief
Agent:  script-director skill
Process:
  • Write narration script matching selected concept
  • Target word count from duration (e.g., 150 words/min)
  • Add enhancement_cues (visual direction markers) every 8-10 seconds
  • Include speaker directions for TTS
  • Incorporate research data points
Output: script (JSON with sections, enhancement_cues)
Cost:   $0.00
Tools:  None (agent reasoning only)
```

### Stage 4: Scene Plan (Zero Cost)

```
Input:  script, proposal_packet
Agent:  scene-director skill
Process:
  • Map script sections to visual scenes
  • Assign scene types (text_card, stat_card, image, video, chart, etc.)
  • Define required_assets per scene
  • Ensure visual variety (no 3+ consecutive same-type scenes)
  • Verify asset feasibility against production plan
Output: scene_plan (JSON with scenes[], required_assets)
Cost:   $0.00
Tools:  None (agent reasoning only)
```

### Stage 5: Assets (Cost-Bearing)

```
Input:  scene_plan, script, proposal_packet
Agent:  asset-director skill
Process:
  • Generate narration audio (TTS)
  • Generate/source images for each scene
  • Generate/source video clips
  • Generate diagrams, code snippets, math animations
  • Generate background music
  • Track cumulative cost against approved budget
Output: asset_manifest (JSON with file paths, metadata)
Cost:   Varies ($0.10 - $5.00+)
Tools:
  ├── tts_selector → elevenlabs_tts | google_tts | openai_tts | piper_tts | doubao_tts
  ├── image_selector → flux_image | google_imagen | grok_image | openai_image | recraft_image | pexels_image | pixabay_image | local_diffusion
  ├── video_selector → veo_video | kling_video | runway_video | seedance_video | heygen_video | grok_video | minimax_video | pexels_video | pixabay_video | hunyuan_video | cogvideo_video | wan_video | ltx_video_local | ltx_video_modal
  ├── diagram_gen
  ├── code_snippet
  ├── math_animate
  └── music_gen → suno_music | freesound_music | pixabay_music
```

### Stage 6: Edit Decisions (Zero Cost)

```
Input:  scene_plan, asset_manifest
Agent:  edit-director skill
Process:
  • Create timeline with cuts referencing asset files
  • Define in/out seconds for each cut
  • Configure subtitle styling (from playbook)
  • Set music ducking parameters
  • Verify no timeline gaps or overlaps
  • Lock render_runtime (carried from proposal)
Output: edit_decisions (JSON with cuts[], subtitles, music_config)
Cost:   $0.00
Tools:  None (agent reasoning only)
```

### Stage 7: Compose/Render (Zero Cost, CPU-Intensive)

```
Input:  edit_decisions, asset_manifest, audio
Agent:  compose-director skill
Process:
  • Route to correct runtime based on edit_decisions.render_runtime
  • Remotion path:
    ├── Generate scene JSON props from edit_decisions
    ├── npx remotion render src/index.tsx Explainer output.mp4 --props=...
    ├── Handles: text cards, stat cards, charts, animations, transitions
    └── Word-level caption burn
  • HyperFrames path:
    ├── Generate HTML/GSAP composition
    ├── npx hyperframes render composition.html output.mp4
    ├── Handles: kinetic typography, product promos, website-to-video
    └── GSAP animations
  • FFmpeg path:
    ├── Trim and concat video segments
    ├── Burn subtitles (ASS format)
    ├── Mux audio (narration + music)
    └── Encode to target profile
  • Run final_review (technical validation + transcript comparison)
Output: render_report (JSON with output paths, duration, file size)
Cost:   $0.00 (compute only)
Tools:
  ├── video_compose (orchestrator)
  ├── hyperframes_compose (alternative runtime)
  ├── audio_mixer
  └── video_stitch
```

### Stage 8: Publish (Zero Cost)

```
Input:  render_report, final_review
Agent:  publish-director skill
Process:
  • Generate SEO metadata (title, description, tags)
  • Create chapter markers
  • Structure export package
  • Generate thumbnail concept
Output: publish_log (JSON with metadata, export paths)
Cost:   $0.00
Tools:  None (agent reasoning only)
```

## Data Flow Diagram

```
User Input (topic/idea)
    │
    ▼
┌─────────┐     ┌──────────────┐     ┌──────────────┐
│research  │────▶│  research_   │────▶│   proposal_  │
│  brief   │     │    brief     │     │    packet    │
└─────────┘     └──────────────┘     └──────┬───────┘
                                            │
                                     APPROVAL GATE
                                            │
                                            ▼
┌─────────┐     ┌──────────────┐     ┌──────────────┐
│  script  │────▶│  scene_plan  │────▶│    asset_    │
│          │     │              │     │   manifest   │
└─────────┘     └──────────────┘     └──────┬───────┘
                                            │
                              ┌──────────────┼──────────────┐
                              ▼              ▼              ▼
                         TTS audio     Images/Video     Music
                              │              │              │
                              └──────────────┼──────────────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │    edit_     │
                                    │  decisions   │
                                    └──────┬───────┘
                                           │
                              ┌────────────┼────────────────┐
                              ▼            ▼                ▼
                          Remotion     HyperFrames       FFmpeg
                              │            │                │
                              └────────────┼────────────────┘
                                           │
                                           ▼
                                   ┌──────────────┐
                                   │ render_report │
                                   └──────┬───────┘
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │  publish_log  │
                                   └──────────────┘
```

## Artifact Schema Chain

Each stage produces a validated artifact that feeds the next stage:

```
research_brief ──▶ proposal_packet ──▶ script ──▶ scene_plan ──▶ asset_manifest ──▶ edit_decisions ──▶ render_report ──▶ publish_log
```

All artifacts are validated against JSON schemas in `schemas/` before proceeding.

## Checkpoint & Resume

Pipeline state is persisted to `pipeline/` directory after each stage:
- `checkpoint_policy: guided` — agent asks user before skipping/redoing stages
- `checkpoint_policy: manual_all` — requires explicit user approval for every stage
- `checkpoint_policy: auto_noncreative` — auto-checkpoints non-creative stages

On restart, the agent reads checkpoint state and can resume from any completed stage.

## Budget Tracking Flow

```
proposal_packet.approval.approved_budget_usd
    │
    ▼
cost_tracker.py
    │
    ├── Track per-tool cost via ToolResult.cost_usd
    ├── Cumulative spend in EP_STATE.budget_spent_usd
    ├── Remaining = approved - spent
    └── Config: budget.mode = observe | warn | cap
        ├── observe: log costs, no enforcement
        ├── warn: alert when approaching limit
        └── cap: halt when limit reached (requires approval)