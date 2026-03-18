"""Unit tests for integration_reporter.py — report generation."""

from __future__ import annotations

from pathlib import Path

from specforge.core.integration_reporter import IntegrationReporter
from specforge.core.orchestrator_models import (
    ContractCheckResult,
    ContractMismatch,
    HealthCheckResult,
    IntegrationReport,
    IntegrationTestResult,
    OrchestrationPlan,
    OrchestrationState,
    Phase,
    PhaseState,
    ServiceStatus,
    VerificationResult,
)


def _make_pass_report() -> IntegrationReport:
    return IntegrationReport(
        architecture="microservice",
        total_phases=3,
        total_services=6,
        verdict="pass",
        succeeded_services=6,
        phase_results=(
            PhaseState(
                index=0,
                status="completed",
                services=(
                    ServiceStatus(
                        slug="identity-service",
                        status="completed",
                        tasks_completed=12,
                        tasks_total=12,
                    ),
                    ServiceStatus(
                        slug="admin-service",
                        status="completed",
                        tasks_completed=8,
                        tasks_total=8,
                    ),
                ),
            ),
            PhaseState(
                index=1,
                status="completed",
                services=(
                    ServiceStatus(
                        slug="ledger-service",
                        status="completed",
                        tasks_completed=15,
                        tasks_total=15,
                    ),
                    ServiceStatus(
                        slug="portfolio-service",
                        status="completed",
                        tasks_completed=10,
                        tasks_total=10,
                    ),
                ),
            ),
            PhaseState(
                index=2,
                status="completed",
                services=(
                    ServiceStatus(
                        slug="planning-service",
                        status="completed",
                        tasks_completed=11,
                        tasks_total=11,
                    ),
                    ServiceStatus(
                        slug="analytics-service",
                        status="completed",
                        tasks_completed=13,
                        tasks_total=13,
                    ),
                ),
            ),
        ),
        verification_results=(
            VerificationResult(after_phase=0, passed=True),
            VerificationResult(after_phase=1, passed=True),
            VerificationResult(after_phase=2, passed=True),
        ),
        integration_result=IntegrationTestResult(
            passed=True,
            health_checks=(
                HealthCheckResult(
                    service="identity-service", passed=True, response_time_ms=45
                ),
                HealthCheckResult(
                    service="ledger-service", passed=True, response_time_ms=62
                ),
            ),
        ),
    )


def _make_fail_report() -> IntegrationReport:
    return IntegrationReport(
        architecture="microservice",
        total_phases=3,
        total_services=6,
        verdict="fail",
        succeeded_services=4,
        failed_services=1,
        skipped_services=1,
        phase_results=(
            PhaseState(
                index=0,
                status="completed",
                services=(
                    ServiceStatus(
                        slug="identity-service",
                        status="completed",
                        tasks_completed=12,
                        tasks_total=12,
                    ),
                ),
            ),
            PhaseState(
                index=1,
                status="partial",
                services=(
                    ServiceStatus(
                        slug="ledger-service",
                        status="failed",
                        error="build error",
                        tasks_completed=5,
                        tasks_total=15,
                    ),
                ),
            ),
        ),
        verification_results=(
            VerificationResult(
                after_phase=1,
                passed=False,
                contract_results=(
                    ContractCheckResult(
                        consumer="ledger-service",
                        provider="identity-service",
                        passed=False,
                        mismatches=(
                            ContractMismatch(
                                contract_file="auth-api.json",
                                field="claims.role",
                                expected='string enum ["admin", "user", "readonly"]',
                                actual="string",
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


class TestIntegrationReporter:
    def test_generate_pass_report(self, tmp_path: Path) -> None:
        report = _make_pass_report()
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(Phase(index=0, services=("identity-service", "admin-service")),),
            total_services=6,
        )
        state = OrchestrationState(architecture="microservice")

        reporter = IntegrationReporter(project_root=tmp_path)
        result = reporter.generate(report, state, plan)

        assert result.ok
        path = result.value
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "PASS" in content
        assert "identity-service" in content
        assert "Phase 0" in content

    def test_generate_fail_report(self, tmp_path: Path) -> None:
        report = _make_fail_report()
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(Phase(index=0, services=("identity-service",)),),
            total_services=6,
        )
        state = OrchestrationState(architecture="microservice")

        reporter = IntegrationReporter(project_root=tmp_path)
        result = reporter.generate(report, state, plan)

        assert result.ok
        content = result.value.read_text(encoding="utf-8")
        assert "FAIL" in content
        assert "claims.role" in content

    def test_generate_partial_report(self, tmp_path: Path) -> None:
        report = IntegrationReport(
            architecture="microservice",
            total_phases=3,
            total_services=6,
            verdict="partial",
            succeeded_services=2,
            failed_services=1,
            phase_results=(
                PhaseState(
                    index=0,
                    status="completed",
                    services=(
                        ServiceStatus(
                            slug="a", status="completed",
                            tasks_completed=5, tasks_total=5,
                        ),
                    ),
                ),
                PhaseState(
                    index=1,
                    status="partial",
                    services=(
                        ServiceStatus(
                            slug="b", status="completed",
                            tasks_completed=5, tasks_total=5,
                        ),
                        ServiceStatus(
                            slug="c", status="failed", error="test fail",
                        ),
                    ),
                ),
            ),
        )
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(Phase(index=0, services=("a",)),),
            total_services=3,
        )
        state = OrchestrationState(architecture="microservice")

        reporter = IntegrationReporter(project_root=tmp_path)
        result = reporter.generate(report, state, plan)

        assert result.ok
        content = result.value.read_text(encoding="utf-8")
        assert "PARTIAL" in content

    def test_report_output_path(self, tmp_path: Path) -> None:
        report = _make_pass_report()
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(),
            total_services=0,
        )
        state = OrchestrationState(architecture="microservice")

        reporter = IntegrationReporter(project_root=tmp_path)
        result = reporter.generate(report, state, plan)

        assert result.ok
        assert result.value.name == "integration-report.md"

    def test_report_includes_elapsed_time(self, tmp_path: Path) -> None:
        state = OrchestrationState(
            architecture="microservice",
            started_at="2026-03-17T10:00:00+00:00",
        )
        report = _make_pass_report()
        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(),
            total_services=6,
        )

        reporter = IntegrationReporter(project_root=tmp_path)
        result = reporter.generate(report, state, plan)

        assert result.ok
        content = result.value.read_text(encoding="utf-8")
        assert "Elapsed" in content or "elapsed" in content or "Time" in content
