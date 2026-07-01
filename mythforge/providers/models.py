"""
Provider request and response models.

All models are plain dataclasses — no provider-specific logic.
They form the contract between pipeline stages and providers.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProviderCapability(str, enum.Enum):
    """Capabilities a provider can declare."""

    LLM = "llm"
    IMAGE = "image"
    AUDIO = "audio"


class ProviderStatus(str, enum.Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class TransactionStatus(str, enum.Enum):
    """Outcome of a provider transaction."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# LLM Request / Response
# ---------------------------------------------------------------------------

@dataclass
class LLMRequest:
    """Input to an LLM provider."""

    prompt: str = ""
    system_prompt: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    stop_sequences: List[str] = field(default_factory=list)
    stream: bool = False
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LLMResponse:
    """Output from an LLM provider."""

    text: str = ""
    finish_reason: str = ""         # stop | length | content_filter
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LLMStreamChunk:
    """A single chunk from a streaming LLM response."""

    delta: str = ""                 # incremental text
    finish_reason: Optional[str] = None
    tokens_out: int = 0
    finished: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Image Request / Response
# ---------------------------------------------------------------------------

@dataclass
class ImageRequest:
    """Input to an image generation provider."""

    prompt: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    num_images: int = 1
    style: Optional[str] = None
    seed: Optional[int] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageEditRequest:
    """Input to an image editing provider."""

    source_path: str = ""           # path to source image
    prompt: str = ""                # edit instruction
    mask_path: Optional[str] = None # optional inpainting mask
    width: Optional[int] = None
    height: Optional[int] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageUpscaleRequest:
    """Input to an image upscaling provider."""

    source_path: str = ""
    scale_factor: int = 2           # 2x or 4x
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageResponse:
    """Output from an image provider."""

    images: List[ImageAsset] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        images: Optional[List[ImageAsset]] = None,
        assets: Optional[List[ImageAsset]] = None,
        provider: str = "",
        model: str = "",
        latency_ms: float = 0.0,
        estimated_cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.images = images or assets or []
        self.provider = provider
        self.model = model
        self.latency_ms = latency_ms
        self.estimated_cost_usd = estimated_cost_usd
        self.metadata = metadata or {}
        self.assets = self.images

    def to_dict(self) -> Dict[str, Any]:
        return {
            "images": [img.to_dict() for img in self.images],
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "metadata": self.metadata,
        }


@dataclass
class ImageAsset:
    """A single generated image."""

    path: str = ""                  # local file path where saved
    url: Optional[str] = None       # remote URL if applicable
    width: int = 0
    height: int = 0
    format: str = "png"             # png | jpg | webp
    seed: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Audio Request / Response
# ---------------------------------------------------------------------------

@dataclass
class NarrationRequest:
    """Input to a TTS / narration provider."""

    text: str = ""
    voice_id: Optional[str] = None
    language: str = "en"
    speed: float = 1.0
    output_format: str = "mp3"      # mp3 | wav | ogg
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MusicRequest:
    """Input to a music generation provider."""

    prompt: str = ""
    duration_s: float = 30.0
    genre: Optional[str] = None
    mood: Optional[str] = None
    bpm: Optional[int] = None
    output_format: str = "mp3"
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SFXRequest:
    """Input to a sound-effects generation provider."""

    prompt: str = ""
    duration_s: float = 5.0
    output_format: str = "mp3"
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AudioResponse:
    """Output from any audio provider."""

    path: str = ""                  # local file path where saved
    url: Optional[str] = None
    duration_s: float = 0.0
    format: str = "mp3"
    sample_rate: int = 0
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@dataclass
class HealthCheckResult:
    """Result of a provider health check."""

    provider: str = ""
    status: ProviderStatus = ProviderStatus.UNKNOWN
    latency_ms: float = 0.0
    available: bool = False
    failure_reason: Optional[str] = None
    last_success_at: Optional[str] = None
    checked_at: str = field(default_factory=lambda: _now_iso())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    """Record of a single provider interaction."""

    transaction_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    provider: str = ""
    operation: str = ""
    capability: str = ""            # llm | image | audio
    status: TransactionStatus = TransactionStatus.PENDING
    started_at: str = field(default_factory=lambda: _now_iso())
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    input_size_bytes: int = 0
    output_size_bytes: int = 0
    retries: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None
    model: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    def complete(
        self,
        status: TransactionStatus,
        *,
        estimated_cost_usd: float = 0.0,
        actual_cost_usd: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        input_size_bytes: int = 0,
        output_size_bytes: int = 0,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark the transaction as complete."""
        self.completed_at = _now_iso()
        self.duration_ms = _duration_ms(self.started_at, self.completed_at)
        self.status = status
        self.estimated_cost_usd = estimated_cost_usd
        self.actual_cost_usd = actual_cost_usd
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.input_size_bytes = input_size_bytes
        self.output_size_bytes = output_size_bytes
        if error:
            self.error = error
        if error_type:
            self.error_type = error_type
        if metadata:
            self.metadata.update(metadata)


# ---------------------------------------------------------------------------
# Cost Estimate
# ---------------------------------------------------------------------------

@dataclass
class CostEstimate:
    """Estimated cost for an operation before execution."""

    provider: str = ""
    operation: str = ""
    estimated_cost_usd: float = 0.0
    estimated_tokens_in: int = 0
    estimated_tokens_out: int = 0
    confidence: float = 0.0         # 0.0–1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_ms(start: str, end: str) -> float:
    """Calculate duration in milliseconds between two ISO timestamps."""
    try:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        return (e - s).total_seconds() * 1000
    except (ValueError, TypeError):
        return 0.0