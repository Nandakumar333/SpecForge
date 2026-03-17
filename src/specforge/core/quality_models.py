"""Quality validation data models (Feature 010)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class ErrorCategory(Enum):
    """Classification label for quality check failures."""

    SYNTAX = "syntax"
    LOGIC = "logic"
    TYPE = "type"
    LINT = "lint"
    COVERAGE = "coverage"
    DOCKER = "docker"
    CONTRACT = "contract"
    BOUNDARY = "boundary"
    SECURITY = "security"


class ContractAttribution(Enum):
    """Sub-classification for contract test failures."""

    CONSUMER = "consumer"
    PROVIDER = "provider"


class CheckLevel(Enum):
    """When a checker should run."""

    TASK = "task"
    SERVICE = "service"


@dataclass(frozen=True)
class ErrorDetail:
    """A single structured error extracted from check output."""

    file_path: str
    line_number: int | None = None
    column: int | None = None
    code: str = ""
    message: str = ""
    context: str = ""


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single quality check execution."""

    checker_name: str
    passed: bool
    category: ErrorCategory
    output: str = ""
    error_details: tuple[ErrorDetail, ...] = ()
    skipped: bool = False
    skip_reason: str = ""
    attribution: ContractAttribution | None = None


@dataclass(frozen=True)
class QualityGateResult:
    """Aggregate outcome of running the full check suite."""

    passed: bool
    check_results: tuple[CheckResult, ...] = ()
    failed_checks: tuple[str, ...] = ()
    skipped_checks: tuple[str, ...] = ()
    architecture: str = "monolithic"
    level: CheckLevel = CheckLevel.TASK


@dataclass(frozen=True)
class FunctionInfo:
    """Result of AST analysis for a single function."""

    name: str
    file_path: str
    start_line: int
    end_line: int
    line_count: int


@dataclass(frozen=True)
class ClassInfo:
    """Result of AST analysis for a single class."""

    name: str
    file_path: str
    start_line: int
    end_line: int
    line_count: int


@dataclass(frozen=True)
class FixAttempt:
    """Record of a single auto-fix iteration."""

    attempt_number: int
    category: ErrorCategory
    fix_prompt: str = ""
    files_changed: tuple[str, ...] = ()
    result: QualityGateResult | None = None
    reverted: bool = False
    revert_reason: str = ""


@dataclass(frozen=True)
class DiagnosticReport:
    """Structured escalation document produced when auto-fix exhausts."""

    task_id: str
    original_error: QualityGateResult
    attempts: tuple[FixAttempt, ...] = ()
    still_failing: tuple[str, ...] = ()
    suggested_steps: tuple[str, ...] = ()
    created_at: str = ""


@dataclass(frozen=True)
class QualityReport:
    """Persistent JSON report written after each quality gate run."""

    schema_version: str
    service_slug: str
    architecture: str
    level: str
    gate_result: QualityGateResult
    task_id: str | None = None
    fix_attempts: tuple[FixAttempt, ...] = ()
    diagnostic: DiagnosticReport | None = None
    timestamp: str = ""
