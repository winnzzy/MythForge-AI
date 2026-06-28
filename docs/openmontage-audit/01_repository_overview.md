# OpenMontage — Repository Overview

## 1. Project Purpose

OpenMontage is an AI-powered video production framework designed to automate the entire video creation pipeline — from research and scripting through asset generation, rendering, and publishing. It is architected as a **tool-first, skill-driven** system where an LLM agent orchestrates a sequence of production stages by invoking specialized tools (TTS, image generation, video generation, composition, etc.) guided by reusable "skill" documents (Markdown prompt files) and YAML pipeline definitions.

The system supports multiple video production styles including animated explainers, talking-head videos, documentary montages, podcast repurposing, screen demos, cinematic pieces, and localization/dubbing workflows.

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER / AI AGENT                          │
│                  (e.g. Cursor, Claude, GPT)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ reads skills + pipeline defs
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE ENGINE                            │
│  YAML pipeline_defs/ → stages → skills → tools                 │
│  Orchestrated by "Executive Producer" skill                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       TOOL REGISTRY                             │
│  Auto-discovers tools/ via pkgutil.walk_packages                │
│  Reports capabilities, status, provider menu                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TOOLS (50+ modules)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Graphics │ │  Audio   │ │  Video   │ │    Analysis      │   │
│  │ (Images) │ │ (TTS,    │ │ (Gen,    │ │ (Transcription,  │   │
│  │          │ │  Music)  │ │  Compose)│ │  Scene Detect)   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Avatar  │ │Enhance-  │ │ Subtitle │ │    Publish       │   │
│  │(Lip Sync)│ │  ment    │ │          │ │                  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RENDERING BACKENDS                            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │   Remotion   │  │  HyperFrames │  │     FFmpeg            │ │
│  │ (React/TSX)  │  │ (HTML/GSAP)  │  │ (Direct composition)  │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Programming Languages

| Language     | Usage                                                        |
|-------------|--------------------------------------------------------------|
| **Python**   | Core framework, tools, pipeline orchestration, CLI, schemas |
| **TypeScript** | Remotion composer (React-based video rendering)           |
| **JavaScript** | Remotion runtime, npm tooling                             |
| **HTML/CSS**  | HyperFrames compositions (GSAP animations)                |
| **YAML**     | Pipeline definitions, playbooks, configuration              |
| **Markdown** | Skill files (LLM prompt documents), agent guides            |
| **JSON**     | Schema definitions, scene props, demo fixtures              |

## 4. Frameworks & Key Libraries

| Framework / Library | Role |
|---------------------|------|
| **Remotion** (v4.x) | React-based programmatic video generation |
| **Pydantic** (v2+) | Data validation, tool schemas, scene JSON |
| **FFmpeg** | Video/audio encoding, composition, format conversion |
| **WhisperX** | Speech-to-text transcription with word-level alignment |
| **HyperFrames** (npm) | HTML/GSAP-based video composition runtime |
| **Pillow / NumPy** | Image processing, frame manipulation |
| **jsonschema** | Pipeline and artifact schema validation |
| **python-dotenv** | Environment variable management |
| **google-auth** | Google Cloud TTS and Vertex AI authentication |
| **Piper TTS** | Free offline text-to-speech |
| **SadTalker / Wav2Lip** | Talking-head avatar generation (optional, local GPU) |
| **HuggingFace Transformers** | Local diffusion models for image/video generation |
| **React** | UI components for Remotion scenes |

## 5. Build System

- **Python**: No build step; source-run via `python3` or Makefile targets
- **TypeScript/Remotion**: `npm install` in `remotion-composer/`, then `npx remotion render`
- **Makefile**: Primary orchestration for setup, install, test, lint, demo, and HyperFrames operations
- **No CI/CD pipeline detected** in the repository

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make setup` | Full one-command setup (Python deps + Remotion + Piper + HyperFrames + .env) |
| `make install` | Install Python dependencies only |
| `make install-dev` | Install dev dependencies |
| `make install-gpu` | Install GPU-accelerated dependencies (diffusers, transformers) |
| `make test` | Run pytest test suite |
| `make test-contracts` | Run contract tests only |
| `make preflight` | Show provider menu (available tools and capabilities) |
| `make demo` | Render zero-key demo videos |
| `make demo-list` | List available demo fixtures |
| `make hyperframes-doctor` | Validate HyperFrames runtime |
| `make hyperframes-warm` | Refresh HyperFrames npx cache |
| `make lint` | Syntax-check core modules |
| `make clean` | Remove __pycache__ and .pyc files |

## 6. Package Managers

| Manager | Scope |
|---------|-------|
| **pip** (Python) | Core dependencies (`requirements.txt`), dev deps, GPU deps |
| **npm** (Node.js) | Remotion composer (`remotion-composer/package.json`) |
| **npx** | HyperFrames CLI runtime (fetched on-demand) |

## 7. Entry Points

| Entry Point | Description |
|-------------|-------------|
| `render_demo.py` | CLI script to render zero-key Remotion demo videos |
| `make setup` | Primary onboarding entry point |
| `make preflight` | Tool/capability discovery |
| AI Agent (Cursor/Claude/GPT) | **Primary production entry point** — the agent reads skills and pipeline defs, then orchestrates tool execution |
| `tools/tool_registry.py` → `registry` singleton | Programmatic entry point for tool discovery |

**Important**: OpenMontage is **not a traditional CLI application**. There is no `main.py` or `cli.py`. The primary user interface is an **AI coding agent** (e.g., Cursor, Claude, ChatGPT) that reads the `AGENT_GUIDE.md`, discovers available tools via the registry, and follows skill documents to produce videos. The `render_demo.py` script is a secondary entry point for demonstration purposes only.

## 8. CLI Commands

OpenMontage does not have a traditional CLI. The primary interaction model is:

1. User opens the project in an AI coding assistant
2. Agent reads `AGENT_GUIDE.md` and `PROJECT_CONTEXT.md`
3. Agent runs `make preflight` to discover available tools
4. Agent reads relevant pipeline definition from `pipeline_defs/`
5. Agent follows skill documents stage-by-stage
6. Agent invokes tools via Python or subprocess calls

For demos: `python render_demo.py [demo-name] [--list]`

## 9. Repository Layout

```
openmontage/
├── AGENT_GUIDE.md              # Instructions for AI agents (Layer 1)
├── PROJECT_CONTEXT.md          # Project philosophy and context (Layer 2)
├── README.md                   # User-facing documentation
├── ROADMAP.md                  # Feature roadmap
├── SECURITY.md                 # Security policy
├── Makefile                    # Build/install/test orchestration
├── config.yaml                 # Global configuration (LLM, budget, output)
├── .env.example                # Environment variable template
├── requirements.txt            # Python core dependencies
├── requirements-dev.txt        # Python dev dependencies
├── requirements-gpu.txt        # Python GPU dependencies
├── render_demo.py              # Demo video renderer
│
├── tools/                      # Tool implementations (50+ tools)
│   ├── base_tool.py            # Abstract base class for all tools
│   ├── tool_registry.py        # Auto-discovery registry (singleton)
│   ├── cost_tracker.py         # Budget tracking
│   ├── google_credentials.py   # Google Cloud auth helper
│   ├── analysis/               # Video/audio analysis tools
│   ├── audio/                  # TTS, music generation, audio mixing
│   ├── avatar/                 # Lip sync, talking head
│   ├── capture/                # Screen recording
│   ├── character/              # Character animation
│   ├── enhancement/            # Image/video enhancement (upscale, denoise)
│   ├── graphics/               # Image generation (11+ providers)
│   ├── publishers/             # Publishing tools (placeholder)
│   ├── subtitle/               # Subtitle generation
│   └── video/                  # Video generation (16+ providers), composition, stitching
│
├── skills/                     # LLM prompt documents (skill library)
│   ├── core/                   # Technical skills (FFmpeg, Remotion, WhisperX)
│   ├── creative/               # Creative skills (storytelling, typography, etc.)
│   ├── meta/                   # Meta-skills (reviewer, checkpoint, onboarding)
│   ├── creative/prompting/     # Image/video generation prompting guides
│   └── pipelines/              # Pipeline-specific director skills
│       ├── explainer/          # Animated explainer pipeline skills
│       ├── talking-head/       # Talking head pipeline skills
│       ├── documentary-montage/ # Documentary pipeline skills
│       ├── podcast-repurpose/  # Podcast repurposing skills
│       ├── screen-demo/        # Screen demo pipeline skills
│       ├── cinematic/          # Cinematic pipeline skills
│       ├── localization-dub/   # Localization/dubbing skills
│       ├── avatar-spokesperson/ # Avatar spokesperson skills
│       ├── character-animation/ # Character animation skills
│       ├── clip-factory/       # Clip factory skills
│       ├── hybrid/             # Hybrid pipeline skills
│       └── animation/          # Animation pipeline skills
│
├── pipeline_defs/              # YAML pipeline definitions
│   ├── animated-explainer.yaml
│   ├── cinematic-broll.yaml
│   ├── talking-head.yaml
│   ├── podcast-repurpose.yaml
│   ├── screen-demo.yaml
│   ├── documentary-montage.yaml
│   ├── localization-dub.yaml
│   ├── avatar-spokesperson.yaml
│   ├── character-animation.yaml
│   ├── clip-factory.yaml
│   └── hybrid-live-animated.yaml
│
├── playbooks/                  # Visual style playbooks (JSON)
│   └── *.json                  # e.g., clean-professional.json, flat-motion-graphics.json
│
├── schemas/                    # JSON Schema definitions for validation
│   └── *.json                  # Artifact schemas (script, scene_plan, etc.)
│
├── remotion-composer/          # Remotion rendering backend (TypeScript/React)
│   ├── package.json
│   ├── src/
│   │   ├── index.tsx           # Remotion entry point
│   │   ├── Root.tsx            # Root composition
│   │   └── ...                 # Scene components, utilities
│   └── public/
│       └── demo-props/         # Demo JSON props for Remotion scenes
│
├── lib/                        # Shared Python libraries
│   └── scoring.py              # Tool quality scoring engine
│
├── library/                    # Reusable asset library (empty/template)
├── output/                     # Default output directory for rendered videos
├── pipeline/                   # Pipeline state/checkpoint storage
├── projects/                   # Project-specific working directories
└── tests/                      # Test suite
    └── contracts/              # Contract tests for tool interfaces
```

## 10. Key Design Principles

1. **Skill-Driven Architecture**: The AI agent's behavior is defined by Markdown skill files, not hard-coded logic
2. **Tool Contract Pattern**: Every tool implements `BaseTool` with uniform `execute()`, `get_info()`, `estimate_cost()`, `dry_run()` interfaces
3. **Provider Agnostic**: Selectors (e.g., `tts_selector`, `image_selector`) abstract over multiple providers
4. **Pipeline as Data**: Pipelines are YAML definitions, not code — stages, skills, tools, and checkpoints are declarative
5. **Zero-Key Operation**: System works without API keys using free/offline tools (Piper TTS, Pexels, Remotion components)
6. **Budget Awareness**: Built-in cost tracking, estimation, and approval gates
7. **Checkpoint & Resume**: Pipeline state is persisted, allowing restart from any stage
8. **Extensibility via Skills**: New capabilities are added by writing Markdown skill files, not modifying framework code