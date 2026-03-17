"""Frozen dataclasses for the sub-agent execution engine (Feature 009)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

ExecutionMode = Literal["prompt-display", "agent-call"]


@dataclass(frozen=True)
class ServiceLock:
    """File-based lock metadata preventing concurrent execution."""

    service_slug: str
    pid: int
    started_at: str
    current_task_id: str
    hostname: str


@dataclass(frozen=True)
class TaskExecution:
    """Per-task progress record within ExecutionState."""

    task_id: str
    status: str = "pending"
    attempt: int = 1
    started_at: str | None = None
    completed_at: str | None = None
    commit_sha: str | None = None
    error_output: str | None = None
    fix_attempts: tuple[str, ...] = ()


@dataclass(frozen=True)
class QualityCheckResult:
    """Outcome of build + lint + test after a task."""

    passed: bool
    build_output: str
    lint_output: str
    test_output: str
    failed_checks: tuple[str, ...] = ()
    is_regression: bool = False


@dataclass(frozen=True)
class AutoFixAttempt:
    """Single retry cycle record."""

    attempt_number: int
    error_input: str
    fix_prompt: str
    files_changed: tuple[str, ...] = ()
    check_result: QualityCheckResult | None = None
    reverted: bool = False


@dataclass(frozen=True)
class VerificationState:
    """Post-implementation verification results (microservice only)."""

    container_built: bool = False
    health_check_passed: bool = False
    contract_tests_passed: bool = False
    compose_registered: bool = False
    errors: tuple[str, ...] = ()


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass(frozen=True)
class ExecutionState:
    """Persistent record of implementation progress for a service."""

    service_slug: str
    architecture: str
    mode: str
    schema_version: str = "1.0"
    tasks: tuple[TaskExecution, ...] = ()
    shared_infra_complete: bool = False
    verification: VerificationState | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


@dataclass(frozen=True)
class ExecutionContext:
    """Assembled read-only context for a task execution."""

    constitution: str
    governance_prompts: str
    service_spec: str
    service_plan: str
    service_data_model: str
    service_edge_cases: str
    service_tasks: str
    current_task: str
    dependency_contracts: dict[str, str] = field(default_factory=dict)
    architecture_prompts: str = ""
    estimated_tokens: int = 0


@dataclass(frozen=True)
class ImplementPrompt:
    """Assembled prompt for a single task execution."""

    system_context: str
    task_description: str
    file_hints: tuple[str, ...] = ()
    dependency_context: str = ""
    prior_task_commits: tuple[str, ...] = ()
