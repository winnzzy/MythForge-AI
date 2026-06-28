"""
Prompt Package validation.

Validates both :class:`PromptTemplate` (pre-composition) and
:class:`PromptPackage` (post-composition) objects.

Usage::

    from mythforge.prompt_engine.validator import PromptValidator

    validator = PromptValidator()
    errors = validator.validate_package(pkg)
    if errors:
        for e in errors:
            print(f"  - {e}")
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError
from .models import PromptPackage, PromptTemplate, VariableSpec
from .resolver import VariableResolver

# Pattern that detects unresolved variables in rendered text
_UNRESOLVED_RE = re.compile(r"\{\{[^>}][^}]*\}\}")


class PromptValidator:
    """Validate prompt templates and packages.

    Parameters
    ----------
    min_system_length:
        Minimum acceptable system prompt length (characters).
    max_total_tokens:
        Maximum estimated token count before a warning is raised.
    """

    def __init__(
        self,
        *,
        min_system_length: int = 10,
        max_total_tokens: int = 100_000,
    ) -> None:
        self.min_system_length = min_system_length
        self.max_total_tokens = max_total_tokens
        self._resolver = VariableResolver(strict=False)

    # ------------------------------------------------------------------
    # Template validation
    # ------------------------------------------------------------------

    def validate_template(
        self,
        template: PromptTemplate,
        *,
        parent: Optional[PromptTemplate] = None,
    ) -> List[str]:
        """Validate a :class:`PromptTemplate`.

        Returns a list of error strings.  An empty list means valid.
        """
        errors: List[str] = []

        # Name
        if not template.name or not template.name.strip():
            errors.append("Template name is required and must not be blank.")

        # At least one prompt section
        has_any_prompt = bool(
            template.system_prompt or template.developer_prompt or template.user_prompt
        )
        if not has_any_prompt:
            errors.append(
                "Template must define at least one of: system_prompt, "
                "developer_prompt, or user_prompt."
            )

        # System prompt minimum length
        if template.system_prompt and len(template.system_prompt) < self.min_system_length:
            errors.append(
                f"System prompt is too short ({len(template.system_prompt)} chars, "
                f"minimum {self.min_system_length})."
            )

        # Undefined variables
        for field_name in ("system_prompt", "developer_prompt", "user_prompt"):
            text = getattr(template, field_name, "") or ""
            for var_name, _ in self._resolver.find_variables(text):
                if var_name not in template.variable_names:
                    errors.append(
                        f"Undefined variable {{{{{var_name}}}}} in {field_name}."
                    )

        # Duplicate variable names
        seen: Dict[str, int] = {}
        for v in template.variables:
            seen[v.name] = seen.get(v.name, 0) + 1
        for name, count in seen.items():
            if count > 1:
                errors.append(f"Duplicate variable definition: {name!r} (defined {count} times).")

        # Parent existence
        if template.extends and parent is None:
            errors.append(
                f"Template declares extends={template.extends!r} but no parent was provided."
            )

        return errors

    # ------------------------------------------------------------------
    # Package validation
    # ------------------------------------------------------------------

    def validate_package(self, pkg: PromptPackage) -> List[str]:
        """Validate a :class:`PromptPackage`.

        Returns a list of error strings.  An empty list means valid.
        """
        errors: List[str] = []

        # Template name
        if not pkg.template_name or not pkg.template_name.strip():
            errors.append("PromptPackage.template_name is required.")

        # At least one prompt
        has_any = bool(pkg.system_prompt or pkg.developer_prompt or pkg.user_prompt)
        if not has_any:
            errors.append(
                "PromptPackage must have at least one of: system_prompt, "
                "developer_prompt, or user_prompt."
            )

        # System prompt minimum length
        if pkg.system_prompt and len(pkg.system_prompt) < self.min_system_length:
            errors.append(
                f"System prompt is too short ({len(pkg.system_prompt)} chars, "
                f"minimum {self.min_system_length})."
            )

        # No unresolved variables
        for field_name in ("system_prompt", "developer_prompt", "user_prompt"):
            text = getattr(pkg, field_name, "") or ""
            unresolved = _UNRESOLVED_RE.findall(text)
            if unresolved:
                errors.append(
                    f"Unresolved variables in {field_name}: {unresolved}"
                )

        # Hash present
        if not pkg.hash:
            errors.append("PromptPackage.hash is empty — hash must be computed before delivery.")

        # Token estimate
        if pkg.estimated_tokens > self.max_total_tokens:
            errors.append(
                f"Estimated token count ({pkg.estimated_tokens}) exceeds "
                f"maximum ({self.max_total_tokens})."
            )

        return errors

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def is_valid_package(self, pkg: PromptPackage) -> bool:
        """Return ``True`` if the package passes all validation checks."""
        return len(self.validate_package(pkg)) == 0

    def is_valid_template(self, template: PromptTemplate) -> bool:
        """Return ``True`` if the template passes all validation checks."""
        return len(self.validate_template(template)) == 0

    def assert_valid_package(self, pkg: PromptPackage) -> None:
        """Raise :class:`ValidationError` if the package is invalid."""
        errors = self.validate_package(pkg)
        if errors:
            raise ValidationError("PromptPackage validation failed.", errors=errors)

    def assert_valid_template(self, template: PromptTemplate) -> None:
        """Raise :class:`ValidationError` if the template is invalid."""
        errors = self.validate_template(template)
        if errors:
            raise ValidationError("PromptTemplate validation failed.", errors=errors)