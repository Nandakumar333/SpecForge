"""Frozen dataclasses for the Project Status Dashboard (Feature 012)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifecyclePhases:
    """Per-service spec/plan/tasks/impl/test/docker status."""

    spec: str | None = None
    plan: str | None = None
    tasks: str | None = None
    impl_percent: int | None = None
    tests_passed: int | None = None
    tests_total: int | None = None
    docker: str | None = None
    boundary_compliance: str | None = None


@dataclass(frozen=True)
class ServiceStatusRecord:
    """One service's full status combining data from all state files."""

    slug: str
    display_name: str
    features: tuple[str, ...]
    lifecycle: LifecyclePhases
    overall_status: str
    phase_index: int | None = None


@dataclass(frozen=True)
class ServicePhaseDetail:
    """Per-service status within a phase (used in phase progress notes)."""

    slug: str
    status: str
    impl_percent: int | None = None


@dataclass(frozen=True)
class PhaseProgressRecord:
    """Execution phase aggregate status."""

    index: int
    label: str
    services: tuple[str, ...]
    completion_percent: float
    status: str
    blocked_by: int | None = None
    service_details: tuple[ServicePhaseDetail, ...] = ()


@dataclass(frozen=True)
class QualitySummaryRecord:
    """Project-wide aggregated quality metrics."""

    services_total: int
    services_complete: int
    services_in_progress: int
    services_planning: int
    services_not_started: int
    services_blocked: int
    services_failed: int
    services_unknown: int
    tasks_total: int
    tasks_complete: int
    tasks_failed: int
    coverage_avg: float | None = None
    docker_built: int | None = None
    docker_total: int | None = None
    docker_failing: int | None = None
    contract_passed: int | None = None
    contract_total: int | None = None
    autofix_success_rate: float | None = None


@dataclass(frozen=True)
class GraphNode:
    """Individual node in the dependency graph."""

    slug: str
    status: str
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class DependencyGraph:
    """Service dependency topology for graph visualization."""

    nodes: tuple[GraphNode, ...]
    phase_groups: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class ProjectStatusSnapshot:
    """Top-level point-in-time capture of the entire project."""

    project_name: str
    architecture: str
    services: tuple[ServiceStatusRecord, ...]
    phases: tuple[PhaseProgressRecord, ...]
    quality: QualitySummaryRecord
    graph: DependencyGraph
    warnings: tuple[str, ...]
    timestamp: str
    has_failures: bool
