"""Communication pattern assignment and Mermaid diagram generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommunicationLink:
    """A directed communication link between two services."""

    target: str
    pattern: str
    required: bool
    description: str


@dataclass(frozen=True)
class Event:
    """An async event produced by one service and consumed by others."""

    name: str
    producer: str
    consumers: tuple[str, ...]
    payload_summary: str


class CommunicationPlanner:
    """Assigns communication patterns and generates diagrams."""

    def plan(
        self,
        services: list,
    ) -> tuple[list, list[Event]]:
        """Assign communication patterns between services."""
        slugs = {s.slug for s in services}
        events: list[Event] = []
        updated: list = []

        for svc in services:
            links = self._assign_links(svc, services, slugs)
            new_events = self._create_events(svc, links)
            events.extend(new_events)
            updated.append(_with_communication(svc, links))

        return updated, events

    def generate_mermaid(
        self,
        services: list,
        events: list[Event],
    ) -> str:
        """Generate a Mermaid flowchart diagram."""
        lines = ["graph LR"]
        for svc in services:
            for link in svc.communication:
                arrow = _mermaid_arrow(link)
                label = link.pattern
                lines.append(
                    f"    {svc.slug}{arrow}|{label}|{link.target}"
                )
        return "\n".join(lines)

    def detect_cycles(self, services: list) -> list[list[str]]:
        """Detect circular dependencies using DFS."""
        graph = _build_graph(services)
        return _find_cycles(graph)

    def _assign_links(
        self,
        svc: object,
        all_services: list,
        slugs: set[str],
    ) -> tuple[CommunicationLink, ...]:
        """Assign communication links for a service."""
        links: list[CommunicationLink] = []
        for other in all_services:
            if other.slug == svc.slug:
                continue
            pattern = _determine_pattern(svc, other)
            required = pattern != "async-event"
            links.append(
                CommunicationLink(
                    target=other.slug,
                    pattern=pattern,
                    required=required,
                    description=f"{svc.name} communicates with {other.name}",
                )
            )
        return tuple(links)

    def _create_events(
        self,
        svc: object,
        links: tuple[CommunicationLink, ...],
    ) -> list[Event]:
        """Create async events for event-based links."""
        events: list[Event] = []
        for link in links:
            if link.pattern == "async-event":
                events.append(
                    Event(
                        name=f"{svc.slug}.data.updated",
                        producer=svc.slug,
                        consumers=(link.target,),
                        payload_summary=f"Data update from {svc.name}",
                    )
                )
        return events


def _determine_pattern(source: object, target: object) -> str:
    """Determine communication pattern using heuristic rules."""
    target_name = target.slug.lower()
    if "notification" in target_name:
        return "async-event"
    if "auth" in target_name or "identity" in target_name:
        return "sync-rest"
    return "sync-rest"


def _with_communication(svc: object, links: tuple) -> object:
    """Return a new Service with updated communication links."""
    from specforge.core.service_mapper import Service

    return Service(
        name=svc.name,
        slug=svc.slug,
        feature_ids=svc.feature_ids,
        rationale=svc.rationale,
        communication=links,
    )


def _mermaid_arrow(link: CommunicationLink) -> str:
    """Return Mermaid arrow syntax based on required flag."""
    if link.required:
        return " --> "
    return " -.-> "


def _build_graph(services: list) -> dict[str, list[str]]:
    """Build adjacency list from service communication links."""
    graph: dict[str, list[str]] = {}
    for svc in services:
        graph.setdefault(svc.slug, [])
        for link in svc.communication:
            graph[svc.slug].append(link.target)
    return graph


def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Find all cycles using DFS."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    in_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        if node in in_stack:
            start = path.index(node)
            cycles.append([*path[start:], node])
            return
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor)
        path.pop()
        in_stack.discard(node)

    for node in graph:
        dfs(node)
    return cycles
