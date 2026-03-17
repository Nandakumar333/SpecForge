"""Unit tests for execution_state.py — state persistence functions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestCreateInitialState:
    """create_initial_state produces a fresh ExecutionState."""

    def test_creates_state_with_tasks(self) -> None:
        from specforge.core.execution_state import create_initial_state

        state = create_initial_state(
            service_slug="ledger-service",
            architecture="microservice",
            mode="prompt-display",
            task_ids=("T001", "T002", "T003"),
        )
        assert state.service_slug == "ledger-service"
        assert state.architecture == "microservice"
        assert state.mode == "prompt-display"
        assert len(state.tasks) == 3
        assert all(t.status == "pending" for t in state.tasks)
        assert state.tasks[0].task_id == "T001"

    def test_empty_tasks(self) -> None:
        from specforge.core.execution_state import create_initial_state

        state = create_initial_state(
            service_slug="identity-service",
            architecture="monolithic",
            mode="agent-call",
            task_ids=(),
        )
        assert state.tasks == ()
        assert state.schema_version == "1.0"
        assert state.shared_infra_complete is False


class TestMarkTaskInProgress:
    """mark_task_in_progress transitions a task to in-progress."""

    def test_marks_pending_task(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            mark_task_in_progress,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001",))
        new_state = mark_task_in_progress(state, "T001")
        assert new_state.tasks[0].status == "in-progress"
        assert new_state.tasks[0].started_at is not None

    def test_unknown_task_returns_err(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            mark_task_in_progress,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001",))
        result = mark_task_in_progress(state, "T999")
        assert not result.ok


class TestMarkTaskCompleted:
    """mark_task_completed transitions a task to completed with commit SHA."""

    def test_marks_task_completed(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            mark_task_completed,
            mark_task_in_progress,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001",))
        state = mark_task_in_progress(state, "T001")
        new_state = mark_task_completed(state, "T001", "abc123")
        assert new_state.tasks[0].status == "completed"
        assert new_state.tasks[0].commit_sha == "abc123"
        assert new_state.tasks[0].completed_at is not None


class TestMarkTaskFailed:
    """mark_task_failed records error output and fix attempts."""

    def test_marks_task_failed(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            mark_task_failed,
            mark_task_in_progress,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001",))
        state = mark_task_in_progress(state, "T001")
        new_state = mark_task_failed(
            state, "T001", "test failed", ("attempt1", "attempt2"),
        )
        assert new_state.tasks[0].status == "failed"
        assert new_state.tasks[0].error_output == "test failed"
        assert new_state.tasks[0].fix_attempts == ("attempt1", "attempt2")


class TestGetNextPendingTask:
    """get_next_pending_task returns the first pending task ID."""

    def test_returns_first_pending(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            get_next_pending_task,
            mark_task_completed,
            mark_task_in_progress,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001", "T002", "T003"))
        state = mark_task_in_progress(state, "T001")
        state = mark_task_completed(state, "T001", "sha1")
        next_task = get_next_pending_task(state)
        assert next_task == "T002"

    def test_returns_none_when_all_complete(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            get_next_pending_task,
            mark_task_completed,
            mark_task_in_progress,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001",))
        state = mark_task_in_progress(state, "T001")
        state = mark_task_completed(state, "T001", "sha1")
        assert get_next_pending_task(state) is None


class TestValidateAgainstTasks:
    """validate_against_tasks syncs state with current tasks.md."""

    def test_removes_orphaned_tasks(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            validate_against_tasks,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001", "T002", "T003"))
        new_state = validate_against_tasks(state, ("T001", "T003"))
        assert len(new_state.tasks) == 2
        task_ids = [t.task_id for t in new_state.tasks]
        assert "T002" not in task_ids

    def test_adds_new_tasks(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            validate_against_tasks,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001",))
        new_state = validate_against_tasks(state, ("T001", "T002", "T003"))
        assert len(new_state.tasks) == 3
        assert new_state.tasks[1].task_id == "T002"
        assert new_state.tasks[1].status == "pending"

    def test_preserves_completed_state(self) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            mark_task_completed,
            mark_task_in_progress,
            validate_against_tasks,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001", "T002"))
        state = mark_task_in_progress(state, "T001")
        state = mark_task_completed(state, "T001", "sha1")
        new_state = validate_against_tasks(state, ("T001", "T002", "T003"))
        assert new_state.tasks[0].status == "completed"
        assert new_state.tasks[0].commit_sha == "sha1"


class TestSaveState:
    """save_state writes atomically via temp + os.replace."""

    def test_saves_and_creates_parent_dirs(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import create_initial_state, save_state

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001",))
        state_path = tmp_path / "subdir" / ".execution-state.json"
        result = save_state(state_path, state)
        assert result.ok
        assert state_path.exists()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["service_slug"] == "svc"

    def test_atomic_write_replaces_existing(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import create_initial_state, save_state

        state_path = tmp_path / ".execution-state.json"
        state1 = create_initial_state("svc1", "microservice", "prompt-display", ("T001",))
        save_state(state_path, state1)

        state2 = create_initial_state("svc2", "monolithic", "agent-call", ("T001", "T002"))
        save_state(state_path, state2)

        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["service_slug"] == "svc2"


class TestLoadState:
    """load_state reads state from disk."""

    def test_missing_file_returns_ok_none(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import load_state

        result = load_state(tmp_path / "nonexistent.json")
        assert result.ok
        assert result.value is None

    def test_loads_saved_state(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import (
            create_initial_state,
            load_state,
            save_state,
        )

        state = create_initial_state("svc", "microservice", "prompt-display", ("T001", "T002"))
        state_path = tmp_path / ".execution-state.json"
        save_state(state_path, state)

        result = load_state(state_path)
        assert result.ok
        loaded = result.value
        assert loaded.service_slug == "svc"
        assert len(loaded.tasks) == 2
        assert loaded.tasks[0].task_id == "T001"

    def test_corrupt_file_returns_err(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import load_state

        state_path = tmp_path / ".execution-state.json"
        state_path.write_text("not valid json{{{", encoding="utf-8")
        result = load_state(state_path)
        assert not result.ok


class TestDetectCommittedTask:
    """detect_committed_task checks git log for task commit."""

    def test_returns_sha_when_found(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import detect_committed_task

        # Create a git repo with a commit containing the task ID
        os.system(f'cd /d "{tmp_path}" && git init && git config user.email "t@t" && git config user.name "t"')
        (tmp_path / "f.txt").write_text("content")
        os.system(f'cd /d "{tmp_path}" && git add . && git commit -m "feat(svc): implement T001 task"')

        result = detect_committed_task("T001", "svc", tmp_path)
        assert result is not None
        assert len(result) >= 7  # Short SHA

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        from specforge.core.execution_state import detect_committed_task

        os.system(f'cd /d "{tmp_path}" && git init && git config user.email "t@t" && git config user.name "t"')
        (tmp_path / "f.txt").write_text("content")
        os.system(f'cd /d "{tmp_path}" && git add . && git commit -m "feat: unrelated commit"')

        result = detect_committed_task("T999", "svc", tmp_path)
        assert result is None
