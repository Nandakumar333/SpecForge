"""Pure aggregation functions: status derivation, phase progress, quality summary."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specforge.core.config import PIPELINE_TO_LIFECYCLE
from specforge.core.result import Err, Ok
from specforge.core.status_models import (
    LifecyclePhases,
    PhaseProgressRecord,
    QualitySummaryRecord,
    ServicePhaseDetail,
)

if TYPE_CHECKING:
    from specforge.core.status_collector import ServiceRawState
    from specforge.core.status_models import ServiceStatusRecord


# ── Status derivation (priority waterfall) ───────────────────────────


def derive_service_status(
    raw_state: ServiceRawState,
    dependencies_met: bool,
) -> str:
    """Derive overall service status using the priority waterfall.

    Priority (highest first):
    1. Any Err → UNKNOWN
    2. Failed tasks / quality gate failed → FAILED
    3. Dependencies not met → BLOCKED
    4. Execution has tasks → IN_PROGRESS
    5. Pipeline in-progress, no execution → PLANNING
    6. All complete → COMPLETE
    7. Nothing exists → NOT_STARTED
    """
    if _has_corrupt_state(raw_state):
        return "UNKNOWN"
    if _has_failures(raw_state):
        return "FAILED"
    if not dependencies_met:
        return "BLOCKED"
    if _is_all_complete(raw_state):
        return "COMPLETE"
    if _has_execution_activity(raw_state):
        return "IN_PROGRESS"
    if _has_pipeline_activity(raw_state):
        return "PLANNING"
    return "NOT_STARTED"


def _has_corrupt_state(raw: ServiceRawState) -> bool:
    """Check if any state file returned Err."""
    return (
        isinstance(raw.pipeline, Err)
        or isinstance(raw.execution, Err)
        or isinstance(raw.quality, Err)
    )


def _has_failures(raw: ServiceRawState) -> bool:
    """Check for failed tasks or quality gate failures."""
    if isinstance(raw.execution, Ok):
        tasks = raw.execution.value.get("tasks", [])
        if any(t.get("status") == "failed" for t in tasks):
            return True
    if isinstance(raw.quality, Ok):
        gate = raw.quality.value.get("gate_result", {})
        if gate.get("passed") is False:
            return True
    return False


def _has_execution_activity(raw: ServiceRawState) -> bool:
    """Check if execution has any tasks."""
    if not isinstance(raw.execution, Ok):
        return False
    tasks = raw.execution.value.get("tasks", [])
    return len(tasks) > 0


def _has_pipeline_activity(raw: ServiceRawState) -> bool:
    """Check if pipeline has in-progress phases."""
    if not isinstance(raw.pipeline, Ok):
        return False
    phases = raw.pipeline.value.get("phases", [])
    return any(
        p.get("status") in ("in-progress", "complete")
        for p in phases
    )


def _is_all_complete(raw: ServiceRawState) -> bool:
    """Check if all pipeline + execution + quality are complete."""
    if not isinstance(raw.pipeline, Ok):
        return False
    phases = raw.pipeline.value.get("phases", [])
    if not phases or not all(
        p.get("status") == "complete" for p in phases
    ):
        return False
    if not isinstance(raw.execution, Ok):
        return False
    tasks = raw.execution.value.get("tasks", [])
    if tasks and not all(
        t.get("status") == "completed" for t in tasks
    ):
        return False
    if isinstance(raw.quality, Ok):
        gate = raw.quality.value.get("gate_result", {})
        if gate.get("passed") is not True:
            return False
    return True


# ── Lifecycle building ───────────────────────────────────────────────


def build_lifecycle(
    raw_state: ServiceRawState,
    architecture: str,
) -> LifecyclePhases:
    """Map raw state files to LifecyclePhases display model."""
    spec_val, plan_val, tasks_val = _map_pipeline_phases(raw_state)
    impl_pct = _calc_impl_percent(raw_state)
    tests_passed, tests_total = _extract_test_counts(raw_state)
    docker_val = _extract_docker_status(raw_state, architecture)
    boundary_val = _extract_boundary_status(raw_state)

    return LifecyclePhases(
        spec=spec_val,
        plan=plan_val,
        tasks=tasks_val,
        impl_percent=impl_pct,
        tests_passed=tests_passed,
        tests_total=tests_total,
        docker=docker_val,
        boundary_compliance=boundary_val,
    )


def _map_pipeline_phases(
    raw: ServiceRawState,
) -> tuple[str | None, str | None, str | None]:
    """Map pipeline phase statuses to lifecycle display values."""
    if not isinstance(raw.pipeline, Ok):
        return None, None, None
    phase_map: dict[str, str] = {}
    for p in raw.pipeline.value.get("phases", []):
        name = p.get("name", "")
        status = p.get("status", "")
        if name in PIPELINE_TO_LIFECYCLE:
            lc_key = PIPELINE_TO_LIFECYCLE[name]
            phase_map[lc_key] = _status_to_display(status)
    return (
        phase_map.get("spec"),
        phase_map.get("plan"),
        phase_map.get("tasks"),
    )


def _status_to_display(status: str) -> str | None:
    """Convert pipeline status to display value."""
    if status == "complete":
        return "DONE"
    if status == "in-progress":
        return "WIP"
    return None


def _calc_impl_percent(raw: ServiceRawState) -> int | None:
    """Calculate implementation percentage from task counts."""
    if not isinstance(raw.execution, Ok):
        return None
    tasks = raw.execution.value.get("tasks", [])
    total = len(tasks)
    if total == 0:
        return 0
    completed = sum(
        1 for t in tasks if t.get("status") == "completed"
    )
    return int(completed / total * 100)


def _extract_test_counts(
    raw: ServiceRawState,
) -> tuple[int | None, int | None]:
    """Extract test passed/total from quality report."""
    if not isinstance(raw.quality, Ok):
        return None, None
    checks = raw.quality.value.get("gate_result", {}).get(
        "check_results", [],
    )
    for check in checks:
        if check.get("checker_name") == "pytest":
            return _parse_test_output(check.get("output", ""))
    return None, None


def _parse_test_output(output: str) -> tuple[int | None, int | None]:
    """Parse 'Tests: N passed, M failed' from pytest output."""
    import re

    match = re.search(r"(\d+)\s+passed", output)
    if not match:
        return None, None
    passed = int(match.group(1))
    failed_match = re.search(r"(\d+)\s+failed", output)
    failed = int(failed_match.group(1)) if failed_match else 0
    return passed, passed + failed


def _extract_docker_status(
    raw: ServiceRawState,
    architecture: str,
) -> str | None:
    """Extract docker check status from quality report."""
    if not isinstance(raw.quality, Ok):
        return None
    checks = raw.quality.value.get("gate_result", {}).get(
        "check_results", [],
    )
    for check in checks:
        if check.get("checker_name") == "docker_checker":
            return "OK" if check.get("passed") else "FAIL"
    return None


def _extract_boundary_status(raw: ServiceRawState) -> str | None:
    """Extract boundary compliance from quality report."""
    if not isinstance(raw.quality, Ok):
        return None
    checks = raw.quality.value.get("gate_result", {}).get(
        "check_results", [],
    )
    for check in checks:
        if check.get("checker_name") == "boundary_checker":
            return "OK" if check.get("passed") else "FAIL"
    return None


# ── Phase progress ────────────────────────────────────────────────────


def calculate_phase_progress(
    orch_data: dict | None,
    service_statuses: dict[str, ServiceStatusRecord],
) -> tuple[PhaseProgressRecord, ...]:
    """Build phase progress records from orchestration state."""
    if orch_data is None:
        return ()
    phases = orch_data.get("phases", [])
    if not phases:
        return ()
    results: list[PhaseProgressRecord] = []
    for i, phase in enumerate(phases):
        record = _build_one_phase(i, phase, phases, service_statuses)
        results.append(record)
    return tuple(results)


def _build_one_phase(
    idx: int,
    phase: dict,
    all_phases: list[dict],
    statuses: dict[str, ServiceStatusRecord],
) -> PhaseProgressRecord:
    """Build a single PhaseProgressRecord."""
    slugs = tuple(s.get("slug", "") for s in phase.get("services", []))
    details = _build_service_details(slugs, statuses)
    pct = _phase_completion(slugs, statuses)
    status = _phase_status(idx, slugs, statuses, all_phases)
    blocked_by = _find_blocker(idx, all_phases, statuses)

    return PhaseProgressRecord(
        index=phase.get("index", idx),
        label=phase.get("label", f"Phase {idx}"),
        services=slugs,
        completion_percent=round(pct, 1),
        status=status,
        blocked_by=blocked_by if status == "blocked" else None,
        service_details=details,
    )


def _service_composite(svc: ServiceStatusRecord) -> float:
    """Weighted composite: pipeline 40%, impl 50%, quality 10%."""
    if svc.overall_status == "COMPLETE":
        return 100.0
    if svc.overall_status == "NOT_STARTED":
        return 0.0
    impl = float(svc.lifecycle.impl_percent or 0)
    pipeline = _pipeline_score(svc.lifecycle)
    quality = 100.0 if svc.lifecycle.tests_total and svc.lifecycle.tests_total > 0 else 0.0
    return pipeline * 0.4 + impl * 0.5 + quality * 0.1


def _pipeline_score(lc: LifecyclePhases) -> float:
    """Score spec/plan/tasks presence: each DONE=33.3, WIP=16.7."""
    score = 0.0
    for val in (lc.spec, lc.plan, lc.tasks):
        if val == "DONE":
            score += 33.33
        elif val == "WIP":
            score += 16.67
    return min(score, 100.0)


def _phase_completion(
    slugs: tuple[str, ...],
    statuses: dict[str, ServiceStatusRecord],
) -> float:
    """Average composite score across all services in a phase."""
    if not slugs:
        return 0.0
    total = sum(_service_composite(statuses[s]) for s in slugs if s in statuses)
    return total / len(slugs)


def _phase_status(
    idx: int,
    slugs: tuple[str, ...],
    statuses: dict[str, ServiceStatusRecord],
    all_phases: list[dict],
) -> str:
    """Determine phase status string."""
    svc_statuses = [statuses[s].overall_status for s in slugs if s in statuses]
    if all(s == "COMPLETE" for s in svc_statuses):
        return "complete"
    if _find_blocker(idx, all_phases, statuses) is not None:
        return "blocked"
    active = {"IN_PROGRESS", "PLANNING", "FAILED", "UNKNOWN"}
    if any(s in active for s in svc_statuses):
        return "in-progress"
    return "pending"


def _find_blocker(
    idx: int,
    all_phases: list[dict],
    statuses: dict[str, ServiceStatusRecord],
) -> int | None:
    """Find prior incomplete phase index, or None."""
    for i in range(idx):
        prior = all_phases[i]
        prior_slugs = [s.get("slug", "") for s in prior.get("services", [])]
        if not all(
            statuses.get(s, _not_started(s)).overall_status == "COMPLETE"
            for s in prior_slugs
        ):
            return prior.get("index", i)
    return None


def _not_started(slug: str) -> ServiceStatusRecord:
    """Fallback record for unknown services."""
    from specforge.core.status_models import ServiceStatusRecord as SSR
    return SSR(
        slug=slug, display_name=slug, features=(),
        lifecycle=LifecyclePhases(), overall_status="NOT_STARTED",
    )


def _build_service_details(
    slugs: tuple[str, ...],
    statuses: dict[str, ServiceStatusRecord],
) -> tuple[ServicePhaseDetail, ...]:
    """Build per-service detail entries for a phase."""
    details: list[ServicePhaseDetail] = []
    for slug in slugs:
        svc = statuses.get(slug)
        if svc is None:
            details.append(ServicePhaseDetail(slug=slug, status="NOT_STARTED"))
        else:
            details.append(ServicePhaseDetail(
                slug=slug,
                status=svc.overall_status,
                impl_percent=svc.lifecycle.impl_percent,
            ))
    return tuple(details)


# ── Quality summary ──────────────────────────────────────────────────


def build_quality_summary(
    services: list[ServiceStatusRecord],
) -> QualitySummaryRecord:
    """Build project-wide quality summary from service records (legacy)."""
    return aggregate_quality(tuple(services), "microservice", {})


def aggregate_quality(
    services: tuple[ServiceStatusRecord, ...],
    architecture: str,
    raw_states: dict[str, ServiceRawState],
) -> QualitySummaryRecord:
    """Build project-wide quality summary with full aggregation."""
    counts = _count_statuses(list(services))
    t_total, t_complete, t_failed = _count_tasks_from_raw(raw_states)
    cov = _compute_coverage_avg(raw_states)
    docker = _compute_docker_metrics(raw_states, architecture)
    contract = _compute_contract_metrics(raw_states, architecture)
    autofix = _compute_autofix_rate(raw_states)

    return QualitySummaryRecord(
        services_total=len(services),
        services_complete=counts.get("COMPLETE", 0),
        services_in_progress=counts.get("IN_PROGRESS", 0),
        services_planning=counts.get("PLANNING", 0),
        services_not_started=counts.get("NOT_STARTED", 0),
        services_blocked=counts.get("BLOCKED", 0),
        services_failed=counts.get("FAILED", 0),
        services_unknown=counts.get("UNKNOWN", 0),
        tasks_total=t_total,
        tasks_complete=t_complete,
        tasks_failed=t_failed,
        coverage_avg=cov,
        docker_built=docker[0],
        docker_total=docker[1],
        docker_failing=docker[2],
        contract_passed=contract[0],
        contract_total=contract[1],
        autofix_success_rate=autofix,
    )


def _count_statuses(
    services: list[ServiceStatusRecord],
) -> dict[str, int]:
    """Count services per status."""
    counts: dict[str, int] = {}
    for svc in services:
        status = svc.overall_status
        counts[status] = counts.get(status, 0) + 1
    return counts


def _count_tasks(
    services: list[ServiceStatusRecord],
) -> tuple[int, int, int]:
    """Count total/complete/failed tasks across all services (legacy)."""
    total = 0
    complete = 0
    failed = 0
    for svc in services:
        lc = svc.lifecycle
        if lc.impl_percent is not None and lc.tests_total is not None:
            total += lc.tests_total
            complete += lc.tests_passed or 0
    return total, complete, failed


def _count_tasks_from_raw(
    raw_states: dict[str, ServiceRawState],
) -> tuple[int, int, int]:
    """Count total/complete/failed tasks from execution states."""
    total = complete = failed = 0
    for raw in raw_states.values():
        if not isinstance(raw.execution, Ok):
            continue
        tasks = raw.execution.value.get("tasks", [])
        total += len(tasks)
        complete += sum(1 for t in tasks if t.get("status") == "completed")
        failed += sum(1 for t in tasks if t.get("status") == "failed")
    return total, complete, failed


def _compute_coverage_avg(
    raw_states: dict[str, ServiceRawState],
) -> float | None:
    """Average coverage percentage across services with data."""
    values: list[float] = []
    for raw in raw_states.values():
        pct = _extract_coverage_pct(raw)
        if pct is not None:
            values.append(pct)
    return sum(values) / len(values) if values else None


def _extract_coverage_pct(raw: ServiceRawState) -> float | None:
    """Parse coverage percentage from quality check output."""
    if not isinstance(raw.quality, Ok):
        return None
    checks = raw.quality.value.get("gate_result", {}).get("check_results", [])
    for check in checks:
        name = check.get("checker_name", "")
        if "coverage" in name:
            match = re.search(r"(\d+(?:\.\d+)?)%", check.get("output", ""))
            if match:
                return float(match.group(1))
    return None


def _compute_docker_metrics(
    raw_states: dict[str, ServiceRawState],
    architecture: str,
) -> tuple[int | None, int | None, int | None]:
    """Count docker built/total/failing. None for non-microservice."""
    if architecture != "microservice":
        return None, None, None
    built = total = failing = 0
    found = False
    for raw in raw_states.values():
        if not isinstance(raw.quality, Ok):
            continue
        checks = raw.quality.value.get("gate_result", {}).get("check_results", [])
        for check in checks:
            if check.get("checker_name") == "docker_checker":
                found = True
                total += 1
                if check.get("passed"):
                    built += 1
                else:
                    failing += 1
    return (built, total, failing) if found else (None, None, None)


def _compute_contract_metrics(
    raw_states: dict[str, ServiceRawState],
    architecture: str,
) -> tuple[int | None, int | None]:
    """Count contract passed/total. None for non-microservice."""
    if architecture != "microservice":
        return None, None
    passed = total = 0
    found = False
    for raw in raw_states.values():
        if not isinstance(raw.quality, Ok):
            continue
        checks = raw.quality.value.get("gate_result", {}).get("check_results", [])
        for check in checks:
            if check.get("checker_name") == "contract_checker":
                found = True
                total += 1
                if check.get("passed"):
                    passed += 1
    return (passed, total) if found else (None, None)


def _compute_autofix_rate(
    raw_states: dict[str, ServiceRawState],
) -> float | None:
    """Compute successful fix attempts / total fix attempts."""
    success = total = 0
    for raw in raw_states.values():
        if not isinstance(raw.execution, Ok):
            continue
        for task in raw.execution.value.get("tasks", []):
            for attempt in task.get("fix_attempts", []):
                total += 1
                if attempt.get("success"):
                    success += 1
    return success / total if total > 0 else None
