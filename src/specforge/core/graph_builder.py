"""Dependency graph construction and ASCII/Mermaid serialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from specforge.core.status_models import DependencyGraph, GraphNode

if TYPE_CHECKING:
    from specforge.core.status_collector import ManifestData

# ── Status display maps ──────────────────────────────────────────────

_STATUS_MARKER: dict[str, str] = {
    "COMPLETE": "✓",
    "IN_PROGRESS": "~",
    "FAILED": "✗",
    "NOT_STARTED": "○",
    "BLOCKED": "!",
    "PLANNING": "~",
}

_STATUS_CLASS: dict[str, str] = {
    "COMPLETE": "done",
    "IN_PROGRESS": "progress",
    "FAILED": "failed",
    "NOT_STARTED": "notstarted",
    "BLOCKED": "blocked",
    "PLANNING": "progress",
}


# ── Graph construction ───────────────────────────────────────────────


def build_dependency_graph(
    manifest_data: ManifestData,
    service_statuses: dict[str, str],
    phase_groups: tuple[tuple[str, ...], ...] = (),
) -> DependencyGraph:
    """Build a DependencyGraph from manifest services and communication."""
    deps_map = _collect_dependencies(manifest_data)
    nodes = tuple(
        GraphNode(
            slug=svc.slug,
            status=service_statuses.get(svc.slug, "UNKNOWN"),
            dependencies=tuple(sorted(deps_map.get(svc.slug, set()))),
        )
        for svc in manifest_data.services
    )
    return DependencyGraph(nodes=nodes, phase_groups=phase_groups)


def _collect_dependencies(
    manifest_data: ManifestData,
) -> dict[str, set[str]]:
    """Map each source service to its dependency targets."""
    deps: dict[str, set[str]] = {}
    for comm in manifest_data.communication:
        deps.setdefault(comm.source, set()).add(comm.target)
    return deps


# ── ASCII renderer ───────────────────────────────────────────────────


def render_ascii(graph: DependencyGraph) -> str:
    """Render layered ASCII art of the dependency graph."""
    if graph.phase_groups:
        return _render_ascii_phased(graph)
    return _render_ascii_flat(graph)


def _status_marker(status: str) -> str:
    """Return the single-char status indicator for a status string."""
    return _STATUS_MARKER.get(status, "?")


def _format_node_label(node: GraphNode) -> str:
    """Format a single node as '[✓] slug'."""
    return f"[{_status_marker(node.status)}] {node.slug}"


def _render_ascii_flat(graph: DependencyGraph) -> str:
    """Render nodes as a simple flat list (no phases)."""
    node_map = {n.slug: n for n in graph.nodes}
    lines = [_format_node_label(node_map[n.slug]) for n in graph.nodes]
    return "\n".join(lines)


def _render_ascii_phased(graph: DependencyGraph) -> str:
    """Render nodes grouped by phase with arrow separators."""
    node_map = {n.slug: n for n in graph.nodes}
    lines: list[str] = []
    for idx, group in enumerate(graph.phase_groups):
        labels = [_format_node_label(node_map[s]) for s in group if s in node_map]
        lines.append(f"Phase {idx}: {'  '.join(labels)}")
        if idx < len(graph.phase_groups) - 1:
            lines.append("          │")
            lines.append("          ▼")
    return "\n".join(lines)


# ── Mermaid renderer ─────────────────────────────────────────────────


def render_mermaid(graph: DependencyGraph) -> str:
    """Render the graph as a valid Mermaid graph TD block."""
    lines: list[str] = ["graph TD"]
    lines.extend(_mermaid_node_lines(graph))
    lines.extend(_mermaid_edge_lines(graph))
    lines.extend(_mermaid_class_defs())
    return "\n".join(lines)


def _mermaid_node_lines(graph: DependencyGraph) -> list[str]:
    """Generate Mermaid node declaration lines."""
    lines: list[str] = []
    for node in graph.nodes:
        marker = _status_marker(node.status)
        cls = _STATUS_CLASS.get(node.status, "notstarted")
        lines.append(f'    {node.slug}["{marker} {node.slug}"]:::{cls}')
    return lines


def _mermaid_edge_lines(graph: DependencyGraph) -> list[str]:
    """Generate Mermaid edge lines from dependency relationships."""
    lines: list[str] = []
    for node in graph.nodes:
        for dep in node.dependencies:
            lines.append(f"    {dep} --> {node.slug}")
    return lines


def _mermaid_class_defs() -> list[str]:
    """Return the standard Mermaid classDef lines."""
    return [
        "    classDef done fill:#2d6,stroke:#000",
        "    classDef progress fill:#fc0,stroke:#000",
        "    classDef failed fill:#f44,stroke:#000",
        "    classDef blocked fill:#999,stroke:#000",
        "    classDef notstarted fill:#eee,stroke:#000",
    ]
