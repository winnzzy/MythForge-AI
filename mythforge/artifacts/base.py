"""
Base artifact and core infrastructure.

Contains:
- :class:`BaseArtifact` — abstract base for all artifact types.
- :class:`ArtifactSerializer` — JSON/YAML/Markdown serialisation.
- :class:`ArtifactValidator` — validation framework.
- :class:`ArtifactRegistry` — type registry with version migration.
- :class:`ArtifactFactory` — construct artifacts from raw data.
- :class:`ArtifactExporter` — export to JSON/Markdown/Dict.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

from .exceptions import (
    ArtifactValidationError,
    ArtifactSerializationError,
    ArtifactAlreadyRegisteredError,
    ArtifactNotRegisteredError,
    ArtifactExportError,
    ArtifactFactoryError,
    UnknownArtifactTypeError,
)
from .hashing import ArtifactHasher
from .models import ArtifactMetadata, ArtifactProvenance
from .versioning import ArtifactVersion


# ===========================================================================
# Base Artifact
# ===========================================================================

class BaseArtifact(ABC):
    """Abstract base class for all MythForge artifacts.

    Every artifact carries:

    - **content** — the domain-specific payload (defined by subclasses).
    - **metadata** — descriptive information (name, tags, file path, etc.).
    - **provenance** — how/when/where this artifact was created.
    - **version** — semantic version of the artifact schema.
    - **content_hash** — deterministic SHA-256 of the content.

    Subclasses must implement:

    - :meth:`artifact_type` — type discriminator string.
    - :meth:`content_fields` — dict of content-only fields for hashing.
    - :meth:`validate_content` — domain-specific validation.
    - :meth:`to_markdown` — human-readable export.
    - :meth:`_content_dict` — content-only dict for serialisation.
    """

    def __init__(
        self,
        *,
        metadata: Optional[ArtifactMetadata] = None,
        provenance: Optional[ArtifactProvenance] = None,
        version: Optional[ArtifactVersion] = None,
        manifest_id: str = "",
    ) -> None:
        self.metadata = metadata or ArtifactMetadata()
        self.provenance = provenance or ArtifactProvenance()
        self.version = version or ArtifactVersion.initial()
        self.content_hash: str = ""
        if manifest_id:
            self.provenance.manifest_id = manifest_id
        self.provenance.artifact_type = self.artifact_type()

    # -- Abstract interface --

    @classmethod
    @abstractmethod
    def artifact_type(cls) -> str:
        """Return the type discriminator string (e.g. ``"ScriptArtifact"``)."""
        ...

    @abstractmethod
    def content_fields(self) -> Dict[str, Any]:
        """Return the content-only fields as a dict (for hashing / export)."""
        ...

    @abstractmethod
    def validate_content(self) -> List[str]:
        """Validate domain-specific content.  Return list of error strings."""
        ...

    @abstractmethod
    def to_markdown(self) -> str:
        """Export artifact content as human-readable Markdown."""
        ...

    @abstractmethod
    def _content_dict(self) -> Dict[str, Any]:
        """Full content dict for JSON/YAML serialisation."""
        ...

    @classmethod
    @abstractmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> "BaseArtifact":
        """Reconstruct an artifact from its content dict."""
        ...

    # -- Concrete helpers --

    @property
    def artifact_id(self) -> str:
        return self.provenance.artifact_id

    def compute_hash(self) -> str:
        """Compute and store the deterministic content hash."""
        hasher = ArtifactHasher()
        self.content_hash = hasher.hash_content(self.content_fields())
        return self.content_hash

    def validate(self) -> List[str]:
        """Run all validations.  Returns list of error strings (empty = valid)."""
        errors: List[str] = []
        if not self.provenance.artifact_type:
            errors.append("provenance.artifact_type is required")
        content_errors = self.validate_content()
        errors.extend(content_errors)
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    # -- Serialisation --

    def to_dict(self) -> Dict[str, Any]:
        """Full serialisation including metadata, provenance, version, hash."""
        return {
            "artifact_type": self.artifact_type(),
            "version": str(self.version),
            "content_hash": self.content_hash,
            "metadata": self.metadata.to_dict(),
            "provenance": self.provenance.to_dict(),
            "content": self._content_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseArtifact":
        """Deserialise from a dict.  Uses the registry if the type differs."""
        content = data.get("content", data)
        metadata = ArtifactMetadata.from_dict(data.get("metadata", {}))
        provenance = ArtifactProvenance.from_dict(data.get("provenance", {}))
        version_str = data.get("version", "0.1.0")
        version = ArtifactVersion.parse(version_str)
        artifact = cls._from_content_dict(
            content,
            metadata=metadata,
            provenance=provenance,
            version=version,
        )
        artifact.content_hash = data.get("content_hash", "")
        return artifact

    def to_json(self, *, indent: int = 2) -> str:
        """Serialise to JSON string."""
        try:
            return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)
        except Exception as exc:
            raise ArtifactSerializationError(str(exc), format="json")

    @classmethod
    def from_json(cls, text: str) -> "BaseArtifact":
        """Deserialise from a JSON string."""
        try:
            data = json.loads(text)
        except Exception as exc:
            raise ArtifactSerializationError(str(exc), format="json")
        return cls.from_dict(data)

    def to_yaml(self) -> str:
        """Serialise to YAML string (requires PyYAML)."""
        try:
            import yaml
        except ImportError:
            raise ArtifactSerializationError("PyYAML is required for YAML export", format="yaml")
        try:
            return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as exc:
            raise ArtifactSerializationError(str(exc), format="yaml")

    @classmethod
    def from_yaml(cls, text: str) -> "BaseArtifact":
        """Deserialise from a YAML string (requires PyYAML)."""
        try:
            import yaml
        except ImportError:
            raise ArtifactSerializationError("PyYAML is required for YAML import", format="yaml")
        try:
            data = yaml.safe_load(text)
        except Exception as exc:
            raise ArtifactSerializationError(str(exc), format="yaml")
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return f"<{self.artifact_type()} id={self.artifact_id} hash={self.content_hash[:12]}>"


# ===========================================================================
# Artifact Serializer
# ===========================================================================

class ArtifactSerializer:
    """Serialise / deserialise artifacts to/from JSON, YAML, and Dict.

    The serializer is stateless and works with any :class:`BaseArtifact`
    subclass.  It delegates to the artifact's own ``to_dict`` / ``from_dict``
    methods and adds format-specific handling.
    """

    @staticmethod
    def to_json(artifact: BaseArtifact, *, indent: int = 2) -> str:
        return artifact.to_json(indent=indent)

    @staticmethod
    def from_json(text: str, artifact_class: type) -> BaseArtifact:
        return artifact_class.from_json(text)

    @staticmethod
    def to_yaml(artifact: BaseArtifact) -> str:
        return artifact.to_yaml()

    @staticmethod
    def from_yaml(text: str, artifact_class: type) -> BaseArtifact:
        return artifact_class.from_yaml(text)

    @staticmethod
    def to_dict(artifact: BaseArtifact) -> Dict[str, Any]:
        return artifact.to_dict()

    @staticmethod
    def from_dict(data: Dict[str, Any], artifact_class: type) -> BaseArtifact:
        return artifact_class.from_dict(data)


# ===========================================================================
# Artifact Validator
# ===========================================================================

class ArtifactValidator:
    """Validate artifacts.

    Validates required fields, content constraints, and hash integrity.
    """

    def validate(self, artifact: BaseArtifact) -> List[str]:
        """Run full validation on an artifact."""
        errors: List[str] = []
        if not artifact.artifact_type():
            errors.append("artifact_type is required")
        if not artifact.provenance.artifact_type:
            errors.append("provenance.artifact_type is required")
        if not str(artifact.version):
            errors.append("version is required")
        content_errors = artifact.validate_content()
        errors.extend(content_errors)
        return errors

    def is_valid(self, artifact: BaseArtifact) -> bool:
        return len(self.validate(artifact)) == 0

    def validate_hash(self, artifact: BaseArtifact) -> bool:
        """Verify the content hash matches the current content."""
        if not artifact.content_hash:
            return False
        hasher = ArtifactHasher()
        expected = hasher.hash_content(artifact.content_fields())
        return artifact.content_hash == expected


# ===========================================================================
# Artifact Registry
# ===========================================================================

class ArtifactRegistry:
    """Registry of artifact types.

    Supports:
    - Register / unregister artifact types.
    - Lookup by name.
    - Version migration via registered migrators.
    """

    def __init__(self) -> None:
        self._types: Dict[str, Type[BaseArtifact]] = {}
        self._migrators: Dict[str, Dict[str, Any]] = {}  # type -> {from_ver: fn}

    def register(self, cls: Type[BaseArtifact]) -> None:
        """Register an artifact class."""
        name = cls.artifact_type()
        if name in self._types:
            raise ArtifactAlreadyRegisteredError(name)
        self._types[name] = cls

    def unregister(self, name: str) -> None:
        """Unregister an artifact type."""
        if name not in self._types:
            raise ArtifactNotRegisteredError(name)
        del self._types[name]

    def get(self, name: str) -> Type[BaseArtifact]:
        """Lookup an artifact class by name."""
        if name not in self._types:
            raise ArtifactNotRegisteredError(name)
        return self._types[name]

    def has(self, name: str) -> bool:
        return name in self._types

    def names(self) -> List[str]:
        return list(self._types.keys())

    def register_migrator(self, artifact_type: str, from_version: str, migrator_fn) -> None:
        """Register a version migration function."""
        if artifact_type not in self._migrators:
            self._migrators[artifact_type] = {}
        self._migrators[artifact_type][from_version] = migrator_fn

    def migrate(self, data: Dict[str, Any], target_version: str) -> Dict[str, Any]:
        """Migrate artifact data to the target version using registered migrators."""
        artifact_type = data.get("artifact_type", "")
        current_version = data.get("version", "0.1.0")
        if current_version == target_version:
            return data
        migrators = self._migrators.get(artifact_type, {})
        migrated = dict(data)
        while migrated.get("version", "") != target_version:
            ver = migrated.get("version", "")
            migrator = migrators.get(ver)
            if migrator is None:
                break
            migrated = migrator(migrated)
        return migrated


# Global registry singleton
_global_registry = ArtifactRegistry()


def get_registry() -> ArtifactRegistry:
    """Return the global artifact registry."""
    return _global_registry


# ===========================================================================
# Artifact Factory
# ===========================================================================

class ArtifactFactory:
    """Construct artifacts from raw data (JSON, dict, YAML).

    The factory uses the registry to resolve the correct artifact class
    from the ``artifact_type`` field in the data.
    """

    def __init__(self, registry: Optional[ArtifactRegistry] = None) -> None:
        self._registry = registry or get_registry()

    def from_dict(self, data: Dict[str, Any]) -> BaseArtifact:
        """Construct an artifact from a dict."""
        artifact_type = data.get("artifact_type", "")
        if not artifact_type:
            raise ArtifactFactoryError("Missing 'artifact_type' field in data")
        cls = self._registry.get(artifact_type)
        return cls.from_dict(data)

    def from_json(self, text: str) -> BaseArtifact:
        """Construct an artifact from a JSON string."""
        try:
            data = json.loads(text)
        except Exception as exc:
            raise ArtifactSerializationError(str(exc), format="json")
        return self.from_dict(data)

    def from_yaml(self, text: str) -> BaseArtifact:
        """Construct an artifact from a YAML string."""
        try:
            import yaml
            data = yaml.safe_load(text)
        except ImportError:
            raise ArtifactSerializationError("PyYAML is required", format="yaml")
        except Exception as exc:
            raise ArtifactSerializationError(str(exc), format="yaml")
        return self.from_dict(data)

    def from_dict_with_migration(self, data: Dict[str, Any], target_version: str) -> BaseArtifact:
        """Construct from a dict, migrating to the target version first."""
        migrated = self._registry.migrate(data, target_version)
        return self.from_dict(migrated)


# ===========================================================================
# Artifact Exporter
# ===========================================================================

class ArtifactExporter:
    """Export artifacts to JSON, Markdown, or plain Dict.

    Stateless; works with any :class:`BaseArtifact` subclass.
    """

    @staticmethod
    def to_json(artifact: BaseArtifact, *, indent: int = 2) -> str:
        """Export as JSON string."""
        return artifact.to_json(indent=indent)

    @staticmethod
    def to_markdown(artifact: BaseArtifact) -> str:
        """Export as Markdown string."""
        parts: List[str] = []
        parts.append(f"# {artifact.artifact_type()}: {artifact.metadata.name}")
        parts.append("")
        parts.append(f"**Version:** {artifact.version}")
        parts.append(f"**ID:** {artifact.artifact_id}")
        parts.append(f"**Hash:** {artifact.content_hash}")
        if artifact.metadata.description:
            parts.append(f"**Description:** {artifact.metadata.description}")
        if artifact.metadata.tags:
            parts.append(f"**Tags:** {', '.join(artifact.metadata.tags)}")
        parts.append("")
        parts.append("## Provenance")
        parts.append("")
        prov = artifact.provenance
        if prov.provider:
            parts.append(f"- **Provider:** {prov.provider}")
        if prov.model:
            parts.append(f"- **Model:** {prov.model}")
        if prov.workflow_stage:
            parts.append(f"- **Workflow Stage:** {prov.workflow_stage}")
        if prov.manifest_id:
            parts.append(f"- **Manifest ID:** {prov.manifest_id}")
        if prov.cost_usd > 0:
            parts.append(f"- **Cost:** ${prov.cost_usd:.4f}")
        if prov.duration_s > 0:
            parts.append(f"- **Duration:** {prov.duration_s:.2f}s")
        parts.append(f"- **Timestamp:** {prov.timestamp}")
        parts.append("")
        parts.append("## Content")
        parts.append("")
        parts.append(artifact.to_markdown())
        return "\n".join(parts)

    @staticmethod
    def to_dict(artifact: BaseArtifact) -> Dict[str, Any]:
        """Export as a plain Python dict."""
        return artifact.to_dict()