"""Integration tests — QualityGate + AutoFixEngine + backward compat shims."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from specforge.core.result import Ok

# -----------------------------------------------------------------------
# Factory tests — create_quality_gate / create_auto_fix_engine
# -----------------------------------------------------------------------


class TestCreateQualityGate:
    """create_quality_gate() produces a working QualityGate."""

    def test_creates_gate_monolithic(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import create_quality_gate

        gate = create_quality_gate(tmp_path, "ledger", "monolithic")
        assert hasattr(gate, "run_task_checks")
        assert hasattr(gate, "run_service_checks")

    def test_creates_gate_microservice(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import create_quality_gate

        gate = create_quality_gate(tmp_path, "ledger", "microservice")
        assert hasattr(gate, "run_task_checks")

    def test_creates_gate_modular_monolith(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import create_quality_gate

        gate = create_quality_gate(tmp_path, "ledger", "modular-monolith")
        assert hasattr(gate, "run_task_checks")

    def test_default_architecture_monolithic(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import create_quality_gate

        gate = create_quality_gate(tmp_path, "ledger")
        assert gate._architecture == "monolithic"


class TestCreateAutoFixEngine:
    """create_auto_fix_engine() produces a working AutoFixEngine."""

    def test_creates_engine(self) -> None:
        from specforge.core.auto_fix_loop import create_auto_fix_engine

        engine = create_auto_fix_engine(
            task_runner=MagicMock(),
            quality_gate=MagicMock(),
            max_attempts=3,
        )
        assert hasattr(engine, "fix")
        assert hasattr(engine, "generate_diagnostic")

    def test_engine_max_attempts(self) -> None:
        from specforge.core.auto_fix_loop import create_auto_fix_engine

        engine = create_auto_fix_engine(
            task_runner=MagicMock(),
            quality_gate=MagicMock(),
            max_attempts=5,
        )
        assert engine._max == 5


# -----------------------------------------------------------------------
# Full pipeline test — gate → fix → diagnostic
# -----------------------------------------------------------------------


class TestQualityGatePipeline:
    """End-to-end: gate runs checkers, auto-fix retries, diagnostic renders."""

    def test_gate_runs_task_level_checkers(self, tmp_path: Path) -> None:
        """QualityGate runs applicable task-level checkers."""
        from specforge.core.quality_gate import QualityGate
        from specforge.core.quality_models import CheckLevel, CheckResult

        mock_checker = MagicMock()
        mock_checker.name = "mock-check"
        mock_checker.category.value = "lint"
        mock_checker.levels = (CheckLevel.TASK,)
        mock_checker.is_applicable.return_value = True
        from specforge.core.quality_models import ErrorCategory

        mock_checker.check.return_value = Ok(
            CheckResult(
                checker_name="mock-check",
                passed=True,
                category=ErrorCategory.LINT,
                output="all good",
            ),
        )

        gate = QualityGate(
            architecture="monolithic",
            project_root=tmp_path,
            service_slug="svc",
            checkers=(mock_checker,),
        )
        result = gate.run_task_checks([tmp_path / "f.py"], None)

        assert result.ok
        assert result.value.passed is True

    def test_gate_filters_microservice_checkers(self, tmp_path: Path) -> None:
        """Monolith gate skips microservice-only checkers."""
        from specforge.core.quality_gate import QualityGate
        from specforge.core.quality_models import CheckLevel

        micro_checker = MagicMock()
        micro_checker.name = "docker-build"
        micro_checker.category.value = "docker"
        micro_checker.levels = (CheckLevel.TASK,)
        micro_checker.is_applicable.return_value = False

        gate = QualityGate(
            architecture="monolithic",
            project_root=tmp_path,
            service_slug="svc",
            checkers=(micro_checker,),
        )
        result = gate.run_task_checks([tmp_path / "f.py"], None)

        assert result.ok
        assert result.value.passed is True
        micro_checker.check.assert_not_called()

    def test_autofix_engine_with_gate_result(self) -> None:
        """AutoFixEngine processes QualityGateResult from gate."""
        from specforge.core.auto_fix_engine import AutoFixEngine
        from specforge.core.quality_models import (
            CheckResult,
            ErrorCategory,
            ErrorDetail,
            QualityGateResult,
        )

        gate_result = QualityGateResult(
            passed=False,
            check_results=(
                CheckResult(
                    checker_name="lint",
                    passed=False,
                    output="E501 line too long",
                    category=ErrorCategory.LINT,
                    error_details=(
                        ErrorDetail(
                            file_path="src/foo.py",
                            line_number=10,
                            message="line too long",
                            code="E501",
                        ),
                    ),
                ),
            ),
            failed_checks=("lint",),
        )

        runner = MagicMock()
        runner.run.return_value = Ok([Path("src/foo.py")])

        gate_mock = MagicMock()
        # Fix succeeds on first recheck
        gate_mock.run_selective_checks.return_value = Ok(
            QualityGateResult(passed=True, check_results=(), failed_checks=()),
        )

        engine = AutoFixEngine(runner, gate_mock, max_attempts=3)

        from specforge.core.executor_models import ImplementPrompt

        prompt = ImplementPrompt(
            system_context="ctx",
            task_description="implement foo",
            file_hints=("src/foo.py",),
        )

        result = engine.fix(prompt, gate_result, [Path("src/foo.py")], "prompt-display")
        assert result.ok

    def test_diagnostic_report_rendering(self, tmp_path: Path) -> None:
        """DiagnosticReporter renders a readable markdown report."""
        from specforge.core.diagnostic_reporter import render_diagnostic
        from specforge.core.quality_models import (
            DiagnosticReport,
            ErrorCategory,
            FixAttempt,
            QualityGateResult,
        )

        gate_result = QualityGateResult(
            passed=False, check_results=(), failed_checks=("lint",),
        )
        report = DiagnosticReport(
            task_id="T001",
            original_error=gate_result,
            attempts=(
                FixAttempt(
                    attempt_number=1,
                    category=ErrorCategory.LINT,
                    fix_prompt="fix lint",
                    files_changed=("src/foo.py",),
                    result=gate_result,
                    reverted=False,
                    revert_reason="",
                ),
            ),
            still_failing=("lint",),
            suggested_steps=(
                "Run ruff check --fix to auto-fix what's possible",
            ),
            created_at="2025-01-01T00:00:00Z",
        )

        result = render_diagnostic(report, tmp_path / "reports")
        assert result.ok
        content = result.value.read_text(encoding="utf-8")
        assert "T001" in content
        assert "lint" in content
        assert "ruff" in content


# -----------------------------------------------------------------------
# Backward compat — existing Feature 009 interface preserved
# -----------------------------------------------------------------------


class TestBackwardCompatQualityChecker:
    """QualityChecker shim preserves Feature 009 interface."""

    def test_import_path_unchanged(self) -> None:
        from specforge.core.quality_checker import QualityChecker

        assert QualityChecker is not None

    def test_constructor_signature(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import QualityChecker

        checker = QualityChecker(tmp_path, "ledger-service")
        assert checker._root == tmp_path
        assert checker._slug == "ledger-service"

    def test_check_returns_quality_check_result(self, tmp_path: Path) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.quality_checker import QualityChecker

        checker = QualityChecker(tmp_path, "svc")
        with patch("specforge.core.quality_checker._run_command") as mock:
            mock.return_value = (0, "ok", "")
            result = checker.check([tmp_path / "f.py"])

        assert result.ok
        assert isinstance(result.value, QualityCheckResult)

    def test_detect_regression_static_method(self) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.quality_checker import QualityChecker

        before = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a", failed_checks=("test",),
        )
        after = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a\nFAILED test_b",
            failed_checks=("test",),
        )
        assert QualityChecker.detect_regression(before, after) is True


class TestBackwardCompatAutoFixLoop:
    """AutoFixLoop shim preserves Feature 009 interface."""

    def test_import_path_unchanged(self) -> None:
        from specforge.core.auto_fix_loop import AutoFixLoop

        assert AutoFixLoop is not None

    def test_constructor_signature(self) -> None:
        from specforge.core.auto_fix_loop import AutoFixLoop

        loop = AutoFixLoop(
            task_runner=MagicMock(),
            quality_checker=MagicMock(),
            max_attempts=3,
        )
        assert loop._max_attempts == 3

    def test_fix_returns_result(self) -> None:
        from specforge.core.auto_fix_loop import AutoFixLoop
        from specforge.core.executor_models import (
            ImplementPrompt,
            QualityCheckResult,
        )

        runner = MagicMock()
        checker = MagicMock()

        runner.run.return_value = Ok([Path("src/foo.py")])
        checker.check.return_value = Ok(
            QualityCheckResult(
                passed=True, build_output="", lint_output="",
                test_output="", failed_checks=(),
            ),
        )

        loop = AutoFixLoop(runner, checker, max_attempts=3)
        prompt = ImplementPrompt(
            system_context="ctx",
            task_description="fix",
            file_hints=("src/foo.py",),
        )
        error = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a", failed_checks=("test",),
        )

        result = loop.fix(prompt, error, [Path("src/foo.py")], "prompt-display")
        assert result.ok
