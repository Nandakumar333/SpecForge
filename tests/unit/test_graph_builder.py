"""Unit tests for graph_builder (Feature 012 — Phase 7)."""

from __future__ import annotations

from specforge.core.graph_builder import (
    build_dependency_graph,
    render_ascii,
    render_mermaid,
)
from specforge.core.status_collector import (
    CommunicationEntry,
    ManifestData,
    ManifestServiceEntry,
)
from specforge.core.status_models import DependencyGraph, GraphNode

# ── Helpers ───────────────────────────────────────────────────────────


def _manifest(
    services: list[dict],
    communication: list[tuple[str, str]] | None = None,
) -> ManifestData:
    """Build ManifestData with compact syntax."""
    svc_entries = tuple(
        ManifestServiceEntry(
            slug=s["slug"],
            display_name=s.get("name", s["slug"]),
            features=tuple(s.get("features", [])),
        )
        for s in services
    )
    comm_entries = tuple(
        CommunicationEntry(source=src, target=tgt)
        for src, tgt in (communication or [])
    )
    return ManifestData(
        project_name="test-project",
        architecture="microservice",
        services=svc_entries,
        communication=comm_entries,
    )


# ── T027: TestBuildDependencyGraph ───────────────────────────────────


class TestBuildDependencyGraph:
    def test_build_graph_from_manifest(self) -> None:
        """Creates correct topology from communication entries."""
        manifest = _manifest(
            services=[
                {"slug": "auth-service"},
                {"slug": "payment-service"},
                {"slug": "order-service"},
            ],
            communication=[
                ("payment-service", "auth-service"),
                ("order-service", "auth-service"),
                ("order-service", "payment-service"),
            ],
        )
        statuses = {
            "auth-service": "COMPLETE",
            "payment-service": "IN_PROGRESS",
            "order-service": "NOT_STARTED",
        }

        graph = build_dependency_graph(manifest, statuses)

        node_map = {n.slug: n for n in graph.nodes}
        assert len(node_map) == 3
        # source depends on target
        assert "auth-service" in node_map["payment-service"].dependencies
        assert "auth-service" in node_map["order-service"].dependencies
        assert "payment-service" in node_map["order-service"].dependencies
        assert node_map["auth-service"].dependencies == ()

    def test_build_graph_annotates_status(self) -> None:
        """Nodes have status values from service_statuses dict."""
        manifest = _manifest(
            services=[{"slug": "svc-a"}, {"slug": "svc-b"}],
        )
        statuses = {"svc-a": "COMPLETE", "svc-b": "FAILED"}

        graph = build_dependency_graph(manifest, statuses)

        node_map = {n.slug: n for n in graph.nodes}
        assert node_map["svc-a"].status == "COMPLETE"
        assert node_map["svc-b"].status == "FAILED"

    def test_build_graph_no_dependencies(self) -> None:
        """Independent nodes have no edges."""
        manifest = _manifest(
            services=[{"slug": "a"}, {"slug": "b"}, {"slug": "c"}],
        )
        statuses = {"a": "COMPLETE", "b": "COMPLETE", "c": "NOT_STARTED"}

        graph = build_dependency_graph(manifest, statuses)

        for node in graph.nodes:
            assert node.dependencies == ()

    def test_build_graph_monolith_flat(self) -> None:
        """Monolith with no communication produces nodes without edges."""
        manifest = _manifest(
            services=[{"slug": "monolith"}],
        )
        statuses = {"monolith": "IN_PROGRESS"}

        graph = build_dependency_graph(manifest, statuses)

        assert len(graph.nodes) == 1
        assert graph.nodes[0].slug == "monolith"
        assert graph.nodes[0].dependencies == ()

    def test_build_graph_unknown_status_defaults(self) -> None:
        """Service not in statuses dict gets 'UNKNOWN' status."""
        manifest = _manifest(services=[{"slug": "orphan"}])

        graph = build_dependency_graph(manifest, {})

        assert graph.nodes[0].status == "UNKNOWN"

    def test_build_graph_preserves_phase_groups(self) -> None:
        """phase_groups parameter is passed through to DependencyGraph."""
        manifest = _manifest(
            services=[{"slug": "a"}, {"slug": "b"}],
        )
        phases = (("a",), ("b",))

        graph = build_dependency_graph(manifest, {}, phase_groups=phases)

        assert graph.phase_groups == phases


# ── T027: TestRenderAscii ────────────────────────────────────────────


class TestRenderAscii:
    def test_render_ascii_contains_status_labels(self) -> None:
        """Status markers ✓ ~ ✗ ○ ! are present for corresponding statuses."""
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="done-svc", status="COMPLETE"),
                GraphNode(slug="wip-svc", status="IN_PROGRESS"),
                GraphNode(slug="fail-svc", status="FAILED"),
                GraphNode(slug="new-svc", status="NOT_STARTED"),
                GraphNode(slug="block-svc", status="BLOCKED"),
            ),
        )

        output = render_ascii(graph)

        assert "[✓] done-svc" in output
        assert "[~] wip-svc" in output
        assert "[✗] fail-svc" in output
        assert "[○] new-svc" in output
        assert "[!] block-svc" in output

    def test_render_ascii_phase_layers(self) -> None:
        """Groups services by phase when phase_groups provided."""
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="auth", status="COMPLETE"),
                GraphNode(slug="user", status="COMPLETE"),
                GraphNode(slug="payment", status="IN_PROGRESS"),
            ),
            phase_groups=(("auth", "user"), ("payment",)),
        )

        output = render_ascii(graph)

        assert "Phase 0" in output
        assert "Phase 1" in output
        assert "[✓] auth" in output
        assert "[~] payment" in output

    def test_render_ascii_flat_when_no_phases(self) -> None:
        """Without phase_groups, renders a flat list."""
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="a", status="COMPLETE"),
                GraphNode(slug="b", status="NOT_STARTED"),
            ),
        )

        output = render_ascii(graph)

        assert "Phase" not in output
        assert "[✓] a" in output
        assert "[○] b" in output

    def test_render_ascii_unknown_status(self) -> None:
        """Unknown status gets ? marker."""
        graph = DependencyGraph(
            nodes=(GraphNode(slug="mystery", status="SOMETHING_WEIRD"),),
        )

        output = render_ascii(graph)

        assert "[?] mystery" in output


# ── T027: TestRenderMermaid ──────────────────────────────────────────


class TestRenderMermaid:
    def test_render_mermaid_valid_syntax(self) -> None:
        """Produces graph TD block with nodes and edges."""
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="auth", status="COMPLETE"),
                GraphNode(
                    slug="payment",
                    status="IN_PROGRESS",
                    dependencies=("auth",),
                ),
            ),
        )

        output = render_mermaid(graph)

        assert output.startswith("graph TD")
        assert 'auth["✓ auth"]' in output
        assert 'payment["~ payment"]' in output
        assert "auth --> payment" in output

    def test_render_mermaid_status_styles(self) -> None:
        """Has classDef lines for done, progress, failed, blocked, notstarted."""
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="a", status="COMPLETE"),
                GraphNode(slug="b", status="FAILED"),
            ),
        )

        output = render_mermaid(graph)

        assert "classDef done" in output
        assert "classDef progress" in output
        assert "classDef failed" in output
        assert "classDef blocked" in output
        assert "classDef notstarted" in output

    def test_render_mermaid_class_assignment(self) -> None:
        """Nodes get correct class based on status."""
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="done-svc", status="COMPLETE"),
                GraphNode(slug="fail-svc", status="FAILED"),
                GraphNode(slug="new-svc", status="NOT_STARTED"),
                GraphNode(slug="block-svc", status="BLOCKED"),
                GraphNode(slug="wip-svc", status="IN_PROGRESS"),
            ),
        )

        output = render_mermaid(graph)

        assert ":::done" in output
        assert ":::failed" in output
        assert ":::notstarted" in output
        assert ":::blocked" in output
        assert ":::progress" in output

    def test_render_mermaid_no_edges_when_no_deps(self) -> None:
        """Graph with independent nodes has no --> lines."""
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="a", status="COMPLETE"),
                GraphNode(slug="b", status="COMPLETE"),
            ),
        )

        output = render_mermaid(graph)

        assert "-->" not in output
