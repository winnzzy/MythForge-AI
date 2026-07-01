"""
Semantic versioning for Prompt Packages.

Implements a lightweight ``PromptVersion`` class that supports
major / minor / patch comparison, bumping, and string conversion.

The version is embedded into every :class:`PromptPackage` and used for
cache invalidation, manifest tracking, and reproducibility checks.

Usage::

    from mythforge.prompt_engine.versioning import PromptVersion

    v = PromptVersion.parse("1.2.3")
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3

    v2 = v.bump_minor()
    assert str(v2) == "1.3.0"

    assert v < v2
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional

from .exceptions import InvalidVersionError

# Matches "MAJOR.MINOR.PATCH" with optional pre-release suffix
_SEMVER_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?$"
)


@total_ordering
@dataclass(frozen=True)
class PromptVersion:
    """Immutable semantic version for prompt templates and packages.

    Parameters
    ----------
    major:
        Breaking changes to template structure or variable contract.
    minor:
        Backward-compatible additions (new optional variables, new sections).
    patch:
        Cosmetic / wording changes that don't affect structure.
    pre_release:
        Optional pre-release label (e.g. ``"beta.1"``).
    """

    major: int = 0
    minor: int = 0
    patch: int = 0
    pre_release: Optional[str] = None

    # ---- Parsing ----------------------------------------------------------

    @classmethod
    def parse(cls, version_string: str) -> PromptVersion:
        """Parse a ``"MAJOR.MINOR.PATCH"`` or ``"MAJOR.MINOR.PATCH-label"``
        string into a :class:`PromptVersion`.

        Raises
        ------
        InvalidVersionError
            If *version_string* does not match the expected format.
        """
        match = _SEMVER_RE.match(version_string.strip())
        if not match:
            raise InvalidVersionError(version_string)

        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
        pre_release = match.group(4)
        return cls(major=major, minor=minor, patch=patch, pre_release=pre_release)

    # ---- Bumping ----------------------------------------------------------

    def bump_major(self) -> PromptVersion:
        """Return a new version with ``major`` incremented, minor and patch reset."""
        return PromptVersion(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> PromptVersion:
        """Return a new version with ``minor`` incremented, patch reset."""
        return PromptVersion(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> PromptVersion:
        """Return a new version with ``patch`` incremented."""
        return PromptVersion(major=self.major, minor=self.minor, patch=self.patch + 1)

    def bump(self, part: str) -> PromptVersion:
        """Return a new version bumped by the requested semantic part."""
        part = (part or "").lower()
        if part == "major":
            return self.bump_major()
        if part == "minor":
            return self.bump_minor()
        if part == "patch":
            return self.bump_patch()
        raise ValueError(f"Unsupported version bump part: {part!r}")

    # ---- Comparison -------------------------------------------------------

    @property
    def _sort_key(self):
        """Comparable key: pre-release versions sort before release versions."""
        pre = self.pre_release or ""
        return (self.major, self.minor, self.patch, pre)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PromptVersion):
            return NotImplemented
        return self._sort_key == other._sort_key

    def __lt__(self, other: PromptVersion) -> bool:
        if not isinstance(other, PromptVersion):
            return NotImplemented
        return self._sort_key < other._sort_key

    def __hash__(self) -> int:
        return hash(self._sort_key)

    # ---- String representation --------------------------------------------

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            return f"{base}-{self.pre_release}"
        return base

    def __repr__(self) -> str:
        return f"PromptVersion({self!s})"

    # ---- Serialisation ----------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""
        d = {"major": self.major, "minor": self.minor, "patch": self.patch}
        if self.pre_release:
            d["pre_release"] = self.pre_release
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PromptVersion:
        """Deserialise from a dict."""
        return cls(
            major=data.get("major", 0),
            minor=data.get("minor", 0),
            patch=data.get("patch", 0),
            pre_release=data.get("pre_release"),
        )

    # ---- Convenience ------------------------------------------------------

    @classmethod
    def initial(cls) -> PromptVersion:
        """Return the initial version ``0.1.0``."""
        return cls(major=0, minor=1, patch=0)

    @classmethod
    def zero(cls) -> PromptVersion:
        """Return version ``0.0.0``."""
        return cls(major=0, minor=0, patch=0)

    def is_initial(self) -> bool:
        """Return ``True`` if this is the initial version (0.1.0)."""
        return self == self.initial()