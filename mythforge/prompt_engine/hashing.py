"""
Deterministic hashing for Prompt Packages.

Produces a stable SHA-256 hash from the *content* of a prompt package.
The hash is used for:

- **Caching** — identical prompts produce identical hashes → cache hit.
- **Version comparison** — detect whether two packages differ.
- **Reproducibility** — verify that a prompt was generated from the same
  template + variables.
- **Manifest tracking** — record which exact prompt was sent to a provider.

The hash is computed from the normalised serialisation of the prompt fields
(excluding metadata that changes between runs such as ``created_at``, ``id``).

Usage::

    from mythforge.prompt_engine.hashing import PromptHasher

    h = PromptHasher()
    digest = h.hash_package({
        "system_prompt": "You are a screenwriter.",
        "user_prompt": "Write a scene about a dragon.",
        "variables": {"genre": "fantasy"},
    })
    assert len(digest) == 64  # SHA-256 hex
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


# Fields that participate in the hash.
# Order matters — we iterate in definition order for determinism.
_HASH_FIELDS = (
    "template_name",
    "system_prompt",
    "developer_prompt",
    "user_prompt",
    "variables",
    "style_guides",
    "knowledge_references",
    "output_schema",
    "negative_prompts",
    "model_preferences",
    "tags",
)


class PromptHasher:
    """Compute deterministic SHA-256 hashes for prompt content.

    Parameters
    ----------
    algorithm:
        Hash algorithm name (default ``"sha256"``).
    encoding:
        Text encoding (default ``"utf-8"``).
    """

    def __init__(
        self,
        *,
        algorithm: str = "sha256",
        encoding: str = "utf-8",
    ) -> None:
        self.algorithm = algorithm
        self.encoding = encoding

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def hash_package(self, data: Dict[str, Any]) -> str:
        """Return a hex digest for the given prompt data dict.

        Only the fields listed in ``_HASH_FIELDS`` are included.
        Fields not present in *data* are silently skipped.
        """
        canonical = self._canonicalise(data)
        serialised = json.dumps(canonical, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return self._digest(serialised)

    def hash_text(self, text: str) -> str:
        """Hash a single text string (convenience method)."""
        return self._digest(text)

    def hash_parts(
        self,
        *,
        system_prompt: str = "",
        developer_prompt: str = "",
        user_prompt: str = "",
        variables: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> str:
        """Hash individual prompt parts (convenience method)."""
        data = {
            "system_prompt": system_prompt,
            "developer_prompt": developer_prompt,
            "user_prompt": user_prompt,
            "variables": variables or {},
        }
        data.update(extra)
        return self.hash_package(data)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _canonicalise(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalise the hashable fields from *data*."""
        canonical: Dict[str, Any] = {}
        for field in _HASH_FIELDS:
            value = data.get(field)
            if value is None:
                continue
            canonical[field] = self._normalise(value)

        for key in sorted(data):
            if key in canonical or key in {"id", "created_at", "metadata"}:
                continue
            canonical[key] = self._normalise(data[key])
        return canonical

    def _normalise(self, value: Any) -> Any:
        """Recursively normalise a value for deterministic serialisation.

        - Dicts → sorted keys
        - Lists → sorted (if elements are comparable) or left as-is
        - Strings → stripped
        """
        if isinstance(value, dict):
            return {k: self._normalise(v) for k, v in sorted(value.items())}
        if isinstance(value, list):
            normalised = [self._normalise(v) for v in value]
            # Attempt sort for determinism; fall back to original order
            try:
                normalised.sort(key=lambda x: json.dumps(x, sort_keys=True))
            except TypeError:
                pass
            return normalised
        if isinstance(value, str):
            return value.strip()
        return value

    def _digest(self, content: str) -> str:
        """Compute the hex digest of *content*."""
        h = hashlib.new(self.algorithm)
        h.update(content.encode(self.encoding))
        return h.hexdigest()