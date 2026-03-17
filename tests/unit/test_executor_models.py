"""Unit tests for executor_models.py — 8 frozen dataclasses + ExecutionMode type alias."""

from __future__ import annotations

import dataclasses
from typing import get_args

import pytest


class TestExecutionMode:
    """ExecutionMode is a Literal type alias, not a dataclass."""

    def test_literal_values(self) -> None:
        from specforge.core.executor_models import ExecutionMode

        values = get_args(ExecutionMode)
        assert set(values) == {"prompt-display", "agent-call"}

    def test_valid_mode_matches(self) -> None:
        from specforge.core.executor_models import ExecutionMode

        mode: ExecutionMode = "prompt-display"
        assert mode in get_args(ExecutionMode)

        mode = "agent-call"
        assert mode in get_args(ExecutionMode)


class TestServiceLock:
    """ServiceLock — file-based lock metadata."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import ServiceLock

        lock = ServiceLock(
            service_slug="ledger-service",
            pid=12345,
            started_at="2026-03-17T10:00:00Z",
            current_task_id="T001",
            hostname="dev-machine",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            lock.service_slug = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        from specforge.core.executor_models import ServiceLock

        lock = ServiceLock(
            service_slug="ledger-service",
            pid=12345,
            started_at="2026-03-17T10:00:00Z",
            current_task_id="T001",
            hostname="dev-machine",
        )
        assert lock.service_slug == "ledger-service"
        assert lock.pid == 12345
        assert lock.current_task_id == "T001"
        assert lock.hostname == "dev-machine"


class TestTaskExecution:
    """TaskExecution — per-task progress record."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import TaskExecution

        task = TaskExecution(task_id="T001")
        with pytest.raises(dataclasses.FrozenInstanceError):
            task.status = "completed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.executor_models import TaskExecution

        task = TaskExecution(task_id="T001")
        assert task.status == "pending"
        assert task.attempt == 1
        assert task.started_at is None
        assert task.completed_at is None
        assert task.commit_sha is None
        assert task.error_output is None
        assert task.fix_attempts == ()

    def test_skipped_status(self) -> None:
        from specforge.core.executor_models import TaskExecution

        task = TaskExecution(task_id="T001", status="skipped")
        assert task.status == "skipped"

    def test_all_statuses_valid(self) -> None:
        from specforge.core.executor_models import TaskExecution

        for status in ("pending", "in-progress", "completed", "failed", "skipped"):
            task = TaskExecution(task_id="T001", status=status)
            assert task.status == status


class TestQualityCheckResult:
    """QualityCheckResult — build + lint + test outcome."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import QualityCheckResult

        result = QualityCheckResult(
            passed=True,
            build_output="",
            lint_output="",
            test_output="",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.executor_models import QualityCheckResult

        result = QualityCheckResult(
            passed=True,
            build_output="ok",
            lint_output="ok",
            test_output="ok",
        )
        assert result.failed_checks == ()
        assert result.is_regression is False

    def test_with_failures(self) -> None:
        from specforge.core.executor_models import QualityCheckResult

        result = QualityCheckResult(
            passed=False,
            build_output="error",
            lint_output="ok",
            test_output="FAILED",
            failed_checks=("build", "test"),
            is_regression=True,
        )
        assert result.failed_checks == ("build", "test")
        assert result.is_regression is True


class TestAutoFixAttempt:
    """AutoFixAttempt — single retry cycle record."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import AutoFixAttempt

        attempt = AutoFixAttempt(
            attempt_number=1,
            error_input="test failed",
            fix_prompt="fix this",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            attempt.reverted = True  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.executor_models import AutoFixAttempt

        attempt = AutoFixAttempt(
            attempt_number=1,
            error_input="test failed",
            fix_prompt="fix this",
        )
        assert attempt.files_changed == ()
        assert attempt.check_result is None
        assert attempt.reverted is False


class TestExecutionState:
    """ExecutionState — persistent progress record."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import ExecutionState

        state = ExecutionState(
            service_slug="ledger-service",
            architecture="microservice",
            mode="prompt-display",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.service_slug = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.executor_models import ExecutionState

        state = ExecutionState(
            service_slug="ledger-service",
            architecture="microservice",
            mode="prompt-display",
        )
        assert state.schema_version == "1.0"
        assert state.tasks == ()
        assert state.shared_infra_complete is False
        assert state.verification is None
        assert state.created_at != ""
        assert state.updated_at != ""

    def test_with_tasks(self) -> None:
        from specforge.core.executor_models import ExecutionState, TaskExecution

        tasks = (
            TaskExecution(task_id="T001", status="completed"),
            TaskExecution(task_id="T002", status="pending"),
        )
        state = ExecutionState(
            service_slug="ledger-service",
            architecture="microservice",
            mode="prompt-display",
            tasks=tasks,
        )
        assert len(state.tasks) == 2
        assert state.tasks[0].status == "completed"


class TestVerificationState:
    """VerificationState — microservice post-implementation results."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import VerificationState

        vs = VerificationState()
        with pytest.raises(dataclasses.FrozenInstanceError):
            vs.container_built = True  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.executor_models import VerificationState

        vs = VerificationState()
        assert vs.container_built is False
        assert vs.health_check_passed is False
        assert vs.contract_tests_passed is False
        assert vs.compose_registered is False
        assert vs.errors == ()


class TestExecutionContext:
    """ExecutionContext — assembled read-only context for task execution."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import ExecutionContext

        ctx = ExecutionContext(
            constitution="const",
            governance_prompts="gov",
            service_spec="spec",
            service_plan="plan",
            service_data_model="dm",
            service_edge_cases="ec",
            service_tasks="tasks",
            current_task="do something",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.constitution = "new"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.executor_models import ExecutionContext

        ctx = ExecutionContext(
            constitution="const",
            governance_prompts="gov",
            service_spec="spec",
            service_plan="plan",
            service_data_model="dm",
            service_edge_cases="ec",
            service_tasks="tasks",
            current_task="do something",
        )
        assert ctx.dependency_contracts == {}
        assert ctx.architecture_prompts == ""
        assert ctx.estimated_tokens == 0


class TestImplementPrompt:
    """ImplementPrompt — assembled prompt for a single task."""

    def test_frozen(self) -> None:
        from specforge.core.executor_models import ImplementPrompt

        prompt = ImplementPrompt(
            system_context="governance context",
            task_description="implement user model",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            prompt.task_description = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.executor_models import ImplementPrompt

        prompt = ImplementPrompt(
            system_context="governance context",
            task_description="implement user model",
        )
        assert prompt.file_hints == ()
        assert prompt.dependency_context == ""
        assert prompt.prior_task_commits == ()
