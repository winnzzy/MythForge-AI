"""
Prompt Engine exceptions.

All exceptions inherit from :class:`PromptEngineError` so callers can catch
the entire hierarchy with a single ``except`` clause.

Usage::

    from mythforge.prompt_engine.exceptions import (
        PromptEngineError,
        TemplateError,
        VariableResolutionError,
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PromptEngineError(Exception):
    """Base exception for all Prompt Engine errors."""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# Template errors
# ---------------------------------------------------------------------------

class TemplateError(PromptEngineError):
    """Base exception for template-related errors."""
    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a template cannot be found in the registry."""

    def __init__(self, template_name: str, *, version: Optional[str] = None) -> None:
        self.template_name = template_name
        self.version = version
        msg = f"Template not found: {template_name!r}"
        if version:
            msg += f" (version {version})"
        super().__init__(msg, details={"template_name": template_name, "version": version})


class TemplateInheritanceError(TemplateError):
    """Raised when template inheritance resolution fails."""

    def __init__(self, message: str, *, chain: Optional[List[str]] = None) -> None:
        self.chain = chain or []
        super().__init__(message, details={"inheritance_chain": self.chain})


class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""

    def __init__(self, message: str, *, errors: Optional[List[str]] = None) -> None:
        self.validation_errors = errors or []
        super().__init__(message, details={"validation_errors": self.validation_errors})


class CircularInheritanceError(TemplateInheritanceError):
    """Raised when a circular inheritance chain is detected."""

    def __init__(self, chain: List[str]) -> None:
        self.cycle = chain
        msg = f"Circular template inheritance detected: {' → '.join(chain)}"
        super().__init__(msg, chain=chain)


# ---------------------------------------------------------------------------
# Variable errors
# ---------------------------------------------------------------------------

class VariableResolutionError(PromptEngineError):
    """Base exception for variable resolution errors."""
    pass


class MissingVariableError(VariableResolutionError):
    """Raised when a required variable is missing and has no default."""

    def __init__(self, variable_name: str, *, template_name: Optional[str] = None) -> None:
        self.variable_name = variable_name
        self.template_name = template_name
        msg = f"Missing required variable: {variable_name!r}"
        if template_name:
            msg += f" (in template {template_name!r})"
        super().__init__(
            msg,
            details={"variable_name": variable_name, "template_name": template_name},
        )


class VariableValidationError(VariableResolutionError):
    """Raised when a variable value fails validation."""

    def __init__(
        self,
        variable_name: str,
        value: Any,
        *,
        expected_type: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        self.variable_name = variable_name
        self.value = value
        msg = f"Variable validation failed: {variable_name!r} = {value!r}"
        if reason:
            msg += f" — {reason}"
        super().__init__(
            msg,
            details={
                "variable_name": variable_name,
                "value": value,
                "expected_type": expected_type,
                "reason": reason,
            },
        )


# ---------------------------------------------------------------------------
# Composition / rendering errors
# ---------------------------------------------------------------------------

class CompositionError(PromptEngineError):
    """Raised when prompt composition fails."""
    pass


class RenderingError(PromptEngineError):
    """Raised when prompt rendering fails."""
    pass


class ValidationError(PromptEngineError):
    """Raised when prompt package validation fails."""

    def __init__(self, message: str, *, errors: Optional[List[str]] = None) -> None:
        self.validation_errors = errors or []
        super().__init__(message, details={"validation_errors": self.validation_errors})


# ---------------------------------------------------------------------------
# Version errors
# ---------------------------------------------------------------------------

class VersionError(PromptEngineError):
    """Raised for version-related errors."""
    pass


class InvalidVersionError(VersionError):
    """Raised when a version string is invalid."""

    def __init__(self, version_string: str) -> None:
        self.version_string = version_string
        super().__init__(f"Invalid version string: {version_string!r}")


# ---------------------------------------------------------------------------
# Cache errors
# ---------------------------------------------------------------------------

class CacheError(PromptEngineError):
    """Raised for cache-related errors."""
    pass