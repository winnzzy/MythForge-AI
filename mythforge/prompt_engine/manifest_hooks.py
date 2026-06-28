"""
Prompt Engine Manifest Hooks.

Registers prompt engine events with the :class:`ManifestEngine`:

- ``prompt_engine.compose`` — compose a prompt from a template
- ``prompt_engine.render`` — render a composed prompt
- ``prompt_engine.cache_check`` — check prompt cache
- ``prompt_engine.validate`` — validate a prompt package

Usage::

    from mythforge.engine.engine import ManifestEngine
    from mythforge.prompt_engine.manifest_hooks import register_prompt_engine

    engine = ManifestEngine()
    register_prompt_engine(engine, prompt_composer=my_composer)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cache import PromptCache
    from .composer import PromptComposer
    from .renderer import PromptRenderer
    from .validator import PromptValidator


def register_prompt_engine(
    engine: Any,
    *,
    prompt_composer: Optional[Any] = None,
    prompt_cache: Optional[Any] = None,
    prompt_renderer: Optional[Any] = None,
    prompt_validator: Optional[Any] = None,
) -> None:
    """Register prompt engine hooks with the ManifestEngine.

    This is **optional** — the Prompt Engine works standalone.
    When registered, it allows the manifest to drive prompt composition
    as part of the pipeline.

    Parameters
    ----------
    engine:
        The :class:`ManifestEngine` instance.
    prompt_composer:
        A :class:`PromptComposer` instance.
    prompt_cache:
        A :class:`PromptCache` instance (optional).
    prompt_renderer:
        A :class:`PromptRenderer` instance (optional).
    prompt_validator:
        A :class:`PromptValidator` instance (optional).
    """
    # Lazy imports to avoid circular dependencies
    from .cache import InMemoryPromptCache
    from .composer import PromptComposer
    from .renderer import PromptRenderer
    from .templates import TemplateRegistry
    from .validator import PromptValidator

    # Create defaults if not provided
    if prompt_composer is None:
        prompt_composer = PromptComposer(registry=TemplateRegistry(), validate_output=False)
    if prompt_renderer is None:
        prompt_renderer = PromptRenderer()
    if prompt_validator is None:
        prompt_validator = PromptValidator()
    if prompt_cache is None:
        prompt_cache = InMemoryPromptCache()

    # ---- compose prompt --------------------------------------------------
    def compose_prompt(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Compose a prompt from a template."""
        template_name = input_data.get("template_name")
        if not template_name:
            raise ValueError("prompt_engine.compose requires 'template_name' in input_data")

        variables = input_data.get("variables", {})
        version = input_data.get("version")
        style_guides = input_data.get("style_guides")
        knowledge_references = input_data.get("knowledge_references")
        metadata = input_data.get("metadata", {})

        pkg = prompt_composer.compose(
            template_name,
            variables=variables,
            version=version,
            style_guides=style_guides,
            knowledge_references=knowledge_references,
            metadata=metadata,
        )

        # Store in manifest context
        if "prompt_packages" not in context:
            context["prompt_packages"] = []
        context["prompt_packages"].append(pkg)

        return pkg.to_dict()

    engine.register_stage_handler("prompt_engine.compose", compose_prompt)

    # ---- render prompt ---------------------------------------------------
    def render_prompt(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Render a composed prompt."""
        from .models import PromptPackage

        pkg_data = input_data.get("package")
        if pkg_data is None:
            raise ValueError("prompt_engine.render requires 'package' in input_data")

        pkg = PromptPackage.from_dict(pkg_data)
        format = input_data.get("format", "chat")

        if format == "chat":
            return {"format": "chat", "messages": prompt_renderer.render_chat(pkg)}
        elif format == "text":
            return {"format": "text", "text": prompt_renderer.render_text(pkg)}
        elif format == "dict":
            return {"format": "dict", "data": prompt_renderer.render_dict(pkg)}
        else:
            raise ValueError(f"Unknown render format: {format}")

    engine.register_stage_handler("prompt_engine.render", render_prompt)

    # ---- validate prompt -------------------------------------------------
    def validate_prompt(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a prompt package."""
        from .models import PromptPackage

        pkg_data = input_data.get("package")
        if pkg_data is None:
            raise ValueError("prompt_engine.validate requires 'package' in input_data")

        pkg = PromptPackage.from_dict(pkg_data)
        errors = prompt_validator.validate_package(pkg)
        is_valid = len(errors) == 0

        if not is_valid and input_data.get("strict", False):
            raise ValueError(f"Prompt validation failed: {errors}")

        return {"is_valid": is_valid, "errors": errors}

    engine.register_stage_handler("prompt_engine.validate", validate_prompt)