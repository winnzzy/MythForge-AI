"""
Provider interfaces — Abstract Base Classes.

Every provider implementation MUST subclass the appropriate interface
and implement all abstract methods.  The interfaces are capability-based:
a provider can implement one or more interfaces.

Usage::

    class MyLLMProvider(LLMProvider):
        name = "my-llm"
        capabilities = [ProviderCapability.LLM]

        async def generate(self, request: LLMRequest) -> LLMResponse:
            ...

        async def health_check(self) -> HealthCheckResult:
            ...
"""

from __future__ import annotations

import abc
import functools
from typing import AsyncIterator, List, Optional

from .models import (
    AudioResponse,
    CostEstimate,
    HealthCheckResult,
    ImageEditRequest,
    ImageRequest,
    ImageResponse,
    ImageUpscaleRequest,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    MusicRequest,
    NarrationRequest,
    ProviderCapability,
    SFXRequest,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

_provider_instances: dict[str, object] = {}


class BaseProvider(abc.ABC):
    """Common contract for **all** providers.

    Concrete providers MUST set the ``name`` class attribute and declare
    their ``capabilities`` list.
    """

    # -- class-level declarations (override in subclass) --
    name: str = ""
    capabilities: List[ProviderCapability] = []

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

        init_method = getattr(cls, "__init__", None)
        if init_method is None or getattr(init_method, "_mythforge_wrapped", False):
            return

        @functools.wraps(init_method)
        def wrapped_init(self: BaseProvider, *args: object, **kwargs: object) -> None:
            init_method(self, *args, **kwargs)
            provider_name = getattr(self, "name", None) or getattr(cls, "name", "")
            if provider_name:
                _provider_instances[str(provider_name)] = self

        wrapped_init._mythforge_wrapped = True
        cls.__init__ = wrapped_init

    # -- lifecycle hooks (optional) --

    async def initialise(self) -> None:
        """Called once after construction.  Override to open connections, etc."""

    async def shutdown(self) -> None:
        """Called when the provider is being removed or the app is shutting down."""

    # -- required --

    @abc.abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Return current health status of this provider."""

    @abc.abstractmethod
    async def estimate_cost(self, operation: str, **kwargs: object) -> CostEstimate:
        """Estimate cost for an operation **before** executing it.

        Parameters
        ----------
        operation:
            The operation name (e.g. ``"generate"``, ``"narrate"``).
        **kwargs:
            Operation-specific parameters.
        """

    def __repr__(self) -> str:
        caps = ", ".join(c.value for c in self.capabilities) or "none"
        return f"<{type(self).__name__} name={self.name!r} capabilities=[{caps}]>"


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

class LLMProvider(BaseProvider, abc.ABC):
    """Interface for Large Language Model providers.

    Required methods:

    * ``generate`` — single-shot text generation
    * ``stream``   — streaming text generation

    Optional overrides:

    * ``estimate_cost``
    * ``health_check``
    """

    @abc.abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete text response.

        Parameters
        ----------
        request:
            The generation request including prompt, parameters, and model hint.

        Returns
        -------
        LLMResponse
            Complete response with text, token counts, and cost estimate.
        """

    @abc.abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        """Stream text generation chunk-by-chunk.

        Parameters
        ----------
        request:
            The generation request. ``request.stream`` will be ``True``.

        Yields
        ------
        LLMStreamChunk
            Incremental text chunks until generation completes.
        """


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------

class ImageProvider(BaseProvider, abc.ABC):
    """Interface for image generation providers.

    Required methods:

    * ``generate`` — create new images from a prompt

    Optional methods (provide default "not supported" implementations):

    * ``edit``     — edit an existing image
    * ``upscale``  — upscale an existing image
    """

    @abc.abstractmethod
    async def generate(self, request: ImageRequest) -> ImageResponse:
        """Generate one or more images from a text prompt.

        Parameters
        ----------
        request:
            Generation request with prompt, dimensions, style, etc.

        Returns
        -------
        ImageResponse
            Generated images with paths and metadata.
        """

    async def edit(self, request: ImageEditRequest) -> ImageResponse:
        """Edit an existing image using a text instruction.

        Default implementation raises ``NotImplementedError``.
        Override in providers that support image editing.

        Raises
        ------
        NotImplementedError
            If the provider does not support image editing.
        """
        raise NotImplementedError(
            f"Provider '{self.name}' does not support image editing."
        )

    async def upscale(self, request: ImageUpscaleRequest) -> ImageResponse:
        """Upscale an existing image.

        Default implementation raises ``NotImplementedError``.
        Override in providers that support upscaling.

        Raises
        ------
        NotImplementedError
            If the provider does not support upscaling.
        """
        raise NotImplementedError(
            f"Provider '{self.name}' does not support image upscaling."
        )


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

class AudioProvider(BaseProvider, abc.ABC):
    """Interface for audio generation providers.

    Covers TTS narration, music generation, and sound effects.

    Required methods:

    * ``narrate`` — text-to-speech narration

    Optional methods:

    * ``generate_music`` — background music generation
    * ``generate_sfx``   — sound effect generation
    """

    @abc.abstractmethod
    async def narrate(self, request: NarrationRequest) -> AudioResponse:
        """Convert text to speech.

        Parameters
        ----------
        request:
            Narration request with text, voice, speed, etc.

        Returns
        -------
        AudioResponse
            Generated audio file with path and metadata.
        """

    async def generate_music(self, request: MusicRequest) -> AudioResponse:
        """Generate background music.

        Default implementation raises ``NotImplementedError``.
        Override in providers that support music generation.

        Raises
        ------
        NotImplementedError
            If the provider does not support music generation.
        """
        raise NotImplementedError(
            f"Provider '{self.name}' does not support music generation."
        )

    async def generate_sfx(self, request: SFXRequest) -> AudioResponse:
        """Generate a sound effect.

        Default implementation raises ``NotImplementedError``.
        Override in providers that support SFX generation.

        Raises
        ------
        NotImplementedError
            If the provider does not support SFX generation.
        """
        raise NotImplementedError(
            f"Provider '{self.name}' does not support SFX generation."
        )