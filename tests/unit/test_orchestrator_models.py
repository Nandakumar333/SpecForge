"""Unit tests for orchestrator_models.py — 14 frozen dataclasses."""

from __future__ import annotations

import dataclasses

import pytest


class TestPhase:
    """Phase — a group of independent services at the same depth."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import Phase

        phase = Phase(index=0, services=("identity-service",))
        with pytest.raises(dataclasses.FrozenInstanceError):
            phase.index = 1  # type: ignore[misc]

    def test_fields(self) -> None:
        from specforge.core.orchestrator_models import Phase

        phase = Phase(
            index=1,
            services=("ledger-service", "portfolio-service"),
            dependencies_satisfied=("identity-service",),
        )
        assert phase.index == 1
        assert phase.services == ("ledger-service", "portfolio-service")
        assert phase.dependencies_satisfied == ("identity-service",)

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import Phase

        phase = Phase(index=0, services=("a",))
        assert phase.dependencies_satisfied == ()

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import Phase

        assert len(dataclasses.fields(Phase)) == 3


class TestOrchestrationPlan:
    """OrchestrationPlan — computed execution plan from manifest."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import OrchestrationPlan, Phase

        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(Phase(index=0, services=("a",)),),
            total_services=1,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            plan.architecture = "monolithic"  # type: ignore[misc]

    def test_fields(self) -> None:
        from specforge.core.orchestrator_models import OrchestrationPlan, Phase

        phases = (Phase(index=0, services=("a", "b")),)
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=phases,
            total_services=2,
            shared_infra_required=True,
        )
        assert plan.architecture == "microservice"
        assert len(plan.phases) == 1
        assert plan.total_services == 2
        assert plan.shared_infra_required is True

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import OrchestrationPlan, Phase

        plan = OrchestrationPlan(
            architecture="monolithic",
            phases=(Phase(index=0, services=("a",)),),
            total_services=1,
        )
        assert plan.shared_infra_required is False

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import OrchestrationPlan

        assert len(dataclasses.fields(OrchestrationPlan)) == 4


class TestServiceStatus:
    """ServiceStatus — per-service implementation status."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import ServiceStatus

        ss = ServiceStatus(slug="identity-service")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ss.status = "completed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import ServiceStatus

        ss = ServiceStatus(slug="identity-service")
        assert ss.status == "pending"
        assert ss.error is None
        assert ss.tasks_completed == 0
        assert ss.tasks_total == 0
        assert ss.started_at is None
        assert ss.completed_at is None

    def test_all_statuses_valid(self) -> None:
        from specforge.core.orchestrator_models import ServiceStatus

        for status in ("pending", "in-progress", "completed", "failed", "skipped"):
            ss = ServiceStatus(slug="svc", status=status)
            assert ss.status == status

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import ServiceStatus

        assert len(dataclasses.fields(ServiceStatus)) == 7


class TestPhaseState:
    """PhaseState — per-phase progress within OrchestrationState."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import PhaseState

        ps = PhaseState(index=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            ps.status = "completed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import PhaseState

        ps = PhaseState(index=0)
        assert ps.status == "pending"
        assert ps.services == ()
        assert ps.started_at is None
        assert ps.completed_at is None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import PhaseState

        assert len(dataclasses.fields(PhaseState)) == 5


class TestOrchestrationState:
    """OrchestrationState — project-level execution progress."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import OrchestrationState

        state = OrchestrationState(architecture="microservice")
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.status = "completed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import OrchestrationState

        state = OrchestrationState(architecture="microservice")
        assert state.schema_version == "1.0"
        assert state.status == "pending"
        assert state.shared_infra_status == "pending"
        assert state.phases == ()
        assert state.verification_results == ()
        assert state.integration_result is None
        assert state.phase_ceiling is None
        assert state.started_at is None
        assert state.created_at is not None
        assert state.updated_at is not None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import OrchestrationState

        assert len(dataclasses.fields(OrchestrationState)) == 11


class TestContractMismatch:
    """ContractMismatch — specific contract violation."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import ContractMismatch

        cm = ContractMismatch(
            contract_file="auth-api.json",
            field="claims.role",
            expected='string enum ["admin"]',
            actual="string",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            cm.field = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import ContractMismatch

        cm = ContractMismatch(
            contract_file="a.json", field="x", expected="y", actual="z",
        )
        assert cm.severity == "error"

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import ContractMismatch

        assert len(dataclasses.fields(ContractMismatch)) == 5


class TestContractCheckResult:
    """ContractCheckResult — per-pair contract verification."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import ContractCheckResult

        ccr = ContractCheckResult(
            consumer="ledger", provider="identity", passed=True,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ccr.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import ContractCheckResult

        ccr = ContractCheckResult(
            consumer="a", provider="b", passed=True,
        )
        assert ccr.mismatches == ()

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import ContractCheckResult

        assert len(dataclasses.fields(ContractCheckResult)) == 4


class TestBoundaryCheckResult:
    """BoundaryCheckResult — shared entity boundary analysis."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import BoundaryCheckResult

        bcr = BoundaryCheckResult(
            entity="User",
            services=("identity", "ledger"),
            violation_type="ownership_conflict",
            details="Both services define User entity",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            bcr.entity = "other"  # type: ignore[misc]

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import BoundaryCheckResult

        assert len(dataclasses.fields(BoundaryCheckResult)) == 4


class TestVerificationResult:
    """VerificationResult — inter-phase verification outcome."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import VerificationResult

        vr = VerificationResult(after_phase=0, passed=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            vr.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import VerificationResult

        vr = VerificationResult(after_phase=0, passed=True)
        assert vr.contract_results == ()
        assert vr.boundary_results == ()
        assert vr.infra_health is None
        assert vr.timestamp is not None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import VerificationResult

        assert len(dataclasses.fields(VerificationResult)) == 6


class TestHealthCheckResult:
    """HealthCheckResult — per-service health check."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import HealthCheckResult

        hcr = HealthCheckResult(service="identity", passed=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            hcr.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import HealthCheckResult

        hcr = HealthCheckResult(service="identity", passed=True)
        assert hcr.status_code is None
        assert hcr.response_time_ms is None
        assert hcr.error is None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import HealthCheckResult

        assert len(dataclasses.fields(HealthCheckResult)) == 5


class TestRouteCheckResult:
    """RouteCheckResult — gateway route verification."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import RouteCheckResult

        rcr = RouteCheckResult(
            route="/api/ledger", target_service="ledger", passed=True,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            rcr.route = "/other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import RouteCheckResult

        rcr = RouteCheckResult(
            route="/api/x", target_service="x", passed=True,
        )
        assert rcr.error is None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import RouteCheckResult

        assert len(dataclasses.fields(RouteCheckResult)) == 4


class TestRequestFlowResult:
    """RequestFlowResult — end-to-end request flow test."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import RequestFlowResult

        rfr = RequestFlowResult(passed=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            rfr.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import RequestFlowResult

        rfr = RequestFlowResult(passed=True)
        assert rfr.steps == ()
        assert rfr.error is None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import RequestFlowResult

        assert len(dataclasses.fields(RequestFlowResult)) == 3


class TestEventPropagationResult:
    """EventPropagationResult — event bus propagation test."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import EventPropagationResult

        epr = EventPropagationResult(passed=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            epr.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import EventPropagationResult

        epr = EventPropagationResult(passed=True)
        assert epr.events_tested == ()
        assert epr.failed_events == ()
        assert epr.error is None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import EventPropagationResult

        assert len(dataclasses.fields(EventPropagationResult)) == 4


class TestIntegrationTestResult:
    """IntegrationTestResult — final integration validation."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import IntegrationTestResult

        itr = IntegrationTestResult(passed=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            itr.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import IntegrationTestResult

        itr = IntegrationTestResult(passed=True)
        assert itr.health_checks == ()
        assert itr.gateway_routes == ()
        assert itr.request_flow is None
        assert itr.event_propagation is None
        assert itr.timestamp is not None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import IntegrationTestResult

        assert len(dataclasses.fields(IntegrationTestResult)) == 6


class TestIntegrationReport:
    """IntegrationReport — final summary report."""

    def test_frozen(self) -> None:
        from specforge.core.orchestrator_models import IntegrationReport

        report = IntegrationReport(
            architecture="microservice",
            total_phases=3,
            total_services=6,
            verdict="pass",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.verdict = "fail"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.orchestrator_models import IntegrationReport

        report = IntegrationReport(
            architecture="microservice",
            total_phases=3,
            total_services=6,
            verdict="pass",
        )
        assert report.succeeded_services == 0
        assert report.failed_services == 0
        assert report.skipped_services == 0
        assert report.phase_results == ()
        assert report.verification_results == ()
        assert report.integration_result is None
        assert report.created_at is not None

    def test_field_count(self) -> None:
        from specforge.core.orchestrator_models import IntegrationReport

        assert len(dataclasses.fields(IntegrationReport)) == 11
