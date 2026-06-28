# MythForge AI — Asset Management

## Overview

MythForge AI generates, stores, and manages a large volume of digital assets during video production. This document defines the asset storage architecture, naming conventions, caching strategy, lifecycle management, and cleanup policies.

---

## Asset Categories

| Category | Format | Source | Size (per video) | Count |
|----------|--------|--------|-------------------|-------|
| Scene Images | PNG | Gemini / Replicate | ~5-10 MB each | 18-25 |
| Narration Audio | MP3 | ElevenLabs / OpenAI | ~2-5 MB each | 18-25 |
| Full Narration Track | MP3 | Concatenated | ~30-60 MB | 1 |
| Music Track | MP3 | Local library | ~5-15 MB | 1-2 |
| Sound Effects | WAV | ElevenLabs SFX / Local | ~1-5 MB each | 5-15 |
| Combined SFX Track | WAV | Mixed | ~20-40 MB | 1 |
| Final Video | MP4 (H.264) | Remotion / FFmpeg | ~200-500 MB | 1 |
| Subtitles | SRT | Generated | ~5-20 KB | 1 |
| Thumbnail | PNG | Gemini | ~2-5 MB | 1 |
| Artifacts | JSON | Generated | ~5-50 KB each | 10-15 |

**Estimated total per video: 500 MB - 1.5 GB**

---

## Directory Structure

```
.mythforge/
└── projects/
    └── {project_id}/
        ├── config/
        │   └── project_config.json
        ├── artifacts/
        │   ├── research.json
        │   ├── script.json
        │   ├── scenes.json
        │   ├── prompts.json
        │   ├── image_generation_log.json
        │   ├── narration_log.json
        │   ├── music_log.json
        │   ├── sfx_log.json
        │   ├── render_log.json
        │   ├── qa_report.json
        │   └── production_report.json
        ├── assets/
        │   ├── images/
        │   │   ├── {project_id}_scene_01.png
        │   │   ├── {project_id}_scene_02.png
        │   │   └── ...
        │   ├── narration/
        │   │   ├── {project_id}_scene_01_narration.mp3
        │   │   ├── {project_id}_scene_02_narration.mp3
        │   │   ├── {project_id}_narration_full.mp3
        │   │   └── ...
        │   ├── music/
        │   │   └── {project_id}_music_track.mp3
        │   └── sfx/
        │       ├── {project_id}_sfx_thunder.wav
        │       ├── {project_id}_sfx_drums.wav
        │       ├── {project_id}_sfx_track.wav
        │       └── ...
        ├── checkpoints/
        │   ├── stage_01_research.json
        │   ├── stage_02_script.json
        │   └── pipeline_state.json
        ├── render/
        │   ├── temp/                    # Temporary rendering files
        │   └── remotion_project/        # Remotion composition
        └── output/
            ├── {project_id}_final.mp4
            ├── {project_id}_subtitles.srt
            ├── {project_id}_thumbnail.png
            ├── {project_id}_metadata.json
            └── {project_id}_production_report.json
```

---

## Naming Conventions

### Project ID

Format: `{sanitized_title}_{YYYYMMDD}`

Examples:
- `shango_thunder_20260628`
- `isis_and_osiris_20260715`
- `thors_hammer_20260801`

Rules:
- Lowercase only
- Spaces replaced with underscores
- Special characters removed
- Maximum 50 characters
- Date suffix ensures uniqueness

### Asset Files

Format: `{project_id}_{asset_type}_{identifier}.{ext}`

Examples:
- `shango_thunder_20260628_scene_01.png`
- `shango_thunder_20260628_scene_05_narration.mp3`
- `shango_thunder_20260628_sfx_thunder.wav`
- `shango_thunder_20260628_final.mp4`

### Artifact Files

Format: `{descriptive_name}.json`

Examples:
- `research.json`
- `script.json`
- `scenes.json`
- `qa_report.json`

---

## Caching System

### Cache Architecture

```
.mythforge/
└── cache/
    ├── images/
    │   ├── index.json           # Cache index with keys and metadata
    │   ├── {hash_1}.png
    │   ├── {hash_2}.png
    │   └── ...
    ├── narration/
    │   ├── index.json
    │   ├── {hash_1}.mp3
    │   └── ...
    ├── music/
    │   ├── index.json
    │   └── {track_id}.mp3
    └── sfx/
        ├── index.json
        ├── {effect_id}.wav
        └── ...
```

### Cache Key Generation

Cache keys are SHA-256 hashes of the input parameters that produced the asset.

| Asset Type | Cache Key Input |
|-----------|----------------|
| Image | `hash(prompt + style_anchor + model + resolution)` |
| Narration | `hash(text + voice_id + model + speed)` |
| Music | `track_id` (exact match) |
| SFX | `effect_id` (exact match) |

### Cache Index

```json
{
  "version": "1.0.0",
  "entries": {
    "a1b2c3d4e5f6...": {
      "file": "a1b2c3d4e5f6.png",
      "created": "2026-06-28T20:15:00Z",
      "last_accessed": "2026-06-28T20:15:00Z",
      "access_count": 3,
      "size_bytes": 2457600,
      "input_hash": "a1b2c3d4e5f6...",
      "provider": "gemini",
      "cost": 0.04
    }
  }
}
```

### Cache Policies

| Policy | Value | Rationale |
|--------|-------|-----------|
| Max cache size | 10 GB | Prevent disk exhaustion |
| Default TTL (images) | 30 days | Images may need regeneration after style updates |
| Default TTL (narration) | 30 days | Narration may change with script revisions |
| Default TTL (music) | Permanent | Licensed music doesn't change |
| Default TTL (SFX) | Permanent | Sound effects don't change |
| Eviction policy | LRU (Least Recently Used) | Keep most valuable assets |
| Cleanup trigger | When cache exceeds 10 GB | Automatic cleanup |

### Cache Commands

```bash
# View cache statistics
mythforge cache stats

# Clear specific cache type
mythforge cache clear --type images

# Clear cache older than N days
mythforge cache clear --type images --older-than 7d

# Clear entire cache
mythforge cache clear --all

# Export cache for backup
mythforge cache export --output backup/cache_export.tar.gz

# Import cache from backup
mythforge cache import --input backup/cache_export.tar.gz
```

---

## Asset Lifecycle

### Generation Phase

```
1. Agent requests asset generation
2. Compute cache key from input parameters
3. Check cache:
   a. Cache hit → Load from cache (cost: $0.00)
   b. Cache miss → Generate via provider (cost: varies)
4. If generated:
   a. Validate asset (file exists, size > 0, format correct)
   b. Save to project assets directory
   c. Save to cache with metadata
   d. Log generation cost
5. Return asset path to agent
```

### Storage Phase

```
1. Asset stored in project directory: .mythforge/projects/{project_id}/assets/
2. Asset also stored in cache (if cacheable): .mythforge/cache/
3. Artifact metadata stored in project artifacts directory
4. All paths tracked in pipeline state checkpoint
```

### Cleanup Phase

```
After pipeline completion:
1. Move temporary files to /dev/null (delete)
2. Keep all final output files
3. Keep all artifacts (for reproducibility)
4. Keep all intermediate assets (for re-rendering)
5. Archive project if inactive for 90+ days
```

---

## Storage Requirements

### Per-Project Storage

| Component | Min Size | Max Size | Typical |
|-----------|----------|----------|---------|
| Images (20 scenes) | 50 MB | 200 MB | 100 MB |
| Narration | 30 MB | 100 MB | 60 MB |
| Music | 5 MB | 20 MB | 10 MB |
| SFX | 10 MB | 50 MB | 25 MB |
| Final video | 200 MB | 500 MB | 300 MB |
| Artifacts | 100 KB | 500 KB | 200 KB |
| Checkpoints | 50 KB | 200 KB | 100 KB |
| **Total** | **~300 MB** | **~900 MB** | **~500 MB** |

### System-Wide Storage

| Component | Size |
|-----------|------|
| Cache (images) | Up to 5 GB |
| Cache (narration) | Up to 3 GB |
| Cache (music) | Up to 1 GB |
| Cache (SFX) | Up to 1 GB |
| Music library | Up to 5 GB |
| SFX library | Up to 2 GB |
| Knowledge Base | Up to 100 MB |
| **Total** | **~17 GB** |

### Disk Space Management

```bash
# Check disk usage
mythforge storage usage

# Archive old projects
mythforge project archive --older-than 90d --output archive/

# Clean up temp files
mythforge storage cleanup --temp-only

# Estimate space for new project
mythforge storage estimate --scenes 20
```

---

## Backup Strategy

### What to Back Up

| Priority | Component | Frequency | Rationale |
|----------|-----------|-----------|-----------|
| Critical | Knowledge Base | On change | Foundation data |
| Critical | Character Bible | On change | Visual consistency |
| Critical | Playbooks | On change | Style definitions |
| High | Project artifacts | After each pipeline | Reproducibility |
| High | Final outputs | After each pipeline | Published content |
| Medium | Cache | Weekly | Cost savings |
| Low | Temp files | Never | Disposable |

### Backup Commands

```bash
# Backup knowledge base
mythforge backup knowledge --output backup/knowledge_$(date +%Y%m%d).tar.gz

# Backup project
mythforge backup project --id shango_thunder_20260628 --output backup/

# Backup everything
mythforge backup full --output backup/full_$(date +%Y%m%d).tar.gz
```

---

## Asset Quality Standards

### Images

| Standard | Requirement | Validation |
|----------|-------------|------------|
| Resolution | ≥ 1024x1024 | FFprobe |
| Format | PNG or JPEG | File extension check |
| File size | ≥ 50 KB | Size check |
| Blank frames | 0 | Pixel analysis |
| Text artifacts | 0 | LLM visual check |

### Audio

| Standard | Requirement | Validation |
|----------|-------------|------------|
| Sample rate | ≥ 44100 Hz | FFprobe |
| Bit depth | ≥ 16-bit | FFprobe |
| Format | MP3, WAV, or AAC | File extension check |
| File size | ≥ 10 KB | Size check |
| Silence | < 3 seconds continuous | Audio analysis |

### Video

| Standard | Requirement | Validation |
|----------|-------------|------------|
| Resolution | 1920x1080 | FFprobe |
| Frame rate | 30 fps | FFprobe |
| Codec | H.264 | FFprobe |
| Audio codec | AAC | FFprobe |
| Audio levels | -14 LUFS ± 2 | FFprobe |
| Duration | 10-15 minutes | FFprobe |