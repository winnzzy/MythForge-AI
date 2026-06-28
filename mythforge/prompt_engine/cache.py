"""
Prompt Cache Interface.

Defines an abstract interface for prompt caching.  Implementations can
back this with Redis, SQLite, in-memory dicts, file systems, or any
other storage.

The cache is keyed by the deterministic hash of a :class:`PromptPackage`,
so identical prompts always produce the same cache key.

Usage::

    from mythforge.prompt_engine.cache import PromptCache, PromptCacheEntry

    class RedisPromptCache(PromptCache):
        async def get(self, hash: str) -> PromptCacheEntry | None:
            ...
        async def put(self, entry: PromptCacheEntry) -> None:
            ...
        async def evict(self, hash: str) -> bool:
            ...

    cache = RedisPromptCache()
    entry = await cache.get(pkg.hash)
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import PromptPackage


@dataclass
class PromptCacheEntry:
    """A single cache entry.

    Parameters
    ----------
    hash:
        The deterministic hash of the prompt (cache key).
    package:
        The cached :class:`PromptPackage`.
    provider_response:
        The raw response from the provider (optional).
    created_at:
        When the entry was cached.
    ttl_seconds:
        Time-to-live in seconds (``None`` = no expiry).
    hit_count:
        How many times this entry has been served from cache.
    metadata:
        Arbitrary metadata.
    """
    hash: str
    package: PromptPackage
    provider_response: Optional[Any] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl_seconds: Optional[int] = None
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Return ``True`` if the entry has exceeded its TTL."""
        if self.ttl_seconds is None:
            return False
        created = datetime.fromisoformat(self.created_at)
        now = datetime.now(timezone.utc)
        return (now - created).total_seconds() > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "hash": self.hash,
            "package": self.package.to_dict(),
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            "hit_count": self.hit_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptCacheEntry:
        """Deserialise from a dict."""
        return cls(
            hash=data["hash"],
            package=PromptPackage.from_dict(data["package"]),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            ttl_seconds=data.get("ttl_seconds"),
            hit_count=data.get("hit_count", 0),
            metadata=data.get("metadata", {}),
        )


class PromptCache(abc.ABC):
    """Abstract interface for prompt caching.

    Implementations must provide ``get``, ``put``, and ``evict``.

    The cache is **optional** — the Prompt Engine works without one.
    When a cache is provided to :class:`PromptComposer`, it will check
    the cache before composing and store results after composition.
    """

    @abc.abstractmethod
    async def get(self, hash: str) -> Optional[PromptCacheEntry]:
        """Retrieve a cache entry by prompt hash.

        Returns ``None`` if the entry does not exist or has expired.
        """
        ...

    @abc.abstractmethod
    async def put(self, entry: PromptCacheEntry) -> None:
        """Store a cache entry."""
        ...

    @abc.abstractmethod
    async def evict(self, hash: str) -> bool:
        """Remove a cache entry by hash.

        Returns ``True`` if the entry existed and was removed.
        """
        ...

    async def exists(self, hash: str) -> bool:
        """Return ``True`` if a non-expired entry exists for the given hash."""
        entry = await self.get(hash)
        return entry is not None

    async def clear(self) -> int:
        """Remove all entries.  Returns the number of entries removed.

        Default implementation does nothing — override for real backends.
        """
        return 0

    async def stats(self) -> Dict[str, Any]:
        """Return cache statistics.

        Default implementation returns empty stats — override for real backends.
        """
        return {"total_entries": 0, "total_hits": 0}


class InMemoryPromptCache(PromptCache):
    """Simple in-memory prompt cache for testing and development.

    Not suitable for production — no persistence, no size limits.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, PromptCacheEntry] = {}

    async def get(self, hash: str) -> Optional[PromptCacheEntry]:
        entry = self._entries.get(hash)
        if entry is None:
            return None
        if entry.is_expired():
            del self._entries[hash]
            return None
        entry.hit_count += 1
        return entry

    async def put(self, entry: PromptCacheEntry) -> None:
        self._entries[entry.hash] = entry

    async def evict(self, hash: str) -> bool:
        if hash in self._entries:
            del self._entries[hash]
            return True
        return False

    async def exists(self, hash: str) -> bool:
        entry = self._entries.get(hash)
        if entry is None:
            return False
        if entry.is_expired():
            del self._entries[hash]
            return False
        return True

    async def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count

    async def stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "total_hits": sum(e.hit_count for e in self._entries.values()),
        }