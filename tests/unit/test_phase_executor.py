"""Unit tests for phase_executor.py — runs services in a phase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from specforge.core.executor_models import ExecutionState, TaskExecution
from specforge.core.orchestrator_models import Phase, ServiceStatus
from specforge.core.phase_executor import PhaseExecutor
from specforge.core.result import Err, Ok


def _mock_executor(
    results: dict[str, Ok | Err],
) -> MagicMock:
    """Create a mock SubAgentExecutor with service-specific results."""
    executor = MagicMock()

    def execute_side_effect(slug, mode, resume=False):
        return results.get(slug, Err(f"Unknown service: {slug}"))

    executor.execute.side_effect = execute_side_effect
    return executor


def _make_success_state(slug: str, completed: int = 10, total: int = 10) -> ExecutionState:
    tasks = tuple(
        TaskExecution(task_id=f"T{i:03d}", status="completed")
        for i in range(completed)
    ) + tuple(
        TaskExecution(task_id=f"T{i:03d}", status="pending")
        for i in range(completed, total)
    )
    return ExecutionState(
        service_slug=slug, architecture="microservice", mode="prompt-display",
        tasks=tasks,
    )


class TestPhaseExecutor:
    def test_run_single_service_phase(self, tmp_path: Path) -> None:
        state = _make_success_state("identity-service", 12, 12)
        executor = _mock_executor({"identity-service": Ok(state)})
        phase = Phase(index=0, services=("identity-service",))

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        result = pe.run(phase, "prompt-display")

        assert len(result) == 1
        assert result[0].slug == "identity-service"
        assert result[0].status == "completed"
        assert result[0].tasks_completed == 12
        assert result[0].tasks_total == 12

    def test_run_parallel_services(self, tmp_path: Path) -> None:
        executor = _mock_executor({
            "identity-service": Ok(_make_success_state("identity-service")),
            "admin-service": Ok(_make_success_state("admin-service", 8, 8)),
        })
        phase = Phase(index=0, services=("identity-service", "admin-service"))

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        result = pe.run(phase, "prompt-display")

        assert len(result) == 2
        assert all(ss.status == "completed" for ss in result)

    def test_continue_on_failure(self, tmp_path: Path) -> None:
        executor = _mock_executor({
            "ledger-service": Ok(_make_success_state("ledger-service")),
            "portfolio-service": Err("build failed"),
            "planning-service": Ok(_make_success_state("planning-service")),
        })
        phase = Phase(
            index=1,
            services=("ledger-service", "portfolio-service", "planning-service"),
        )

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        result = pe.run(phase, "prompt-display")

        assert len(result) == 3
        ledger = next(s for s in result if s.slug == "ledger-service")
        portfolio = next(s for s in result if s.slug == "portfolio-service")
        planning = next(s for s in result if s.slug == "planning-service")
        assert ledger.status == "completed"
        assert portfolio.status == "failed"
        assert portfolio.error == "build failed"
        assert planning.status == "completed"

    def test_all_services_fail(self, tmp_path: Path) -> None:
        executor = _mock_executor({
            "a": Err("error a"),
            "b": Err("error b"),
        })
        phase = Phase(index=0, services=("a", "b"))

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        result = pe.run(phase, "prompt-display")

        assert len(result) == 2
        assert all(ss.status == "failed" for ss in result)

    def test_service_status_includes_task_counts(self, tmp_path: Path) -> None:
        state = _make_success_state("svc", completed=5, total=10)
        executor = _mock_executor({"svc": Ok(state)})
        phase = Phase(index=0, services=("svc",))

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        result = pe.run(phase, "prompt-display")

        assert result[0].tasks_completed == 5
        assert result[0].tasks_total == 10

    def test_skipped_service(self, tmp_path: Path) -> None:
        executor = _mock_executor({
            "a": Ok(_make_success_state("a")),
        })
        phase = Phase(index=0, services=("a", "b"))

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        result = pe.run(phase, "prompt-display", skipped_services=frozenset({"b"}))

        assert len(result) == 2
        b_status = next(s for s in result if s.slug == "b")
        assert b_status.status == "skipped"
        # executor should NOT have been called for "b"
        calls = [c for c in executor.execute.call_args_list if c[0][0] == "b"]
        assert len(calls) == 0

    def test_sequential_execution_order(self, tmp_path: Path) -> None:
        call_order = []

        def execute_side_effect(slug, mode, resume=False):
            call_order.append(slug)
            return Ok(_make_success_state(slug))

        executor = MagicMock()
        executor.execute.side_effect = execute_side_effect
        phase = Phase(index=0, services=("alpha", "beta", "gamma"))

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        pe.run(phase, "prompt-display")

        assert call_order == ["alpha", "beta", "gamma"]

    def test_context_isolation_only_dep_contracts(self, tmp_path: Path) -> None:
        """Verify executor is called correctly - no sibling context leakage."""
        executor = _mock_executor({
            "ledger-service": Ok(_make_success_state("ledger-service")),
            "portfolio-service": Ok(_make_success_state("portfolio-service")),
        })
        phase = Phase(
            index=1,
            services=("ledger-service", "portfolio-service"),
            dependencies_satisfied=("identity-service",),
        )

        pe = PhaseExecutor(sub_agent_executor=executor, project_root=tmp_path)
        pe.run(phase, "prompt-display")

        # Both services should have been called
        assert executor.execute.call_count == 2
