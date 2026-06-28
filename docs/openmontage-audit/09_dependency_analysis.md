# OpenMontage — Dependency Analysis

## Overview

OpenMontage has dependencies across two ecosystems: **Python** (tools, orchestration) and **Node.js/TypeScript** (Remotion rendering). Dependencies are split across three requirements files and one `package.json`.

---

## Python Core Dependencies (`requirements.txt`)

| Package | Version | Purpose | Criticality | Replaceable | Risk if Upgraded |
|---------|---------|---------|-------------|-------------|------------------|
| **whisperx** | Latest | Speech-to-text with word-level alignment | **CRITICAL** — Transcription backbone | Difficult — core to subtitle sync | HIGH — API changes between versions |
| **ffmpeg-python** | Latest | Python bindings for FFmpeg | **CRITICAL** — Audio/video processing | No — FFmpeg is industry standard | LOW — Stable API |
| **python-dotenv** | Latest | Load .env environment variables | **CRITICAL** — Secret management | Yes — standard pattern | LOW — Stable |
| **pydantic** | Latest | Data validation and settings management | **HIGH** — Used for artifact validation | Yes — could use dataclasses | MEDIUM — v1→v2 breaking changes |
| **pyyaml** | Latest | YAML parsing for pipeline definitions | **HIGH** — Pipeline config loading | Yes — could use TOML/JSON | LOW — Stable |
| **requests** | Latest | HTTP client for API calls | **HIGH** — All API-based tools | Yes — could use httpx/aiohttp | LOW — Stable |
| **Pillow** | Latest | Image processing | **MEDIUM** — Image manipulation | Yes — could use opencv | LOW — Stable |
| **numpy** | Latest | Numerical computing | **MEDIUM** — Audio/video array ops | No — fundamental dependency | LOW — Stable |
| **rich** | Latest | Terminal formatting and progress bars | **LOW** — CLI output only | Yes — cosmetic | LOW — Stable |
| **click** | Latest | CLI argument parsing | **LOW** — Used in render_demo.py | Yes — could use argparse | LOW — Stable |
| **tqdm** | Latest | Progress bars | **LOW** — CLI progress display | Yes — cosmetic | LOW — Stable |
| **scikit-learn** | Latest | ML utilities | **LOW** — Used in scoring.py | Yes — could simplify | LOW — Stable |
| **jsonschema** | Latest | JSON Schema validation | **MEDIUM** — Artifact validation | Yes — could use pydantic | LOW — Stable |

---

## Python Dev Dependencies (`requirements-dev.txt`)

| Package | Version | Purpose | Criticality |
|---------|---------|---------|-------------|
| **pytest** | Latest | Test framework | HIGH — Test infrastructure |
| **pytest-cov** | Latest | Coverage reporting | MEDIUM |
| **ruff** | Latest | Linting and formatting | MEDIUM |
| **black** | Latest | Code formatting | LOW |
| **mypy** | Latest | Type checking | LOW |

---

## Python GPU Dependencies (`requirements-gpu.txt`)

| Package | Version | Purpose | Criticality |
|---------|---------|---------|-------------|
| **torch** | Latest | PyTorch for local models | MEDIUM — Only for local diffusion |
| **torchvision** | Latest | Vision models | MEDIUM — Only for local diffusion |
| **torchaudio** | Latest | Audio models | LOW — Only for local TTS |
| **diffusers** | Latest | HuggingFace diffusion models | MEDIUM — Only for local SD/SDXL |
| **transformers** | Latest | HuggingFace transformers | MEDIUM — Only for local models |
| **accelerate** | Latest | Model acceleration | LOW — Optimization only |

**Note**: GPU dependencies are **optional** — they enable local model inference (no API costs) but require CUDA-capable hardware.

---

## Node.js Dependencies (`remotion-composer/package.json`)

| Package | Version | Purpose | Criticality | Replaceable | Risk if Upgraded |
|---------|---------|---------|-------------|-------------|------------------|
| **remotion** | v4.x | Video rendering framework | **CRITICAL** — Primary render engine | No — core to explainer pipeline | HIGH — Major versions break APIs |
| **@remotion/cli** | v4.x | Remotion CLI for rendering | **CRITICAL** — Render invocation | No — required by remotion | HIGH — Tied to remotion version |
| **@remotion/renderer** | v4.x | Remotion rendering engine | **CRITICAL** — Frame rendering | No — required by remotion | HIGH — Tied to remotion version |
| **react** | 18.x | UI component library | **HIGH** — Scene components | Difficult — deeply integrated | MEDIUM — Generally backwards-compatible |
| **react-dom** | 18.x | React DOM rendering | **HIGH** — Scene rendering | Difficult — deeply integrated | MEDIUM — Tied to react version |
| **typescript** | 5.x | TypeScript compiler | **HIGH** — Type safety | Yes — could use JavaScript | LOW — Stable |
| **@types/react** | 18.x | React type definitions | **MEDIUM** — Developer experience | No — tied to react | LOW — Auto-generated |

---

## System Dependencies

| Dependency | Version | Purpose | Criticality | Installation |
|------------|---------|---------|-------------|-------------|
| **FFmpeg** | 6.x+ | Video/audio processing CLI | **CRITICAL** — All video operations | System package manager |
| **Node.js** | 18+ | JavaScript runtime for Remotion | **CRITICAL** — Remotion rendering | nodejs.org |
| **npm** | 9+ | Node package manager | **CRITICAL** — Install Remotion deps | Bundled with Node.js |
| **Python** | 3.10+ | Python runtime | **CRITICAL** — All tools | python.org |
| **Git** | 2.x+ | Version control | **HIGH** — Repository management | System package manager |

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM LAYER                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Python   │  │ Node.js  │  │  FFmpeg  │  │   Git    │   │
│  │  3.10+   │  │   18+    │  │   6.x+   │  │   2.x+   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘   │
│       │              │              │                        │
├───────┼──────────────┼──────────────┼────────────────────────┤
│       │              │              │                        │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐                  │
│  │PyYAML    │  │ Remotion │  │ffmpeg-   │                  │
│  │Pydantic  │  │ React    │  │python    │                  │
│  │requests  │  │ TS       │  │          │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │              │              │                        │
├───────┼──────────────┼──────────────┼────────────────────────┤
│       │              │              │                        │
│  ┌────▼──────────────▼──────────────▼──────────────────┐    │
│  │                    TOOLS LAYER                       │    │
│  │  base_tool.py ← tool_registry.py ← cost_tracker.py  │    │
│  └────────────────────────┬────────────────────────────┘    │
│                           │                                  │
│  ┌────────────────────────▼────────────────────────────┐    │
│  │              TOOL IMPLEMENTATIONS                    │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │    │
│  │  │  audio/  │ │graphics/│ │ video/  │ │analysis/│  │    │
│  │  │  (10)    │ │  (11)   │ │  (18)   │ │  (3)    │  │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              SKILLS LAYER (Markdown)                 │    │
│  │  No code dependencies — pure prompt documents        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              PIPELINE LAYER (YAML)                   │    │
│  │  No code dependencies — declarative definitions      │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## External API Dependencies (Runtime)

These are external services that tools depend on at runtime:

| Service | API | Tools Depending On It | Fallback |
|---------|-----|----------------------|----------|
| **ElevenLabs** | REST API | `elevenlabs_tts.py` | Google TTS, OpenAI TTS, Piper |
| **Google Cloud** | REST/gRPC | `google_imagen.py`, `google_tts.py`, `veo_video.py` | Other providers |
| **OpenAI** | REST API | `openai_image.py`, `openai_tts.py` | Other providers |
| **Pexels** | REST API | `pexels_image.py`, `pexels_video.py` | Pixabay |
| **Pixabay** | REST API | `pixabay_image.py`, `pixabay_video.py` | Pexels |
| **HeyGen** | REST API | `heygen_avatar.py`, `heygen_video.py` | Hedra, Wav2Lip |
| **Replicate** | REST API | Various local diffusion tools | Local models |
| **FLUX** | REST API | `flux_image.py` | Other image providers |
| **Runway** | REST API | `runway_video.py` | Other video providers |
| **Suno** | REST API | `suno_music.py` | Freesound, Pixabay |

**Key Observation**: Every external API dependency has at least one fallback provider. No single service failure can halt the entire pipeline.

---

## Dependency Risk Summary

### CRITICAL (Cannot operate without)
- Python 3.10+
- Node.js 18+
- FFmpeg 6.x+
- Remotion v4.x
- whisperx

### HIGH (Degraded functionality without)
- pydantic, pyyaml, requests
- react, react-dom, typescript
- At least one TTS provider API key
- At least one image provider API key

### MEDIUM (Optional features affected)
- torch/diffusers (local models)
- scikit-learn (scoring)
- jsonschema (validation)

### LOW (Cosmetic/convenience)
- rich, click, tqdm
- black, ruff, mypy

---

## Key Observations

1. **Dual ecosystem** — Python + Node.js/TypeScript creates two dependency trees to manage
2. **Remotion is the riskiest dependency** — major version upgrades break scene components
3. **whisperx is critical** — transcription quality directly affects subtitle accuracy
4. **External APIs are well-fallbacked** — no single point of failure in provider chain
5. **GPU dependencies are optional** — local inference is a cost optimization, not a requirement
6. **No dependency pinning** — requirements.txt uses `latest` (risk of unexpected breakage)
7. **No lock files** — no `package-lock.json` or `requirements.lock` verified in repo