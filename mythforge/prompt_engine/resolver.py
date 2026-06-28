"""
Variable resolver for Prompt Templates.

Handles ``{{variable}}`` substitution in prompt text, including:

- Simple variables: ``{{name}}``
- Nested variables: ``{{character.name}}``
- Default values: ``{{location|a dark forest}}``
- Partial insertion: ``{{>partial_name}}``
- Missing variable detection
- Type validation against :class:`VariableSpec`

Usage::

    from mythforge.prompt_engine.resolver import VariableResolver

    resolver = VariableResolver()
    result = resolver.resolve(
        "Write a {{scene_type}} scene in {{location|a castle}}.",
        variables={"scene_type": "action"},
    )
    assert result == "Write a action scene in a castle."
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import MissingVariableError, VariableResolutionError, VariableValidationError
from .models import VariableSpec

# Matches {{variable}}, {{variable|default}}, {{>partial}}
_VARIABLE_RE = re.compile(r"\{\{([^}]+)\}\}")


class VariableResolver:
    """Resolve ``{{variable}}`` placeholders in template text.

    Parameters
    ----------
    strict:
        If ``True``, raise :class:`MissingVariableError` for any variable
        that is missing and has no default.  If ``False``, leave the
        placeholder in place.
    """

    def __init__(self, *, strict: bool = True) -> None:
        self.strict = strict

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        text: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        variable_specs: Optional[List[VariableSpec]] = None,
        partials: Optional[Dict[str, str]] = None,
        template_name: Optional[str] = None,
    ) -> str:
        """Resolve all ``{{variable}}`` placeholders in *text*.

        Parameters
        ----------
        text:
            The template text containing ``{{variable}}`` placeholders.
        variables:
            Variable values to inject.
        variable_specs:
            Variable specifications for validation (optional).
        partials:
            Named partial templates for ``{{>partial_name}}`` insertion.
        template_name:
            Template name for error messages.

        Returns
        -------
        str
            The resolved text with all placeholders replaced.
        """
        variables = variables or {}
        partials = partials or {}
        specs_map = {s.name: s for s in (variable_specs or [])}

        def replacer(match: re.Match) -> str:
            raw = match.group(1).strip()

            # Partial insertion: {{>partial_name}}
            if raw.startswith(">"):
                partial_name = raw[1:].strip()
                if partial_name not in partials:
                    raise VariableResolutionError(
                        f"Partial not found: {partial_name!r}",
                        details={"partial_name": partial_name},
                    )
                return partials[partial_name]

            # Variable with default: {{variable|default_value}}
            if "|" in raw:
                var_name, default_value = raw.split("|", 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
            else:
                var_name = raw
                default_value = None

            # Resolve the variable value
            value = self._lookup(var_name, variables)

            if value is None:
                value = default_value

            if value is None:
                if self.strict:
                    raise MissingVariableError(var_name, template_name=template_name)
                return match.group(0)  # Leave placeholder in place

            # Validate against spec if available
            spec = specs_map.get(var_name)
            if spec is not None:
                self._validate(var_name, value, spec)

            return str(value)

        return _VARIABLE_RE.sub(replacer, text)

    def find_variables(self, text: str) -> List[Tuple[str, Optional[str]]]:
        """Extract all variable references from *text*.

        Returns a list of ``(variable_name, default_value_or_None)`` tuples.
        Partial references (``{{>name}}``) are excluded.
        """
        variables: List[Tuple[str, Optional[str]]] = []
        for match in _VARIABLE_RE.finditer(text):
            raw = match.group(1).strip()
            if raw.startswith(">"):
                continue  # Skip partials
            if "|" in raw:
                var_name, default = raw.split("|", 1)
                variables.append((var_name.strip(), default.strip()))
            else:
                variables.append((raw, None))
        return variables

    def find_missing(
        self,
        text: str,
        variables: Dict[str, Any],
        *,
        variable_specs: Optional[List[VariableSpec]] = None,
    ) -> List[str]:
        """Return names of variables that are missing and have no default.

        Only considers variables that are actually used in *text*.
        """
        specs_map = {s.name: s for s in (variable_specs or [])}
        missing: List[str] = []
        for var_name, default_value in self.find_variables(text):
            if var_name in variables:
                continue
            if default_value is not None:
                continue
            spec = specs_map.get(var_name)
            if spec and not spec.required and spec.default is not None:
                continue
            if spec and not spec.required:
                continue
            missing.append(var_name)
        return missing

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _lookup(self, var_name: str, variables: Dict[str, Any]) -> Any:
        """Look up a variable, supporting dotted paths for nested access.

        ``{{character.name}}`` → ``variables["character"]["name"]``
        """
        parts = var_name.split(".")
        current: Any = variables
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    return None
                current = current[part]
            else:
                return None
        return current

    def _validate(self, var_name: str, value: Any, spec: VariableSpec) -> None:
        """Validate a variable value against its spec."""
        # Enum validation
        if spec.enum is not None and value not in spec.enum:
            raise VariableValidationError(
                var_name, value,
                reason=f"Value must be one of {spec.enum}",
            )