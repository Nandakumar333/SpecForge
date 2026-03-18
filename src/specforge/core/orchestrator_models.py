"""Frozen dataclasses for the integration orchestrator (Feature 011)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


# ── Plan & Phase ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Phase:
    """A group of independent services at the same dependency depth."""

    index: int
    services: tuple[str, ...]
    dependencies_satisfied: tuple[str, ...] = ()


@dataclass(frozen=True)
class OrchestrationPlan:
    """Computed execution plan derived from the manifest dependency graph."""

    architecture: str
    phases: tuple[Phase, ...]
    total_services: int
    shared_infra_required: bool = False


# ── Per-Service / Per-Phase Status ────────────────────────────────────


@dataclass(frozen=True)
class ServiceStatus:
    """Per-service implementation status within a phase."""

    slug: str
    status: str = "pending"
    error: str | None = None
    tasks_completed: int = 0
    tasks_total: int = 0
    started_at: str | None = None
    completed_at: str | None = None


@dataclass(frozen=True)
class PhaseState:
    """Per-phase progress within OrchestrationState."""

    index: int
    status: str = "pending"
    services: tuple[ServiceStatus, ...] = ()
    started_at: str | None = None
    completed_at: str | None = None


# ── Project-Level State ───────────────────────────────────────────────


@dataclass(frozen=True)
class OrchestrationState:
    """Project-level execution progress, persisted to JSON."""

    architecture: str
    schema_version: str = "1.0"
    status: str = "pending"
    shared_infra_status: str = "pending"
    phases: tuple[PhaseState, ...] = ()
    verification_results: tuple[VerificationResult, ...] = ()
    integration_result: IntegrationTestResult | None = None
    phase_ceiling: int | None = None
    started_at: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


# ── Contract Verification ─────────────────────────────────────────────


@dataclass(frozen=True)
class ContractMismatch:
    """A specific contract violation between two services."""

    contract_file: str
    field: str
    expected: str
    actual: str
    severity: str = "error"


@dataclass(frozen=True)
class ContractCheckResult:
    """Result of contract verification between a service pair."""

    consumer: str
    provider: str
    passed: bool
    mismatches: tuple[ContractMismatch, ...] = ()


@dataclass(frozen=True)
class BoundaryCheckResult:
    """Result of shared entity boundary analysis between services."""

    entity: str
    services: tuple[str, ...]
    violation_type: str
    details: str


# ── Verification (inter-phase) ────────────────────────────────────────


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of inter-phase contract/boundary verification."""

    after_phase: int
    passed: bool
    contract_results: tuple[ContractCheckResult, ...] = ()
    boundary_results: tuple[BoundaryCheckResult, ...] = ()
    infra_health: bool | None = None
    timestamp: str = field(default_factory=_now_iso)


# ── Integration Test Results ──────────────────────────────────────────


@dataclass(frozen=True)
class HealthCheckResult:
    """Per-service health check result."""

    service: str
    passed: bool
    status_code: int | None = None
    response_time_ms: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class RouteCheckResult:
    """Gateway route verification result."""

    route: str
    target_service: str
    passed: bool
    error: str | None = None


@dataclass(frozen=True)
class RequestFlowResult:
    """Cross-service request flow test result."""

    passed: bool
    steps: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class EventPropagationResult:
    """Event bus propagation test result."""

    passed: bool
    events_tested: tuple[str, ...] = ()
    failed_events: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class IntegrationTestResult:
    """Result of final integration validation."""

    passed: bool
    health_checks: tuple[HealthCheckResult, ...] = ()
    gateway_routes: tuple[RouteCheckResult, ...] = ()
    request_flow: RequestFlowResult | None = None
    event_propagation: EventPropagationResult | None = None
    timestamp: str = field(default_factory=_now_iso)


# ── Final Report ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class IntegrationReport:
    """Final summary report covering the entire orchestration run."""

    architecture: str
    total_phases: int
    total_services: int
    verdict: str
    succeeded_services: int = 0
    failed_services: int = 0
    skipped_services: int = 0
    phase_results: tuple[PhaseState, ...] = ()
    verification_results: tuple[VerificationResult, ...] = ()
    integration_result: IntegrationTestResult | None = None
    created_at: str = field(default_factory=_now_iso)
