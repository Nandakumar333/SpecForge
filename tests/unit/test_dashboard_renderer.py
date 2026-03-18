"""Unit tests for Rich dashboard rendering (Feature 012 — Phase 8)."""

from __future__ import annotations

import io

from rich.console import Console

from specforge.cli.dashboard_renderer import (
    render_badge,
    render_dashboard,
    render_graph,
    render_phase_progress,
    render_quality_summary,
    render_service_table,
)
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

# ── Helpers ───────────────────────────────────────────────────────────


def _capture_console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120, highlight=False)
    return console, buf


def _make_quality(**overrides: object) -> QualitySummaryRecord:
    defaults: dict = {
        "services_total": 3,
        "services_complete": 1,
        "services_in_progress": 1,
        "services_planning": 0,
        "services_not_started": 1,
        "services_blocked": 0,
        "services_failed": 0,
        "services_unknown": 0,
        "tasks_total": 10,
        "tasks_complete": 5,
        "tasks_failed": 0,
    }
    defaults.update(overrides)
    return QualitySummaryRecord(**defaults)


def _make_service(**overrides: object) -> ServiceStatusRecord:
    defaults: dict = {
        "slug": "auth-service",
        "display_name": "Auth Service",
        "features": ("user-auth",),
        "lifecycle": LifecyclePhases(),
        "overall_status": "NOT_STARTED",
    }
    defaults.update(overrides)
    return ServiceStatusRecord(**defaults)


def _make_snapshot(**overrides: object) -> ProjectStatusSnapshot:
    defaults: dict = {
        "project_name": "TestProject",
        "architecture": "microservice",
        "services": (_make_service(),),
        "phases": (),
        "quality": _make_quality(),
        "graph": DependencyGraph(nodes=()),
        "warnings": (),
        "timestamp": "2026-03-18T00:00:00Z",
        "has_failures": False,
    }
    defaults.update(overrides)
    return ProjectStatusSnapshot(**defaults)


# ── TestRenderBadge ───────────────────────────────────────────────────


class TestRenderBadge:
    def test_render_badge_microservice(self) -> None:
        console, buf = _capture_console()
        render_badge(console, "microservice")
        assert "MICROSERVICE" in buf.getvalue()

    def test_render_badge_monolith(self) -> None:
        console, buf = _capture_console()
        render_badge(console, "monolithic")
        assert "MONOLITH" in buf.getvalue()

    def test_render_badge_modular(self) -> None:
        console, buf = _capture_console()
        render_badge(console, "modular-monolith")
        assert "MODULAR" in buf.getvalue()


# ── TestRenderServiceTable ────────────────────────────────────────────


class TestRenderServiceTable:
    def test_includes_docker_column_for_microservice(self) -> None:
        console, buf = _capture_console()
        snap = _make_snapshot(architecture="microservice")
        render_service_table(console, snap)
        assert "Docker" in buf.getvalue()

    def test_omits_docker_column_for_monolith(self) -> None:
        console, buf = _capture_console()
        snap = _make_snapshot(architecture="monolithic")
        render_service_table(console, snap)
        assert "Docker" not in buf.getvalue()

    def test_includes_boundary_column_for_modular(self) -> None:
        console, buf = _capture_console()
        snap = _make_snapshot(architecture="modular-monolith")
        render_service_table(console, snap)
        assert "Boundary" in buf.getvalue()

    def test_not_started_shows_dashes(self) -> None:
        console, buf = _capture_console()
        svc = _make_service(lifecycle=LifecyclePhases(), overall_status="NOT_STARTED")
        snap = _make_snapshot(services=(svc,))
        render_service_table(console, snap)
        output = buf.getvalue()
        # Dashes should appear for None lifecycle fields
        assert "-" in output

    def test_single_service(self) -> None:
        console, buf = _capture_console()
        svc = _make_service(
            slug="api-gateway",
            display_name="API Gateway",
            lifecycle=LifecyclePhases(spec="DONE", plan="WIP"),
            overall_status="PLANNING",
        )
        snap = _make_snapshot(services=(svc,))
        render_service_table(console, snap)
        output = buf.getvalue()
        assert "API Gateway" in output

    def test_15_services(self) -> None:
        console, buf = _capture_console()
        services = tuple(
            _make_service(
                slug=f"svc-{i:02d}",
                display_name=f"Service {i:02d}",
                overall_status="IN_PROGRESS" if i % 2 == 0 else "NOT_STARTED",
            )
            for i in range(15)
        )
        snap = _make_snapshot(services=services)
        render_service_table(console, snap)
        output = buf.getvalue()
        for i in range(15):
            assert f"Service {i:02d}" in output


# ── TestRenderPhaseProgress ───────────────────────────────────────────


class TestRenderPhaseProgress:
    def test_render_phase_progress_bars(self) -> None:
        console, buf = _capture_console()
        phases = (
            PhaseProgressRecord(
                index=0,
                label="Phase 0: Foundation",
                services=("auth-service",),
                completion_percent=75.0,
                status="in-progress",
                service_details=(
                    ServicePhaseDetail(slug="auth-service", status="IN_PROGRESS", impl_percent=75),
                ),
            ),
            PhaseProgressRecord(
                index=1,
                label="Phase 1: Core",
                services=("pay-service",),
                completion_percent=0.0,
                status="blocked",
                blocked_by=0,
                service_details=(
                    ServicePhaseDetail(slug="pay-service", status="BLOCKED"),
                ),
            ),
        )
        render_phase_progress(console, phases)
        output = buf.getvalue()
        assert "Phase 0: Foundation" in output
        assert "75%" in output
        assert "Phase 1: Core" in output
        assert "blocked" in output.lower()


# ── TestRenderQualitySummary ──────────────────────────────────────────


class TestRenderQualitySummary:
    def test_render_quality_summary_panel(self) -> None:
        console, buf = _capture_console()
        quality = _make_quality(
            services_total=5,
            services_complete=2,
            services_in_progress=1,
            tasks_total=20,
            tasks_complete=10,
            tasks_failed=1,
        )
        render_quality_summary(console, quality, "microservice")
        output = buf.getvalue()
        assert "5 total" in output
        assert "2 complete" in output
        assert "20 total" in output
        assert "10 complete" in output

    def test_omits_docker_for_monolith(self) -> None:
        console, buf = _capture_console()
        quality = _make_quality(docker_built=2, docker_total=3, docker_failing=0)
        render_quality_summary(console, quality, "monolithic")
        output = buf.getvalue()
        assert "Docker" not in output


# ── TestRenderGraph ───────────────────────────────────────────────────


class TestRenderGraph:
    def test_render_graph_ascii(self) -> None:
        console, buf = _capture_console()
        graph = DependencyGraph(
            nodes=(
                GraphNode(slug="auth", status="COMPLETE"),
                GraphNode(slug="pay", status="IN_PROGRESS", dependencies=("auth",)),
            ),
        )
        snap = _make_snapshot(graph=graph)
        render_graph(console, snap)
        output = buf.getvalue()
        # ASCII graph contains status indicators
        assert "auth" in output
        assert "pay" in output


# ── TestRenderDashboard ───────────────────────────────────────────────


class TestRenderDashboard:
    def test_render_dashboard_full(self) -> None:
        console, buf = _capture_console()
        svc = _make_service(
            lifecycle=LifecyclePhases(spec="DONE", plan="DONE", tasks="WIP", impl_percent=50),
            overall_status="IN_PROGRESS",
        )
        phases = (
            PhaseProgressRecord(
                index=0,
                label="Phase 0: Foundation",
                services=("auth-service",),
                completion_percent=50.0,
                status="in-progress",
            ),
        )
        quality = _make_quality(services_total=1, services_in_progress=1, tasks_total=5, tasks_complete=2)
        graph = DependencyGraph(
            nodes=(GraphNode(slug="auth-service", status="IN_PROGRESS"),),
        )
        snap = _make_snapshot(
            services=(svc,),
            phases=phases,
            quality=quality,
            graph=graph,
            warnings=("Test warning",),
        )
        render_dashboard(console, snap, show_graph=True)
        output = buf.getvalue()
        # All sections should be present
        assert "MICROSERVICE" in output  # badge
        assert "Service Status" in output  # table title
        assert "Phase Progress" in output  # phases
        assert "Quality Summary" in output  # quality panel
        assert "Dependency Graph" in output  # graph panel
        assert "Warnings" in output  # warnings panel
