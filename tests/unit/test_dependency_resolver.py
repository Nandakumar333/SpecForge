"""Tests for DependencyResolver — DAG, topological sort, cycle detection."""

from __future__ import annotations

import pytest

from specforge.core.task_models import TaskItem


def _task(
    tid: str,
    deps: tuple[str, ...] = (),
    phase: int = 1,
    paths: tuple[str, ...] = (),
) -> TaskItem:
    """Create a minimal TaskItem for testing."""
    return TaskItem(
        id=tid, description=f"Task {tid}", phase=phase, layer="test",
        dependencies=deps, parallel=False, effort="S", user_story="US1",
        file_paths=paths, service_scope="test", governance_rules=(),
        commit_message=f"feat: {tid}",
    )


class TestBuildGraph:
    """DependencyResolver.build_graph() tests."""

    def test_empty_task_list(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        result = resolver.build_graph([])
        assert result.ok
        assert result.value.adjacency == {}

    def test_linear_chain(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [_task("T001"), _task("T002", ("T001",))]
        resolver = DependencyResolver()
        result = resolver.build_graph(tasks)
        assert result.ok
        graph = result.value
        assert graph.in_degree["T001"] == 0
        assert graph.in_degree["T002"] == 1

    def test_branching_deps(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001"),
            _task("T002", ("T001",)),
            _task("T003", ("T001",)),
        ]
        resolver = DependencyResolver()
        result = resolver.build_graph(tasks)
        assert result.ok
        graph = result.value
        assert graph.in_degree["T002"] == 1
        assert graph.in_degree["T003"] == 1

    def test_missing_dependency_returns_err(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [_task("T001", ("T999",))]
        resolver = DependencyResolver()
        result = resolver.build_graph(tasks)
        assert not result.ok
        assert "T999" in result.error

    def test_xdep_references_skipped(self) -> None:
        """External XDEP references are valid but not in local graph."""
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001"),
            _task("T002", ("T001", "cross-service-infra/X-T001")),
        ]
        resolver = DependencyResolver()
        result = resolver.build_graph(tasks)
        assert result.ok


class TestTopologicalSort:
    """DependencyResolver.topological_sort() — Kahn's algorithm."""

    def test_linear_chain_order(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001", phase=1),
            _task("T002", ("T001",), phase=2),
            _task("T003", ("T002",), phase=3),
        ]
        resolver = DependencyResolver()
        graph = resolver.build_graph(tasks).value
        ordered = resolver.topological_sort(graph)
        ids = [t.id for t in ordered]
        assert ids == ["T001", "T002", "T003"]

    def test_stable_sort_by_phase_and_order(self) -> None:
        """Tasks at same depth sorted by (phase, id) for determinism."""
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001", phase=1),
            _task("T003", ("T001",), phase=3),
            _task("T002", ("T001",), phase=2),
        ]
        resolver = DependencyResolver()
        graph = resolver.build_graph(tasks).value
        ordered = resolver.topological_sort(graph)
        ids = [t.id for t in ordered]
        assert ids[0] == "T001"
        # T002 (phase=2) before T003 (phase=3) due to stable sort
        assert ids.index("T002") < ids.index("T003")

    def test_deterministic_output(self) -> None:
        """Same input always produces same output."""
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001"), _task("T002", ("T001",)),
            _task("T003", ("T001",)), _task("T004", ("T002", "T003")),
        ]
        resolver = DependencyResolver()
        results = []
        for _ in range(10):
            graph = resolver.build_graph(tasks).value
            ordered = resolver.topological_sort(graph)
            results.append([t.id for t in ordered])
        assert all(r == results[0] for r in results)

    def test_no_task_before_its_dependencies(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001"),
            _task("T002", ("T001",)),
            _task("T003", ("T002",)),
            _task("T004", ("T001",)),
        ]
        resolver = DependencyResolver()
        graph = resolver.build_graph(tasks).value
        ordered = resolver.topological_sort(graph)
        ids = [t.id for t in ordered]
        for task in tasks:
            task_idx = ids.index(task.id)
            for dep in task.dependencies:
                if "/" not in dep:
                    dep_idx = ids.index(dep)
                    assert dep_idx < task_idx, (
                        f"{dep} must come before {task.id}"
                    )


class TestCycleDetection:
    """Cycle detection in DependencyResolver."""

    def test_cycle_returns_err(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001", ("T002",)),
            _task("T002", ("T001",)),
        ]
        resolver = DependencyResolver()
        result = resolver.build_graph(tasks)
        if result.ok:
            sorted_result = resolver.topological_sort(result.value)
            # Kahn's detects cycles as incomplete processing
            assert len(sorted_result) < len(tasks) or not result.ok
        else:
            assert "ircular" in result.error or "ycle" in result.error

    def test_self_referential_detected(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [_task("T001", ("T001",))]
        resolver = DependencyResolver()
        result = resolver.build_graph(tasks)
        if result.ok:
            graph = result.value
            sorted_tasks = resolver.topological_sort(graph)
            assert len(sorted_tasks) == 0  # Kahn's won't process it

    def test_valid_dag_returns_ok(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001"),
            _task("T002", ("T001",)),
        ]
        resolver = DependencyResolver()
        result = resolver.build_graph(tasks)
        assert result.ok


class TestMarkParallel:
    """DependencyResolver.mark_parallel() tests."""

    def test_disjoint_paths_marked_parallel(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001", phase=1, paths=("src/svc/",)),
            _task("T002", ("T001",), phase=2, paths=("src/svc/clients/",)),
            _task("T003", ("T001",), phase=2, paths=("src/svc/controllers/",)),
        ]
        resolver = DependencyResolver()
        graph = resolver.build_graph(tasks).value
        marked = resolver.mark_parallel(tasks, graph)
        t2 = next(t for t in marked if t.id == "T002")
        t3 = next(t for t in marked if t.id == "T003")
        assert t2.parallel is True
        assert t3.parallel is True

    def test_shared_paths_not_parallel(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [
            _task("T001", phase=1, paths=("src/svc/",)),
            _task("T002", ("T001",), phase=2, paths=("src/svc/shared/",)),
            _task("T003", ("T001",), phase=2, paths=("src/svc/shared/",)),
        ]
        resolver = DependencyResolver()
        graph = resolver.build_graph(tasks).value
        marked = resolver.mark_parallel(tasks, graph)
        t2 = next(t for t in marked if t.id == "T002")
        t3 = next(t for t in marked if t.id == "T003")
        assert t2.parallel is False
        assert t3.parallel is False

    def test_root_task_not_parallel(self) -> None:
        from specforge.core.dependency_resolver import DependencyResolver

        tasks = [_task("T001", phase=1, paths=("src/svc/",))]
        resolver = DependencyResolver()
        graph = resolver.build_graph(tasks).value
        marked = resolver.mark_parallel(tasks, graph)
        assert marked[0].parallel is False
