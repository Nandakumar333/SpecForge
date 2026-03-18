"""Unit tests for status data models (Feature 012)."""

from __future__ import annotations

import pytest

from specforge.core.status_models import (
    DependencyGraph,
    GraphNode,
    LifecyclePhases,
    PhaseProgressRecord,
    ProjectStatusSnapshot,
    QualitySummaryRecord,
    ServicePhaseDetail,
    ServiceStatusRecord,
)


class TestLifecyclePhases:
    def test_frozen(self) -> None:
        lc = LifecyclePhases()
        with pytest.raises(AttributeError):
            lc.spec = "DONE"  # type: ignore[misc]

    def test_all_fields_nullable(self) -> None:
        lc = LifecyclePhases()
        assert lc.spec is None
        assert lc.plan is None
        assert lc.tasks is None
        assert lc.impl_percent is None
        assert lc.tests_passed is None
        assert lc.tests_total is None
        assert lc.docker is None
        assert lc.boundary_compliance is None

    def test_with_values(self) -> None:
        lc = LifecyclePhases(
            spec="DONE",
            plan="WIP",
            tasks=None,
            impl_percent=75,
            tests_passed=10,
            tests_total=15,
            docker="OK",
            boundary_compliance=None,
        )
        assert lc.spec == "DONE"
        assert lc.plan == "WIP"
        assert lc.impl_percent == 75
        assert lc.docker == "OK"


class TestServiceStatusRecord:
    def test_frozen(self) -> None:
        r = ServiceStatusRecord(
            slug="svc",
            display_name="Svc",
            features=("001",),
            lifecycle=LifecyclePhases(),
            overall_status="NOT_STARTED",
        )
        with pytest.raises(AttributeError):
            r.slug = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        r = ServiceStatusRecord(
            slug="auth-service",
            display_name="Auth Service",
            features=("001", "002"),
            lifecycle=LifecyclePhases(spec="DONE"),
            overall_status="PLANNING",
            phase_index=0,
        )
        assert r.slug == "auth-service"
        assert r.display_name == "Auth Service"
        assert r.features == ("001", "002")
        assert r.lifecycle.spec == "DONE"
        assert r.overall_status == "PLANNING"
        assert r.phase_index == 0

    def test_phase_index_defaults_none(self) -> None:
        r = ServiceStatusRecord(
            slug="s",
            display_name="S",
            features=(),
            lifecycle=LifecyclePhases(),
            overall_status="NOT_STARTED",
        )
        assert r.phase_index is None


class TestServicePhaseDetail:
    def test_fields(self) -> None:
        d = ServicePhaseDetail(slug="auth", status="COMPLETE", impl_percent=100)
        assert d.slug == "auth"
        assert d.status == "COMPLETE"
        assert d.impl_percent == 100

    def test_impl_percent_default_none(self) -> None:
        d = ServicePhaseDetail(slug="s", status="NOT_STARTED")
        assert d.impl_percent is None


class TestPhaseProgressRecord:
    def test_fields(self) -> None:
        detail = ServicePhaseDetail(slug="auth", status="COMPLETE", impl_percent=100)
        p = PhaseProgressRecord(
            index=0,
            label="Phase 1",
            services=("auth",),
            completion_percent=100.0,
            status="complete",
            blocked_by=None,
            service_details=(detail,),
        )
        assert p.index == 0
        assert p.label == "Phase 1"
        assert p.services == ("auth",)
        assert p.completion_percent == 100.0
        assert p.status == "complete"
        assert p.blocked_by is None
        assert len(p.service_details) == 1

    def test_blocked(self) -> None:
        p = PhaseProgressRecord(
            index=1,
            label="Phase 2",
            services=("pay",),
            completion_percent=0.0,
            status="blocked",
            blocked_by=0,
        )
        assert p.blocked_by == 0
        assert p.service_details == ()


class TestQualitySummaryRecord:
    def test_all_14_fields(self) -> None:
        q = QualitySummaryRecord(
            services_total=8,
            services_complete=2,
            services_in_progress=1,
            services_planning=1,
            services_not_started=2,
            services_blocked=1,
            services_failed=1,
            services_unknown=0,
            tasks_total=100,
            tasks_complete=50,
            tasks_failed=3,
            coverage_avg=82.5,
            docker_built=2,
            docker_total=8,
            docker_failing=1,
            contract_passed=3,
            contract_total=5,
            autofix_success_rate=78.0,
        )
        assert q.services_total == 8
        total = (
            q.services_complete
            + q.services_in_progress
            + q.services_planning
            + q.services_not_started
            + q.services_blocked
            + q.services_failed
            + q.services_unknown
        )
        assert total == q.services_total

    def test_optional_defaults_none(self) -> None:
        q = QualitySummaryRecord(
            services_total=1,
            services_complete=0,
            services_in_progress=0,
            services_planning=0,
            services_not_started=1,
            services_blocked=0,
            services_failed=0,
            services_unknown=0,
            tasks_total=0,
            tasks_complete=0,
            tasks_failed=0,
        )
        assert q.coverage_avg is None
        assert q.docker_built is None
        assert q.docker_total is None
        assert q.docker_failing is None
        assert q.contract_passed is None
        assert q.contract_total is None
        assert q.autofix_success_rate is None


class TestGraphNodeAndDependencyGraph:
    def test_graph_node(self) -> None:
        n = GraphNode(slug="auth", status="COMPLETE", dependencies=("db",))
        assert n.slug == "auth"
        assert n.dependencies == ("db",)

    def test_graph_node_no_deps(self) -> None:
        n = GraphNode(slug="auth", status="COMPLETE")
        assert n.dependencies == ()

    def test_dependency_graph(self) -> None:
        n1 = GraphNode(slug="auth", status="COMPLETE")
        n2 = GraphNode(slug="pay", status="IN_PROGRESS", dependencies=("auth",))
        g = DependencyGraph(
            nodes=(n1, n2), phase_groups=(("auth",), ("pay",))
        )
        assert len(g.nodes) == 2
        assert g.phase_groups == (("auth",), ("pay",))

    def test_dependency_graph_empty_groups(self) -> None:
        g = DependencyGraph(nodes=())
        assert g.phase_groups == ()


class TestProjectStatusSnapshot:
    def test_full_snapshot(self) -> None:
        svc = ServiceStatusRecord(
            slug="auth",
            display_name="Auth",
            features=("001",),
            lifecycle=LifecyclePhases(spec="DONE"),
            overall_status="PLANNING",
        )
        quality = QualitySummaryRecord(
            services_total=1,
            services_complete=0,
            services_in_progress=0,
            services_planning=1,
            services_not_started=0,
            services_blocked=0,
            services_failed=0,
            services_unknown=0,
            tasks_total=0,
            tasks_complete=0,
            tasks_failed=0,
        )
        graph = DependencyGraph(nodes=())
        snap = ProjectStatusSnapshot(
            project_name="TestProject",
            architecture="microservice",
            services=(svc,),
            phases=(),
            quality=quality,
            graph=graph,
            warnings=("test warning",),
            timestamp="2026-03-18T00:00:00Z",
            has_failures=False,
        )
        assert snap.project_name == "TestProject"
        assert snap.architecture == "microservice"
        assert len(snap.services) == 1
        assert snap.warnings == ("test warning",)
        assert snap.has_failures is False

    def test_frozen(self) -> None:
        quality = QualitySummaryRecord(
            services_total=0,
            services_complete=0,
            services_in_progress=0,
            services_planning=0,
            services_not_started=0,
            services_blocked=0,
            services_failed=0,
            services_unknown=0,
            tasks_total=0,
            tasks_complete=0,
            tasks_failed=0,
        )
        snap = ProjectStatusSnapshot(
            project_name="P",
            architecture="monolithic",
            services=(),
            phases=(),
            quality=quality,
            graph=DependencyGraph(nodes=()),
            warnings=(),
            timestamp="t",
            has_failures=False,
        )
        with pytest.raises(AttributeError):
            snap.project_name = "X"  # type: ignore[misc]
