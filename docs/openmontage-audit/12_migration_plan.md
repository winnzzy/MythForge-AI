# OpenMontage — Migration Plan: OpenMontage → MythForge AI

## Overview

This document outlines the migration strategy for evolving OpenMontage into MythForge AI. Components are categorized into three tiers: **KEEP** (unchanged), **EXTEND** (designed for customization), and **REPLACE** (should become MythForge-specific).

---

## Decision Framework

Each component was evaluated against these criteria:

| Criterion | KEEP | EXTEND | REPLACE |
|-----------|------|--------|---------|
| Stability | Mature, proven | Functional but needs growth | Inadequate for commercial use |
| Coupling | Standalone | Has extension points | Deeply coupled to OpenMontage identity |
| Reusability | Universally applicable | Adaptable with effort | OpenMontage-specific |
| Quality | Production-ready | Good but improvable | Below commercial standard |

---

## KEEP — Components That Should Remain Unchanged

These components are well-designed, stable, and universally applicable. They should be preserved as-is.

### Core Infrastructure

| Component | File/Directory | Reason to Keep |
|-----------|---------------|----------------|
| **BaseTool** | `tools/base_tool.py` | Clean abstraction, proven pattern |
| **ToolRegistry** | `tools/tool_registry.py` | Auto-discovery works well |
| **Pipeline Loader** | `lib/pipeline.py` | YAML-driven pipeline definitions are elegant |
| **ArtifactManager** | `lib/artifact_manager.py` | Stage handoff mechanism is solid |
| **CostTracker** | `lib/cost_tracker.py` | Budget enforcement is essential |
| **CheckpointManager** | `lib/checkpoint.py` | Pipeline resume capability is critical |

### Tool Ecosystem

| Component | File/Directory | Reason to Keep |
|-----------|---------------|----------------|
| **All TTS Tools** | `tools/audio/*.py` | Multi-provider TTS is a strength |
| **All Image Tools** | `tools/graphics/*.py` | Comprehensive image generation coverage |
| **All Video Tools** | `tools/video/*.py` | Extensive video provider support |
| **All Analysis Tools** | `tools/analysis/*.py` | Transcription, scene detection, video understanding |
| **All Enhancement Tools** | `tools/enhancement/*.py` | Upscale, denoise, face restore, BG remove |
| **All Subtitle Tools** | `tools/subtitle/*.py` | SRT/ASS generation with word-level timing |
| **Audio Mixer** | `tools/audio/audio_mixer.py` | Narration + music ducking is essential |
| **Video Stitch** | `tools/video/video_stitch.py` | FFmpeg-based concat/trim is universal |

### Rendering

| Component | File/Directory | Reason to Keep |
|-----------|---------------|----------------|
| **Remotion Composer** | `remotion-composer/` | Proven video rendering engine |
| **HyperFrames Compose** | `tools/video/hyperframes_compose.py` | Kinetic typography capability |
| **Scene Components** | `remotion-composer/src/scenes/*.tsx` | Reusable scene types |

### Configuration

| Component | File/Directory | Reason to Keep |
|-----------|---------------|----------------|
| **Playbook System** | `playbooks/*.json` | Visual style abstraction is elegant |
| **Schema Validation** | `schemas/*.json` | Artifact contracts are essential |
| **Media Profiles** | `lib/media_profiles.py` | Output format definitions are universal |

### Documentation

| Component | File/Directory | Reason to Keep |
|-----------|---------------|----------------|
| **Agent Guide** | `AGENT_GUIDE.md` | Core operating principles |
| **Project Context** | `PROJECT_CONTEXT.md` | Design philosophy |

---

## EXTEND — Components Designed for Customization

These components have built-in extension points and should be enhanced, not replaced.

### Pipeline System

| Component | Current State | Extension Plan |
|-----------|--------------|----------------|
| **Pipeline Definitions** | `pipeline_defs/*.yaml` | Add MythForge-specific pipelines (reaction, tutorial, shorts) |
| **Pipeline Loader** | `lib/pipeline.py` | Add validation, dependency checking, parallel stages |
| **Executive Producer** | `skills/pipelines/*/executive-producer.md` | Add MythForge brand voice, quality standards |

### Skills System

| Component | Current State | Extension Plan |
|-----------|--------------|----------------|
| **Research Director** | `skills/pipelines/*/research-director.md` | Add SEO research, competitor analysis, trend detection |
| **Script Director** | `skills/pipelines/*/script-director.md` | Add brand voice templates, audience targeting |
| **Scene Director** | `skills/pipelines/*/scene-director.md` | Add new scene types for MythForge content |
| **Asset Director** | `skills/pipelines/*/asset-director.md` | Add caching strategy, quality tiers |
| **Publish Director** | `skills/pipelines/*/publish-director.md` | Add YouTube automation, multi-platform publishing |
| **Reviewer** | `skills/meta/reviewer.md` | Add MythForge quality standards |

### Knowledge System

| Component | Current State | Extension Plan |
|-----------|--------------|----------------|
| **Knowledge Directory** | `knowledge/` (sparse) | Add Character Bible, Brand Guide, Topic Database |
| **Playbooks** | `playbooks/*.json` | Add MythForge brand playbooks |

### Tool Extensions

| Component | Current State | Extension Plan |
|-----------|--------------|----------------|
| **ElevenLabs TTS** | `tools/audio/elevenlabs_tts.py` | Add voice cloning, sound effects, dubbing |
| **Image Selector** | `tools/graphics/image_selector.py` | Add Gemini Image API routing |
| **Video Selector** | `tools/video/video_selector.py` | Add quality tier routing |

---

## REPLACE — Components That Should Become MythForge-Specific

These components are functional but tied to OpenMontage's identity. They should be evolved into MythForge-specific versions.

### Identity & Branding

| Component | Current State | Replacement Plan |
|-----------|--------------|------------------|
| **README.md** | OpenMontage branding | MythForge AI product README |
| **License** | OpenMontage license | MythForge AI commercial license |
| **Demo Content** | `demo/` | MythForge-specific demo videos |
| **GitHub Config** | `.github/` | MythForge CI/CD, issue templates |

### Configuration

| Component | Current State | Replacement Plan |
|-----------|--------------|------------------|
| **config.yaml** | Generic defaults | MythForge-tuned defaults (budget, quality, providers) |
| **.env.example** | All providers listed | MythForge-required providers only |
| **Makefile** | Basic targets | MythForge build/deploy/test targets |

### Pipeline Defaults

| Component | Current State | Replacement Plan |
|-----------|--------------|------------------|
| **animated-explainer.yaml** | Generic explainer | MythForge explainer with brand voice |
| **Default Playbook** | `clean-professional.json` | MythForge brand playbook |
| **Default Providers** | Generic defaults | MythForge-preferred providers (ElevenLabs, FLUX, Veo) |

### Scoring & Quality

| Component | Current State | Replacement Plan |
|-----------|--------------|------------------|
| **scoring.py** | Generic quality scoring | MythForge quality standards |
| **Quality thresholds** | Basic pass/fail | MythForge tiered quality (draft, review, publish) |

### Publishing

| Component | Current State | Replacement Plan |
|-----------|--------------|------------------|
| **Publish Director** | Generic SEO/metadata | YouTube-optimized publishing with MythForge branding |
| **Thumbnail Generation** | Basic concept | MythForge thumbnail templates with brand elements |

---

## Migration Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Preserve OpenMontage core, add MythForge identity

```
KEEP:   All tools, registry, pipeline loader, artifacts, cost tracker
EXTEND: Knowledge directory with Character Bible and Brand Guide
REPLACE: README, license, config.yaml defaults, .env.example
```

**Deliverables**:
- [ ] Fork OpenMontage into MythForge AI repo
- [ ] Update README with MythForge branding
- [ ] Create MythForge-specific config.yaml
- [ ] Create MythForge-specific .env.example
- [ ] Add knowledge/characters/ with initial Character Bible
- [ ] Add knowledge/brand-guide.md

### Phase 2: Pipeline Customization (Week 3-4)

**Goal**: Create MythForge-specific pipelines

```
KEEP:   Pipeline loader, artifact manager, checkpoint system
EXTEND: Pipeline definitions, executive producer, all directors
REPLACE: Default pipeline, default playbook
```

**Deliverables**:
- [ ] Create `pipeline_defs/mythforge-explainer.yaml`
- [ ] Create `playbooks/mythforge-brand.json`
- [ ] Extend research-director with SEO and trend analysis
- [ ] Extend script-director with brand voice templates
- [ ] Extend publish-director with YouTube automation
- [ ] Add MythForge quality standards to reviewer

### Phase 3: Provider Optimization (Week 5-6)

**Goal**: Optimize provider selection for MythForge quality/cost targets

```
KEEP:   All existing tools, tool registry, cost tracker
EXTEND: Selector tools with MythForge routing logic
REPLACE: Default provider configuration
```

**Deliverables**:
- [ ] Configure preferred providers in config.yaml
- [ ] Add Gemini Image API tool
- [ ] Extend ElevenLabs with voice cloning
- [ ] Add asset cache layer
- [ ] Add provider health checks

### Phase 4: Quality & Automation (Week 7-8)

**Goal**: Add commercial-grade quality assurance and automation

```
KEEP:   Scoring framework, reviewer skill
EXTEND: Scoring with MythForge thresholds, reviewer with brand checks
REPLACE: Generic publish flow with YouTube automation
```

**Deliverables**:
- [ ] Add MythForge quality tiers (draft/review/publish)
- [ ] Add YouTube upload automation
- [ ] Add thumbnail generation with brand templates
- [ ] Add multi-platform publishing (YouTube, TikTok, LinkedIn)
- [ ] Add A/B testing framework

### Phase 5: Scale & Polish (Week 9-10)

**Goal**: Production readiness

```
KEEP:   All core infrastructure
EXTEND: Error handling, monitoring, logging
REPLACE: Nothing — all components now MythForge-specific
```

**Deliverables**:
- [ ] Pin all dependency versions
- [ ] Add comprehensive test coverage
- [ ] Add CI/CD pipeline
- [ ] Add monitoring and alerting
- [ ] Add documentation for MythForge team

---

## Component Migration Checklist

### Files to KEEP (no changes)

```
tools/base_tool.py
tools/tool_registry.py
tools/audio/*.py
tools/graphics/*.py
tools/video/*.py
tools/analysis/*.py
tools/enhancement/*.py
tools/subtitle/*.py
tools/avatar/*.py
tools/graphics/diagram*.py
tools/graphics/code*.py
tools/graphics/math*.py
lib/pipeline.py
lib/artifact_manager.py
lib/checkpoint.py
lib/cost_tracker.py
lib/media_profiles.py
lib/scoring.py
lib/text_utils.py
remotion-composer/src/**/*
remotion-composer/package.json
remotion-composer/tsconfig.json
pipeline/explainer.py
project/manager.py
```

### Files to EXTEND (modify in place)

```
skills/pipelines/explainer/*.md    → Add MythForge voice
skills/meta/*.md                   → Add brand checks
pipeline_defs/*.yaml               → Add MythForge pipelines
playbooks/*.json                   → Add MythForge playbook
schemas/*.json                     → Add new artifact types
config.yaml                        → Tune defaults
.env.example                       → Add MythForge-required keys
Makefile                           → Add MythForge targets
```

### Files to REPLACE (rewrite)

```
README.md                          → MythForge AI product README
LICENSE                            → Commercial license
.github/                           → MythForge CI/CD
demo/                              → MythForge demo content
knowledge/                         → MythForge knowledge base
```

### Files to ADD (new)

```
knowledge/characters/main-narrator.md
knowledge/characters/expert-analyst.md
knowledge/brand-guide.md
knowledge/audiences.md
knowledge/topics.md
knowledge/seo-templates.md
pipeline_defs/mythforge-explainer.yaml
pipeline_defs/mythforge-shorts.yaml
pipeline_defs/mythforge-reaction.yaml
playbooks/mythforge-brand.json
playbooks/mythforge-social.json
tools/graphics/gemini_image.py
tools/publish/youtube_upload.py
tools/publish/youtube_seo.py
tools/publish/thumbnail_gen.py
lib/asset_cache.py
lib/provider_health.py
tests/tools/test_all_tools.py
```

---

## Risk Mitigation During Migration

| Risk | Mitigation |
|------|-----------|
| Breaking existing pipelines | Keep all original pipeline YAML files, add new ones alongside |
| Tool incompatibility | All tools extend BaseTool — no interface changes needed |
| Skill reference breakage | Keep original skill files, add new MythForge skills in subdirectories |
| Configuration conflicts | Use MythForge-specific config.yaml with all defaults documented |
| Dependency issues | Pin versions before any other changes |
| Knowledge overload | Keep knowledge files concise, use references not inline data |

---

## Key Principles

1. **Never delete, only add** — OpenMontage components remain available
2. **Fork, don't modify** — MythForge changes are additive
3. **Preserve the tool ecosystem** — 40+ tools are the framework's greatest asset
4. **Preserve the skill architecture** — Markdown-driven agent behavior is elegant
5. **Preserve the pipeline pattern** — YAML-driven pipeline definitions are powerful
6. **Identity changes only** — Most "replacement" is branding, not architecture