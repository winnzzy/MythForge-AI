"""
Artifact System data models.

Core data structures shared across all artifact types:

- :class:`ArtifactMetadata` — descriptive metadata (name, description, tags).
- :class:`ArtifactProvenance` — provenance tracking (provider, model, cost, etc.).

Both are JSON-serialisable via ``to_dict`` / ``from_dict``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Artifact Metadata
# ---------------------------------------------------------------------------

@dataclass
class ArtifactMetadata:
    """Descriptive metadata for an artifact.

    This is separate from provenance — metadata describes *what* the artifact
    is, while provenance describes *how* it was created.

    Parameters
    ----------
    name:
        Human-readable name.
    description:
        What this artifact contains.
    tags:
        Searchable tags for filtering and discovery.
    author:
        Who created this artifact (human or system component).
    category:
        Category classification (e.g. ``"research"``, ``"scene"``, ``"audio"``).
    language:
        Content language code (e.g. ``"en"``).
    mime_type:
        MIME type if the artifact wraps binary content.
    file_path:
        Path to the associated file on disk (if any).
    file_size_bytes:
        Size of the associated file in bytes.
    duration_s:
        Duration in seconds (for audio/video artifacts).
    dimensions:
        Image/video dimensions as ``{"width": w, "height": h}``.
    extra:
        Arbitrary extra metadata.
    """

    name: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    author: str = ""
    category: str = ""
    language: str = ""
    mime_type: str = ""
    file_path: str = ""
    file_size_bytes: int = 0
    duration_s: float = 0.0
    dimensions: Dict[str, int] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    # -- serialisation --

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ArtifactMetadata:
        """Deserialise from a dict, ignoring unknown keys."""
        known = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# Artifact Provenance
# ---------------------------------------------------------------------------

@dataclass
class ArtifactProvenance:
    """Provenance record — *how* and *when* an artifact was created.

    Provenance is separated from content so that artifacts remain
    provider-agnostic.  The provenance tracks the provider, model, and
    workflow context that produced the artifact.

    Parameters
    ----------
    artifact_id:
        Unique identifier for the artifact instance.
    artifact_type:
        Type discriminator (e.g. ``"ScriptArtifact"``).
    provider:
        AI provider that produced the content (e.g. ``"openai"``).
    model:
        Model identifier (e.g. ``"gpt-4o"``).
    workflow_stage:
        Pipeline stage that created this artifact (e.g. ``"RESEARCH"``).
    prompt_hash:
        SHA-256 hash of the prompt that generated the content.
    manifest_id:
        ID of the manifest this artifact belongs to.
    cost_usd:
        Cost in USD to produce this artifact.
    duration_s:
        Wall-clock time in seconds to produce this artifact.
    timestamp:
        ISO-8601 UTC timestamp of creation.
    software_version:
        Version of the MythForge software that created this.
    parent_artifact_id:
        ID of the parent artifact (for derived artifacts).
    chain:
        Ordered list of ancestor artifact IDs.
    extra:
        Arbitrary extra provenance data.
    """

    artifact_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    artifact_type: str = ""
    provider: str = ""
    model: str = ""
    workflow_stage: str = ""
    prompt_hash: str = ""
    manifest_id: str = ""
    cost_usd: float = 0.0
    duration_s: float = 0.0
    timestamp: str = field(default_factory=lambda: _now_iso())
    software_version: str = ""
    parent_artifact_id: str = ""
    chain: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    # -- serialisation --

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ArtifactProvenance:
        """Deserialise from a dict, ignoring unknown keys."""
        known = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """UTC now as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()