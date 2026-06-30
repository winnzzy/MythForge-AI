# MythForge Artifact System

The Artifact System is the foundational data layer of the MythForge pipeline. Every workflow stage consumes artifacts and produces artifacts. Providers never exchange raw strings — everything passes through strongly-typed artifacts.

## Architecture

```
Workflow → Artifact → Prompt Engine → Provider SDK → Artifact → Workflow
```

## Quick Start

```python
from mythforge.artifacts import (
    ScriptArtifact,
    ArtifactExporter,
    ArtifactFactory,
    ArtifactProvenance,
)

# Create a strongly-typed artifact
script = ScriptArtifact(
    title="Dragon's Fury",
    genre="Fantasy",
    raw_text="FADE IN:\nEXT. MOUNTAIN - DAY\nA dragon soars above.",
    provenance=ArtifactProvenance(
        provider="openai",
        model="gpt-4",
        workflow_stage="scripting",
        cost_usd=0.05,
    ),
)

# Validate
assert script.is_valid()

# Compute deterministic hash
script.compute_hash()

# Export to multiple formats
json_str = ArtifactExporter.to_json(script)
markdown = ArtifactExporter.to_markdown(script)
dict_data = ArtifactExporter.to_dict(script)

# Reconstruct from any format
factory = ArtifactFactory()
reconstructed = factory.from_json(json_str)
assert reconstructed.content_hash == script.content_hash
```

## Artifact Types

| Type | Purpose |
|------|---------|
| `ResearchArtifact` | Research results, findings, sources |
| `ScriptArtifact` | Screenplay with scenes and dialogue |
| `SceneArtifact` | Single scene description |
| `ImageArtifact` | Generated or sourced images |
| `NarrationArtifact` | Narration audio with transcript |
| `MusicArtifact` | Background music tracks |
| `SFXArtifact` | Sound effects |
| `TimelineArtifact` | Master compositing timeline |
| `ThumbnailArtifact` | Video thumbnails |
| `MetadataArtifact` | Project-level metadata |
| `VideoArtifact` | Final rendered video |

## Core Features

- **Validation** — Every artifact validates itself
- **Serialization** — JSON, YAML, Dict
- **Hashing** — Deterministic SHA-256
- **Versioning** — Semantic version with migration support
- **Provenance** — Provider, model, cost, duration, timestamps
- **Metadata** — Name, tags, description, file info
- **Registry** — Auto-registration, lookup, migration
- **Factory** — Construct from JSON, Dict, YAML
- **Exporters** — JSON, Markdown, Dict

## Modules

| Module | Purpose |
|--------|---------|
| `exceptions.py` | Custom exception hierarchy |
| `models.py` | `ArtifactMetadata`, `ArtifactProvenance` |
| `hashing.py` | `ArtifactHasher` — deterministic SHA-256 |
| `versioning.py` | `ArtifactVersion` — semantic versioning |
| `base.py` | `BaseArtifact`, Serializer, Validator, Registry, Factory, Exporter |
| `artifacts.py` | All 11 concrete artifact types |
| `__init__.py` | Public API with auto-registration |