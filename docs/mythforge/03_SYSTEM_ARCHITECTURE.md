# MythForge AI — System Architecture

## Architecture Overview

MythForge AI is built as a layered system on top of OpenMontage. The architecture follows a clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    MYTHFORGE AI LAYER                        │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Knowledge   │ │ Character    │ │ MythForge Pipeline   │ │
│  │ Base        │ │ Bible        │ │ (mythforge.py)       │ │
│  └─────────────┘ └──────────────┘ └──────────────────────┘ │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Scene JSON  │ │ Asset Cache  │ │ QA Agent             │ │
│  │ System      │ │              │ │                      │ │
│  └─────────────┘ └──────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    OPENMONTAGE CORE                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Pipeline Orchestrator                 │   │
│  │              (pipeline/base.py)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │ Agents     │ │ Tools      │ │ Providers  │ │ Budget  │ │
│  │ (7 core)   │ │ (40+)      │ │ (14+)      │ │ Tracker │ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │ FFmpeg     │ │ Remotion   │ │ TypeScript │ │ Python  │ │
│  │ Renderer   │ │ Renderer   │ │ Bridge     │ │ Core    │ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    EXTERNAL PROVIDERS                        │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │
│  │OpenAI  │ │Gemini  │ │Eleven- │ │Replicate│ │Unsplash │ │
│  │        │ │        │ │Labs    │ │        │ │          │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Architecture

### Layer 1: OpenMontage Core (KEEP — Do Not Modify)

The foundation layer. This is the existing OpenMontage codebase that provides:

| Component | Location | Purpose |
|-----------|----------|---------|
| Pipeline Orchestrator | `src/pipeline/base.py` | Agent execution loop, dependency resolution, tool dispatch |
| Agent System | `src/agents/*.py` | Modular AI agents (Planner, Researcher, Script Writer, etc.) |
| Tool System | `src/tools/*.py` | 40+ tools for API calls, media processing, file I/O |
| Provider System | `src/providers/*.py` | Abstraction layer for 14+ external services |
| Budget Tracker | `src/utils/budget_tracker.py` | Per-run and per-stage cost tracking |
| Config System | `src/config/` | YAML-based configuration with profiles |
| CLI Entry Point | `src/main.py` | Click-based CLI with profile support |
| Rendering System | `src/rendering/` | FFmpeg and Remotion rendering engines |
| TypeScript Bridge | `src/bridge/` | Python↔Remotion communication layer |

**Architecture Rule**: OpenMontage core is treated as a dependency, not as source to modify. If core changes are needed, they are contributed upstream or implemented as wrapper/extension layers.

### Layer 2: MythForge Extension Layer (EXTEND — Custom Implementation)

The customization layer that makes MythForge AI unique:

| Component | Location | Purpose |
|-----------|----------|---------|
| MythForge Pipeline | `src/pipelines/mythforge.py` | Custom pipeline orchestrating the mythology video production flow |
| Knowledge Base | `src/knowledge/` | Structured mythology data (characters, kingdoms, stories, symbols) |
| Character Bible | `src/knowledge/characters/` | Character visual identity, reference images, prompt templates |
| Scene JSON System | `src/knowledge/scenes/` | Scene templates, transition patterns, visual styles |
| MythForge Agents | `src/agents/mythforge_*.py` | Custom agents for mythology-specific production stages |
| Asset Cache | `src/cache/` | Local cache for generated images, audio, music |
| QA Agent | `src/agents/mythforge_qa.py` | Automated quality assurance checks |
| Publisher | `src/agents/mythforge_publisher.py` | YouTube/platform publishing automation |

### Layer 3: Configuration Layer (EXTEND — MythForge-Specific)

Configuration that defines MythForge's behavior:

| Component | Location | Purpose |
|-----------|----------|---------|
| MythForge Profile | `config/profiles/mythforge.yaml` | Main configuration profile |
| Provider Config | `config/providers/` | Per-provider API keys and settings |
| Knowledge Config | `config/knowledge.yaml` | Knowledge base paths and search settings |
| Character Config | `config/characters/` | Per-character visual identity settings |
| Rendering Presets | `config/rendering/` | Video format presets (YouTube, TikTok, Reels) |

---

## Data Flow Architecture

```
User Input: "The Legend of Shango"
         │
         ▼
┌─────────────────────────────────────────────────┐
│              MYTHFORGE PIPELINE                   │
│                                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ Stage 1  │───▶│ Stage 2  │───▶│ Stage 3  │   │
│  │ Research │    │ Script   │    │ Scenes   │   │
│  └──────────┘    └──────────┘    └──────────┘   │
│       │                                │         │
│       ▼                                ▼         │
│  ┌──────────────────────────────────────────┐   │
│  │           ARTIFACT STORE                  │   │
│  │  .mythforge/projects/{project_id}/        │   │
│  │  ├── research.json                        │   │
│  │  ├── script.json                          │   │
│  │  ├── scenes.json                          │   │
│  │  ├── assets/                              │   │
│  │  │   ├── images/                          │   │
│  │  │   ├── narration/                       │   │
│  │  │   ├── music/                           │   │
│  │  │   └── sfx/                             │   │
│  │  ├── render/                              │   │
│  │  │   └── final.mp4                        │   │
│  │  ├── thumbnail.png                        │   │
│  │  ├── metadata.json                        │   │
│  │  └── production_report.json               │   │
│  └──────────────────────────────────────────┘   │
│                                                   │
│  ┌──────────────────────────────────────────┐   │
│  │         CHECKPOINT SYSTEM                  │   │
│  │  Stores progress after each stage          │   │
│  │  Enables resume on failure                 │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              OPENMONTAGE CORE (KEEP)             │
│                                                   │
│  Pipeline Orchestrator executes agents using      │
│  the same agent/tool/provider infrastructure      │
│  that OpenMontage already provides.               │
│                                                   │
│  MythForge pipeline registers its agents and      │
│  tools with the orchestrator at startup.          │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              EXTERNAL PROVIDERS                   │
│                                                   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │
│  │ChatGPT │ │Gemini  │ │Eleven- │ │Remotion/ │ │
│  │(research│ │(images)│ │Labs    │ │FFmpeg    │ │
│  │& script)│ │        │ │(TTS)   │ │(render)  │ │
│  └────────┘ └────────┘ └────────┘ └──────────┘ │
└─────────────────────────────────────────────────┘
```

---

## Component Interaction Map

### How MythForge Extends OpenMontage

```
OpenMontage Pipeline (pipeline/base.py)
    │
    ├── MythForge Pipeline inherits from PipelineBase
    │   └── mythforge_pipeline.py
    │       ├── Defines stage order (Research → Script → ... → Publish)
    │       ├── Each stage maps to an agent
    │       ├── Each agent uses OpenMontage tools
    │       └── Results stored as project artifacts
    │
    ├── MythForge Agents inherit from BaseAgent
    │   ├── mythforge_researcher.py → uses research_agent prompt + knowledge base
    │   ├── mythforge_scriptwriter.py → uses script_agent prompt + character bible
    │   ├── mythforge_scene_director.py → uses scene generation prompt
    │   ├── mythforge_prompt_agent.py → uses image prompt engineering
    │   ├── mythforge_image_agent.py → uses Gemini tool
    │   ├── mythforge_narrator.py → uses ElevenLabs tool
    │   ├── mythforge_music_agent.py → uses music tool
    │   ├── mythforge_sfx_agent.py → uses SFX tool
    │   ├── mythforge_renderer.py → uses rendering tools
    │   ├── mythforge_qa.py → uses analysis tools
    │   └── mythforge_publisher.py → uses platform upload tools
    │
    └── MythForge Tools extend OpenMontage tools
        ├── knowledge_base_tool.py → search/lookup mythology data
        ├── character_consistency_tool.py → inject character identity
        ├── gemini_image_tool.py → Gemini Image API wrapper
        ├── asset_cache_tool.py → local asset caching
        └── youtube_upload_tool.py → YouTube API wrapper
```

---

## KEEP / EXTEND / REPLACE Matrix

### KEEP (Do Not Modify)

| Component | File(s) | Reason |
|-----------|---------|--------|
| Pipeline Orchestrator | `src/pipeline/base.py` | Core execution engine; well-designed for extension |
| Base Agent | `src/agents/base.py` | Agent interface is clean and extensible |
| Tool Registry | `src/tools/base.py` | Tool discovery and registration works correctly |
| Provider Base | `src/providers/base.py` | Provider abstraction is solid |
| Budget Tracker | `src/utils/budget_tracker.py` | Cost tracking is provider-agnostic |
| Remotion Rendering | `src/rendering/remotion_renderer.py` | Timeline-based rendering is production-ready |
| FFmpeg Rendering | `src/rendering/ffmpeg_renderer.py` | Fallback renderer is reliable |
| TypeScript Bridge | `src/bridge/` | Python↔Remotion IPC is working |
| Subtitle Handler | `src/rendering/subtitle_handler.py` | SRT generation is functional |
| Audio Handler | `src/rendering/audio_handler.py` | Audio normalization is correct |
| Scene Handler | `src/rendering/scene_handler.py` | Scene-based rendering is the right abstraction |
| Config Loader | `src/config/config_manager.py` | YAML config loading is flexible |

### EXTEND (Customize for MythForge)

| Component | Current State | MythForge Extension |
|-----------|--------------|---------------------|
| Pipeline | Generic pipeline | MythForge-specific stage ordering and agents |
| Config | Generic YAML profiles | MythForge profile with provider selections |
| Prompts | Generic video prompts | Mythology-focused prompt templates |
| Tools | Generic tools | Knowledge base, character bible, asset cache tools |
| Agents | Generic agents | Mythology-specific agent specializations |
| Playbooks | Generic style guides | African mythology art style playbooks |

### REPLACE (Generic → MythForge-Specific)

| Component | Current | Replacement |
|-----------|---------|-------------|
| Default pipeline | `construct_video` | `mythforge_production` |
| Default profile | `default.yaml` | `mythforge.yaml` |
| Default prompts | Generic video prompts | Mythology narrative prompts |
| Image provider | Configurable | Gemini Image API (primary) |
| Voice provider | Configurable | ElevenLabs (primary, mythology voice) |

---

## Extension Registration Mechanism

MythForge components register with OpenMontage using the existing extension points:

```
┌─────────────────────────────────────────────┐
│          REGISTRATION FLOW                    │
│                                               │
│  1. MythForge package defines its agents,     │
│     tools, and pipeline in its own modules     │
│                                               │
│  2. At startup, mythforge/__init__.py          │
│     registers all components with the          │
│     OpenMontage registry                       │
│                                               │
│  3. OpenMontage registry makes them            │
│     available to the pipeline orchestrator     │
│                                               │
│  4. mythforge.yaml profile selects which       │
│     agents and tools to use                    │
└─────────────────────────────────────────────┘
```

---

## Recommended Directory Structure

```
mythforge-ai/
├── src/                          # OpenMontage core (KEEP)
│   ├── main.py                   # CLI entry point
│   ├── pipeline/                 # Pipeline orchestration
│   ├── agents/                   # Base agents + MythForge agents
│   ├── tools/                    # Base tools + MythForge tools
│   ├── providers/                # Provider abstractions
│   ├── rendering/                # FFmpeg + Remotion rendering
│   ├── bridge/                   # TypeScript bridge
│   ├── config/                   # Configuration management
│   └── utils/                    # Utilities
│
├── mythforge/                    # MythForge extension layer (EXTEND)
│   ├── __init__.py               # Extension registration
│   ├── pipeline.py               # MythForge pipeline definition
│   ├── agents/                   # MythForge-specific agents
│   ├── tools/                    # MythForge-specific tools
│   ├── knowledge/                # Knowledge base
│   │   ├── characters/           # Character bible
│   │   ├── kingdoms/             # Mythological kingdoms
│   │   ├── stories/              # Story database
│   │   ├── locations/            # Location database
│   │   ├── artifacts/            # Mythological artifacts
│   │   ├── symbols/              # Cultural symbols
│   │   └── timeline/             # Mythological timeline
│   ├── prompts/                  # MythForge prompt templates
│   │   ├── research.md
│   │   ├── script.md
│   │   ├── scene_director.md
│   │   ├── image_prompt.md
│   │   ├── narration.md
│   │   ├── music.md
│   │   ├── sfx.md
│   │   ├── thumbnail.md
│   │   ├── metadata.md
│   │   └── qa.md
│   ├── playbooks/                # Art style playbooks
│   │   ├── cinematic_realistic.yaml
│   │   ├── animated_3d.yaml
│   │   └── dark_fantasy.yaml
│   ├── cache/                    # Asset cache system
│   └── publisher/                # Platform publishing
│
├── config/                       # Configuration (EXTEND)
│   ├── default.yaml              # OpenMontage defaults
│   ├── mythforge.yaml            # MythForge profile
│   ├── providers/                # Provider-specific config
│   └── rendering/                # Rendering presets
│
├── extensions/
│   └── remotion/                 # Remotion project (KEEP)
│       └── src/
│           ├── Root.tsx
│           └── compositions/
│               ├── Video.tsx
│               └── Subtitle.tsx
│
├── .env                          # API keys (gitignored)
├── pyproject.toml                # Python project config
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

---

## Security Architecture

### API Key Management

```
┌─────────────────────────────────────────┐
│           API KEY FLOW                    │
│                                           │
│  .env file (gitignored)                   │
│  ├── OPENAI_API_KEY                       │
│  ├── GEMINI_API_KEY                       │
│  ├── ELEVENLABS_API_KEY                   │
│  ├── REPLICATE_API_TOKEN                  │
│  ├── YOUTUBE_API_KEY (future)             │
│  └── GOOGLE_SEARCH_API_KEY                │
│           │                               │
│           ▼                               │
│  config/providers/*.yaml                  │
│  References env vars, never stores keys   │
│           │                               │
│           ▼                               │
│  src/providers/*.py                       │
│  Reads keys at runtime from env/config    │
└─────────────────────────────────────────┘
```

### Cost Control Architecture

```
┌─────────────────────────────────────────┐
│           COST CONTROL                    │
│                                           │
│  Budget Tracker (src/utils/budget_*)      │
│  ├── Per-run limit: $5.00 (configurable)  │
│  ├── Per-stage limit: $1.00 (configurable)│
│  ├── Warning at 80% of limit              │
│  ├── Hard stop at 100% of limit           │
│  └── Detailed cost breakdown per provider │
│                                           │
│  Provider-level rate limiting              │
│  ├── Exponential backoff on 429 errors    │
│  ├── Request queuing for rate-limited APIs│
│  └── Fallback provider selection          │
└─────────────────────────────────────────┘
```

---

## Summary

The architecture is designed around a single principle: **extend, don't modify**. OpenMontage provides the engine; MythForge provides the soul. Every MythForge component plugs into OpenMontage through established extension points. If OpenMontage is upgraded, MythForge should continue working without changes. If a MythForge component needs to be replaced, the swap happens at the MythForge layer without touching the core.