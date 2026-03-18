"""Pure aggregation functions: status derivation, phase progress, quality summary."""

from __future__ import annotations

from typing import TYPE_CHECKING

from specforge.core.config import PIPELINE_TO_LIFECYCLE
from specforge.core.result import Err, Ok
from specforge.core.status_models import LifecyclePhases, QualitySummaryRecord

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


# ── Quality summary ──────────────────────────────────────────────────


def build_quality_summary(
    services: list[ServiceStatusRecord],
) -> QualitySummaryRecord:
    """Build project-wide quality summary from service records."""
    counts = _count_statuses(services)
    tasks_total, tasks_complete, tasks_failed = _count_tasks(services)

    return QualitySummaryRecord(
        services_total=len(services),
        services_complete=counts.get("COMPLETE", 0),
        services_in_progress=counts.get("IN_PROGRESS", 0),
        services_planning=counts.get("PLANNING", 0),
        services_not_started=counts.get("NOT_STARTED", 0),
        services_blocked=counts.get("BLOCKED", 0),
        services_failed=counts.get("FAILED", 0),
        services_unknown=counts.get("UNKNOWN", 0),
        tasks_total=tasks_total,
        tasks_complete=tasks_complete,
        tasks_failed=tasks_failed,
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
    """Count total/complete/failed tasks across all services."""
    total = 0
    complete = 0
    failed = 0
    for svc in services:
        lc = svc.lifecycle
        if lc.impl_percent is not None and lc.tests_total is not None:
            total += lc.tests_total
            complete += lc.tests_passed or 0
    return total, complete, failed
