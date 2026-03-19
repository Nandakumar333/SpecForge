"""Frozen dataclasses and persistence for parallel execution state (Feature 016)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass(frozen=True)
class ServiceRunStatus:
    """Per-service progress within a parallel run."""

    slug: str
    status: str = "pending"
    wave_index: int = 0
    phases_completed: int = 0
    phases_total: int = 7
    error: str | None = None
    blocked_by: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


@dataclass(frozen=True)
class WaveStatus:
    """Per-wave progress (implement mode only)."""

    index: int
    status: str = "pending"
    services: tuple[str, ...] = ()
    started_at: str | None = None
    completed_at: str | None = None


@dataclass(frozen=True)
class ParallelExecutionState:
    """Overall parallel run state, persisted for resume."""

    run_id: str
    mode: str  # "decompose" or "implement"
    architecture: str
    total_services: int
    max_workers: int
    fail_fast: bool = False
    status: str = "pending"
    services: tuple[ServiceRunStatus, ...] = ()
    waves: tuple[WaveStatus, ...] = ()
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


# ── State Transition Functions ───────────────────────────────────────


def mark_service_in_progress(
    state: ParallelExecutionState, slug: str,
) -> ParallelExecutionState:
    """Mark a service as in-progress."""
    services = tuple(
        replace(s, status="in-progress", started_at=_now_iso())
        if s.slug == slug else s
        for s in state.services
    )
    return replace(state, services=services, updated_at=_now_iso())


def mark_service_completed(
    state: ParallelExecutionState, slug: str,
    phases_completed: int = 7,
) -> ParallelExecutionState:
    """Mark a service as completed."""
    services = tuple(
        replace(
            s, status="completed",
            phases_completed=phases_completed,
            completed_at=_now_iso(),
        )
        if s.slug == slug else s
        for s in state.services
    )
    return replace(state, services=services, updated_at=_now_iso())


def mark_service_failed(
    state: ParallelExecutionState, slug: str, error: str,
    phases_completed: int = 0,
) -> ParallelExecutionState:
    """Mark a service as failed."""
    services = tuple(
        replace(
            s, status="failed", error=error,
            phases_completed=phases_completed,
            completed_at=_now_iso(),
        )
        if s.slug == slug else s
        for s in state.services
    )
    return replace(state, services=services, updated_at=_now_iso())


def mark_service_blocked(
    state: ParallelExecutionState, slug: str, blocked_by: str,
) -> ParallelExecutionState:
    """Mark a service as blocked by a failed dependency."""
    services = tuple(
        replace(
            s, status="blocked", blocked_by=blocked_by,
            completed_at=_now_iso(),
        )
        if s.slug == slug else s
        for s in state.services
    )
    return replace(state, services=services, updated_at=_now_iso())


def mark_service_cancelled(
    state: ParallelExecutionState, slug: str,
) -> ParallelExecutionState:
    """Mark a service as cancelled."""
    services = tuple(
        replace(s, status="cancelled", completed_at=_now_iso())
        if s.slug == slug else s
        for s in state.services
    )
    return replace(state, services=services, updated_at=_now_iso())


# ── Initialization & Resume ──────────────────────────────────────────


def create_initial_state(
    mode: str,
    architecture: str,
    service_slugs: tuple[str, ...],
    max_workers: int,
    fail_fast: bool = False,
    waves: tuple[WaveStatus, ...] = (),
) -> ParallelExecutionState:
    """Create initial parallel execution state."""
    services = tuple(
        ServiceRunStatus(slug=slug, wave_index=_wave_for(slug, waves))
        for slug in service_slugs
    )
    return ParallelExecutionState(
        run_id=_now_iso(),
        mode=mode,
        architecture=architecture,
        total_services=len(service_slugs),
        max_workers=max_workers,
        fail_fast=fail_fast,
        services=services,
        waves=waves,
    )


def _wave_for(slug: str, waves: tuple[WaveStatus, ...]) -> int:
    """Find the wave index for a service slug."""
    for wave in waves:
        if slug in wave.services:
            return wave.index
    return 0


def detect_resume_point(
    state: ParallelExecutionState,
) -> tuple[str, ...]:
    """Return slugs of services that still need to run."""
    return tuple(
        s.slug for s in state.services
        if s.status not in ("completed", "blocked")
    )


# ── Persistence ──────────────────────────────────────────────────────


def save_state(path: Path, state: ParallelExecutionState) -> None:
    """Atomically persist parallel state to JSON."""
    data = _state_to_dict(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_state(path: Path) -> ParallelExecutionState | None:
    """Load parallel state from JSON. Returns None if not found."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _dict_to_state(data)
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _state_to_dict(state: ParallelExecutionState) -> dict:
    """Serialize state to dict."""
    return {
        "run_id": state.run_id,
        "mode": state.mode,
        "architecture": state.architecture,
        "total_services": state.total_services,
        "max_workers": state.max_workers,
        "fail_fast": state.fail_fast,
        "status": state.status,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "services": [_svc_to_dict(s) for s in state.services],
        "waves": [_wave_to_dict(w) for w in state.waves],
    }


def _svc_to_dict(svc: ServiceRunStatus) -> dict:
    return {
        "slug": svc.slug,
        "status": svc.status,
        "wave_index": svc.wave_index,
        "phases_completed": svc.phases_completed,
        "phases_total": svc.phases_total,
        "error": svc.error,
        "blocked_by": svc.blocked_by,
        "started_at": svc.started_at,
        "completed_at": svc.completed_at,
    }


def _wave_to_dict(wave: WaveStatus) -> dict:
    return {
        "index": wave.index,
        "status": wave.status,
        "services": list(wave.services),
        "started_at": wave.started_at,
        "completed_at": wave.completed_at,
    }


def _dict_to_state(data: dict) -> ParallelExecutionState:
    """Deserialize state from dict."""
    services = tuple(
        ServiceRunStatus(**s) for s in data.get("services", [])
    )
    waves = tuple(
        WaveStatus(
            index=w["index"],
            status=w["status"],
            services=tuple(w.get("services", [])),
            started_at=w.get("started_at"),
            completed_at=w.get("completed_at"),
        )
        for w in data.get("waves", [])
    )
    return ParallelExecutionState(
        run_id=data["run_id"],
        mode=data["mode"],
        architecture=data["architecture"],
        total_services=data["total_services"],
        max_workers=data["max_workers"],
        fail_fast=data.get("fail_fast", False),
        status=data.get("status", "pending"),
        services=services,
        waves=waves,
        started_at=data.get("started_at"),
        completed_at=data.get("completed_at"),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )
