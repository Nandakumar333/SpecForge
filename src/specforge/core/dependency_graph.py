"""Pure functions for dependency graph operations (Feature 011).

Implements Kahn's algorithm for topological sort with phase grouping.
"""

from __future__ import annotations

from specforge.core.orchestrator_models import Phase
from specforge.core.result import Err, Ok, Result


def build_graph(
    manifest: dict,
) -> Result[dict[str, tuple[str, ...]], str]:
    """Extract dependency adjacency dict from manifest.

    Returns mapping of service_slug → tuple of dependency slugs.
    """
    services: list[dict] = manifest.get("services", [])
    if not services:
        return Err("Manifest contains no services")

    slugs = frozenset(svc["slug"] for svc in services)
    graph: dict[str, tuple[str, ...]] = {}

    for svc in services:
        slug: str = svc["slug"]
        deps: list[str] = []
        for link in svc.get("communication", []):
            target: str = link["target"]
            if target not in slugs:
                return Err(
                    f"Service '{slug}' depends on '{target}' "
                    f"which is not in the manifest"
                )
            deps.append(target)
        graph[slug] = tuple(sorted(deps))

    return Ok(graph)


def detect_cycles(
    graph: dict[str, tuple[str, ...]],
) -> tuple[tuple[str, ...], ...]:
    """Detect cycles using DFS. Returns tuple of cycles found."""
    white, gray, black = 0, 1, 2
    color: dict[str, int] = {node: white for node in graph}
    path: list[str] = []
    cycles: list[tuple[str, ...]] = []

    def _dfs(node: str) -> None:
        color[node] = gray
        path.append(node)
        for neighbor in graph.get(node, ()):
            if color.get(neighbor) == gray:
                cycle_start = path.index(neighbor)
                cycles.append(tuple(path[cycle_start:]))
            elif color.get(neighbor) == white:
                _dfs(neighbor)
        path.pop()
        color[node] = black

    for node in sorted(graph):
        if color[node] == white:
            _dfs(node)

    return tuple(cycles)


def compute_phases(
    graph: dict[str, tuple[str, ...]],
) -> Result[tuple[Phase, ...], str]:
    """Compute execution phases via Kahn's algorithm.

    Services with no remaining deps form a phase. Within each phase,
    services are sorted alphabetically for determinism.
    """
    cycles = detect_cycles(graph)
    if cycles:
        cycle_str = " → ".join(cycles[0])
        return Err(f"Dependency cycle detected: {cycle_str}")

    satisfied: set[str] = set()
    satisfied_order: list[str] = []
    remaining: set[str] = set(graph)
    phases: list[Phase] = []

    while remaining:
        ready = sorted(
            n for n in remaining
            if all(d in satisfied for d in graph[n])
        )
        if not ready:
            return Err("Unexpected cycle in dependency graph")

        phase = Phase(
            index=len(phases),
            services=tuple(ready),
            dependencies_satisfied=tuple(satisfied_order),
        )
        phases.append(phase)

        for node in ready:
            remaining.discard(node)
            satisfied.add(node)
            satisfied_order.append(node)

    return Ok(tuple(phases))
