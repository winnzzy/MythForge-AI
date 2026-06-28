"""
Template loading, inheritance resolution, and registry.

Provides:

- :class:`TemplateLoader` — load templates from dicts, files, or directories.
- :class:`TemplateRegistry` — in-memory registry with lookup, versioning,
  and inheritance resolution.

Templates can be loaded from:

- Python dicts (programmatic)
- JSON files (``*.json``)
- YAML files (``*.yaml`` / ``*.yml``)  — requires PyYAML (optional)
- Directories of template files (recursive)

Inheritance is resolved at registration time via ``TemplateRegistry.register()``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import (
    CircularInheritanceError,
    TemplateInheritanceError,
    TemplateNotFoundError,
    TemplateValidationError,
)
from .models import PromptTemplate, VariableSpec
from .versioning import PromptVersion


class TemplateLoader:
    """Load :class:`PromptTemplate` instances from various sources."""

    # ---- From dict --------------------------------------------------------

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> PromptTemplate:
        """Create a template from a dict."""
        return PromptTemplate.from_dict(data)

    # ---- From file --------------------------------------------------------

    @staticmethod
    def from_file(path: str | Path) -> PromptTemplate:
        """Load a single template from a JSON or YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {path}")

        text = path.read_text(encoding="utf-8")

        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore[import-untyped]
                data = yaml.safe_load(text)
            except ImportError:
                raise ImportError(
                    "PyYAML is required to load YAML templates. "
                    "Install it with: pip install pyyaml"
                )
        else:
            data = json.loads(text)

        if not isinstance(data, dict):
            raise TemplateValidationError(
                f"Template file must contain a JSON/YAML object: {path}",
                errors=[f"Expected dict, got {type(data).__name__}"],
            )

        # If no name is specified, derive from filename
        if "name" not in data:
            data["name"] = path.stem

        return PromptTemplate.from_dict(data)

    # ---- From directory ---------------------------------------------------

    @staticmethod
    def from_directory(directory: str | Path) -> List[PromptTemplate]:
        """Recursively load all template files from a directory."""
        directory = Path(directory)
        templates: List[PromptTemplate] = []
        for ext in ("*.json", "*.yaml", "*.yml"):
            for file_path in sorted(directory.rglob(ext)):
                templates.append(TemplateLoader.from_file(file_path))
        return templates


class TemplateRegistry:
    """In-memory registry of prompt templates.

    Supports:
    - Registration and lookup by name (+ optional version)
    - Inheritance resolution (``extends``)
    - Cyclic inheritance detection
    - Bulk loading from directories

    Usage::

        registry = TemplateRegistry()
        registry.register(my_template)
        resolved = registry.resolve("scene-description")
    """

    def __init__(self) -> None:
        # {name: {version_string: PromptTemplate}}
        self._templates: Dict[str, Dict[str, PromptTemplate]] = {}
        # Resolved (flattened) templates cache
        self._resolved_cache: Dict[str, PromptTemplate] = {}

    # ---- Registration -----------------------------------------------------

    def register(self, template: PromptTemplate) -> None:
        """Register a template.  If a version already exists it is overwritten."""
        if template.name not in self._templates:
            self._templates[template.name] = {}
        self._templates[template.name][str(template.version)] = template
        # Invalidate resolved cache for this name
        self._resolved_cache.pop(template.name, None)

    def register_many(self, templates: List[PromptTemplate]) -> None:
        """Register multiple templates."""
        for t in templates:
            self.register(t)

    def load_directory(self, directory: str | Path) -> int:
        """Load and register all templates from a directory.  Returns count."""
        templates = TemplateLoader.from_directory(directory)
        self.register_many(templates)
        return len(templates)

    # ---- Lookup -----------------------------------------------------------

    def get(self, name: str, version: Optional[str] = None) -> PromptTemplate:
        """Get a template by name (and optional version).

        If *version* is ``None``, the latest registered version is returned.
        """
        if name not in self._templates:
            raise TemplateNotFoundError(name, version=version)

        versions = self._templates[name]
        if not versions:
            raise TemplateNotFoundError(name, version=version)

        if version is not None:
            if version not in versions:
                raise TemplateNotFoundError(name, version=version)
            return versions[version]

        # Return latest version
        latest_key = max(versions.keys(), key=lambda v: PromptVersion.parse(v))
        return versions[latest_key]

    def get_latest(self, name: str) -> PromptTemplate:
        """Get the latest version of a template by name."""
        return self.get(name)

    def list_templates(self) -> List[str]:
        """Return all registered template names."""
        return sorted(self._templates.keys())

    def list_versions(self, name: str) -> List[str]:
        """Return all registered versions for a template name."""
        if name not in self._templates:
            raise TemplateNotFoundError(name)
        return sorted(self._templates[name].keys(), key=lambda v: PromptVersion.parse(v))

    # ---- Resolution (inheritance) -----------------------------------------

    def resolve(self, name: str, version: Optional[str] = None) -> PromptTemplate:
        """Resolve a template, applying inheritance.

        Returns a new :class:`PromptTemplate` with all inherited fields
        merged.  The original registered templates are not modified.
        """
        cache_key = f"{name}@{version}" if version else name
        if cache_key in self._resolved_cache:
            return self._resolved_cache[cache_key]

        template = self.get(name, version=version)
        resolved = self._resolve_chain(template, chain=[])
        self._resolved_cache[cache_key] = resolved
        return resolved

    def _resolve_chain(
        self,
        template: PromptTemplate,
        *,
        chain: List[str],
    ) -> PromptTemplate:
        """Recursively resolve the inheritance chain."""
        if template.name in chain:
            cycle = chain + [template.name]
            raise CircularInheritanceError(cycle)

        if template.extends is None:
            return template

        parent = self.get(template.extends)
        resolved_parent = self._resolve_chain(parent, chain=chain + [template.name])

        return self._merge(resolved_parent, template)

    @staticmethod
    def _merge(parent: PromptTemplate, child: PromptTemplate) -> PromptTemplate:
        """Merge a parent and child template.

        Child fields override parent fields.  Lists and dicts are merged
        (child values appended / updated).
        """
        # Merge variables: child overrides parent by name
        parent_vars = {v.name: v for v in parent.variables}
        parent_vars.update({v.name: v for v in child.variables})
        merged_variables = list(parent_vars.values())

        # Merge partials
        merged_partials = {**parent.partials, **child.partials}

        # Merge lists
        merged_negatives = parent.negative_prompts + [
            n for n in child.negative_prompts if n not in parent.negative_prompts
        ]

        # Merge model preferences
        merged_prefs = {**parent.model_preferences, **child.model_preferences}

        return PromptTemplate(
            name=child.name,
            version=child.version,
            system_prompt=child.system_prompt or parent.system_prompt,
            developer_prompt=child.developer_prompt or parent.developer_prompt,
            user_prompt=child.user_prompt or parent.user_prompt,
            variables=merged_variables,
            extends=child.extends,
            partials=merged_partials,
            output_schema=child.output_schema or parent.output_schema,
            negative_prompts=merged_negatives,
            model_preferences=merged_prefs,
            metadata=child.metadata,
        )

    # ---- Validation -------------------------------------------------------

    def validate(self, template: PromptTemplate) -> List[str]:
        """Validate a template.  Returns a list of error strings (empty = valid)."""
        errors: List[str] = []

        if not template.name:
            errors.append("Template name is required.")

        if template.extends:
            if template.extends not in self._templates:
                errors.append(f"Parent template not found: {template.extends!r}")

        # Check for circular inheritance
        try:
            self.resolve(template.name)
        except CircularInheritanceError as exc:
            errors.append(str(exc))
        except TemplateNotFoundError:
            pass  # Not yet registered

        # Check for undefined variables in text
        from .resolver import VariableResolver
        resolver = VariableResolver()
        for field_name in ("system_prompt", "developer_prompt", "user_prompt"):
            text = getattr(template, field_name)
            if not text:
                continue
            for var_name, _ in resolver.find_variables(text):
                if var_name not in template.variable_names:
                    errors.append(
                        f"Undefined variable {{{{{var_name}}}}} in {field_name}"
                    )

        return errors

    def is_valid(self, template: PromptTemplate) -> bool:
        """Return ``True`` if the template passes validation."""
        return len(self.validate(template)) == 0