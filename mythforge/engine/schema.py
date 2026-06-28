"""
Manifest schema — data model definitions.

Every dataclass is JSON-serialisable via ``to_dict`` / ``from_dict`` helpers.
The schema is intentionally extensible: add optional fields at the end of
each dataclass and bump ``ManifestVersion.CURRENT`` when the shape changes.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProjectStatus(str, enum.Enum):
    """Lifecycle states for a MythForge project."""

    CREATED = "CREATED"
    RESEARCHING = "RESEARCHING"
    WRITING = "WRITING"
    SCENE_BREAKDOWN = "SCENE_BREAKDOWN"
    PROMPT_GENERATION = "PROMPT_GENERATION"
    IMAGE_GENERATION = "IMAGE_GENERATION"
    NARRATION = "NARRATION"
    SFX = "SFX"
    MUSIC = "MUSIC"
    RENDERING = "RENDERING"
    QA = "QA"
    READY = "READY"
    FAILED = "FAILED"
    PUBLISHED = "PUBLISHED"


# Canonical pipeline order — used by resume logic to determine "next stage".
PIPELINE_ORDER: List[ProjectStatus] = [
    ProjectStatus.CREATED,
    ProjectStatus.RESEARCHING,
    ProjectStatus.WRITING,
    ProjectStatus.SCENE_BREAKDOWN,
    ProjectStatus.PROMPT_GENERATION,
    ProjectStatus.IMAGE_GENERATION,
    ProjectStatus.NARRATION,
    ProjectStatus.SFX,
    ProjectStatus.MUSIC,
    ProjectStatus.RENDERING,
    ProjectStatus.QA,
    ProjectStatus.READY,
    ProjectStatus.PUBLISHED,
]


class ManifestVersion(str, enum.Enum):
    """Schema version tag embedded in every manifest file."""

    V1 = "1.0"
    CURRENT = V1


# ---------------------------------------------------------------------------
# Sub-records
# ---------------------------------------------------------------------------

@dataclass
class AssetRecord:
    """One asset (image, audio file, thumbnail, etc.) produced by a stage."""

    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage: str = ""          # pipeline stage that created it
    kind: str = ""           # image | narration | music | sfx | thumbnail | render
    path: str = ""           # relative path inside project directory
    provider: str = ""       # e.g. "gemini", "elevenlabs"
    created_at: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- serialisation --
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AssetRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CostRecord:
    """A single cost entry recorded by a pipeline stage."""

    stage: str = ""
    provider: str = ""
    operation: str = ""      # e.g. "generate_image", "tts"
    amount_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    recorded_at: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CostRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ErrorRecord:
    """An error encountered during pipeline execution."""

    stage: str = ""
    message: str = ""
    traceback: str = ""
    timestamp: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ErrorRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WarningRecord:
    """A non-fatal warning recorded during pipeline execution."""

    stage: str = ""
    message: str = ""
    timestamp: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WarningRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProviderRecord:
    """Tracks which provider was used for a given capability."""

    capability: str = ""     # llm | image | tts | music | sfx | render
    provider: str = ""       # e.g. "openai", "gemini", "elevenlabs"
    model: str = ""          # e.g. "gpt-4o", "gemini-2.0-flash"
    selected_at: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProviderRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class QualityCheck:
    """Result of a quality-assurance check."""

    check_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    stage: str = ""
    check_type: str = ""     # e.g. "subtitle_sync", "scene_duration", "lip_sync"
    passed: bool = False
    score: float = 0.0
    details: str = ""
    timestamp: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QualityCheck":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RenderRecord:
    """One render attempt (draft or final)."""

    render_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    kind: str = "draft"      # draft | final
    path: str = ""
    resolution: str = "1080p"
    duration_s: float = 0.0
    file_size_bytes: int = 0
    timestamp: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RenderRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class StageRecord:
    """Tracks execution of a single pipeline stage."""

    stage: str = ""           # ProjectStatus value
    status: str = "pending"   # pending | running | completed | failed | skipped
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_s: float = 0.0
    retry_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StageRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Top-level Manifest
# ---------------------------------------------------------------------------

@dataclass
class Manifest:
    """
    The central manifest for a MythForge video project.

    This is the **single source of truth**.  Every pipeline stage reads from
    it and writes back to it.  The manifest is serialised to ``manifest.json``
    inside the project directory.
    """

    # -- identity --
    project_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    slug: str = ""
    version: str = ManifestVersion.CURRENT.value

    # -- timestamps --
    created_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())

    # -- lifecycle --
    status: str = ProjectStatus.CREATED.value
    current_stage: str = ProjectStatus.CREATED.value
    completed_stages: List[str] = field(default_factory=list)

    # -- providers --
    providers: List[Dict[str, Any]] = field(default_factory=list)

    # -- costs --
    costs: List[Dict[str, Any]] = field(default_factory=list)

    # -- assets --
    assets: List[Dict[str, Any]] = field(default_factory=list)

    # -- renders --
    render_history: List[Dict[str, Any]] = field(default_factory=list)

    # -- quality --
    quality_checks: List[Dict[str, Any]] = field(default_factory=list)

    # -- retries & diagnostics --
    retry_counts: Dict[str, int] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    # -- settings & snapshot --
    settings: Dict[str, Any] = field(default_factory=dict)
    configuration_snapshot: Dict[str, Any] = field(default_factory=dict)

    # -- user metadata (genre, target audience, etc.) --
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise manifest to a JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Manifest":
        """Deserialise a manifest from a dict, ignoring unknown keys."""
        known = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    # -- convenience ---------------------------------------------------------

    @property
    def total_cost_usd(self) -> float:
        """Sum of all recorded costs."""
        return sum(c.get("amount_usd", 0) for c in self.costs)

    @property
    def asset_count(self) -> int:
        return len(self.assets)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def is_terminal(self) -> bool:
        """True if the project is in a final state (READY, PUBLISHED, FAILED)."""
        return self.status in {
            ProjectStatus.READY.value,
            ProjectStatus.PUBLISHED.value,
            ProjectStatus.FAILED.value,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """UTC now as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()