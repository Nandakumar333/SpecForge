"""Unit tests for orchestration_progress.py — Rich progress display."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from specforge.core.orchestration_progress import (
    render_final_summary,
    render_phase_map,
    render_service_table,
    render_verification_result,
)
from specforge.core.orchestrator_models import (
    IntegrationReport,
    OrchestrationPlan,
    OrchestrationState,
    Phase,
    PhaseState,
    ServiceStatus,
    VerificationResult,
)


def _capture(renderable) -> str:
    """Capture Rich renderable as plain text."""
    console = Console(file=StringIO(), force_terminal=True, width=120)
    console.print(renderable)
    return console.file.getvalue()


class TestRenderPhaseMap:
    def test_three_phase_plan(self) -> None:
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(
                Phase(index=0, services=("identity-service", "admin-service")),
                Phase(index=1, services=("ledger-service", "portfolio-service")),
                Phase(index=2, services=("planning-service",)),
            ),
            total_services=5,
        )
        state = OrchestrationState(
            architecture="microservice",
            phases=(
                PhaseState(index=0, status="completed"),
                PhaseState(index=1, status="in-progress"),
                PhaseState(index=2, status="pending"),
            ),
        )

        tree = render_phase_map(plan, state)
        output = _capture(tree)

        assert "Phase 0" in output
        assert "Phase 1" in output
        assert "Phase 2" in output
        assert "✅" in output  # completed phase
        assert "⏳" in output or "…" in output  # in-progress phase

    def test_single_phase(self) -> None:
        plan = OrchestrationPlan(
            architecture="monolith",
            phases=(Phase(index=0, services=("web-app",)),),
            total_services=1,
        )
        state = OrchestrationState(
            architecture="monolith",
            phases=(PhaseState(index=0, status="pending"),),
        )

        tree = render_phase_map(plan, state)
        output = _capture(tree)

        assert "Phase 0" in output
        assert "monolith" in output

    def test_missing_state_defaults_to_pending(self) -> None:
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(
                Phase(index=0, services=("svc-a",)),
                Phase(index=1, services=("svc-b",)),
            ),
            total_services=2,
        )
        state = OrchestrationState(
            architecture="microservice",
            phases=(PhaseState(index=0, status="completed"),),
        )

        tree = render_phase_map(plan, state)
        output = _capture(tree)

        assert "⏸" in output  # pending icon for missing phase


class TestRenderServiceTable:
    def test_mixed_statuses(self) -> None:
        phase_state = PhaseState(
            index=1,
            status="in-progress",
            services=(
                ServiceStatus(slug="ledger-service", status="completed", tasks_completed=15, tasks_total=15),
                ServiceStatus(slug="portfolio-service", status="in-progress", tasks_completed=5, tasks_total=10),
                ServiceStatus(slug="integration-service", status="pending"),
            ),
        )

        table = render_service_table(phase_state)
        output = _capture(table)

        assert "ledger-service" in output
        assert "portfolio-service" in output
        assert "integration-service" in output

    def test_empty_services(self) -> None:
        phase_state = PhaseState(index=0, status="pending", services=())

        table = render_service_table(phase_state)
        output = _capture(table)

        assert "Phase 0" in output

    def test_task_counts_rendered(self) -> None:
        phase_state = PhaseState(
            index=0,
            status="in-progress",
            services=(
                ServiceStatus(slug="api-svc", status="in-progress", tasks_completed=3, tasks_total=8),
            ),
        )

        table = render_service_table(phase_state)
        output = _capture(table)

        assert "3/8" in output


class TestRenderVerificationResult:
    def test_passed(self) -> None:
        vr = VerificationResult(after_phase=0, passed=True)
        text = render_verification_result(vr)
        assert "✅" in text
        assert "contracts" in text.lower() or "OK" in text

    def test_failed(self) -> None:
        vr = VerificationResult(after_phase=0, passed=False)
        text = render_verification_result(vr)
        assert "❌" in text

    def test_failed_with_details(self) -> None:
        from specforge.core.orchestrator_models import (
            BoundaryCheckResult,
            ContractCheckResult,
            ContractMismatch,
        )

        vr = VerificationResult(
            after_phase=1,
            passed=False,
            contract_results=(
                ContractCheckResult(
                    consumer="svc-a",
                    provider="svc-b",
                    passed=False,
                    mismatches=(
                        ContractMismatch(
                            contract_file="api.json",
                            field="price",
                            expected="int",
                            actual="string",
                        ),
                    ),
                ),
            ),
            boundary_results=(
                BoundaryCheckResult(
                    entity="User",
                    services=("svc-a", "svc-b"),
                    violation_type="shared-write",
                    details="Both services write User",
                ),
            ),
        )
        text = render_verification_result(vr)
        assert "❌" in text
        assert "contract" in text.lower()
        assert "boundary" in text.lower()


class TestRenderFinalSummary:
    def test_pass_verdict(self) -> None:
        report = IntegrationReport(
            architecture="microservice",
            total_phases=3,
            total_services=6,
            verdict="pass",
            succeeded_services=6,
        )

        panel = render_final_summary(report)
        output = _capture(panel)

        assert "PASS" in output
        assert "6" in output

    def test_fail_verdict_with_failures(self) -> None:
        report = IntegrationReport(
            architecture="microservice",
            total_phases=2,
            total_services=4,
            verdict="fail",
            succeeded_services=2,
            failed_services=1,
            skipped_services=1,
        )

        panel = render_final_summary(report)
        output = _capture(panel)

        assert "FAIL" in output
        assert "❌" in output
        assert "Failed" in output
        assert "Skipped" in output
