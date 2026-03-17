"""Execution state persistence — atomic writes following pipeline_state.py patterns."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from specforge.core.executor_models import ExecutionState, TaskExecution
from specforge.core.result import Err, Ok, Result


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def create_initial_state(
    service_slug: str,
    architecture: str,
    mode: str,
    task_ids: tuple[str, ...],
) -> ExecutionState:
    """Create a fresh ExecutionState with all tasks pending."""
    tasks = tuple(TaskExecution(task_id=tid) for tid in task_ids)
    return ExecutionState(
        service_slug=service_slug,
        architecture=architecture,
        mode=mode,
        tasks=tasks,
    )


def mark_task_in_progress(
    state: ExecutionState, task_id: str,
) -> ExecutionState | Result:
    """Transition a task to in-progress status."""
    idx = _find_task_index(state, task_id)
    if idx is None:
        return Err(f"Task '{task_id}' not found in execution state")
    task = state.tasks[idx]
    updated = replace(task, status="in-progress", started_at=_now_iso())
    return _replace_task(state, idx, updated)


def mark_task_completed(
    state: ExecutionState, task_id: str, commit_sha: str,
) -> ExecutionState:
    """Transition a task to completed status with commit SHA."""
    idx = _find_task_index(state, task_id)
    if idx is None:
        return Err(f"Task '{task_id}' not found in execution state")
    task = state.tasks[idx]
    updated = replace(
        task,
        status="completed",
        commit_sha=commit_sha,
        completed_at=_now_iso(),
    )
    return _replace_task(state, idx, updated)


def mark_task_failed(
    state: ExecutionState,
    task_id: str,
    error: str,
    fix_attempts: tuple[str, ...],
) -> ExecutionState:
    """Transition a task to failed status with error details."""
    idx = _find_task_index(state, task_id)
    if idx is None:
        return Err(f"Task '{task_id}' not found in execution state")
    task = state.tasks[idx]
    updated = replace(
        task,
        status="failed",
        error_output=error,
        fix_attempts=fix_attempts,
        completed_at=_now_iso(),
    )
    return _replace_task(state, idx, updated)


def get_next_pending_task(state: ExecutionState) -> str | None:
    """Return the ID of the first pending task, or None."""
    for task in state.tasks:
        if task.status == "pending":
            return task.task_id
    return None


def validate_against_tasks(
    state: ExecutionState,
    current_task_ids: tuple[str, ...],
) -> ExecutionState:
    """Sync state with current tasks.md — remove orphans, add new."""
    current_set = set(current_task_ids)
    existing_by_id = {t.task_id: t for t in state.tasks}

    new_tasks: list[TaskExecution] = []
    for tid in current_task_ids:
        if tid in existing_by_id:
            new_tasks.append(existing_by_id[tid])
        else:
            new_tasks.append(TaskExecution(task_id=tid))

    return replace(state, tasks=tuple(new_tasks), updated_at=_now_iso())


def save_state(path: Path, state: ExecutionState) -> Result:
    """Write execution state atomically: temp file + fsync + replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _state_to_dict(state)
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
        return Err(f"Failed to write execution state '{path}': {exc}")
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def load_state(path: Path) -> Result:
    """Load execution state from disk. Returns Ok(None) if missing."""
    if not path.exists():
        return Ok(None)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return Ok(_dict_to_state(data))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return Err(f"Invalid execution state file '{path}': {exc}")


def detect_committed_task(
    task_id: str, service_slug: str, repo_path: Path,
) -> str | None:
    """Check git log for a task's conventional commit. Returns SHA or None."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--grep={task_id}"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            first_line = result.stdout.strip().splitlines()[0]
            return first_line.split()[0]
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


# ── Private helpers ─────────────────────────────────────────────────


def _find_task_index(
    state: ExecutionState, task_id: str,
) -> int | None:
    """Find the index of a task by ID."""
    for i, task in enumerate(state.tasks):
        if task.task_id == task_id:
            return i
    return None


def _replace_task(
    state: ExecutionState, idx: int, updated_task: TaskExecution,
) -> ExecutionState:
    """Replace a task at index, returning new state."""
    tasks = list(state.tasks)
    tasks[idx] = updated_task
    return replace(state, tasks=tuple(tasks), updated_at=_now_iso())


def _state_to_dict(state: ExecutionState) -> dict:
    """Serialize ExecutionState to a JSON-safe dict."""
    return {
        "schema_version": state.schema_version,
        "service_slug": state.service_slug,
        "architecture": state.architecture,
        "mode": state.mode,
        "shared_infra_complete": state.shared_infra_complete,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "tasks": [_task_to_dict(t) for t in state.tasks],
        "verification": _verification_to_dict(state.verification),
    }


def _task_to_dict(task: TaskExecution) -> dict:
    """Serialize a TaskExecution to dict."""
    return {
        "task_id": task.task_id,
        "status": task.status,
        "attempt": task.attempt,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "commit_sha": task.commit_sha,
        "error_output": task.error_output,
        "fix_attempts": list(task.fix_attempts),
    }


def _verification_to_dict(v) -> dict | None:
    """Serialize VerificationState to dict."""
    if v is None:
        return None
    return {
        "container_built": v.container_built,
        "health_check_passed": v.health_check_passed,
        "contract_tests_passed": v.contract_tests_passed,
        "compose_registered": v.compose_registered,
        "errors": list(v.errors),
    }


def _dict_to_state(data: dict) -> ExecutionState:
    """Deserialize dict to ExecutionState."""
    from specforge.core.executor_models import VerificationState

    tasks = tuple(
        TaskExecution(
            task_id=t["task_id"],
            status=t["status"],
            attempt=t.get("attempt", 1),
            started_at=t.get("started_at"),
            completed_at=t.get("completed_at"),
            commit_sha=t.get("commit_sha"),
            error_output=t.get("error_output"),
            fix_attempts=tuple(t.get("fix_attempts", ())),
        )
        for t in data.get("tasks", ())
    )

    v_data = data.get("verification")
    verification = None
    if v_data is not None:
        verification = VerificationState(
            container_built=v_data.get("container_built", False),
            health_check_passed=v_data.get("health_check_passed", False),
            contract_tests_passed=v_data.get("contract_tests_passed", False),
            compose_registered=v_data.get("compose_registered", False),
            errors=tuple(v_data.get("errors", ())),
        )

    return ExecutionState(
        schema_version=data.get("schema_version", "1.0"),
        service_slug=data["service_slug"],
        architecture=data["architecture"],
        mode=data["mode"],
        tasks=tasks,
        shared_infra_complete=data.get("shared_infra_complete", False),
        verification=verification,
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )
