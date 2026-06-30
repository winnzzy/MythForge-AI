"""
Artifact System exceptions.

All custom exceptions for the artifact subsystem.
Every exception inherits from :class:`ArtifactError` for unified error handling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ArtifactError(Exception):
    """Base exception for all artifact errors."""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class ArtifactValidationError(ArtifactError):
    """Raised when artifact validation fails."""

    def __init__(self, message: str, *, errors: Optional[List[str]] = None) -> None:
        self.validation_errors = errors or []
        super().__init__(message, details={"validation_errors": self.validation_errors})


# ---------------------------------------------------------------------------
# Serialization errors
# ---------------------------------------------------------------------------

class ArtifactSerializationError(ArtifactError):
    """Raised when serialization or deserialization fails."""

    def __init__(self, message: str, *, format: str = "") -> None:
        self.format = format
        super().__init__(message, details={"format": format})


# ---------------------------------------------------------------------------
# Registry errors
# ---------------------------------------------------------------------------

class ArtifactRegistryError(ArtifactError):
    """Raised for registry-related errors."""
    pass


class ArtifactAlreadyRegisteredError(ArtifactRegistryError):
    """Raised when attempting to register an artifact type that is already registered."""

    def __init__(self, artifact_type: str) -> None:
        self.artifact_type = artifact_type
        super().__init__(f"Artifact type already registered: {artifact_type!r}")


class ArtifactNotRegisteredError(ArtifactRegistryError):
    """Raised when looking up an artifact type that is not registered."""

    def __init__(self, artifact_type: str) -> None:
        self.artifact_type = artifact_type
        super().__init__(f"Artifact type not registered: {artifact_type!r}")


# ---------------------------------------------------------------------------
# Factory errors
# ---------------------------------------------------------------------------

class ArtifactFactoryError(ArtifactError):
    """Raised when artifact construction from raw data fails."""
    pass


class UnknownArtifactTypeError(ArtifactFactoryError):
    """Raised when the factory encounters an unknown artifact type."""

    def __init__(self, artifact_type: str) -> None:
        self.artifact_type = artifact_type
        super().__init__(f"Unknown artifact type: {artifact_type!r}")


# ---------------------------------------------------------------------------
# Version errors
# ---------------------------------------------------------------------------

class ArtifactVersionError(ArtifactError):
    """Raised for version-related errors."""
    pass


class InvalidArtifactVersionError(ArtifactVersionError):
    """Raised when a version string is invalid."""

    def __init__(self, version_string: str) -> None:
        self.version_string = version_string
        super().__init__(f"Invalid artifact version string: {version_string!r}")


# ---------------------------------------------------------------------------
# Export errors
# ---------------------------------------------------------------------------

class ArtifactExportError(ArtifactError):
    """Raised when artifact export fails."""

    def __init__(self, message: str, *, format: str = "") -> None:
        self.format = format
        super().__init__(message, details={"format": format})


# ---------------------------------------------------------------------------
# Hash errors
# ---------------------------------------------------------------------------

class ArtifactHashError(ArtifactError):
    """Raised when hashing fails."""
    pass