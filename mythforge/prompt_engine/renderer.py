"""
Prompt Renderer.

Converts a :class:`PromptPackage` into provider-neutral output formats.

Providers never see templates — they receive the rendered output from this
module.  The renderer is responsible for:

- Assembling the final message structure (system / developer / user roles)
- Formatting negative prompts
- Formatting output schemas
- Producing a plain-text rendering
- Producing a structured dict rendering (for chat-style APIs)

Usage::

    from mythforge.prompt_engine.renderer import PromptRenderer

    renderer = PromptRenderer()
    messages = renderer.render_chat(pkg)
    # [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    text = renderer.render_text(pkg)
    # "System: ...\n\nUser: ..."
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .exceptions import RenderingError
from .models import PromptPackage


class PromptRenderer:
    """Render a :class:`PromptPackage` into provider-neutral formats.

    This renderer is intentionally simple — it produces structures that
    any provider SDK can consume without modification.
    """

    # ------------------------------------------------------------------
    # Chat-style rendering (list of message dicts)
    # ------------------------------------------------------------------

    def render_chat(self, pkg: PromptPackage) -> List[Dict[str, str]]:
        """Render as a list of ``{"role": ..., "content": ...}`` dicts.

        The order follows the OpenAI chat convention but is provider-neutral:

        1. system (if present)
        2. developer (if present)
        3. user (with negative prompts and output schema appended)
        """
        messages: List[Dict[str, str]] = []

        if pkg.system_prompt:
            messages.append({"role": "system", "content": pkg.system_prompt})

        if pkg.developer_prompt:
            messages.append({"role": "developer", "content": pkg.developer_prompt})

        user_content = self._build_user_content(pkg)
        if user_content:
            messages.append({"role": "user", "content": user_content})

        if not messages:
            raise RenderingError(
                "Cannot render empty PromptPackage — at least one prompt section is required.",
                details={"package_id": pkg.id, "template_name": pkg.template_name},
            )

        return messages

    # ------------------------------------------------------------------
    # Plain text rendering
    # ------------------------------------------------------------------

    def render_text(self, pkg: PromptPackage) -> str:
        """Render as a single plain-text string with role labels."""
        sections: List[str] = []

        if pkg.system_prompt:
            sections.append(f"[SYSTEM]\n{pkg.system_prompt}")

        if pkg.developer_prompt:
            sections.append(f"[DEVELOPER]\n{pkg.developer_prompt}")

        user_content = self._build_user_content(pkg)
        if user_content:
            sections.append(f"[USER]\n{user_content}")

        if not sections:
            raise RenderingError(
                "Cannot render empty PromptPackage.",
                details={"package_id": pkg.id},
            )

        return "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Structured dict rendering
    # ------------------------------------------------------------------

    def render_dict(self, pkg: PromptPackage) -> Dict[str, Any]:
        """Render as a structured dict suitable for JSON serialisation.

        Includes all prompt sections plus metadata for provider SDKs.
        """
        result: Dict[str, Any] = {
            "template_name": pkg.template_name,
            "version": str(pkg.version),
            "hash": pkg.hash,
        }

        if pkg.system_prompt:
            result["system_prompt"] = pkg.system_prompt
        if pkg.developer_prompt:
            result["developer_prompt"] = pkg.developer_prompt

        user_content = self._build_user_content(pkg)
        if user_content:
            result["user_prompt"] = user_content

        if pkg.negative_prompts:
            result["negative_prompts"] = pkg.negative_prompts
        if pkg.output_schema:
            result["output_schema"] = pkg.output_schema
        if pkg.model_preferences:
            result["model_preferences"] = pkg.model_preferences
        if pkg.metadata:
            result["metadata"] = pkg.metadata

        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_user_content(self, pkg: PromptPackage) -> str:
        """Build the full user-facing content string."""
        parts: List[str] = []

        if pkg.user_prompt:
            parts.append(pkg.user_prompt)

        # Append negative prompts as constraints
        if pkg.negative_prompts:
            neg = "\n".join(f"- {n}" for n in pkg.negative_prompts)
            parts.append(f"IMPORTANT CONSTRAINTS:\n{neg}")

        # Append output schema hint
        if pkg.output_schema:
            import json
            schema_str = json.dumps(pkg.output_schema, indent=2, ensure_ascii=False)
            parts.append(f"EXPECTED OUTPUT FORMAT:\n{schema_str}")

        return "\n\n".join(parts)