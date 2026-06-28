"""
Prompt Engine data models.

Provides the two core types:

- :class:`PromptTemplate` — a reusable, versioned template with variables,
  inheritance, and metadata.
- :class:`PromptPackage` — an immutable, fully-resolved prompt ready to be
  sent to any provider.

Both models are ``dataclass``-based and JSON-serialisable via ``to_dict()`` /
``from_dict()``.

Usage::

    from mythforge.prompt_engine.models import (
        PromptTemplate, PromptPackage, VariableSpec, TemplateMetadata,
    )
    from mythforge.prompt_engine.versioning import PromptVersion

    tpl = PromptTemplate(
        name="scene-description",
        version=PromptVersion.parse("1.0.0"),
        system_prompt="You are a cinematic screenwriter.",
        user_prompt="Write a {{scene_type}} scene set in {{location}}.",
        variables=[
            VariableSpec(name="scene_type", required=True),
            VariableSpec(name="location", required=True, default="a city"),
        ],
    )
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .versioning import PromptVersion


# =========================================================================
# Variable specification
# =========================================================================

@dataclass
class VariableSpec:
    """Specification for a single template variable.

    Parameters
    ----------
    name:
        Variable name (used in ``{{name}}`` syntax).
    required:
        Whether the variable must be provided at composition time.
    default:
        Default value used when the variable is not provided.
    description:
        Human-readable description for documentation.
    type_hint:
        Expected type (``"str"``, ``"int"``, ``"list"``, etc.) — for validation.
    enum:
        Optional list of allowed values.
    """
    name: str
    required: bool = True
    default: Optional[Any] = None
    description: str = ""
    type_hint: str = "str"
    enum: Optional[List[Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "required": self.required,
            "description": self.description,
            "type_hint": self.type_hint,
        }
        if self.default is not None:
            d["default"] = self.default
        if self.enum is not None:
            d["enum"] = self.enum
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VariableSpec:
        return cls(
            name=data["name"],
            required=data.get("required", True),
            default=data.get("default"),
            description=data.get("description", ""),
            type_hint=data.get("type_hint", "str"),
            enum=data.get("enum"),
        )


# =========================================================================
# Template metadata
# =========================================================================

@dataclass
class TemplateMetadata:
    """Metadata attached to a template.

    Parameters
    ----------
    author:
        Who created the template.
    description:
        What the template does.
    tags:
        Searchable tags.
    category:
        Category (e.g. ``"scene"``, ``"narration"``, ``"character"``).
    deprecated:
        Whether the template is deprecated.
    deprecation_message:
        Explanation of what to use instead.
    """
    author: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    category: str = ""
    deprecated: bool = False
    deprecation_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
        }
        if self.deprecated:
            d["deprecated"] = True
            d["deprecation_message"] = self.deprecation_message
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TemplateMetadata:
        return cls(
            author=data.get("author", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", ""),
            deprecated=data.get("deprecated", False),
            deprecation_message=data.get("deprecation_message", ""),
        )


# =========================================================================
# Prompt Template
# =========================================================================

@dataclass
class PromptTemplate:
    """A reusable, versioned prompt template.

    Templates are the blueprints from which :class:`PromptPackage` instances
    are composed.  They support inheritance (``extends``), partial templates,
    and variable definitions.

    Parameters
    ----------
    name:
        Unique template identifier (e.g. ``"scene-description"``).
    version:
        Semantic version.
    system_prompt:
        The system prompt (role instruction).  May contain ``{{variables}}``.
    developer_prompt:
        The developer prompt (additional constraints).  May contain ``{{variables}}``.
    user_prompt:
        The user prompt (task instruction).  May contain ``{{variables}}``.
    variables:
        Variable specifications for validation and documentation.
    extends:
        Name of a parent template to inherit from.
    partials:
        Named partial templates that can be inserted via ``{{>partial_name}}``.
    output_schema:
        Expected output schema (JSON Schema dict or description).
    negative_prompts:
        List of things the model should NOT do.
    model_preferences:
        Preferred model settings (temperature, top_p, etc.).
    metadata:
        Template metadata.
    """
    name: str
    version: PromptVersion = field(default_factory=PromptVersion.initial)
    system_prompt: str = ""
    developer_prompt: str = ""
    user_prompt: str = ""
    variables: List[VariableSpec] = field(default_factory=list)
    extends: Optional[str] = None
    partials: Dict[str, str] = field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    negative_prompts: List[str] = field(default_factory=list)
    model_preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: TemplateMetadata = field(default_factory=TemplateMetadata)

    @property
    def variable_names(self) -> List[str]:
        """Return all variable names declared in this template."""
        return [v.name for v in self.variables]

    @property
    def required_variables(self) -> List[str]:
        """Return names of required variables."""
        return [v.name for v in self.variables if v.required]

    @property
    def optional_variables(self) -> List[str]:
        """Return names of optional variables."""
        return [v.name for v in self.variables if not v.required]

    def get_variable(self, name: str) -> Optional[VariableSpec]:
        """Get a variable spec by name, or ``None``."""
        for v in self.variables:
            if v.name == name:
                return v
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        d: Dict[str, Any] = {
            "name": self.name,
            "version": str(self.version),
            "system_prompt": self.system_prompt,
            "developer_prompt": self.developer_prompt,
            "user_prompt": self.user_prompt,
            "variables": [v.to_dict() for v in self.variables],
            "metadata": self.metadata.to_dict(),
        }
        if self.extends:
            d["extends"] = self.extends
        if self.partials:
            d["partials"] = self.partials
        if self.output_schema:
            d["output_schema"] = self.output_schema
        if self.negative_prompts:
            d["negative_prompts"] = self.negative_prompts
        if self.model_preferences:
            d["model_preferences"] = self.model_preferences
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptTemplate:
        """Deserialise from a dict."""
        return cls(
            name=data["name"],
            version=PromptVersion.parse(data["version"]) if "version" in data else PromptVersion.initial(),
            system_prompt=data.get("system_prompt", ""),
            developer_prompt=data.get("developer_prompt", ""),
            user_prompt=data.get("user_prompt", ""),
            variables=[VariableSpec.from_dict(v) for v in data.get("variables", [])],
            extends=data.get("extends"),
            partials=data.get("partials", {}),
            output_schema=data.get("output_schema"),
            negative_prompts=data.get("negative_prompts", []),
            model_preferences=data.get("model_preferences", {}),
            metadata=TemplateMetadata.from_dict(data.get("metadata", {})),
        )


# =========================================================================
# Prompt Package
# =========================================================================

@dataclass
class PromptPackage:
    """An immutable, fully-resolved prompt ready for any provider.

    A ``PromptPackage`` is the **only** object that leaves the Prompt Engine.
    Providers never see templates — they receive this package.

    Instances are created by the :class:`~mythforge.prompt_engine.composer.PromptComposer`.

    Parameters
    ----------
    id:
        Unique identifier (auto-generated UUID).
    name:
        Human-readable name (usually the template name).
    version:
        Version of the template that produced this package.
    created_at:
        ISO-8601 timestamp of creation.
    template_name:
        Name of the source template.
    system_prompt:
        Fully-resolved system prompt (no ``{{variables}}`` remaining).
    developer_prompt:
        Fully-resolved developer prompt.
    user_prompt:
        Fully-resolved user prompt.
    variables:
        The variables that were injected (for reproducibility).
    metadata:
        Arbitrary metadata dict.
    style_guides:
        Style guide texts injected during composition.
    knowledge_references:
        Knowledge base references injected during composition.
    output_schema:
        Expected output schema.
    negative_prompts:
        Constraints / prohibitions.
    model_preferences:
        Preferred model settings.
    estimated_tokens:
        Estimated token count for the combined prompts.
    hash:
        Deterministic SHA-256 hash of the prompt content.
    tags:
        Searchable tags.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: PromptVersion = field(default_factory=PromptVersion.initial)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    template_name: str = ""
    system_prompt: str = ""
    developer_prompt: str = ""
    user_prompt: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    style_guides: List[str] = field(default_factory=list)
    knowledge_references: List[str] = field(default_factory=list)
    output_schema: Optional[Dict[str, Any]] = None
    negative_prompts: List[str] = field(default_factory=list)
    model_preferences: Dict[str, Any] = field(default_factory=dict)
    estimated_tokens: int = 0
    hash: str = ""
    tags: List[str] = field(default_factory=list)

    # ---- Convenience ------------------------------------------------------

    @property
    def full_prompt(self) -> str:
        """Return the combined prompt text (system + developer + user)."""
        parts = []
        if self.system_prompt:
            parts.append(self.system_prompt)
        if self.developer_prompt:
            parts.append(self.developer_prompt)
        if self.user_prompt:
            parts.append(self.user_prompt)
        return "\n\n".join(parts)

    @property
    def token_estimate(self) -> int:
        """Return ``estimated_tokens`` if set, otherwise a rough estimate."""
        if self.estimated_tokens:
            return self.estimated_tokens
        # Rough estimate: ~4 characters per token
        return len(self.full_prompt) // 4

    # ---- Serialisation ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        d: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "version": str(self.version),
            "created_at": self.created_at,
            "template_name": self.template_name,
            "system_prompt": self.system_prompt,
            "developer_prompt": self.developer_prompt,
            "user_prompt": self.user_prompt,
            "variables": self.variables,
            "metadata": self.metadata,
            "estimated_tokens": self.estimated_tokens,
            "hash": self.hash,
        }
        if self.style_guides:
            d["style_guides"] = self.style_guides
        if self.knowledge_references:
            d["knowledge_references"] = self.knowledge_references
        if self.output_schema:
            d["output_schema"] = self.output_schema
        if self.negative_prompts:
            d["negative_prompts"] = self.negative_prompts
        if self.model_preferences:
            d["model_preferences"] = self.model_preferences
        if self.tags:
            d["tags"] = self.tags
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptPackage:
        """Deserialise from a dict."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            version=PromptVersion.parse(data["version"]) if "version" in data else PromptVersion.initial(),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            template_name=data.get("template_name", ""),
            system_prompt=data.get("system_prompt", ""),
            developer_prompt=data.get("developer_prompt", ""),
            user_prompt=data.get("user_prompt", ""),
            variables=data.get("variables", {}),
            metadata=data.get("metadata", {}),
            style_guides=data.get("style_guides", []),
            knowledge_references=data.get("knowledge_references", []),
            output_schema=data.get("output_schema"),
            negative_prompts=data.get("negative_prompts", []),
            model_preferences=data.get("model_preferences", {}),
            estimated_tokens=data.get("estimated_tokens", 0),
            hash=data.get("hash", ""),
            tags=data.get("tags", []),
        )