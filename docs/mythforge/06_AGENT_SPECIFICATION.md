# MythForge AI — Agent Specification

## Overview

MythForge AI defines 11 specialized agents that each handle one stage of the video production pipeline. Every agent inherits from the OpenMontage `BaseAgent` interface and uses existing OpenMontage tools for provider interaction. No agent contains business logic — each agent is a prompt-driven orchestrator that transforms inputs into outputs using AI providers.

---

## Agent Inheritance Model

```
BaseAgent (OpenMontage)
    │
    └── MythForgeAgent (MythForge base)
            │
            ├── MythForgeResearcher
            ├── MythForgeScriptWriter
            ├── MythForgeSceneDirector
            ├── MythForgePromptAgent
            ├── MythForgeImageAgent
            ├── MythForgeNarrator
            ├── MythForgeMusicAgent
            ├── MythForgeSfxAgent
            ├── MythForgeRenderer
            ├── MythForgeQA
            └── MythForgePublisher
```

---

## Agent 1: MythForge Researcher

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_researcher` |
| Pipeline Stage | `research` (Stage 1) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Parse the video title to extract mythology topic, character names, and cultural origin
- Search the local Knowledge Base for matching entries (characters, kingdoms, stories)
- If Knowledge Base coverage is insufficient, perform web research using search tools
- Synthesize all findings into a structured Research Brief
- Identify the story arc (Setup, Conflict, Resolution)
- Flag cultural sensitivities, content warnings, and pronunciation notes
- Cross-reference multiple sources for accuracy

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Video title | User input | String |
| Knowledge base | `mythforge/knowledge/` | JSON files |
| Web search results | Google Custom Search API | Search result snippets |
| Active playbook | `mythforge/playbooks/` | YAML |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Research Brief | `artifacts/research.json` | JSON |
| Knowledge Base matches | Embedded in Research Brief | JSON |
| Cultural flags | Embedded in Research Brief | JSON |
| Pronunciation guide | Embedded in Research Brief | JSON |

### Prompt Template

- File: `mythforge/prompts/research.md`
- System role: Expert mythology researcher and cultural consultant
- Temperature: 0.3 (low — accuracy matters more than creativity)
- Model: `gpt-4o`

### Dependencies

- OpenMontage tools: `web_search_tool`, `llm_tool`
- MythForge tools: `knowledge_base_tool`
- Providers: ChatGPT, Google Custom Search

### Extension Notes

- Can be extended by adding new Knowledge Base domains (e.g., Norse, Greek)
- Can be extended by adding new web search sources
- Core research logic should remain untouched
- Prompt template is the primary customization point

---

## Agent 2: MythForge Script Writer

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_scriptwriter` |
| Pipeline Stage | `script` (Stage 2) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Transform the Research Brief into a cinematic narration script
- Write in documentary storytelling style (authoritative, dramatic, respectful)
- Structure the narrative as three acts with clear scene breaks
- Write character dialogue in first person where appropriate
- Weave in cultural elements: proverbs, idioms, cultural references from the mythology's tradition
- Target 1,500-2,250 words (10-15 minutes at ~150 words/minute)
- Ensure the story has proper pacing: rising tension, climax, resolution

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Research Brief | `artifacts/research.json` | JSON |
| Character data | Knowledge Base | JSON |
| Style guide | Active playbook | YAML |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Script document | `artifacts/script.json` | JSON |
| Word count estimate | Embedded in script | Integer |
| Duration estimate | Embedded in script | Float (seconds) |

### Prompt Template

- File: `mythforge/prompts/script.md`
- System role: Master storyteller and mythology scholar
- Temperature: 0.8 (high — creativity and narrative flair)
- Model: `gpt-4o`

### Dependencies

- OpenMontage tools: `llm_tool`
- MythForge tools: `knowledge_base_tool` (for character details)
- Providers: ChatGPT

### Extension Notes

- Script style is defined by the prompt template — changing the template changes the voice
- Cultural notes from the Research Brief guide the writing style
- The three-act structure is a guideline, not a rigid constraint
- Prompt template is the primary customization point

---

## Agent 3: MythForge Scene Director

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_scene_director` |
| Pipeline Stage | `scene_director` (Stage 3) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Break the script into individual scenes with visual direction
- Define scene types: narration, action, transition, title card, outro
- Specify camera movement for Ken Burns effect (zoom in/out, pan left/right)
- Define text overlays and subtitle timing
- Specify transitions between scenes (cross-dissolve, fade-to-black, wipe)
- Ensure visual variety: no two consecutive scenes with similar composition
- Assign mood tags to each scene for music and SFX selection
- Calculate scene durations based on narration word count

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Script document | `artifacts/script.json` | JSON |
| Research Brief | `artifacts/research.json` | JSON |
| Scene templates | `mythforge/knowledge/scenes/` | JSON |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Scene plan | `artifacts/scenes.json` | JSON |
| Scene count | Embedded in scenes | Integer |
| Total duration | Embedded in scenes | Float (seconds) |

### Prompt Template

- File: `mythforge/prompts/scene_director.md`
- System role: Cinematographer and visual storytelling director
- Temperature: 0.6 (moderate — visual creativity with structure)
- Model: `gpt-4o`

### Dependencies

- OpenMontage tools: `llm_tool`
- MythForge tools: `knowledge_base_tool`
- Providers: ChatGPT

### Extension Notes

- Scene templates define reusable visual patterns
- New scene types can be added by extending the scene template library
- Camera movement patterns can be customized per art style
- Transition types are extensible through the rendering system

---

## Agent 4: MythForge Prompt Agent

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_prompt_agent` |
| Pipeline Stage | `prompt_engineering` (Stage 4) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Transform scene descriptions into optimized image generation prompts
- Inject character visual identity from the Character Bible into every prompt containing characters
- Apply the active art style from the Playbook (style anchor sentence)
- Include negative prompts to prevent common generation failures
- Ensure cultural accuracy in visual descriptions (skin tone, clothing, architecture, environment)
- Generate the "style anchor" — a consistent style sentence that appears in every prompt for visual coherence
- Reference specific visual attributes from the Character Bible (not generic descriptions)

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene plan | `artifacts/scenes.json` | JSON |
| Research Brief | `artifacts/research.json` | JSON |
| Character Bible | `mythforge/knowledge/characters/` | JSON files |
| Active Playbook | `mythforge/playbooks/` | YAML |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Image prompts | `artifacts/prompts.json` | JSON |
| Style anchor | Embedded in prompts | String |
| Negative prompts | Embedded in prompts | String per scene |

### Prompt Template

- File: `mythforge/prompts/image_prompt.md`
- System role: Expert AI image prompt engineer specializing in cinematic mythology
- Temperature: 0.5 (moderate — precision with creative flair)
- Model: `gpt-4o-mini` (cost-efficient for structured prompt generation)

### Dependencies

- OpenMontage tools: `llm_tool`
- MythForge tools: `knowledge_base_tool`, `character_bible_tool`
- Providers: ChatGPT

### Extension Notes

- Playbooks define the visual style — adding a new playbook changes the entire aesthetic
- Character Bible entries define character appearance — updating entries changes character visuals
- Negative prompts can be customized per mythology or art style
- This agent is the most critical for visual quality — prompt templates should be carefully maintained

---

## Agent 5: MythForge Image Agent

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_image_agent` |
| Pipeline Stage | `image_generation` (Stage 5) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Generate one image per scene using the prepared prompts
- Submit prompts to Gemini Image API (or fallback provider)
- Validate generated images: no blank frames, no text artifacts, no obvious errors
- Store images with consistent naming convention
- Log generation cost per image
- If an image fails quality validation, regenerate with the same prompt (up to 3 retries)
- If quality validation continues to fail, adjust prompt slightly and retry (up to 2 retries)
- Check asset cache before generating (cache hit = skip generation)

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Image prompts | `artifacts/prompts.json` | JSON |
| Asset cache | `mythforge/cache/images/` | Cached files |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Scene images | `assets/images/{project_id}_scene_{id}.png` | PNG files |
| Generation log | `artifacts/image_generation_log.json` | JSON |

### Prompt Template

- File: `mythforge/prompts/image_quality_check.md`
- System role: Image quality assessor
- Temperature: 0.1 (low — objective quality assessment)
- Model: `gpt-4o-mini`

### Dependencies

- OpenMontage tools: `image_generation_tool`, `file_tool`
- MythForge tools: `asset_cache_tool`
- Providers: Gemini Image API (primary), Replicate (fallback)

### Extension Notes

- Image quality validation thresholds can be adjusted
- New image providers can be added through the provider abstraction
- Cache behavior is configurable (TTL, max size)
- Retry logic and prompt adjustment strategy can be tuned

---

## Agent 6: MythForge Narrator

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_narrator` |
| Pipeline Stage | `narration` (Stage 6) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Generate narration audio for each scene using the narration text from the scene plan
- Apply correct pronunciation for mythology-specific names using the pronunciation guide
- Use SSML phoneme tags for names that have non-obvious pronunciation
- Normalize audio levels to -14 LUFS (broadcast standard)
- Generate appropriate silence gaps between scenes (0.5-1.5 seconds)
- Concatenate individual scene narrations into a single continuous narration track
- Check asset cache before generating

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene plan | `artifacts/scenes.json` | JSON |
| Pronunciation guide | `artifacts/research.json` | JSON |
| Voice configuration | `config/providers/elevenlabs.yaml` | YAML |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Scene narration files | `assets/narration/{project_id}_scene_{id}_narration.mp3` | MP3 |
| Full narration track | `assets/narration/{project_id}_narration_full.mp3` | MP3 |
| Narration log | `artifacts/narration_log.json` | JSON |

### Prompt Template

- No LLM prompt needed — this agent uses TTS API directly
- SSML template: `mythforge/prompts/narration_ssml.md`

### Dependencies

- OpenMontage tools: `tts_tool`, `audio_tool`, `file_tool`
- MythForge tools: `asset_cache_tool`
- Providers: ElevenLabs (primary), OpenAI TTS (fallback), Edge TTS (fallback)

### Extension Notes

- Voice selection is configurable (different voices for different mythologies)
- SSML templates can be customized per language or cultural origin
- Audio normalization settings are tunable
- New TTS providers can be added through the provider abstraction

---

## Agent 7: MythForge Music Agent

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_music_agent` |
| Pipeline Stage | `music` (Stage 7) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Analyze scene moods from the scene plan to determine music requirements
- Identify the cultural origin of the mythology from the Research Brief
- Search the local music library for tracks matching cultural origin + mood
- If multiple mood transitions exist, create a playlist or select a track with appropriate dynamics
- Ensure the selected music duration covers the full video length
- Apply fade-in at the start (2-3 seconds) and fade-out at the end (3-5 seconds)
- If no local track matches, flag for future AI music generation

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene plan | `artifacts/scenes.json` | JSON |
| Research Brief | `artifacts/research.json` | JSON |
| Music library | `assets/music/` | MP3/WAV files |
| Music index | `assets/music/index.json` | JSON |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Music track | `assets/music/{project_id}_music_track.mp3` | MP3 |
| Music selection log | `artifacts/music_log.json` | JSON |

### Prompt Template

- File: `mythforge/prompts/music_selection.md`
- System role: Music supervisor for cinematic mythology
- Temperature: 0.3 (low — music selection is precise)
- Model: `gpt-4o-mini`

### Dependencies

- OpenMontage tools: `audio_tool`, `file_tool`
- MythForge tools: `music_library_tool`
- Providers: Local Asset Cache (V1), ElevenLabs Music (future)

### Extension Notes

- Music library is extensible by adding categorized tracks
- Music selection algorithm can be tuned (mood matching, cultural matching)
- AI music generation will be added when provider becomes available
- Music categories and mood tags are configurable

---

## Agent 8: MythForge SFX Agent

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_sfx_agent` |
| Pipeline Stage | `sfx` (Stage 8) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Analyze each scene for appropriate sound effects
- Identify SFX requirements from scene descriptions (ambient, impact, transition, environmental)
- Search the local SFX library for matching effects
- If local library lacks a needed effect, generate it using ElevenLabs SFX API
- Layer SFX with appropriate volume levels relative to narration (-20 LUFS under narration, -14 LUFS during pauses)
- Produce a combined SFX track synchronized to scene timing
- Check asset cache before generating

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene plan | `artifacts/scenes.json` | JSON |
| Research Brief | `artifacts/research.json` | JSON |
| SFX library | `assets/sfx/` | WAV files |
| SFX index | `assets/sfx/index.json` | JSON |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Individual SFX files | `assets/sfx/{project_id}_sfx_{name}.wav` | WAV |
| Combined SFX track | `assets/sfx/{project_id}_sfx_track.wav` | WAV |
| SFX log | `artifacts/sfx_log.json` | JSON |

### Prompt Template

- File: `mythforge/prompts/sfx_selection.md`
- System role: Sound designer for cinematic mythology
- Temperature: 0.3 (low — precise sound design)
- Model: `gpt-4o-mini`

### Dependencies

- OpenMontage tools: `audio_tool`, `file_tool`
- MythForge tools: `sfx_library_tool`, `asset_cache_tool`
- Providers: ElevenLabs SFX (primary), Local Cache (fallback)

### Extension Notes

- SFX library is extensible by adding categorized effects
- SFX volume mixing rules are configurable per scene type
- New SFX providers can be added through the provider abstraction
- Ambient sound layering can be customized per mythology setting

---

## Agent 9: MythForge Renderer

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_renderer` |
| Pipeline Stage | `rendering` (Stage 9) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Compose all generated assets into a timeline-based video
- Build a Remotion timeline JSON from the scene plan
- Apply Ken Burns effect (slow pan/zoom) to all static images
- Render transitions between scenes (cross-dissolve, fade-to-black, wipe)
- Overlay subtitles synchronized with narration
- Mix audio tracks: narration (primary) + music (background) + SFX (accent)
- Add title card at opening and credits at closing
- Encode final output to H.264 MP4 at 1920x1080, 30fps
- Normalize final audio to -14 LUFS
- If Remotion fails, fall back to FFmpeg-based rendering
- Generate SRT subtitle file alongside the video

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Scene plan | `artifacts/scenes.json` | JSON |
| Scene images | `assets/images/` | PNG files |
| Narration audio | `assets/narration/` | MP3 files |
| Music track | `assets/music/` | MP3 file |
| SFX track | `assets/sfx/` | WAV file |
| Playbook | `mythforge/playbooks/` | YAML |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Final video | `output/{project_id}_final.mp4` | MP4/H.264 |
| Subtitles | `output/{project_id}_subtitles.srt` | SRT |
| Render log | `artifacts/render_log.json` | JSON |

### Prompt Template

- No LLM prompt needed — this agent orchestrates rendering tools
- Remotion timeline template: `extensions/remotion/src/`

### Dependencies

- OpenMontage tools: `remotion_tool`, `ffmpeg_tool`, `audio_tool`, `file_tool`
- MythForge tools: None (uses OpenMontage rendering directly)
- Providers: Remotion (primary), FFmpeg (fallback)

### Extension Notes

- Ken Burns movement patterns are configurable per scene type
- Transition types are extensible through the Remotion composition
- Subtitle styling (font, size, color, position) is configurable
- New rendering backends can be added (e.g., After Effects automation)
- Resolution and codec settings are configurable per output target

---

## Agent 10: MythForge QA

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_qa` |
| Pipeline Stage | `qa` (Stage 10) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Validate the final video against all quality gates
- Check technical specifications: resolution (1920x1080), fps (30), codec (H.264), audio levels (-14 LUFS)
- Check for visual issues: blank frames, duplicate frames, text artifacts
- Verify narration-to-scene synchronization (within 2-second tolerance)
- Validate subtitle accuracy against narration text
- Check cultural accuracy against Research Brief notes
- Generate a quality score (0-100)
- Recommend action: PASS (proceed), REVISE (fix specific issues), FAIL (re-render)
- Track and report total production cost

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Final video | `output/{project_id}_final.mp4` | MP4 |
| All artifacts | `artifacts/` | JSON files |
| Quality gates | `config/quality_gates.yaml` | YAML |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| QA report | `artifacts/qa_report.json` | JSON |
| Quality score | Embedded in report | Integer (0-100) |
| Recommendation | Embedded in report | String (PASS/REVISE/FAIL) |
| Cost report | Embedded in report | JSON |

### Prompt Template

- File: `mythforge/prompts/qa.md`
- System role: Quality assurance engineer for cinematic video production
- Temperature: 0.1 (low — objective analysis)
- Model: `gpt-4o-mini`

### Dependencies

- OpenMontage tools: `video_analysis_tool`, `audio_analysis_tool`, `llm_tool`, `file_tool`
- MythForge tools: `budget_tracker_tool`
- Providers: ChatGPT (analysis), FFprobe (technical validation)

### Extension Notes

- Quality gate thresholds are configurable
- New quality checks can be added (e.g., cultural review by specific criteria)
- Scoring algorithm can be weighted per gate
- The QA agent can be configured to auto-fix certain issues (e.g., re-normalize audio)

---

## Agent 11: MythForge Publisher

| Property | Value |
|----------|-------|
| Agent ID | `mythforge_publisher` |
| Pipeline Stage | `thumbnail_metadata` (Stage 11) |
| Inherits | `MythForgeAgent` |

### Responsibilities

- Generate a YouTube-optimized thumbnail image (1280x720, bold, dramatic)
- Write SEO-optimized video title (60-70 characters)
- Write video description (200-500 words with timestamps and context)
- Generate 15-30 tags for YouTube SEO
- Generate video chapter timestamps
- Create a production report summarizing the entire pipeline run (costs, timing, quality)
- Package all final deliverables into the output directory

### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Research Brief | `artifacts/research.json` | JSON |
| Script document | `artifacts/script.json` | JSON |
| QA report | `artifacts/qa_report.json` | JSON |
| Primary character image | `assets/images/` | PNG |

### Outputs

| Output | Destination | Format |
|--------|-------------|--------|
| Thumbnail | `output/{project_id}_thumbnail.png` | PNG |
| Metadata | `output/{project_id}_metadata.json` | JSON |
| Production report | `output/{project_id}_production_report.json` | JSON |

### Prompt Template

- File: `mythforge/prompts/thumbnail.md` — Thumbnail concept generation
- File: `mythforge/prompts/metadata.md` — SEO metadata generation
- System role: YouTube content strategist and SEO specialist
- Temperature: 0.5 (moderate — creative titles with SEO discipline)
- Model: `gpt-4o-mini`

### Dependencies

- OpenMontage tools: `image_generation_tool`, `llm_tool`, `file_tool`
- MythForge tools: None additional
- Providers: Gemini Image API (thumbnail), ChatGPT (metadata)

### Extension Notes

- Thumbnail style is configurable (text-heavy vs. image-focused)
- Metadata templates can be customized per platform (YouTube, TikTok, etc.)
- Production report format can be extended with new metrics
- Platform publishing (upload) will be added in V1.1

---

## Agent Summary Table

| Agent | Stage | LLM Model | Image Provider | Audio Provider | Complexity |
|-------|-------|-----------|---------------|----------------|-----------|
| Researcher | S1 | gpt-4o | — | — | Medium |
| Script Writer | S2 | gpt-4o | — | — | High |
| Scene Director | S3 | gpt-4o | — | — | Medium |
| Prompt Agent | S4 | gpt-4o-mini | — | — | Medium |
| Image Agent | S5 | gpt-4o-mini | Gemini | — | High |
| Narrator | S6 | — | — | ElevenLabs | Medium |
| Music Agent | S7 | gpt-4o-mini | — | Local | Low |
| SFX Agent | S8 | gpt-4o-mini | — | ElevenLabs | Medium |
| Renderer | S9 | — | — | — | High |
| QA | S10 | gpt-4o-mini | — | — | Medium |
| Publisher | S11 | gpt-4o-mini | Gemini | — | Low |

---

## Agent Extension Principles

1. **Prompt over code**: Every agent's behavior is primarily defined by its prompt template. Changing the prompt changes the agent's output without changing code.

2. **Tool delegation**: Agents never call APIs directly. They use OpenMontage tools, which use providers. This keeps agents provider-agnostic.

3. **Idempotent by design**: Every agent can be re-run safely. Re-running produces the same output (given the same inputs and provider state).

4. **Cache-aware**: Every agent that generates expensive assets (images, audio) checks the cache first.

5. **Fail-safe**: Every agent saves its output as an artifact before reporting success. If the agent crashes after generating but before saving, the checkpoint system catches the inconsistency.