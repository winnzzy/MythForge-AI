"""
Prompt Engine — MythForge AI.

.. currentmodule:: mythforge.prompt_engine

Core Classes
------------

.. autosummary::
    :toctree: generated

    PromptTemplate
    PromptPackage
    VariableSpec
    PromptComposer
    TemplateRegistry
    PromptRenderer
    PromptValidator
    PromptHasher
    VariableResolver

Composition
-----------

.. code-block:: python

    from mythforge.prompt_engine import PromptComposer, TemplateRegistry

    registry = TemplateRegistry()
    registry.load_directory("templates/")

    composer = PromptComposer(registry=registry)
    pkg = composer.compose(
        template_name="scene-description",
        variables={"scene_type": "action", "location": "a dragon's lair"},
        style_guides=["Use vivid, cinematic language."],
    )

    print(pkg.hash)
    print(pkg.system_prompt)

Rendering
---------

.. code-block:: python

    from mythforge.prompt_engine import PromptRenderer

    renderer = PromptRenderer()
    messages = renderer.render_chat(pkg)
    # [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

Caching
-------

.. code-block:: python

    from mythforge.prompt_engine import InMemoryPromptCache

    cache = InMemoryPromptCache()
    # Use with PromptComposer for automatic caching
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Core models
from .models import PromptPackage, PromptTemplate, VariableSpec

# Core classes
from .composer import PromptComposer
from .templates import TemplateRegistry, TemplateLoader
from .renderer import PromptRenderer
from .validator import PromptValidator
from .hashing import PromptHasher
from .resolver import VariableResolver

# Versioning
from .versioning import PromptVersion

# Cache
from .cache import PromptCache, PromptCacheEntry, InMemoryPromptCache

# Exceptions
from .exceptions import (
    PromptEngineError,
    TemplateError,
    TemplateNotFoundError,
    TemplateInheritanceError,
    CircularInheritanceError,
    TemplateValidationError,
    CompositionError,
    RenderingError,
    ValidationError,
    VariableResolutionError,
    MissingVariableError,
    VariableValidationError,
    VersionError,
    CacheError,
)

# Manifest hooks (lazy import to avoid circular dependency)
from .manifest_hooks import register_prompt_engine

__all__ = [
    # Core models
    "PromptTemplate",
    "PromptPackage",
    "VariableSpec",
    # Core classes
    "PromptComposer",
    "TemplateRegistry",
    "TemplateLoader",
    "PromptRenderer",
    "PromptValidator",
    "PromptHasher",
    "VariableResolver",
    "PromptVersion",
    # Cache
    "PromptCache",
    "PromptCacheEntry",
    "InMemoryPromptCache",
    # Exceptions
    "PromptEngineError",
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateInheritanceError",
    "CircularInheritanceError",
    "TemplateValidationError",
    "CompositionError",
    "RenderingError",
    "ValidationError",
    "VariableResolutionError",
    "MissingVariableError",
    "VariableValidationError",
    "VersionError",
    "CacheError",
    # Manifest hooks
    "register_prompt_engine",
]