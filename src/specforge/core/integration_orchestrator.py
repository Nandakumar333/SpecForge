"""Integration orchestrator — phased multi-service implementation (Feature 011).

Coordinates SubAgentExecutor across services in dependency order with
inter-phase contract verification and final integration testing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path

from specforge.core.config import (
    ORCHESTRATION_LOCK_FILENAME,
    ORCHESTRATION_STATE_FILENAME,
)
from specforge.core.contract_enforcer import ContractEnforcer
from specforge.core.dependency_graph import build_graph, compute_phases
from specforge.core.executor_models import ExecutionMode
from specforge.core.integration_reporter import IntegrationReporter
from specforge.core.integration_test_runner import IntegrationTestRunner
from specforge.core.orchestration_state import (
    add_verification_result,
    compute_phase_status,
    create_initial_state,
    get_completed_services,
    load_state,
    mark_phase_in_progress,
    mark_service_completed,
    mark_service_failed,
    mark_shared_infra_complete,
    mark_shared_infra_failed,
    save_state,
)
from specforge.core.orchestrator_models import (
    IntegrationReport,
    OrchestrationPlan,
    OrchestrationState,
    Phase,
    ServiceStatus,
    _now_iso,
)
from specforge.core.phase_executor import PhaseExecutor
from specforge.core.pipeline_lock import acquire_lock, release_lock
from specforge.core.result import Err, Ok, Result
from specforge.core.shared_infra_executor import SharedInfraExecutor
from specforge.core.sub_agent_executor import SubAgentExecutor

logger = logging.getLogger(__name__)

_MONOLITHIC = "monolithic"


class IntegrationOrchestrator:
    """Orchestrates phased implementation across all services."""

    def __init__(
        self,
        sub_agent_executor: SubAgentExecutor,
        shared_infra_executor: SharedInfraExecutor,
        contract_enforcer: ContractEnforcer,
        integration_test_runner: IntegrationTestRunner,
        integration_reporter: IntegrationReporter,
        project_root: Path,
    ) -> None:
        self._sub_agent_executor = sub_agent_executor
        self._shared_infra_executor = shared_infra_executor
        self._contract_enforcer = contract_enforcer
        self._integration_test_runner = integration_test_runner
        self._reporter = integration_reporter
        self._root = project_root
        self._phase_executor = PhaseExecutor(sub_agent_executor, project_root)

    def execute(
        self,
        mode: ExecutionMode,
        resume: bool = False,
        phase_ceiling: int | None = None,
    ) -> Result[IntegrationReport, str]:
        """Execute phased implementation with verification."""
        manifest_r = self._load_manifest()
        if not manifest_r.ok:
            return manifest_r

        manifest = manifest_r.value
        plan_r = self._build_plan(manifest)
        if not plan_r.ok:
            return plan_r

        plan = plan_r.value
        lock_path = self._root / ORCHESTRATION_LOCK_FILENAME
        lock_r = acquire_lock(lock_path, "orchestration")
        if not lock_r.ok:
            return lock_r

        try:
            return self._run(manifest, plan, mode, resume, phase_ceiling)
        finally:
            release_lock(lock_path)

    # ── Pipeline Steps ────────────────────────────────────────────────

    def _run(
        self,
        manifest: dict,
        plan: OrchestrationPlan,
        mode: ExecutionMode,
        resume: bool,
        phase_ceiling: int | None,
    ) -> Result[IntegrationReport, str]:
        """Core orchestration loop."""
        state = self._load_or_create_state(plan, resume, phase_ceiling)
        state = replace(state, status="in-progress", started_at=_now_iso())

        if plan.shared_infra_required:
            state = self._run_shared_infra(state, mode)
            if state.shared_infra_status == "failed":
                return Ok(self._build_report(state, plan))

        state = self._run_phases(state, plan, manifest, mode)
        state = self._run_integration(state, plan, manifest)
        report = self._build_report(state, plan)
        self._reporter.generate(report, state, plan)
        return Ok(report)

    def _load_manifest(self) -> Result[dict, str]:
        """Load and return the project manifest."""
        path = self._root / ".specforge" / "manifest.json"
        if not path.exists():
            return Err(f"Manifest not found: {path}")
        try:
            return Ok(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as exc:
            return Err(f"Invalid manifest: {exc}")

    def _build_plan(
        self, manifest: dict,
    ) -> Result[OrchestrationPlan, str]:
        """Build execution plan from manifest dependency graph."""
        graph_r = build_graph(manifest)
        if not graph_r.ok:
            return Err(graph_r.error)
        phases_r = compute_phases(graph_r.value)
        if not phases_r.ok:
            return Err(phases_r.error)
        arch = manifest.get("architecture", _MONOLITHIC)
        infra = arch != _MONOLITHIC
        total = sum(len(p.services) for p in phases_r.value)
        return Ok(OrchestrationPlan(
            architecture=arch,
            phases=phases_r.value,
            total_services=total,
            shared_infra_required=infra,
        ))

    def _load_or_create_state(
        self,
        plan: OrchestrationPlan,
        resume: bool,
        phase_ceiling: int | None,
    ) -> OrchestrationState:
        """Load existing state on resume, or create fresh state."""
        state_path = self._root / ORCHESTRATION_STATE_FILENAME
        if resume:
            load_r = load_state(state_path)
            if load_r.ok:
                return replace(load_r.value, phase_ceiling=phase_ceiling)
        state = create_initial_state(plan)
        return replace(state, phase_ceiling=phase_ceiling)

    def _run_shared_infra(
        self,
        state: OrchestrationState,
        mode: ExecutionMode,
    ) -> OrchestrationState:
        """Execute shared infrastructure pre-phase."""
        if state.shared_infra_status == "completed":
            return state
        result = self._shared_infra_executor.execute(mode)
        if result.ok:
            return mark_shared_infra_complete(state)
        return mark_shared_infra_failed(
            replace(state, status="failed"),
        )

    def _run_phases(
        self,
        state: OrchestrationState,
        plan: OrchestrationPlan,
        manifest: dict,
        mode: ExecutionMode,
    ) -> OrchestrationState:
        """Execute phases sequentially with verification."""
        for phase in plan.phases:
            if not self._should_run_phase(state, phase):
                continue
            state = self._execute_single_phase(
                state, phase, manifest, mode,
            )
            if self._has_phase_failure(state, phase.index):
                break
        return state

    def _should_run_phase(
        self,
        state: OrchestrationState,
        phase: Phase,
    ) -> bool:
        """Check if a phase should execute (ceiling + resume logic)."""
        if state.phase_ceiling is not None and phase.index > state.phase_ceiling:
                return False
        if phase.index < len(state.phases):
            ps = state.phases[phase.index]
            if ps.status == "completed":
                return False
        return True

    def _execute_single_phase(
        self,
        state: OrchestrationState,
        phase: Phase,
        manifest: dict,
        mode: ExecutionMode,
    ) -> OrchestrationState:
        """Run one phase: services → verify → update state."""
        state = mark_phase_in_progress(state, phase.index)
        skipped = self._compute_skipped(phase, state)
        statuses = self._phase_executor.run(phase, mode, skipped)
        state = self._apply_phase_results(state, phase.index, statuses)
        state = self._verify_phase(state, phase, manifest)
        self._save_checkpoint(state)
        return state

    def _compute_skipped(
        self, phase: Phase, state: OrchestrationState,
    ) -> frozenset[str]:
        """Determine which services to skip (missing artifacts)."""
        features = self._root / ".specforge" / "features"
        skipped: set[str] = set()
        for slug in phase.services:
            tasks_path = features / slug / "tasks.md"
            if not tasks_path.exists():
                skipped.add(slug)
        return frozenset(skipped)

    def _apply_phase_results(
        self,
        state: OrchestrationState,
        phase_index: int,
        statuses: tuple[ServiceStatus, ...],
    ) -> OrchestrationState:
        """Update state with phase execution results."""
        for ss in statuses:
            if ss.status == "completed":
                state = mark_service_completed(
                    state, phase_index, ss.slug,
                    ss.tasks_completed, ss.tasks_total,
                )
            elif ss.status == "failed":
                state = mark_service_failed(
                    state, phase_index, ss.slug,
                    ss.error or "unknown error",
                )
        phase_state = state.phases[phase_index]
        ps_status = compute_phase_status(phase_state)
        updated = replace(phase_state, status=ps_status, completed_at=_now_iso())
        phases = (
            *state.phases[:phase_index],
            updated,
            *state.phases[phase_index + 1:],
        )
        return replace(state, phases=phases)

    def _verify_phase(
        self,
        state: OrchestrationState,
        phase: Phase,
        manifest: dict,
    ) -> OrchestrationState:
        """Run contract verification after a phase (microservice only)."""
        arch = manifest.get("architecture", _MONOLITHIC)
        if arch == _MONOLITHIC:
            return state
        implemented = get_completed_services(state)
        if not implemented:
            return state
        vr_r = self._contract_enforcer.verify(implemented, manifest)
        if vr_r.ok:
            return add_verification_result(state, vr_r.value)
        return state

    def _has_phase_failure(
        self, state: OrchestrationState, phase_index: int,
    ) -> bool:
        """Check if a phase had any failures requiring halt."""
        ps = state.phases[phase_index]
        if ps.status in ("partial", "failed"):
            return True
        vrs = state.verification_results
        return bool(vrs and not vrs[-1].passed)

    def _run_integration(
        self,
        state: OrchestrationState,
        plan: OrchestrationPlan,
        manifest: dict,
    ) -> OrchestrationState:
        """Run final integration tests (only if all phases complete)."""
        if state.phase_ceiling is not None:
            return state
        all_complete = all(
            ps.status == "completed" for ps in state.phases
        )
        if not all_complete:
            return state
        implemented = get_completed_services(state)
        arch = manifest.get("architecture", _MONOLITHIC)
        result = self._integration_test_runner.run(implemented, arch)
        if result.ok:
            return replace(
                state, integration_result=result.value,
            )
        return state

    def _build_report(
        self,
        state: OrchestrationState,
        plan: OrchestrationPlan,
    ) -> IntegrationReport:
        """Build final IntegrationReport from orchestration state."""
        succeeded = sum(
            1 for p in state.phases for s in p.services
            if s.status == "completed"
        )
        failed = sum(
            1 for p in state.phases for s in p.services
            if s.status == "failed"
        )
        skipped = sum(
            1 for p in state.phases for s in p.services
            if s.status == "skipped"
        )
        verdict = self._compute_verdict(state, plan)
        return IntegrationReport(
            architecture=plan.architecture,
            total_phases=len(plan.phases),
            total_services=plan.total_services,
            verdict=verdict,
            succeeded_services=succeeded,
            failed_services=failed,
            skipped_services=skipped,
            phase_results=state.phases,
            verification_results=state.verification_results,
            integration_result=state.integration_result,
        )

    def _compute_verdict(
        self,
        state: OrchestrationState,
        plan: OrchestrationPlan,
    ) -> str:
        """Determine pass/fail/partial verdict."""
        has_failure = any(
            s.status == "failed"
            for p in state.phases for s in p.services
        )
        has_vr_fail = any(
            not vr.passed for vr in state.verification_results
        )
        if has_failure or has_vr_fail:
            return "fail"
        if state.shared_infra_status == "failed":
            return "fail"
        all_done = all(
            ps.status == "completed" for ps in state.phases
        )
        if all_done:
            return "pass"
        return "partial"

    def _save_checkpoint(self, state: OrchestrationState) -> None:
        """Persist state to disk after each phase."""
        path = self._root / ORCHESTRATION_STATE_FILENAME
        save_state(path, state)
