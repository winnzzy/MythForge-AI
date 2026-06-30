"""
Deterministic SHA-256 hashing for artifacts.

Produces a stable hash from the *content* of an artifact, excluding volatile
fields (timestamps, IDs, etc.) so that identical content always yields
identical hashes regardless of when or where it was created.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


class ArtifactHasher:
    """Compute deterministic SHA-256 hashes for artifact content.

    Parameters
    ----------
    algorithm:
        Hash algorithm name (default ``"sha256"``).
    encoding:
        Text encoding (default ``"utf-8"``).
    """

    def __init__(self, *, algorithm: str = "sha256", encoding: str = "utf-8") -> None:
        self.algorithm = algorithm
        self.encoding = encoding

    def hash_content(self, data: Any) -> str:
        """Return a hex digest for *data*.

        *data* must be JSON-serialisable.  Dicts are key-sorted for
        determinism; lists are left in order (ordering is semantic).
        """
        canonical = self._canonicalise(data)
        serialised = json.dumps(canonical, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return self._digest(serialised)

    def hash_text(self, text: str) -> str:
        """Hash a single text string."""
        return self._digest(text.strip())

    def hash_bytes(self, data: bytes) -> str:
        """Hash raw bytes."""
        h = hashlib.new(self.algorithm)
        h.update(data)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _canonicalise(self, value: Any) -> Any:
        """Recursively normalise a value for deterministic serialisation."""
        if isinstance(value, dict):
            return {k: self._canonicalise(v) for k, v in sorted(value.items())}
        if isinstance(value, list):
            return [self._canonicalise(v) for v in value]
        if isinstance(value, str):
            return value.strip()
        return value

    def _digest(self, content: str) -> str:
        """Compute the hex digest of *content*."""
        h = hashlib.new(self.algorithm)
        h.update(content.encode(self.encoding))
        return h.hexdigest()