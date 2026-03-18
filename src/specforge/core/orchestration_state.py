"""OrchestrationState — pure function state management with atomic persistence."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import asdict, replace
from pathlib import Path

from specforge.core.orchestrator_models import (
    BoundaryCheckResult,
    ContractCheckResult,
    ContractMismatch,
    IntegrationTestResult,
    OrchestrationPlan,
    OrchestrationState,
    PhaseState,
    ServiceStatus,
    VerificationResult,
    _now_iso,
)
from specforge.core.result import Err, Ok, Result

# ── State Creation ────────────────────────────────────────────────────


def create_initial_state(plan: OrchestrationPlan) -> OrchestrationState:
    """Create a fresh OrchestrationState from an execution plan."""
    phases = tuple(
        PhaseState(
            index=p.index,
            services=tuple(ServiceStatus(slug=s) for s in p.services),
        )
        for p in plan.phases
    )
    infra = "skipped" if not plan.shared_infra_required else "pending"
    return OrchestrationState(
        architecture=plan.architecture,
        shared_infra_status=infra,
        phases=phases,
    )


# ── Shared Infrastructure ────────────────────────────────────────────


def mark_shared_infra_complete(state: OrchestrationState) -> OrchestrationState:
    """Mark shared infrastructure as completed."""
    return replace(state, shared_infra_status="completed", updated_at=_now_iso())


def mark_shared_infra_failed(state: OrchestrationState) -> OrchestrationState:
    """Mark shared infrastructure as failed."""
    return replace(state, shared_infra_status="failed", updated_at=_now_iso())


# ── Phase Transitions ────────────────────────────────────────────────


def mark_phase_in_progress(
    state: OrchestrationState, phase_index: int,
) -> OrchestrationState:
    """Mark a phase as in-progress with a start timestamp."""
    now = _now_iso()
    updated = replace(state.phases[phase_index], status="in-progress", started_at=now)
    return _replace_phase(state, phase_index, updated)


# ── Service Transitions ──────────────────────────────────────────────


def mark_service_completed(
    state: OrchestrationState,
    phase_index: int,
    slug: str,
    tasks_completed: int,
    tasks_total: int,
) -> OrchestrationState:
    """Mark a service as completed with task counts."""
    now = _now_iso()
    phase = state.phases[phase_index]
    svc_idx = _find_service_index(phase, slug)
    updated_svc = replace(
        phase.services[svc_idx],
        status="completed",
        tasks_completed=tasks_completed,
        tasks_total=tasks_total,
        completed_at=now,
    )
    return _replace_service(state, phase_index, svc_idx, updated_svc)


def mark_service_failed(
    state: OrchestrationState,
    phase_index: int,
    slug: str,
    error: str,
) -> OrchestrationState:
    """Mark a service as failed with an error message."""
    now = _now_iso()
    phase = state.phases[phase_index]
    svc_idx = _find_service_index(phase, slug)
    updated_svc = replace(
        phase.services[svc_idx],
        status="failed",
        error=error,
        completed_at=now,
    )
    return _replace_service(state, phase_index, svc_idx, updated_svc)


# ── Phase Status Computation ─────────────────────────────────────────


def compute_phase_status(phase_state: PhaseState) -> str:
    """Derive aggregate phase status from service statuses."""
    statuses = {s.status for s in phase_state.services}
    if statuses == {"completed"}:
        return "completed"
    if statuses == {"failed"}:
        return "failed"
    if "in-progress" in statuses:
        return "in-progress"
    if statuses == {"pending"}:
        return "pending"
    if statuses <= {"completed", "failed"}:
        return "partial"
    return "in-progress"


# ── Verification ──────────────────────────────────────────────────────


def add_verification_result(
    state: OrchestrationState, result: VerificationResult,
) -> OrchestrationState:
    """Append a verification result to the state."""
    results = (*state.verification_results, result)
    return replace(state, verification_results=results, updated_at=_now_iso())


# ── Queries ───────────────────────────────────────────────────────────


def get_completed_services(state: OrchestrationState) -> tuple[str, ...]:
    """Return slugs of all services with status 'completed'."""
    return tuple(
        svc.slug
        for phase in state.phases
        for svc in phase.services
        if svc.status == "completed"
    )


def detect_resume_point(state: OrchestrationState) -> tuple[int, str | None]:
    """Find the first incomplete phase and first incomplete service."""
    for phase in state.phases:
        if compute_phase_status(phase) == "completed":
            continue
        has_progress = any(s.status == "completed" for s in phase.services)
        if not has_progress:
            return (phase.index, None)
        for svc in phase.services:
            if svc.status != "completed":
                return (phase.index, svc.slug)
    return (len(state.phases) - 1, None)


# ── Persistence ───────────────────────────────────────────────────────


def save_state(path: Path, state: OrchestrationState) -> Result:
    """Save orchestration state atomically to disk."""
    data = _state_to_dict(state)
    return _atomic_write_json(path, data)


def load_state(path: Path) -> Result:
    """Load orchestration state from disk. Returns Err if missing."""
    if not path.exists():
        return Err(f"State file not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return Ok(_dict_to_state(data))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return Err(f"Invalid state file '{path}': {exc}")


# ── Internal Helpers ──────────────────────────────────────────────────


def _find_service_index(phase: PhaseState, slug: str) -> int:
    """Find the index of a service within a phase by slug."""
    for i, svc in enumerate(phase.services):
        if svc.slug == slug:
            return i
    msg = f"Service '{slug}' not found in phase {phase.index}"
    raise ValueError(msg)


def _replace_phase(
    state: OrchestrationState, idx: int, updated_phase: PhaseState,
) -> OrchestrationState:
    """Return a new state with one phase replaced."""
    phases = (*state.phases[:idx], updated_phase, *state.phases[idx + 1 :])
    return replace(state, phases=phases, updated_at=_now_iso())


def _replace_service(
    state: OrchestrationState, phase_idx: int, svc_idx: int, updated_svc: ServiceStatus,
) -> OrchestrationState:
    """Return a new state with one service replaced within a phase."""
    phase = state.phases[phase_idx]
    services = (*phase.services[:svc_idx], updated_svc, *phase.services[svc_idx + 1 :])
    updated_phase = replace(phase, services=services)
    return _replace_phase(state, phase_idx, updated_phase)


def _state_to_dict(state: OrchestrationState) -> dict:
    """Convert OrchestrationState to a JSON-serializable dict."""
    return {
        "architecture": state.architecture,
        "schema_version": state.schema_version,
        "status": state.status,
        "shared_infra_status": state.shared_infra_status,
        "phases": [_phase_to_dict(p) for p in state.phases],
        "verification_results": [_vr_to_dict(v) for v in state.verification_results],
        "integration_result": _itr_to_dict(state.integration_result),
        "phase_ceiling": state.phase_ceiling,
        "started_at": state.started_at,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
    }


def _phase_to_dict(phase: PhaseState) -> dict:
    """Convert PhaseState to a dict."""
    return {
        "index": phase.index,
        "status": phase.status,
        "services": [_svc_to_dict(s) for s in phase.services],
        "started_at": phase.started_at,
        "completed_at": phase.completed_at,
    }


def _svc_to_dict(svc: ServiceStatus) -> dict:
    """Convert ServiceStatus to a dict."""
    return {
        "slug": svc.slug,
        "status": svc.status,
        "error": svc.error,
        "tasks_completed": svc.tasks_completed,
        "tasks_total": svc.tasks_total,
        "started_at": svc.started_at,
        "completed_at": svc.completed_at,
    }


def _vr_to_dict(vr: VerificationResult) -> dict:
    """Convert VerificationResult to a dict."""
    return {
        "after_phase": vr.after_phase,
        "passed": vr.passed,
        "contract_results": [asdict(c) for c in vr.contract_results],
        "boundary_results": [asdict(b) for b in vr.boundary_results],
        "infra_health": vr.infra_health,
        "timestamp": vr.timestamp,
    }


def _itr_to_dict(itr: IntegrationTestResult | None) -> dict | None:
    """Convert IntegrationTestResult to a dict, or None."""
    if itr is None:
        return None
    return asdict(itr)


def _dict_to_state(data: dict) -> OrchestrationState:
    """Reconstruct OrchestrationState from a dict."""
    phases = tuple(_dict_to_phase(p) for p in data["phases"])
    vrs = tuple(_dict_to_vr(v) for v in data.get("verification_results", ()))
    return OrchestrationState(
        architecture=data["architecture"],
        schema_version=data.get("schema_version", "1.0"),
        status=data.get("status", "pending"),
        shared_infra_status=data.get("shared_infra_status", "pending"),
        phases=phases,
        verification_results=vrs,
        integration_result=None,
        phase_ceiling=data.get("phase_ceiling"),
        started_at=data.get("started_at"),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )


def _dict_to_phase(data: dict) -> PhaseState:
    """Reconstruct PhaseState from a dict."""
    services = tuple(
        ServiceStatus(
            slug=s["slug"],
            status=s.get("status", "pending"),
            error=s.get("error"),
            tasks_completed=s.get("tasks_completed", 0),
            tasks_total=s.get("tasks_total", 0),
            started_at=s.get("started_at"),
            completed_at=s.get("completed_at"),
        )
        for s in data.get("services", ())
    )
    return PhaseState(
        index=data["index"],
        status=data.get("status", "pending"),
        services=services,
        started_at=data.get("started_at"),
        completed_at=data.get("completed_at"),
    )


def _dict_to_vr(data: dict) -> VerificationResult:
    """Reconstruct VerificationResult from a dict."""
    contracts = tuple(
        ContractCheckResult(
            consumer=c["consumer"],
            provider=c["provider"],
            passed=c["passed"],
            mismatches=tuple(
                ContractMismatch(**m) for m in c.get("mismatches", ())
            ),
        )
        for c in data.get("contract_results", ())
    )
    boundaries = tuple(
        BoundaryCheckResult(**b)
        for b in data.get("boundary_results", ())
    )
    return VerificationResult(
        after_phase=data["after_phase"],
        passed=data["passed"],
        contract_results=contracts,
        boundary_results=boundaries,
        infra_health=data.get("infra_health"),
        timestamp=data.get("timestamp", ""),
    )


def _atomic_write_json(path: Path, data: dict) -> Result:
    """Write JSON atomically: temp file + fsync + os.replace()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    fd: int | None = None
    tmp_path: Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_str)
        os.write(fd, content)
        os.fsync(fd)
        os.close(fd)
        fd = None
        tmp_path.replace(path)
        tmp_path = None
        return Ok(path)
    except OSError as exc:
        return Err(f"Failed to write state '{path}': {exc}")
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
