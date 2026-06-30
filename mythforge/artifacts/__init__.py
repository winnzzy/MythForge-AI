"""
MythForge Artifact System
=========================

Strongly-typed workflow artifacts that flow between pipeline stages.

Every workflow stage **consumes** artifacts and **produces** artifacts.
Providers never exchange raw strings — everything passes through typed
artifacts with full provenance, hashing, versioning, and validation.

Quick start::

    from mythforge.artifacts import ScriptArtifact, ArtifactExporter

    script = ScriptArtifact(title="My Film", raw_text="FADE IN:")
    script.compute_hash()
    print(ArtifactExporter.to_markdown(script))

Architecture
------------

::

    Workflow → Artifact → Prompt Engine → Provider SDK → Artifact → Workflow

All concrete artifact types are auto-registered in the global registry
on import so that :class:`ArtifactFactory` can reconstruct any artifact
from its JSON/dict representation.
"""

from __future__ import annotations

# -- Exceptions --
from .exceptions import (
    ArtifactError,
    ArtifactValidationError,
    ArtifactSerializationError,
    ArtifactRegistryError,
    ArtifactAlreadyRegisteredError,
    ArtifactNotRegisteredError,
    ArtifactFactoryError,
    UnknownArtifactTypeError,
    ArtifactVersionError,
    InvalidArtifactVersionError,
    ArtifactExportError,
    ArtifactHashError,
)

# -- Models --
from .models import ArtifactMetadata, ArtifactProvenance

# -- Infrastructure --
from .hashing import ArtifactHasher
from .versioning import ArtifactVersion
from .base import (
    BaseArtifact,
    ArtifactSerializer,
    ArtifactValidator,
    ArtifactRegistry,
    ArtifactFactory,
    ArtifactExporter,
    get_registry,
)

# -- Concrete artifacts --
from .artifacts import (
    ResearchArtifact,
    ScriptArtifact,
    SceneArtifact,
    ImageArtifact,
    NarrationArtifact,
    MusicArtifact,
    SFXArtifact,
    TimelineArtifact,
    ThumbnailArtifact,
    MetadataArtifact,
    VideoArtifact,
)

# ---------------------------------------------------------------------------
# Auto-register all artifact types in the global registry
# ---------------------------------------------------------------------------

_ALL_ARTIFACTS = [
    ResearchArtifact,
    ScriptArtifact,
    SceneArtifact,
    ImageArtifact,
    NarrationArtifact,
    MusicArtifact,
    SFXArtifact,
    TimelineArtifact,
    ThumbnailArtifact,
    MetadataArtifact,
    VideoArtifact,
]

_registry = get_registry()
for _cls in _ALL_ARTIFACTS:
    if not _registry.has(_cls.artifact_type()):
        _registry.register(_cls)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Exceptions
    "ArtifactError",
    "ArtifactValidationError",
    "ArtifactSerializationError",
    "ArtifactRegistryError",
    "ArtifactAlreadyRegisteredError",
    "ArtifactNotRegisteredError",
    "ArtifactFactoryError",
    "UnknownArtifactTypeError",
    "ArtifactVersionError",
    "InvalidArtifactVersionError",
    "ArtifactExportError",
    "ArtifactHashError",
    # Models
    "ArtifactMetadata",
    "ArtifactProvenance",
    # Infrastructure
    "ArtifactHasher",
    "ArtifactVersion",
    "BaseArtifact",
    "ArtifactSerializer",
    "ArtifactValidator",
    "ArtifactRegistry",
    "ArtifactFactory",
    "ArtifactExporter",
    "get_registry",
    # Concrete artifacts
    "ResearchArtifact",
    "ScriptArtifact",
    "SceneArtifact",
    "ImageArtifact",
    "NarrationArtifact",
    "MusicArtifact",
    "SFXArtifact",
    "TimelineArtifact",
    "ThumbnailArtifact",
    "MetadataArtifact",
    "VideoArtifact",
]