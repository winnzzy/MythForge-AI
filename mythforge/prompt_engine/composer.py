"""
Prompt Composer.

The **Prompt Composer** is the central orchestrator of the Prompt Engine.

It takes a template name + variables + optional style guides and knowledge
references, and produces a fully-resolved :class:`PromptPackage` that is
ready for any provider.

Composition pipeline::

    Template Resolution
           │
    Inheritance Merge
           │
    Variable Injection
           │
    Style Guide Injection
           │
    Knowledge Reference Injection
           │
    Hash Computation
           │
    PromptPackage

Usage::

    from mythforge.prompt_engine.composer import PromptComposer

    composer = PromptComposer(registry=registry)
    pkg = composer.compose(
        template_name="scene-description",
        variables={"scene_type": "action", "location": "a dragon's lair"},
        style_guides=["Use vivid, cinematic language."],
    )
    print(pkg.hash)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .exceptions import CompositionError
from .hashing import PromptHasher
from .models import PromptPackage, PromptTemplate
from .renderer import PromptRenderer
from .resolver import VariableResolver
from .templates import TemplateRegistry
from .validator import PromptValidator
from .versioning import PromptVersion


class PromptComposer:
    """Compose fully-resolved :class:`PromptPackage` instances.

    Parameters
    ----------
    registry:
        Template registry for template lookup and inheritance resolution.
    resolver:
        Variable resolver (optional — a default is created if not provided).
    validator:
        Prompt validator (optional — a default is created if not provided).
    hasher:
        Prompt hasher (optional — a default is created if not provided).
    renderer:
        Prompt renderer (optional — a default is created if not provided).
    validate_output:
        If ``True`` (default), the composed package is validated before
        being returned.
    """

    def __init__(
        self,
        *,
        registry: TemplateRegistry,
        resolver: Optional[VariableResolver] = None,
        validator: Optional[PromptValidator] = None,
        hasher: Optional[PromptHasher] = None,
        renderer: Optional[PromptRenderer] = None,
        validate_output: bool = True,
    ) -> None:
        self.registry = registry
        self.resolver = resolver or VariableResolver(strict=True)
        self.validator = validator or PromptValidator()
        self.hasher = hasher or PromptHasher()
        self.renderer = renderer or PromptRenderer()
        self.validate_output = validate_output

    # ------------------------------------------------------------------
    # Main composition method
    # ------------------------------------------------------------------

    def compose(
        self,
        template_name: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        style_guides: Optional[List[str]] = None,
        knowledge_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> PromptPackage:
        """Compose a :class:`PromptPackage` from a template.

        Parameters
        ----------
        template_name:
            Name of the template in the registry.
        variables:
            Variable values to inject into the template.
        version:
            Specific template version (default: latest).
        style_guides:
            Style guide texts to attach to the package.
        knowledge_references:
            Knowledge base references to attach to the package.
        metadata:
            Arbitrary metadata to attach to the package.
        tags:
            Tags for the package.

        Returns
        -------
        PromptPackage
            A fully-resolved, hashed prompt package.

        Raises
        ------
        CompositionError
            If composition fails for any reason.
        """
        variables = variables or {}

        try:
            # 1. Resolve template (with inheritance)
            template = self.registry.resolve(template_name, version=version)

            # 2. Validate template
            template_errors = self.validator.validate_template(template)
            if template_errors:
                raise CompositionError(
                    f"Template {template_name!r} failed validation.",
                    details={"errors": template_errors},
                )

            # 3. Resolve variables in all prompt sections
            resolved_system = self._resolve_section(
                template.system_prompt, variables, template, "system_prompt"
            )
            resolved_developer = self._resolve_section(
                template.developer_prompt, variables, template, "developer_prompt"
            )
            resolved_user = self._resolve_section(
                template.user_prompt, variables, template, "user_prompt"
            )

            # 4. Inject style guides into system prompt
            if style_guides:
                guide_text = "\n\n".join(f"[STYLE GUIDE]\n{g}" for g in style_guides)
                if resolved_system:
                    resolved_system = f"{resolved_system}\n\n{guide_text}"
                else:
                    resolved_system = guide_text

            # 5. Inject knowledge references into system prompt
            if knowledge_references:
                ref_text = "\n\n".join(
                    f"[KNOWLEDGE REFERENCE]\n{r}" for r in knowledge_references
                )
                if resolved_system:
                    resolved_system = f"{resolved_system}\n\n{ref_text}"
                else:
                    resolved_system = ref_text

            # 6. Build the package
            pkg = PromptPackage(
                name=template_name,
                version=template.version,
                template_name=template_name,
                system_prompt=resolved_system,
                developer_prompt=resolved_developer,
                user_prompt=resolved_user,
                variables=variables,
                metadata=metadata or {},
                style_guides=style_guides or [],
                knowledge_references=knowledge_references or [],
                output_schema=template.output_schema,
                negative_prompts=list(template.negative_prompts),
                model_preferences=dict(template.model_preferences),
                tags=tags or list(template.metadata.tags),
            )

            # 7. Compute hash
            pkg.hash = self.hasher.hash_package(pkg.to_dict())

            # 8. Estimate tokens
            pkg.estimated_tokens = pkg.token_estimate

            # 9. Validate output
            if self.validate_output:
                pkg_errors = self.validator.validate_package(pkg)
                if pkg_errors:
                    raise CompositionError(
                        f"Composed PromptPackage for {template_name!r} failed validation.",
                        details={"errors": pkg_errors},
                    )

            return pkg

        except CompositionError:
            raise
        except Exception as exc:
            raise CompositionError(
                f"Failed to compose prompt from template {template_name!r}: {exc}",
                details={"template_name": template_name, "original_error": str(exc)},
            ) from exc

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def compose_and_render(
        self,
        template_name: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        style_guides: Optional[List[str]] = None,
        knowledge_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        format: str = "chat",
    ) -> Any:
        """Compose and immediately render in one call.

        Parameters
        ----------
        format:
            Rendering format — ``"chat"``, ``"text"``, or ``"dict"``.
        """
        pkg = self.compose(
            template_name,
            variables=variables,
            version=version,
            style_guides=style_guides,
            knowledge_references=knowledge_references,
            metadata=metadata,
            tags=tags,
        )
        if format == "chat":
            return self.renderer.render_chat(pkg)
        elif format == "text":
            return self.renderer.render_text(pkg)
        elif format == "dict":
            return self.renderer.render_dict(pkg)
        else:
            raise CompositionError(f"Unknown render format: {format!r}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_section(
        self,
        text: str,
        variables: Dict[str, Any],
        template: PromptTemplate,
        field_name: str,
    ) -> str:
        """Resolve variables in a single prompt section."""
        if not text:
            return ""
        return self.resolver.resolve(
            text,
            variables=variables,
            variable_specs=template.variables,
            partials=template.partials,
            template_name=template.name,
        )