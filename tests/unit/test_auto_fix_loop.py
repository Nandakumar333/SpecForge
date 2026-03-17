"""Tests for AutoFixLoop — error → fix prompt → retry → regression detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.auto_fix_loop import AutoFixLoop
from specforge.core.executor_models import ImplementPrompt, QualityCheckResult
from specforge.core.result import Err, Ok


def _make_prompt(desc: str = "implement foo") -> ImplementPrompt:
    return ImplementPrompt(
        system_context="ctx",
        task_description=desc,
        file_hints=("src/foo.py",),
    )


def _make_qc(passed: bool, failed: tuple = (), test_out: str = "") -> QualityCheckResult:
    return QualityCheckResult(
        passed=passed,
        build_output="",
        lint_output="",
        test_output=test_out,
        failed_checks=failed,
    )


class TestAutoFixLoopFix:
    """Tests for AutoFixLoop.fix()."""

    def test_fix_succeeds_on_first_retry(self) -> None:
        runner = MagicMock()
        checker = MagicMock()

        runner.run.return_value = Ok([Path("src/foo.py")])
        checker.check.return_value = Ok(_make_qc(passed=True))

        loop = AutoFixLoop(runner, checker, max_attempts=3)
        original_error = _make_qc(passed=False, failed=("test",), test_out="FAILED test_a")
        result = loop.fix(
            _make_prompt(), original_error,
            [Path("src/foo.py")], "prompt-display",
        )

        assert result.ok
        assert len(result.value) >= 1  # at least the fix files

    def test_fix_exhausts_max_attempts(self) -> None:
        runner = MagicMock()
        checker = MagicMock()

        runner.run.return_value = Ok([Path("src/foo.py")])
        checker.check.return_value = Ok(_make_qc(
            passed=False, failed=("test",), test_out="FAILED test_a",
        ))

        loop = AutoFixLoop(runner, checker, max_attempts=3)
        original_error = _make_qc(passed=False, failed=("test",), test_out="FAILED test_a")
        result = loop.fix(
            _make_prompt(), original_error,
            [Path("src/foo.py")], "prompt-display",
        )

        assert not result.ok
        assert "3 attempts" in result.error
        assert runner.run.call_count == 3

    def test_fix_detects_regression_and_reverts(self) -> None:
        runner = MagicMock()
        checker = MagicMock()

        runner.run.return_value = Ok([Path("src/foo.py")])
        # First attempt: regression (new failure)
        checker.check.side_effect = [
            Ok(_make_qc(
                passed=False, failed=("test",),
                test_out="FAILED test_a\nFAILED test_b",
            )),
            # Second attempt: passes
            Ok(_make_qc(passed=True)),
        ]

        with patch("specforge.core.auto_fix_loop._git_checkout_files") as mock_checkout:
            loop = AutoFixLoop(runner, checker, max_attempts=3)
            original_error = _make_qc(
                passed=False, failed=("test",), test_out="FAILED test_a",
            )
            result = loop.fix(
                _make_prompt(), original_error,
                [Path("src/foo.py")], "prompt-display",
            )

            assert result.ok
            mock_checkout.assert_called_once()

    def test_fix_returns_err_when_runner_fails(self) -> None:
        runner = MagicMock()
        checker = MagicMock()

        runner.run.return_value = Err("user rejected")

        loop = AutoFixLoop(runner, checker, max_attempts=3)
        original_error = _make_qc(passed=False, failed=("test",))
        result = loop.fix(
            _make_prompt(), original_error,
            [Path("src/foo.py")], "prompt-display",
        )

        assert not result.ok
        assert "user rejected" in result.error

    def test_fix_passes_updated_error_to_next_attempt(self) -> None:
        runner = MagicMock()
        checker = MagicMock()

        runner.run.return_value = Ok([Path("src/foo.py")])
        # Both attempts fail with different errors
        checker.check.side_effect = [
            Ok(_make_qc(passed=False, failed=("test",), test_out="FAILED test_x")),
            Ok(_make_qc(passed=False, failed=("test",), test_out="FAILED test_y")),
            Ok(_make_qc(passed=False, failed=("test",), test_out="FAILED test_z")),
        ]

        loop = AutoFixLoop(runner, checker, max_attempts=3)
        original_error = _make_qc(passed=False, failed=("test",), test_out="FAILED test_a")
        loop.fix(
            _make_prompt(), original_error,
            [Path("src/foo.py")], "prompt-display",
        )

        # Each call to runner.run should get an updated prompt with prior error
        calls = runner.run.call_args_list
        assert len(calls) == 3
        # Second call's prompt should reference first attempt's error
        second_prompt = calls[1][0][0]
        assert "FAILED test_x" in second_prompt.task_description
