"""Unit tests for dependency_graph.py — pure functions for topological sort."""

from __future__ import annotations

import pytest

from specforge.core.dependency_graph import build_graph, compute_phases, detect_cycles


class TestBuildGraph:
    def test_build_graph_from_manifest(self) -> None:
        """6-service manifest → adjacency dict with correct deps."""
        manifest = _make_manifest(
            services=[
                "identity-service",
                "admin-service",
                "ledger-service",
                "portfolio-service",
                "planning-service",
                "analytics-service",
            ],
            links=[
                ("ledger-service", "identity-service"),
                ("portfolio-service", "identity-service"),
                ("planning-service", "ledger-service"),
                ("analytics-service", "ledger-service"),
                ("analytics-service", "portfolio-service"),
            ],
        )
        result = build_graph(manifest)
        assert result.ok
        graph = result.value
        assert graph["identity-service"] == ()
        assert graph["admin-service"] == ()
        assert graph["ledger-service"] == ("identity-service",)
        assert graph["portfolio-service"] == ("identity-service",)
        assert graph["planning-service"] == ("ledger-service",)
        assert set(graph["analytics-service"]) == {"ledger-service", "portfolio-service"}

    def test_build_graph_empty_manifest(self) -> None:
        manifest = {"services": []}
        result = build_graph(manifest)
        assert not result.ok

    def test_build_graph_no_communication(self) -> None:
        manifest = _make_manifest(services=["a", "b", "c"], links=[])
        result = build_graph(manifest)
        assert result.ok
        for svc in ("a", "b", "c"):
            assert result.value[svc] == ()

    def test_build_graph_unknown_dependency_target(self) -> None:
        manifest = _make_manifest(
            services=["a"],
            links=[("a", "nonexistent")],
        )
        result = build_graph(manifest)
        assert not result.ok
        assert "nonexistent" in result.error


class TestDetectCycles:
    def test_no_cycles(self) -> None:
        graph = {"a": (), "b": ("a",), "c": ("b",)}
        assert detect_cycles(graph) == ()

    def test_simple_cycle(self) -> None:
        graph = {"a": ("b",), "b": ("a",)}
        cycles = detect_cycles(graph)
        assert len(cycles) > 0

    def test_self_cycle(self) -> None:
        graph = {"a": ("a",)}
        cycles = detect_cycles(graph)
        assert len(cycles) > 0

    def test_complex_cycle(self) -> None:
        graph = {"a": ("b",), "b": ("c",), "c": ("a",), "d": ("a",)}
        cycles = detect_cycles(graph)
        assert len(cycles) > 0
        # d should NOT be in the cycle
        cycle_nodes = {n for cycle in cycles for n in cycle}
        assert "d" not in cycle_nodes


class TestComputePhases:
    def test_three_phase_scenario(self) -> None:
        """The canonical 3-phase test scenario."""
        graph = {
            "identity-service": (),
            "admin-service": (),
            "ledger-service": ("identity-service",),
            "portfolio-service": ("identity-service",),
            "planning-service": ("ledger-service",),
            "analytics-service": ("ledger-service", "portfolio-service"),
        }
        result = compute_phases(graph)
        assert result.ok
        phases = result.value
        assert len(phases) == 3
        # Phase 0: admin + identity (sorted alpha)
        assert phases[0].index == 0
        assert phases[0].services == ("admin-service", "identity-service")
        assert phases[0].dependencies_satisfied == ()
        # Phase 1: ledger + portfolio
        assert phases[1].index == 1
        assert phases[1].services == ("ledger-service", "portfolio-service")
        # Phase 2: analytics + planning
        assert phases[2].index == 2
        assert phases[2].services == ("analytics-service", "planning-service")

    def test_single_service(self) -> None:
        graph = {"only-service": ()}
        result = compute_phases(graph)
        assert result.ok
        assert len(result.value) == 1
        assert result.value[0].services == ("only-service",)

    def test_all_independent(self) -> None:
        graph = {"a": (), "b": (), "c": (), "d": ()}
        result = compute_phases(graph)
        assert result.ok
        assert len(result.value) == 1
        assert result.value[0].services == ("a", "b", "c", "d")

    def test_linear_chain(self) -> None:
        graph = {"a": (), "b": ("a",), "c": ("b",)}
        result = compute_phases(graph)
        assert result.ok
        assert len(result.value) == 3
        assert result.value[0].services == ("a",)
        assert result.value[1].services == ("b",)
        assert result.value[2].services == ("c",)

    def test_graph_with_cycle_returns_err(self) -> None:
        graph = {"a": ("b",), "b": ("a",)}
        result = compute_phases(graph)
        assert not result.ok
        assert "cycle" in result.error.lower()

    def test_notification_service_phase(self) -> None:
        """notification depends on ledger + planning → must be Phase 3."""
        graph = {
            "identity-service": (),
            "admin-service": (),
            "ledger-service": ("identity-service",),
            "portfolio-service": ("identity-service",),
            "planning-service": ("ledger-service",),
            "analytics-service": ("ledger-service", "portfolio-service"),
            "notification-service": ("ledger-service", "planning-service"),
        }
        result = compute_phases(graph)
        assert result.ok
        phases = result.value
        # notification depends on planning (Phase 2), so must be Phase 3
        notification_phase = None
        for phase in phases:
            if "notification-service" in phase.services:
                notification_phase = phase.index
                break
        assert notification_phase == 3


def _make_manifest(
    services: list[str],
    links: list[tuple[str, str]],
) -> dict:
    """Build a minimal manifest dict for testing."""
    svc_list = []
    for slug in services:
        comm = [{"target": target} for source, target in links if source == slug]
        svc_list.append({"slug": slug, "communication": comm})
    return {"services": svc_list}


class TestEdgeCases:
    """Edge case tests for dependency graph."""

    def test_single_service_no_deps_single_phase(self) -> None:
        """1 service → 1 phase, acts as pass-through."""
        graph = {"only-service": ()}
        result = compute_phases(graph)
        assert result.ok
        assert len(result.value) == 1
        assert result.value[0].services == ("only-service",)
        assert result.value[0].dependencies_satisfied == ()

    def test_service_missing_from_manifest_in_communication(self) -> None:
        """A depends on B but B not in services → Err."""
        manifest = {
            "services": [
                {"slug": "a", "communication": [{"target": "b"}]},
            ],
        }
        result = build_graph(manifest)
        assert not result.ok
        assert "b" in result.error
