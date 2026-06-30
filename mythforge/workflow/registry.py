"""
Stage Registry.

Central registry for stage definitions.  Allows future engineers to register
new stages without modifying engine code.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from mythforge.workflow.models import (
    CostEstimate,
    RetryPolicy,
    StageDefinition,
)

logger = logging.getLogger(__name__)


class StageRegistry:
    """Registry of stage definitions.

    Stages can be registered at any time before workflow execution.
    The registry is the single source of truth for what stages exist
    and how they behave.

    Usage::

        registry = StageRegistry()

        @registry.stage("RESEARCH", dependencies=[], parallel_eligible=True)
        def do_research(input_data, context):
            ...

        @registry.stage("SCRIPT", dependencies=["RESEARCH"])
        def do_script(input_data, context):
            ...

        # Retrieve definitions
        definitions = registry.definitions()
    """

    def __init__(self) -> None:
        self._stages: Dict[str, StageDefinition] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        definition: StageDefinition,
    ) -> None:
        """Register a stage definition.

        Parameters
        ----------
        definition:
            A :class:`StageDefinition` instance.

        Raises
        ------
        ValueError
            If a stage with the same name is already registered.
        """
        if definition.name in self._stages:
            raise ValueError(
                f"Stage '{definition.name}' is already registered. "
                "Use unregister() first to replace it."
            )
        self._stages[definition.name] = definition
        logger.debug("Registered stage: %s", definition.name)

    def register_handler(
        self,
        name: str,
        handler: Callable[..., Dict[str, Any]],
        *,
        dependencies: Optional[List[str]] = None,
        required_inputs: Optional[List[str]] = None,
        produced_outputs: Optional[List[str]] = None,
        parallel_eligible: bool = False,
        retry_policy: Optional[RetryPolicy] = None,
        cost_estimate: Optional[CostEstimate] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StageDefinition:
        """Register a stage by name and handler.

        Convenience method that builds a :class:`StageDefinition` from
        the provided parameters and registers it.

        Returns the created :class:`StageDefinition`.
        """
        defn = StageDefinition(
            name=name,
            handler=handler,
            dependencies=dependencies or [],
            required_inputs=required_inputs or [],
            produced_outputs=produced_outputs or [],
            parallel_eligible=parallel_eligible,
            retry_policy=retry_policy or RetryPolicy(),
            cost_estimate=cost_estimate or CostEstimate(),
            metadata=metadata or {},
        )
        self.register(defn)
        return defn

    def stage(
        self,
        name: str,
        *,
        dependencies: Optional[List[str]] = None,
        required_inputs: Optional[List[str]] = None,
        produced_outputs: Optional[List[str]] = None,
        parallel_eligible: bool = False,
        retry_policy: Optional[RetryPolicy] = None,
        cost_estimate: Optional[CostEstimate] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Decorator to register a function as a stage handler.

        Usage::

            @registry.stage("RESEARCH", dependencies=[], parallel_eligible=True)
            def do_research(input_data, context):
                ...
        """

        def decorator(fn: Callable[..., Dict[str, Any]]) -> Callable:
            self.register_handler(
                name,
                fn,
                dependencies=dependencies,
                required_inputs=required_inputs,
                produced_outputs=produced_outputs,
                parallel_eligible=parallel_eligible,
                retry_policy=retry_policy,
                cost_estimate=cost_estimate,
                metadata=metadata,
            )
            return fn

        return decorator

    def unregister(self, name: str) -> None:
        """Remove a registered stage.

        Raises ``KeyError`` if the stage is not registered.
        """
        if name not in self._stages:
            raise KeyError(f"Stage '{name}' is not registered.")
        del self._stages[name]
        logger.debug("Unregistered stage: %s", name)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[StageDefinition]:
        """Return the stage definition for *name*, or ``None``."""
        return self._stages.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._stages

    def __len__(self) -> int:
        return len(self._stages)

    def names(self) -> List[str]:
        """Return all registered stage names."""
        return list(self._stages.keys())

    def definitions(self) -> List[StageDefinition]:
        """Return all registered stage definitions."""
        return list(self._stages.values())

    def clear(self) -> None:
        """Remove all registered stages."""
        self._stages.clear()

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def register_all(self, definitions: List[StageDefinition]) -> None:
        """Register multiple stage definitions at once.

        Raises ``ValueError`` if any name conflicts.
        """
        for defn in definitions:
            self.register(defn)

    def to_workflow_stages(self) -> List[StageDefinition]:
        """Return stage definitions as a list suitable for
        :class:`WorkflowDefinition.stages`.
        """
        return self.definitions()