"""PipelineState — phase tracking with atomic persistence."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from specforge.core.config import PIPELINE_PHASES, SCHEMA_VERSION
from specforge.core.result import Err, Ok, Result


@dataclass(frozen=True)
class PhaseStatus:
    """Status of a single pipeline phase."""

    name: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    artifact_paths: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class PipelineState:
    """Aggregate pipeline state for a service."""

    service_slug: str
    schema_version: str
    phases: tuple[PhaseStatus, ...]
    created_at: str
    updated_at: str


def create_initial_state(service_slug: str) -> PipelineState:
    """Create a fresh PipelineState with all phases pending."""
    now = datetime.now(tz=UTC).isoformat()
    phases = tuple(
        PhaseStatus(name=name, status="pending")
        for name in PIPELINE_PHASES
    )
    return PipelineState(
        service_slug=service_slug,
        schema_version=SCHEMA_VERSION,
        phases=phases,
        created_at=now,
        updated_at=now,
    )


def mark_in_progress(state: PipelineState, phase_name: str) -> PipelineState:
    """Mark a phase as in-progress with a start timestamp."""
    now = datetime.now(tz=UTC).isoformat()
    return _update_phase(
        state,
        phase_name,
        lambda ps: replace(ps, status="in-progress", started_at=now),
    )


def mark_complete(
    state: PipelineState,
    phase_name: str,
    artifact_paths: tuple[str, ...],
) -> PipelineState:
    """Mark a phase as complete with artifact paths."""
    now = datetime.now(tz=UTC).isoformat()
    return _update_phase(
        state,
        phase_name,
        lambda ps: replace(
            ps,
            status="complete",
            completed_at=now,
            artifact_paths=artifact_paths,
        ),
    )


def mark_failed(
    state: PipelineState, phase_name: str, error: str
) -> PipelineState:
    """Mark a phase as failed with an error message."""
    now = datetime.now(tz=UTC).isoformat()
    return _update_phase(
        state,
        phase_name,
        lambda ps: replace(
            ps, status="failed", completed_at=now, error=error
        ),
    )


def is_phase_complete(state: PipelineState, phase_name: str) -> bool:
    """Check if a phase has completed successfully."""
    for ps in state.phases:
        if ps.name == phase_name:
            return ps.status == "complete"
    return False


def get_next_phase(state: PipelineState) -> str | None:
    """Get the next phase that needs to run."""
    for ps in state.phases:
        if ps.status != "complete":
            return ps.name
    return None


def detect_interrupted(state: PipelineState) -> PipelineState:
    """Reset in-progress phases (stale) back to pending."""
    return _update_phases(
        state,
        lambda ps: (
            replace(ps, status="pending", started_at=None)
            if ps.status == "in-progress"
            else ps
        ),
    )


def reset_all_phases(state: PipelineState) -> PipelineState:
    """Reset all phases to pending (--force)."""
    return _update_phases(
        state,
        lambda ps: PhaseStatus(name=ps.name, status="pending"),
    )


def save_state(path: Path, state: PipelineState) -> Result:
    """Save pipeline state atomically to disk."""
    data = _state_to_dict(state)
    return _atomic_write_json(path, data)


def load_state(path: Path) -> Result:
    """Load pipeline state from disk. Returns Ok(None) if missing."""
    if not path.exists():
        return Ok(None)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return Ok(_dict_to_state(data))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return Err(f"Invalid state file '{path}': {exc}")


def _update_phase(
    state: PipelineState,
    phase_name: str,
    updater: object,
) -> PipelineState:
    """Apply an updater function to a specific phase."""
    now = datetime.now(tz=UTC).isoformat()
    phases = tuple(
        updater(ps) if ps.name == phase_name else ps
        for ps in state.phases
    )
    return replace(state, phases=phases, updated_at=now)


def _update_phases(
    state: PipelineState, updater: object
) -> PipelineState:
    """Apply an updater function to all phases."""
    now = datetime.now(tz=UTC).isoformat()
    phases = tuple(updater(ps) for ps in state.phases)
    return replace(state, phases=phases, updated_at=now)


def _state_to_dict(state: PipelineState) -> dict:
    """Convert PipelineState to a serializable dict."""
    return {
        "service_slug": state.service_slug,
        "schema_version": state.schema_version,
        "phases": [
            {
                "name": ps.name,
                "status": ps.status,
                "started_at": ps.started_at,
                "completed_at": ps.completed_at,
                "artifact_paths": list(ps.artifact_paths),
                "error": ps.error,
            }
            for ps in state.phases
        ],
        "created_at": state.created_at,
        "updated_at": state.updated_at,
    }


def _dict_to_state(data: dict) -> PipelineState:
    """Convert a dict back to PipelineState."""
    phases = tuple(
        PhaseStatus(
            name=p["name"],
            status=p["status"],
            started_at=p.get("started_at"),
            completed_at=p.get("completed_at"),
            artifact_paths=tuple(p.get("artifact_paths", ())),
            error=p.get("error"),
        )
        for p in data["phases"]
    )
    return PipelineState(
        service_slug=data["service_slug"],
        schema_version=data.get("schema_version", "1.0"),
        phases=phases,
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
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
