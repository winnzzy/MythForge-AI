"""
Dependency Graph (DAG).

Validates and queries the directed acyclic graph of stage dependencies.
Topological sort produces deterministic execution order.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set

from mythforge.workflow.models import StageDefinition

logger = logging.getLogger(__name__)


class CyclicDependencyError(Exception):
    """The dependency graph contains a cycle."""

    def __init__(self, cycle: List[str]) -> None:
        self.cycle = cycle
        path = " -> ".join(cycle)
        super().__init__(f"Cyclic dependency detected: {path}")


class DependencyGraph:
    """Directed acyclic graph of stage dependencies.

    Build from a list of :class:`StageDefinition` instances, then query
    for topological order, ready stages, etc.

    Parameters
    ----------
    stages:
        List of stage definitions to build the graph from.
    """

    def __init__(self, stages: List[StageDefinition]) -> None:
        self._stages: Dict[str, StageDefinition] = {s.name: s for s in stages}
        self._edges: Dict[str, List[str]] = defaultdict(list)  # name -> [dependants]
        self._in_degree: Dict[str, int] = {}
        self._build()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Build adjacency lists and in-degree counts."""
        all_names: Set[str] = set(self._stages.keys())

        for name in all_names:
            self._in_degree.setdefault(name, 0)

        for name, defn in self._stages.items():
            for dep in defn.dependencies:
                if dep not in all_names:
                    raise ValueError(
                        f"Stage '{name}' depends on '{dep}' which is not defined."
                    )
                self._edges[dep].append(name)
                self._in_degree[name] += 1

        # Validate acyclicity
        self._detect_cycles()

    def _detect_cycles(self) -> None:
        """Detect cycles using Kahn's algorithm.

        Raises :class:`CyclicDependencyError` if a cycle is found.
        """
        in_deg = dict(self._in_degree)
        queue = deque(n for n, d in in_deg.items() if d == 0)
        visited = 0

        while queue:
            node = queue.popleft()
            visited += 1
            for neighbour in self._edges.get(node, []):
                in_deg[neighbour] -= 1
                if in_deg[neighbour] == 0:
                    queue.append(neighbour)

        if visited != len(self._stages):
            # Find the cycle for the error message
            remaining = [n for n, d in in_deg.items() if d > 0]
            raise CyclicDependencyError(remaining)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def stage_names(self) -> List[str]:
        """All stage names in the graph."""
        return list(self._stages.keys())

    def get_stage(self, name: str) -> Optional[StageDefinition]:
        """Return the stage definition for *name*, or ``None``."""
        return self._stages.get(name)

    def dependencies_of(self, name: str) -> List[str]:
        """Return the direct dependencies of *name*."""
        defn = self._stages.get(name)
        if defn is None:
            raise KeyError(f"Stage '{name}' not in graph.")
        return list(defn.dependencies)

    def dependants_of(self, name: str) -> List[str]:
        """Return the stages that depend on *name*."""
        if name not in self._stages:
            raise KeyError(f"Stage '{name}' not in graph.")
        return list(self._edges.get(name, []))

    def in_degree(self, name: str) -> int:
        """Return the in-degree (number of unresolved dependencies) of *name*."""
        return self._in_degree.get(name, 0)

    # ------------------------------------------------------------------
    # Topological sort
    # ------------------------------------------------------------------

    def topological_order(self) -> List[str]:
        """Return a deterministic topological ordering of all stages.

        Uses Kahn's algorithm with sorted keys for determinism.
        """
        in_deg = dict(self._in_degree)
        queue = sorted(n for n, d in in_deg.items() if d == 0)
        order: List[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbour in sorted(self._edges.get(node, [])):
                in_deg[neighbour] -= 1
                if in_deg[neighbour] == 0:
                    # Insert maintaining sorted order for determinism
                    self._sorted_insert(queue, neighbour)

        return order

    @staticmethod
    def _sorted_insert(lst: List[str], item: str) -> None:
        """Insert *item* into *lst* maintaining sorted order."""
        for i, v in enumerate(lst):
            if item < v:
                lst.insert(i, item)
                return
        lst.append(item)

    # ------------------------------------------------------------------
    # Execution frontier
    # ------------------------------------------------------------------

    def ready_stages(
        self,
        completed: Set[str],
        exclude: Optional[Set[str]] = None,
    ) -> List[str]:
        """Return stages whose dependencies are all in *completed*.

        Parameters
        ----------
        completed:
            Set of stage names that have already completed.
        exclude:
            Set of stage names to exclude (e.g. already running or failed).

        Returns
        -------
        list[str]
            Sorted list of stage names ready to execute.
        """
        exclude = exclude or set()
        ready = []
        for name in self._stages:
            if name in completed or name in exclude:
                continue
            deps = self._stages[name].dependencies
            if all(d in completed for d in deps):
                ready.append(name)
        return sorted(ready)

    def parallel_groups(self) -> List[List[str]]:
        """Return stages grouped by execution level.

        Each group contains stages that can run in parallel.
        Groups are ordered by dependency depth.

        Returns
        -------
        list[list[str]]
            List of groups, each group a sorted list of stage names.
        """
        in_deg = dict(self._in_degree)
        levels: List[List[str]] = []
        current = sorted(n for n, d in in_deg.items() if d == 0)

        while current:
            levels.append(current)
            next_level = []
            for node in current:
                for neighbour in self._edges.get(node, []):
                    in_deg[neighbour] -= 1
                    if in_deg[neighbour] == 0:
                        next_level.append(neighbour)
            current = sorted(next_level)

        return levels

    def ancestors(self, name: str) -> Set[str]:
        """Return all ancestors (transitive dependencies) of *name*."""
        result: Set[str] = set()
        queue = deque(self._stages[name].dependencies)
        while queue:
            dep = queue.popleft()
            if dep in result:
                continue
            result.add(dep)
            queue.extend(self._stages[dep].dependencies)
        return result

    def validate_inputs(self, context_keys: Set[str]) -> List[str]:
        """Check that all required_inputs are satisfiable.

        Returns a list of error messages for unsatisfied inputs.
        """
        errors = []
        for name, defn in self._stages.items():
            for inp in defn.required_inputs:
                # Input must be either in context or produced by a dependency
                produced_by_deps = set()
                for dep in defn.dependencies:
                    dep_defn = self._stages.get(dep)
                    if dep_defn:
                        produced_by_deps.update(dep_defn.produced_outputs)
                if inp not in context_keys and inp not in produced_by_deps:
                    errors.append(
                        f"Stage '{name}' requires input '{inp}' "
                        "but it is not in context and not produced by any dependency."
                    )
        return errors

    def __len__(self) -> int:
        return len(self._stages)

    def __contains__(self, name: str) -> bool:
        return name in self._stages