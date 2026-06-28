# OpenMontage — Extension Points

## Overview

OpenMontage is **designed for extension**. The architecture separates concerns into layers (tools, skills, pipelines, playbooks) that can each be independently extended without modifying core framework code. This document identifies every safe extension point and the recommended approach for each.

---

## Extension Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  EXTENSION LAYER          HOW TO EXTEND                     │
├─────────────────────────────────────────────────────────────┤
│  Custom Pipelines         Add YAML in pipeline_defs/        │
│  Custom Agents            Add Markdown in skills/            │
│  Custom Tools             Add Python in tools/               │
│  Custom Playbooks         Add JSON in playbooks/              │
│  Custom Schemas           Add JSON in schemas/                │
│  Custom Remotion Scenes   Add TSX in remotion-composer/src/   │
│  Knowledge Base           Add files in knowledge/             │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Custom Pipelines

**Location**: `pipeline_defs/`
**Method**: Create a new YAML file
**Risk**: LOW

### How to Add

1. Create `pipeline_defs/my-custom-pipeline.yaml`
2. Define stages, required skills, tools, and schemas
3. Reference existing or new skills
4. No code changes required — YAML is parsed by `lib/pipeline.py`

### Example Structure

```yaml
name: mythforge-reaction
description: "Reaction video pipeline"
stages:
  - name: source_analysis
    skill: source-analyst
    required_skills:
      - skills/pipelines/reaction/source-analyst.md
    required_tools:
      - transcriber
      - scene_detect
    schema: schemas/source_analysis.json
  - name: reaction_script
    skill: reaction-writer
    # ... additional stages
```

### What's Safe
- Adding new pipeline YAML files
- Referencing existing tools and skills
- Defining new artifact schemas

### What's Dangerous
- Modifying existing pipeline YAML files (breaks running productions)
- Changing stage ordering (breaks data dependencies)

---

## 2. Custom Agents (Skills)

**Location**: `skills/`
**Method**: Create a new Markdown file
**Risk**: LOW

### How to Add

1. Create a Markdown file in the appropriate `skills/` subdirectory
2. Define responsibilities, inputs, outputs, guidelines, quality checklists
3. Reference the skill in a pipeline YAML definition
4. The AI agent will load and follow the new skill automatically

### Extension Categories

| Category | Directory | Purpose |
|----------|-----------|---------|
| Pipeline Skills | `skills/pipelines/<name>/` | Stage-specific directors |
| Meta Skills | `skills/meta/` | Cross-cutting capabilities |
| Core Skills | `skills/core/` | Fundamental agent behaviors |

### What's Safe
- Adding new skill files
- Extending existing skills with additional guidelines
- Creating new pipeline-specific skill sets

### What's Dangerous
- Modifying `AGENT_GUIDE.md` (changes all agent behavior)
- Removing existing skills (breaks pipelines that reference them)
- Changing skill file names (breaks pipeline YAML references)

---

## 3. Knowledge Base

**Location**: `knowledge/`
**Method**: Add Markdown or text files
**Risk**: LOW

### How to Add

1. Create files in `knowledge/` directory
2. The agent loads knowledge files when skills reference them
3. Knowledge can include domain expertise, style guides, brand guidelines

### Recommended Knowledge Additions for MythForge AI

| Knowledge Type | File | Purpose |
|----------------|------|---------|
| Character Bible | `knowledge/characters.md` | Recurring character definitions |
| Brand Guidelines | `knowledge/brand-guide.md` | Visual and tonal consistency |
| Topic Database | `knowledge/topics.md` | Content ideas and research |
| Audience Profiles | `knowledge/audiences.md` | Target audience definitions |
| SEO Templates | `knowledge/seo-templates.md` | Title/description patterns |
| Quality Standards | `knowledge/quality-standards.md` | Acceptance criteria |

### What's Safe
- Adding any knowledge files
- Updating knowledge as domain expertise grows

### What's Dangerous
- Overloading knowledge with too much content (context window limits)
- Contradictory knowledge entries

---

## 4. Character Bible

**Location**: `knowledge/characters/`
**Method**: Add character definition files
**Risk**: LOW

### Recommended Structure

```
knowledge/characters/
├── main-narrator.md        # Primary voice/personality
├── expert-analyst.md       # Technical explainer character
├── social-host.md          # Social media host character
└── templates/
    └── character-template.md
```

### Character Definition Format

```markdown
# Character: Main Narrator

## Voice
- Tone: Warm, authoritative, curious
- Pace: Medium, measured
- Vocabulary: Accessible but intelligent

## Visual Style
- Primary colors: ...
- Typography: ...
- Motion style: ...

## Content Guidelines
- Always explain "why" not just "what"
- Use analogies from everyday life
- Include one surprising fact per segment
```

---

## 5. Gemini Image API Integration

**Location**: `tools/graphics/gemini_image.py`
**Method**: Create new tool file extending `BaseTool`
**Risk**: LOW

### Steps

1. Create `tools/graphics/gemini_image.py`
2. Extend `BaseTool` class
3. Implement `run()` method with Gemini API calls
4. Implement `get_info()` with capabilities and cost
5. Add `GEMINI_API_KEY` to `.env.example`
6. Tool is auto-discovered by `tool_registry.py`

### Integration Points
- Reference in `image_selector` tool routing logic
- Add to Provider Menu options
- Update playbook quality budget if needed

---

## 6. ElevenLabs Integration

**Location**: Already exists at `tools/audio/elevenlabs_tts.py`
**Method**: Extend existing tool or add new ElevenLabs features
**Risk**: LOW

### Potential Extensions
- Add voice cloning support
- Add sound effects generation
- Add dubbing/localization support
- Add voice design (create custom voices)

### What's Safe
- Adding new methods to existing tool
- Adding new ElevenLabs-specific tools

---

## 7. YouTube Automation

**Location**: New tool or publish director extension
**Method**: Create `tools/publish/youtube_upload.py` or extend publish-director
**Risk**: MEDIUM

### Potential Components

| Component | Location | Purpose |
|-----------|----------|---------|
| YouTube Upload | `tools/publish/youtube_upload.py` | Upload video via YouTube API |
| YouTube SEO | `tools/publish/youtube_seo.py` | Optimize title/tags/description |
| Thumbnail Generator | `tools/publish/thumbnail_gen.py` | Generate click-worthy thumbnails |
| Playlist Manager | `tools/publish/playlist_manager.py` | Organize videos into playlists |
| Analytics Tracker | `tools/publish/youtube_analytics.py` | Track performance metrics |

### Integration Points
- Extend `publish-director.md` skill with YouTube-specific steps
- Add YouTube API credentials to `.env`
- Create YouTube-specific playbook for thumbnail style

---

## 8. Asset Cache

**Location**: New module `lib/asset_cache.py`
**Method**: Create caching layer for generated assets
**Risk**: MEDIUM

### Recommended Design

```
cache/
├── images/
│   ├── <hash>.png           # Content-addressed storage
│   └── manifest.json        # Cache index
├── audio/
│   ├── <hash>.mp3
│   └── manifest.json
├── video/
│   ├── <hash>.mp4
│   └── manifest.json
└── cache_config.json        # Cache settings (TTL, max size)
```

### Benefits
- Reduce API costs for repeated content
- Faster asset generation for similar topics
- Offline capability for cached assets

### Integration Points
- Wrap existing tool `run()` methods with cache check
- Add cache hit/miss tracking to `cost_tracker.py`
- Add cache management to Makefile

---

## 9. Scene JSON Extensions

**Location**: `schemas/scene_plan.json` and `remotion-composer/src/scenes/`
**Method**: Add new scene types
**Risk**: MEDIUM

### How to Add New Scene Types

1. **Define schema**: Add scene type to `schemas/scene_plan.json`
2. **Create component**: Add React component in `remotion-composer/src/scenes/`
3. **Register component**: Add to scene type mapping in Remotion composition
4. **Update skill**: Add scene type to `scene-director.md` options

### Potential New Scene Types

| Scene Type | Component | Use Case |
|------------|-----------|----------|
| `comparison_scene` | Two-side comparison | Before/after, pros/cons |
| `timeline_scene` | Animated timeline | Historical events, process steps |
| `quote_scene` | Quote display | Testimonials, famous quotes |
| `map_scene` | Animated map | Geographic content |
| `poll_scene` | Interactive poll | Engagement content |
| `countdown_scene` | Countdown timer | Lists, rankings |

---

## 10. Quality Assurance Extensions

**Location**: `lib/scoring.py` and `skills/meta/reviewer.md`
**Method**: Extend scoring criteria and review checklists
**Risk**: LOW

### Potential Extensions

| Extension | Location | Purpose |
|-----------|----------|---------|
| A/B Testing | `lib/ab_test.py` | Compare video variants |
| Audience Feedback | `lib/feedback.py` | Collect and incorporate viewer feedback |
| Brand Compliance | `lib/brand_check.py` | Verify brand guideline adherence |
| Accessibility | `lib/accessibility.py` | Check caption quality, color contrast |
| SEO Scoring | `lib/seo_score.py` | Rate metadata quality |
| Engagement Prediction | `lib/engagement.py` | Predict viewer retention |

---

## Extension Priority Matrix for MythForge AI

| Extension | Impact | Effort | Priority |
|-----------|--------|--------|----------|
| Knowledge Base | HIGH | LOW | **P0** |
| Character Bible | HIGH | LOW | **P0** |
| Custom Pipeline | HIGH | LOW | **P0** |
| ElevenLabs Extension | HIGH | LOW | **P1** |
| Gemini Image API | HIGH | MEDIUM | **P1** |
| Asset Cache | HIGH | MEDIUM | **P1** |
| YouTube Automation | MEDIUM | MEDIUM | **P2** |
| New Scene Types | MEDIUM | HIGH | **P2** |
| Quality Assurance | MEDIUM | MEDIUM | **P2** |
| A/B Testing | LOW | HIGH | **P3** |

---

## Key Observations

1. **Every extension is additive** — no core code modification required
2. **Tools auto-register** — drop a Python file and it's discovered
3. **Skills are pure Markdown** — no code, no compilation, no deployment
4. **Pipelines are declarative** — YAML definitions are the integration contract
5. **Playbooks are independent** — visual style can be changed without touching code
6. **The framework is designed for this** — extension is the primary design goal