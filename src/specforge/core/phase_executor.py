"""Phase executor — runs all services in a phase sequentially (Feature 011)."""

from __future__ import annotations

from pathlib import Path

from specforge.core.executor_models import ExecutionMode, ExecutionState
from specforge.core.orchestrator_models import Phase, ServiceStatus, _now_iso
from specforge.core.sub_agent_executor import SubAgentExecutor


class PhaseExecutor:
    """Runs all services in a phase, implementing continue-then-halt policy."""

    def __init__(
        self,
        sub_agent_executor: SubAgentExecutor,
        project_root: Path,
    ) -> None:
        self._executor = sub_agent_executor
        self._root = project_root

    def run(
        self,
        phase: Phase,
        mode: ExecutionMode,
        skipped_services: frozenset[str] = frozenset(),
    ) -> tuple[ServiceStatus, ...]:
        """Execute all services in the phase sequentially.

        Continues on failure (DD-003: same-phase services are independent).
        Returns a ServiceStatus for every service in the phase.
        """
        statuses: list[ServiceStatus] = []
        for slug in phase.services:
            if slug in skipped_services:
                statuses.append(ServiceStatus(slug=slug, status="skipped"))
                continue
            status = self._execute_service(slug, mode)
            statuses.append(status)
        return tuple(statuses)

    def _execute_service(
        self, slug: str, mode: ExecutionMode,
    ) -> ServiceStatus:
        """Execute a single service and map result to ServiceStatus."""
        started = _now_iso()
        result = self._executor.execute(slug, mode)
        completed = _now_iso()
        if result.ok:
            return self._success_status(slug, result.value, started, completed)
        return ServiceStatus(
            slug=slug, status="failed", error=result.error,
            started_at=started, completed_at=completed,
        )

    def _success_status(
        self,
        slug: str,
        state: ExecutionState,
        started: str,
        completed: str,
    ) -> ServiceStatus:
        """Build ServiceStatus from a successful ExecutionState."""
        done = sum(1 for t in state.tasks if t.status == "completed")
        total = len(state.tasks)
        return ServiceStatus(
            slug=slug, status="completed",
            tasks_completed=done, tasks_total=total,
            started_at=started, completed_at=completed,
        )
