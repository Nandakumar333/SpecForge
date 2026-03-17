"""Unit tests for quality_checker.py — thin wrapper for build/lint/test."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


class TestQualityCheckerCheck:
    """QualityChecker.check() runs build + ruff + pytest."""

    def test_all_pass_returns_passed(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import QualityChecker

        checker = QualityChecker(tmp_path, "ledger-service")
        with patch("specforge.core.quality_checker._run_command") as mock_run:
            mock_run.return_value = (0, "ok", "")
            result = checker.check([tmp_path / "src" / "main.py"])

        assert result.ok
        assert result.value.passed is True
        assert result.value.failed_checks == ()

    def test_lint_failure_returns_failed(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import QualityChecker

        checker = QualityChecker(tmp_path, "ledger-service")
        returns = [
            (0, "build ok", ""),   # build passes
            (1, "", "E501 line too long"),  # ruff fails
            (0, "tests ok", ""),   # pytest passes
        ]
        with patch("specforge.core.quality_checker._run_command", side_effect=returns):
            result = checker.check([tmp_path / "src" / "main.py"])

        assert result.ok
        assert result.value.passed is False
        assert "lint" in result.value.failed_checks

    def test_test_failure_returns_failed(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import QualityChecker

        checker = QualityChecker(tmp_path, "ledger-service")
        returns = [
            (0, "build ok", ""),
            (0, "lint ok", ""),
            (1, "", "FAILED test_user.py::test_create"),
        ]
        with patch("specforge.core.quality_checker._run_command", side_effect=returns):
            result = checker.check([tmp_path / "src" / "main.py"])

        assert result.ok
        assert result.value.passed is False
        assert "test" in result.value.failed_checks

    def test_no_build_command_is_noop(self, tmp_path: Path) -> None:
        from specforge.core.quality_checker import QualityChecker

        checker = QualityChecker(tmp_path, "ledger-service")
        returns = [
            (0, "", ""),  # build no-op
            (0, "lint ok", ""),
            (0, "tests ok", ""),
        ]
        with patch("specforge.core.quality_checker._run_command", side_effect=returns):
            result = checker.check([])

        assert result.ok
        assert result.value.passed is True


class TestDetectRegression:
    """detect_regression finds new failures not in original error set."""

    def test_new_failure_is_regression(self) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.quality_checker import QualityChecker

        before = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a.py::test_one",
            failed_checks=("test",),
        )
        after = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a.py::test_one\nFAILED test_b.py::test_two",
            failed_checks=("test",),
        )
        assert QualityChecker.detect_regression(before, after) is True

    def test_same_failures_not_regression(self) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.quality_checker import QualityChecker

        before = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a.py::test_one",
            failed_checks=("test",),
        )
        after = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a.py::test_one",
            failed_checks=("test",),
        )
        assert QualityChecker.detect_regression(before, after) is False

    def test_fewer_failures_not_regression(self) -> None:
        from specforge.core.executor_models import QualityCheckResult
        from specforge.core.quality_checker import QualityChecker

        before = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a.py::test_one\nFAILED test_b.py::test_two",
            failed_checks=("test",),
        )
        after = QualityCheckResult(
            passed=False, build_output="", lint_output="",
            test_output="FAILED test_a.py::test_one",
            failed_checks=("test",),
        )
        assert QualityChecker.detect_regression(before, after) is False
