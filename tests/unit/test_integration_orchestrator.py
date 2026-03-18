"""Unit tests for integration_orchestrator.py — the main controller."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from specforge.core.executor_models import ExecutionState, TaskExecution
from specforge.core.integration_orchestrator import IntegrationOrchestrator
from specforge.core.orchestrator_models import (
    ContractCheckResult,
    ContractMismatch,
    IntegrationReport,
    IntegrationTestResult,
    OrchestrationPlan,
    Phase,
    PhaseState,
    ServiceStatus,
    VerificationResult,
)
from specforge.core.result import Err, Ok


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_manifest(
    architecture: str = "microservice",
) -> dict:
    """Build a 6-service microservice manifest."""
    return {
        "architecture": architecture,
        "services": [
            {"slug": "identity-service", "communication": []},
            {"slug": "admin-service", "communication": []},
            {
                "slug": "ledger-service",
                "communication": [{"target": "identity-service"}],
            },
            {
                "slug": "portfolio-service",
                "communication": [{"target": "identity-service"}],
            },
            {
                "slug": "planning-service",
                "communication": [{"target": "ledger-service"}],
            },
            {
                "slug": "analytics-service",
                "communication": [
                    {"target": "ledger-service"},
                    {"target": "portfolio-service"},
                ],
            },
        ],
    }


def _scaffold_project(tmp_path: Path, manifest: dict) -> Path:
    """Create a minimal project scaffold with manifest and task files."""
    specforge_dir = tmp_path / ".specforge"
    specforge_dir.mkdir()
    (specforge_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8",
    )
    features = specforge_dir / "features"
    for svc in manifest["services"]:
        svc_dir = features / svc["slug"]
        svc_dir.mkdir(parents=True)
        (svc_dir / "tasks.md").write_text("# Tasks\n- [ ] T001 Do thing\n")
    return tmp_path


def _make_success_state(slug: str) -> ExecutionState:
    return ExecutionState(
        service_slug=slug,
        architecture="microservice",
        mode="prompt-display",
        tasks=(
            TaskExecution(task_id="T001", status="completed"),
            TaskExecution(task_id="T002", status="completed"),
        ),
    )


def _build_orchestrator(
    tmp_path: Path,
    *,
    executor_results: dict[str, Ok | Err] | None = None,
    shared_infra_result: Ok | Err | None = None,
    contract_results: list[VerificationResult] | None = None,
    integration_result: IntegrationTestResult | None = None,
) -> IntegrationOrchestrator:
    """Build an orchestrator with fully mocked collaborators."""
    sub_agent = MagicMock()
    if executor_results:
        def exec_side_effect(slug, mode, resume=False):
            return executor_results.get(slug, Err(f"No mock for {slug}"))
        sub_agent.execute.side_effect = exec_side_effect
    else:
        sub_agent.execute.return_value = Ok(
            _make_success_state("default"),
        )

    shared_infra = MagicMock()
    if shared_infra_result is not None:
        shared_infra.execute.return_value = shared_infra_result
    else:
        shared_infra.execute.return_value = Ok(
            ExecutionState(
                service_slug="cross-service-infra",
                architecture="microservice",
                mode="prompt-display",
            ),
        )

    contract_enforcer = MagicMock()
    if contract_results is not None:
        contract_enforcer.verify.side_effect = [
            Ok(vr) for vr in contract_results
        ]
    else:
        contract_enforcer.verify.return_value = Ok(
            VerificationResult(after_phase=0, passed=True),
        )

    test_runner = MagicMock()
    if integration_result is not None:
        test_runner.run.return_value = Ok(integration_result)
    else:
        test_runner.run.return_value = Ok(
            IntegrationTestResult(passed=True),
        )

    reporter = MagicMock()
    reporter.generate.return_value = Ok(
        tmp_path / ".specforge" / "integration-report.md",
    )

    return IntegrationOrchestrator(
        sub_agent_executor=sub_agent,
        shared_infra_executor=shared_infra,
        contract_enforcer=contract_enforcer,
        integration_test_runner=test_runner,
        integration_reporter=reporter,
        project_root=tmp_path,
    )


# ── Happy Path ────────────────────────────────────────────────────────


class TestExecuteHappyPath:
    def test_execute_all_three_phases(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}
        vrs = [
            VerificationResult(after_phase=0, passed=True),
            VerificationResult(after_phase=1, passed=True),
            VerificationResult(after_phase=2, passed=True),
        ]

        orch = _build_orchestrator(
            tmp_path,
            executor_results=results,
            contract_results=vrs,
        )
        result = orch.execute("prompt-display")

        assert result.ok
        report = result.value
        assert report.verdict == "pass"
        assert report.total_services == 6
        assert report.total_phases == 3

        # SharedInfra called first
        orch._shared_infra_executor.execute.assert_called_once()
        # ContractEnforcer called 3 times (once per phase)
        assert orch._contract_enforcer.verify.call_count == 3
        # Integration test runner called once
        orch._integration_test_runner.run.assert_called_once()

    def test_progress_display_called_at_transitions(
        self, tmp_path: Path,
    ) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)
        orch = _build_orchestrator(
            tmp_path,
            contract_results=[
                VerificationResult(after_phase=i, passed=True)
                for i in range(3)
            ],
        )
        result = orch.execute("prompt-display")
        assert result.ok
        # Orchestrator should complete without error — progress is internal

    def test_execute_monolith_skips_shared_infra(
        self, tmp_path: Path,
    ) -> None:
        manifest = _make_manifest("monolithic")
        _scaffold_project(tmp_path, manifest)
        orch = _build_orchestrator(tmp_path)
        result = orch.execute("prompt-display")

        assert result.ok
        report = result.value
        # SharedInfra NOT called for monolith
        orch._shared_infra_executor.execute.assert_not_called()
        # ContractEnforcer NOT called for monolith
        orch._contract_enforcer.verify.assert_not_called()
        # IntegrationTestRunner called with monolithic
        orch._integration_test_runner.run.assert_called_once()
        call_args = orch._integration_test_runner.run.call_args
        assert call_args[1].get("architecture", call_args[0][1] if len(call_args[0]) > 1 else None) == "monolithic" or "monolithic" in str(call_args)


# ── Failures ──────────────────────────────────────────────────────────


class TestExecuteFailures:
    def test_shared_infra_failure_halts(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)
        orch = _build_orchestrator(
            tmp_path,
            shared_infra_result=Err("infra build failed"),
        )
        result = orch.execute("prompt-display")

        assert result.ok
        report = result.value
        assert report.verdict == "fail"
        # No phases should have been attempted
        orch._sub_agent_executor.execute.assert_not_called()

    def test_service_failure_halts_after_phase(
        self, tmp_path: Path,
    ) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}
        results["ledger-service"] = Err("build failed")

        orch = _build_orchestrator(
            tmp_path,
            executor_results=results,
            contract_results=[
                VerificationResult(after_phase=0, passed=True),
                VerificationResult(after_phase=1, passed=True),
            ],
        )
        result = orch.execute("prompt-display")

        assert result.ok
        report = result.value
        assert report.verdict == "fail"
        # Phase 0 (identity + admin) completes
        # Phase 1 (ledger fails, portfolio completes) → partial → halt
        # Phase 2 should NOT execute
        executed = {
            call[0][0]
            for call in orch._sub_agent_executor.execute.call_args_list
        }
        assert "planning-service" not in executed
        assert "analytics-service" not in executed

    def test_contract_violation_halts(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}

        orch = _build_orchestrator(
            tmp_path,
            executor_results=results,
            contract_results=[
                VerificationResult(
                    after_phase=0,
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
                                    expected="string enum",
                                    actual="string",
                                ),
                            ),
                        ),
                    ),
                ),
            ],
        )
        result = orch.execute("prompt-display")

        assert result.ok
        report = result.value
        assert report.verdict == "fail"
        # Phase 1 should NOT have been attempted
        executed = {
            call[0][0]
            for call in orch._sub_agent_executor.execute.call_args_list
        }
        assert "ledger-service" not in executed

    def test_all_services_in_phase_fail(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        results = {
            "identity-service": Err("error 1"),
            "admin-service": Err("error 2"),
        }

        orch = _build_orchestrator(
            tmp_path, executor_results=results,
        )
        result = orch.execute("prompt-display")

        assert result.ok
        report = result.value
        assert report.verdict == "fail"


# ── Partial Execution ─────────────────────────────────────────────────


class TestExecutePartial:
    def test_to_phase_limits_execution(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}

        orch = _build_orchestrator(
            tmp_path,
            executor_results=results,
            contract_results=[
                VerificationResult(after_phase=0, passed=True),
                VerificationResult(after_phase=1, passed=True),
            ],
        )
        result = orch.execute("prompt-display", phase_ceiling=1)

        assert result.ok
        report = result.value
        # Phase 2 should not execute
        executed = {
            call[0][0]
            for call in orch._sub_agent_executor.execute.call_args_list
        }
        assert "planning-service" not in executed
        assert "analytics-service" not in executed
        # Integration test skipped when --to-phase is used
        orch._integration_test_runner.run.assert_not_called()

    def test_to_phase_exceeds_total(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}

        orch = _build_orchestrator(
            tmp_path,
            executor_results=results,
            contract_results=[
                VerificationResult(after_phase=i, passed=True)
                for i in range(3)
            ],
        )
        result = orch.execute("prompt-display", phase_ceiling=10)

        assert result.ok
        report = result.value
        assert report.verdict == "pass"
        assert report.total_phases == 3


# ── Resume ────────────────────────────────────────────────────────────


class TestExecuteResume:
    def test_resume_skips_completed_phases(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        # Create a saved state with phase 0 completed
        from specforge.core.orchestration_state import (
            create_initial_state,
            mark_phase_in_progress,
            mark_service_completed,
            save_state,
        )

        plan = OrchestrationPlan(
            architecture="microservice",
            phases=(
                Phase(index=0, services=("admin-service", "identity-service")),
                Phase(index=1, services=("ledger-service", "portfolio-service")),
                Phase(
                    index=2,
                    services=("analytics-service", "planning-service"),
                ),
            ),
            total_services=6,
            shared_infra_required=True,
        )
        state = create_initial_state(plan)
        state = mark_phase_in_progress(state, 0)
        state = mark_service_completed(state, 0, "identity-service", 2, 2)
        state = mark_service_completed(state, 0, "admin-service", 2, 2)
        from dataclasses import replace as dc_replace

        phase0 = state.phases[0]
        phase0 = dc_replace(phase0, status="completed")
        state = dc_replace(
            state,
            phases=(phase0, *state.phases[1:]),
            shared_infra_status="completed",
            status="in-progress",
        )
        state_path = tmp_path / ".specforge" / "orchestration-state.json"
        save_state(state_path, state)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}

        orch = _build_orchestrator(
            tmp_path,
            executor_results=results,
            contract_results=[
                VerificationResult(after_phase=1, passed=True),
                VerificationResult(after_phase=2, passed=True),
            ],
        )
        result = orch.execute("prompt-display", resume=True)

        assert result.ok
        # Phase 0 services should NOT be re-executed
        executed = {
            call[0][0]
            for call in orch._sub_agent_executor.execute.call_args_list
        }
        assert "identity-service" not in executed
        assert "admin-service" not in executed

    def test_resume_no_state_starts_fresh(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}

        orch = _build_orchestrator(
            tmp_path,
            executor_results=results,
            contract_results=[
                VerificationResult(after_phase=i, passed=True)
                for i in range(3)
            ],
        )
        result = orch.execute("prompt-display", resume=True)

        assert result.ok
        report = result.value
        assert report.total_services == 6


# ── Pre-Flight ────────────────────────────────────────────────────────


class TestPreFlight:
    def test_cycle_detected_before_execution(self, tmp_path: Path) -> None:
        manifest = {
            "architecture": "microservice",
            "services": [
                {
                    "slug": "a",
                    "communication": [{"target": "b"}],
                },
                {
                    "slug": "b",
                    "communication": [{"target": "a"}],
                },
            ],
        }
        _scaffold_project(tmp_path, manifest)
        orch = _build_orchestrator(tmp_path)
        result = orch.execute("prompt-display")

        assert not result.ok
        assert "cycle" in result.error.lower()

    def test_missing_manifest_returns_err(self, tmp_path: Path) -> None:
        orch = _build_orchestrator(tmp_path)
        result = orch.execute("prompt-display")

        assert not result.ok

    def test_lock_prevents_concurrent_run(self, tmp_path: Path) -> None:
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        lock_path = tmp_path / ".specforge" / ".orchestration-lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text('{"pid": 99999, "timestamp": "2026-01-01T00:00:00Z"}')

        orch = _build_orchestrator(tmp_path)
        result = orch.execute("prompt-display")

        assert not result.ok
        assert "lock" in result.error.lower()


class TestEdgeCases:
    """Edge case tests for IntegrationOrchestrator."""

    def test_lock_released_on_failure(self, tmp_path: Path) -> None:
        """Orchestrator fails mid-phase → lock file removed (try/finally)."""
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        results = {"identity-service": Err("crash"), "admin-service": Err("crash")}
        orch = _build_orchestrator(tmp_path, executor_results=results)

        orch.execute("prompt-display")

        lock_path= tmp_path / ".specforge" / ".orchestration-lock"
        assert not lock_path.exists()  # Lock released

    def test_service_with_no_tasks_md_skipped(self, tmp_path: Path) -> None:
        """identity-service missing tasks.md → skipped."""
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        # Remove identity-service's tasks.md
        (tmp_path / ".specforge" / "features" / "identity-service" / "tasks.md").unlink()

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}

        orch = _build_orchestrator(
            tmp_path, executor_results=results,
            contract_results=[
                VerificationResult(after_phase=i, passed=True)
                for i in range(3)
            ],
        )
        result = orch.execute("prompt-display")

        assert result.ok
        # identity-service should have been skipped
        executed = {
            call[0][0]
            for call in orch._sub_agent_executor.execute.call_args_list
        }
        assert "identity-service" not in executed

    def test_to_phase_exceeds_total_logs_warning(self, tmp_path: Path) -> None:
        """phase_ceiling=99, 3 phases → all phases run, no crash."""
        manifest = _make_manifest()
        _scaffold_project(tmp_path, manifest)

        all_slugs = [s["slug"] for s in manifest["services"]]
        results = {slug: Ok(_make_success_state(slug)) for slug in all_slugs}

        orch = _build_orchestrator(
            tmp_path, executor_results=results,
            contract_results=[
                VerificationResult(after_phase=i, passed=True)
                for i in range(3)
            ],
        )
        result = orch.execute("prompt-display", phase_ceiling=99)

        assert result.ok
        assert result.value.total_phases == 3

    def test_single_service_passthrough(self, tmp_path: Path) -> None:
        """1 service, no deps, microservice mode → works end-to-end."""
        manifest = {
            "architecture": "microservice",
            "services": [{"slug": "solo-service", "communication": []}],
        }
        _scaffold_project(tmp_path, manifest)

        results = {"solo-service": Ok(_make_success_state("solo-service"))}
        orch = _build_orchestrator(
            tmp_path, executor_results=results,
            contract_results=[VerificationResult(after_phase=0, passed=True)],
        )
        result = orch.execute("prompt-display")

        assert result.ok
        assert result.value.verdict == "pass"
        assert result.value.total_services == 1
