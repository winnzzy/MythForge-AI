"""
Semantic versioning for Artifacts.

Lightweight ``ArtifactVersion`` class supporting major/minor/patch
comparison, bumping, and string conversion.  Embedded in every artifact
for manifest tracking and migration support.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional

from .exceptions import InvalidArtifactVersionError

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?$")


@total_ordering
@dataclass(frozen=True)
class ArtifactVersion:
    """Immutable semantic version for artifacts.

    Parameters
    ----------
    major:
        Breaking changes to artifact schema.
    minor:
        Backward-compatible additions (new optional fields).
    patch:
        Cosmetic / wording changes that don't affect structure.
    pre_release:
        Optional pre-release label (e.g. ``"beta.1"``).
    """

    major: int = 0
    minor: int = 0
    patch: int = 0
    pre_release: Optional[str] = None

    # -- Parsing --

    @classmethod
    def parse(cls, version_string: str) -> ArtifactVersion:
        """Parse a ``"MAJOR.MINOR.PATCH"`` string."""
        match = _SEMVER_RE.match(version_string.strip())
        if not match:
            raise InvalidArtifactVersionError(version_string)
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            pre_release=match.group(4),
        )

    # -- Bumping --

    def bump_major(self) -> ArtifactVersion:
        return ArtifactVersion(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> ArtifactVersion:
        return ArtifactVersion(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> ArtifactVersion:
        return ArtifactVersion(major=self.major, minor=self.minor, patch=self.patch + 1)

    def bump(self, level: str) -> ArtifactVersion:
        """Bump by level name (``"major"``, ``"minor"``, or ``"patch"``)."""
        method = getattr(self, f"bump_{level}", None)
        if method is None:
            raise ValueError(f"Invalid bump level: {level!r}")
        return method()

    # -- Comparison --

    @property
    def _sort_key(self):
        pre = self.pre_release or ""
        return (self.major, self.minor, self.patch, pre)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArtifactVersion):
            return NotImplemented
        return self._sort_key == other._sort_key

    def __lt__(self, other: ArtifactVersion) -> bool:
        if not isinstance(other, ArtifactVersion):
            return NotImplemented
        return self._sort_key < other._sort_key

    def __hash__(self) -> int:
        return hash(self._sort_key)

    # -- String --

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            return f"{base}-{self.pre_release}"
        return base

    def __repr__(self) -> str:
        return f"ArtifactVersion({self!s})"

    # -- Serialisation --

    def to_dict(self) -> dict:
        d = {"major": self.major, "minor": self.minor, "patch": self.patch}
        if self.pre_release:
            d["pre_release"] = self.pre_release
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ArtifactVersion:
        return cls(
            major=data.get("major", 0),
            minor=data.get("minor", 0),
            patch=data.get("patch", 0),
            pre_release=data.get("pre_release"),
        )

    # -- Convenience --

    @classmethod
    def initial(cls) -> ArtifactVersion:
        return cls(major=0, minor=1, patch=0)

    @classmethod
    def zero(cls) -> ArtifactVersion:
        return cls(major=0, minor=0, patch=0)