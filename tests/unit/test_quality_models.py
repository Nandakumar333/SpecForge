"""Unit tests for quality_models.py — 3 enums + 9 frozen dataclasses."""

from __future__ import annotations

import dataclasses

import pytest


class TestErrorCategory:
    """ErrorCategory — classification labels for quality check failures."""

    def test_has_nine_members(self) -> None:
        from specforge.core.quality_models import ErrorCategory

        assert len(ErrorCategory) == 9

    def test_all_values(self) -> None:
        from specforge.core.quality_models import ErrorCategory

        expected = {
            "syntax", "logic", "type", "lint", "coverage",
            "docker", "contract", "boundary", "security",
        }
        assert {e.value for e in ErrorCategory} == expected


class TestContractAttribution:
    """ContractAttribution — sub-classification for contract failures."""

    def test_has_two_members(self) -> None:
        from specforge.core.quality_models import ContractAttribution

        assert len(ContractAttribution) == 2

    def test_values(self) -> None:
        from specforge.core.quality_models import ContractAttribution

        assert ContractAttribution.CONSUMER.value == "consumer"
        assert ContractAttribution.PROVIDER.value == "provider"


class TestCheckLevel:
    """CheckLevel — when a checker should run."""

    def test_has_two_members(self) -> None:
        from specforge.core.quality_models import CheckLevel

        assert len(CheckLevel) == 2

    def test_values(self) -> None:
        from specforge.core.quality_models import CheckLevel

        assert CheckLevel.TASK.value == "task"
        assert CheckLevel.SERVICE.value == "service"


class TestErrorDetail:
    """ErrorDetail — a single structured error."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import ErrorDetail

        detail = ErrorDetail(file_path="src/main.py")
        with pytest.raises(dataclasses.FrozenInstanceError):
            detail.file_path = "other.py"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.quality_models import ErrorDetail

        detail = ErrorDetail(file_path="src/main.py")
        assert detail.file_path == "src/main.py"
        assert detail.line_number is None
        assert detail.column is None
        assert detail.code == ""
        assert detail.message == ""
        assert detail.context == ""

    def test_all_fields(self) -> None:
        from specforge.core.quality_models import ErrorDetail

        detail = ErrorDetail(
            file_path="app.py",
            line_number=42,
            column=10,
            code="E501",
            message="line too long",
            context="x = 1 + 2 + ...",
        )
        assert detail.line_number == 42
        assert detail.column == 10
        assert detail.code == "E501"
        assert detail.message == "line too long"


class TestCheckResult:
    """CheckResult — outcome of a single quality check."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import CheckResult, ErrorCategory

        result = CheckResult(
            checker_name="ruff",
            passed=True,
            category=ErrorCategory.LINT,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.quality_models import CheckResult, ErrorCategory

        result = CheckResult(
            checker_name="ruff",
            passed=True,
            category=ErrorCategory.LINT,
        )
        assert result.output == ""
        assert result.error_details == ()
        assert result.skipped is False
        assert result.skip_reason == ""
        assert result.attribution is None

    def test_attribution_set(self) -> None:
        from specforge.core.quality_models import (
            CheckResult,
            ContractAttribution,
            ErrorCategory,
        )

        result = CheckResult(
            checker_name="pact",
            passed=False,
            category=ErrorCategory.CONTRACT,
            attribution=ContractAttribution.CONSUMER,
        )
        assert result.attribution == ContractAttribution.CONSUMER


class TestQualityGateResult:
    """QualityGateResult — aggregate check suite outcome."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import QualityGateResult

        gate = QualityGateResult(passed=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            gate.passed = False  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.quality_models import CheckLevel, QualityGateResult

        gate = QualityGateResult(passed=True)
        assert gate.check_results == ()
        assert gate.failed_checks == ()
        assert gate.skipped_checks == ()
        assert gate.architecture == "monolithic"
        assert gate.level == CheckLevel.TASK

    def test_level_defaults_to_task(self) -> None:
        from specforge.core.quality_models import CheckLevel, QualityGateResult

        gate = QualityGateResult(passed=False)
        assert gate.level is CheckLevel.TASK


class TestFunctionInfo:
    """FunctionInfo — AST analysis result for a function."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import FunctionInfo

        info = FunctionInfo(
            name="parse",
            file_path="parser.py",
            start_line=1,
            end_line=10,
            line_count=10,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            info.name = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        from specforge.core.quality_models import FunctionInfo

        info = FunctionInfo(
            name="parse",
            file_path="parser.py",
            start_line=1,
            end_line=10,
            line_count=10,
        )
        assert info.name == "parse"
        assert info.file_path == "parser.py"
        assert info.start_line == 1
        assert info.end_line == 10
        assert info.line_count == 10


class TestClassInfo:
    """ClassInfo — AST analysis result for a class."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import ClassInfo

        info = ClassInfo(
            name="Parser",
            file_path="parser.py",
            start_line=1,
            end_line=50,
            line_count=50,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            info.name = "Other"  # type: ignore[misc]


class TestFixAttempt:
    """FixAttempt — record of a single auto-fix iteration."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import ErrorCategory, FixAttempt

        attempt = FixAttempt(attempt_number=1, category=ErrorCategory.SYNTAX)
        with pytest.raises(dataclasses.FrozenInstanceError):
            attempt.reverted = True  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.quality_models import ErrorCategory, FixAttempt

        attempt = FixAttempt(attempt_number=1, category=ErrorCategory.LINT)
        assert attempt.fix_prompt == ""
        assert attempt.files_changed == ()
        assert attempt.result is None
        assert attempt.reverted is False
        assert attempt.revert_reason == ""


class TestDiagnosticReport:
    """DiagnosticReport — escalation document when auto-fix exhausts."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import DiagnosticReport, QualityGateResult

        gate = QualityGateResult(passed=False)
        report = DiagnosticReport(task_id="T001", original_error=gate)
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.task_id = "T002"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.quality_models import DiagnosticReport, QualityGateResult

        gate = QualityGateResult(passed=False)
        report = DiagnosticReport(task_id="T001", original_error=gate)
        assert report.attempts == ()
        assert report.still_failing == ()
        assert report.suggested_steps == ()
        assert report.created_at == ""


class TestQualityReport:
    """QualityReport — persistent JSON report after each gate run."""

    def test_frozen(self) -> None:
        from specforge.core.quality_models import QualityGateResult, QualityReport

        gate = QualityGateResult(passed=True)
        report = QualityReport(
            schema_version="1.0",
            service_slug="auth",
            architecture="monolithic",
            level="task",
            gate_result=gate,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.schema_version = "2.0"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from specforge.core.quality_models import QualityGateResult, QualityReport

        gate = QualityGateResult(passed=True)
        report = QualityReport(
            schema_version="1.0",
            service_slug="auth",
            architecture="monolithic",
            level="task",
            gate_result=gate,
        )
        assert report.task_id is None
        assert report.fix_attempts == ()
        assert report.diagnostic is None
        assert report.timestamp == ""

    def test_schema_version_present(self) -> None:
        from specforge.core.quality_models import QualityGateResult, QualityReport

        gate = QualityGateResult(passed=True)
        report = QualityReport(
            schema_version="1.0",
            service_slug="auth",
            architecture="monolithic",
            level="task",
            gate_result=gate,
        )
        assert report.schema_version == "1.0"
