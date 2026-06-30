# Artifact System Architecture

## Overview

The Artifact System is the canonical data layer of MythForge. It enforces a strict contract: **no raw strings cross stage boundaries**. Every piece of data flowing through the pipeline is a strongly-typed artifact with full provenance, hashing, and validation.

## Design Principles

1. **Strong Typing** — Every artifact is a concrete class with validated fields.
2. **Content Isolation** — Domain content is separate from metadata and provenance.
3. **Deterministic Hashing** — SHA-256 of content fields enables deduplication and integrity checks.
4. **Provider Agnostic** — Artifacts contain no provider-specific logic.
5. **Self-Validating** — Each artifact knows its own invariants.
6. **Serializable** — Every artifact roundtrips through JSON, YAML, and Dict.
7. **Versioned** — Schema versions with migration support.

## Layer Diagram

```
┌─────────────────────────────────────────────────┐
│                   Workflow Engine                │
│  (DAG executor, checkpointing, event bus)        │
└──────────────────────┬──────────────────────────┘
                       │ consumes / produces
                       ▼
┌─────────────────────────────────────────────────┐
│                  Artifact Layer                  │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ BaseArtifact  │  │  Models      │             │
│  │  - validate   │  │  - Metadata  │             │
│  │  - serialize  │  │  - Provenance│             │
│  │  - hash       │  └──────────────┘             │
│  └──────┬───────┘                                │
│         │                                        │
│  ┌──────┴───────────────────────────────────┐   │
│  │          Concrete Artifacts              │   │
│  │  Research │ Script │ Scene │ Image │ ...  │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  Registry   │  │  Factory   │  │ Exporter │  │
│  └────────────┘  └────────────┘  └──────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ consumed by
                       ▼
┌─────────────────────────────────────────────────┐
│               Prompt Engine                      │
│  (templates, rendering, composition)             │
└──────────────────────┬──────────────────────────┘
                       │ sends to
                       ▼
┌─────────────────────────────────────────────────┐
│              Provider SDK                        │
│  (OpenAI, Stability, ElevenLabs, etc.)           │
└──────────────────────┬──────────────────────────┘
                       │ returns
                       ▼
┌─────────────────────────────────────────────────┐
│            Back to Artifact Layer                │
│  (new artifacts with provenance attached)         │
└─────────────────────────────────────────────────┘
```

## Class Hierarchy

```
BaseArtifact (abstract)
├── ResearchArtifact
├── ScriptArtifact
├── SceneArtifact
├── ImageArtifact
├── NarrationArtifact
├── MusicArtifact
├── SFXArtifact
├── TimelineArtifact
├── ThumbnailArtifact
├── MetadataArtifact
└── VideoArtifact
```

## Data Flow

### Artifact Structure

Every artifact serializes to this envelope:

```json
{
  "artifact_type": "ScriptArtifact",
  "version": "0.1.0",
  "content_hash": "a1b2c3...",
  "metadata": {
    "name": "...",
    "description": "...",
    "tags": [],
    "author": "..."
  },
  "provenance": {
    "artifact_id": "uuid",
    "artifact_type": "ScriptArtifact",
    "provider": "openai",
    "model": "gpt-4",
    "workflow_stage": "scripting",
    "prompt_hash": "...",
    "cost_usd": 0.05,
    "duration_s": 3.2,
    "timestamp": "2026-06-30T08:00:00Z",
    "software_version": "1.0.0",
    "manifest_id": "m-001"
  },
  "content": {
    // Domain-specific fields
  }
}
```

### Provenance Separation

Provenance is **never mixed into content**. This means:
- Content hashing is deterministic and unaffected by runtime metadata.
- Provider details (model, cost, duration) are tracked separately.
- The same content produced by different providers has the same content hash.

### Hashing Strategy

Content hashing uses `ArtifactHasher` which:
1. Extracts only content fields from the artifact.
2. Serializes to a canonical JSON string (sorted keys).
3. Computes SHA-256 of the canonical bytes.

This ensures:
- Same content → same hash (deterministic).
- Different content → different hash.
- Metadata/provenance changes don't affect content hash.

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `BaseArtifact` | Abstract contract: validate, serialize, hash, export |
| `ArtifactMetadata` | Name, description, tags, author, file info |
| `ArtifactProvenance` | Provider, model, cost, duration, timestamps |
| `ArtifactHasher` | Deterministic SHA-256 hashing |
| `ArtifactVersion` | Semantic version parsing and comparison |
| `ArtifactSerializer` | Stateless JSON/YAML/Dict conversion |
| `ArtifactValidator` | Full validation including hash integrity |
| `ArtifactRegistry` | Type registration, lookup, version migration |
| `ArtifactFactory` | Construct artifacts from raw data |
| `ArtifactExporter` | Export to JSON, Markdown, Dict |