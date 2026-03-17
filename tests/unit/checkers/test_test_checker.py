"""Tests for TestChecker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.checkers.test_checker import TestChecker, _parse_failed_tests
from specforge.core.quality_models import CheckLevel, ErrorCategory
from specforge.core.result import Err, Ok


class TestTestCheckerProperties:
    """Property tests for TestChecker."""

    def test_name(self) -> None:
        checker = TestChecker()
        assert checker.name == "test"

    def test_category(self) -> None:
        checker = TestChecker()
        assert checker.category == ErrorCategory.LOGIC

    def test_levels(self) -> None:
        checker = TestChecker()
        assert checker.levels == (CheckLevel.TASK,)

    def test_is_applicable_all(self) -> None:
        checker = TestChecker()
        assert checker.is_applicable("monolith") is True
        assert checker.is_applicable("microservice") is True
        assert checker.is_applicable("anything") is True


class TestTestCheckerCheck:
    """Check method tests for TestChecker."""

    @patch("specforge.core.checkers.test_checker._run_test_command")
    def test_passing_tests_return_passed(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="5 passed in 0.5s\n",
            stderr="",
        )
        checker = TestChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is True
        assert result.value.error_details == ()

    @patch("specforge.core.checkers.test_checker._run_test_command")
    def test_failing_tests_return_logic_category(
        self, mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="FAILED tests/test_foo.py::test_bar - AssertionError\n1 failed\n",
            stderr="",
        )
        checker = TestChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is False
        assert result.value.category == ErrorCategory.LOGIC
        assert len(result.value.error_details) == 1
        assert "test_bar" in result.value.error_details[0].file_path

    @patch("specforge.core.checkers.test_checker._run_test_command")
    def test_multiple_failures_parsed(self, mock_run: MagicMock) -> None:
        stdout = (
            "FAILED tests/test_a.py::test_one - assert\n"
            "FAILED tests/test_b.py::test_two - assert\n"
            "2 failed\n"
        )
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=stdout, stderr="",
        )
        checker = TestChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert len(result.value.error_details) == 2

    @patch("specforge.core.checkers.test_checker._run_test_command")
    def test_timeout_returns_err(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="", timeout=300)
        checker = TestChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Err)
        assert "timed out" in result.error

    @patch("specforge.core.checkers.test_checker._run_test_command")
    def test_missing_interpreter_returns_err(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        checker = TestChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Err)
        assert "not found" in result.error


class TestParseFailedTests:
    """Tests for _parse_failed_tests helper."""

    def test_parses_failed_lines(self) -> None:
        output = "FAILED tests/test_foo.py::test_bar - AssertionError\n"
        details = _parse_failed_tests(output)
        assert len(details) == 1
        assert details[0].file_path == "tests/test_foo.py::test_bar"

    def test_no_failures(self) -> None:
        assert _parse_failed_tests("5 passed in 0.5s\n") == ()

    def test_multiple_failures(self) -> None:
        output = (
            "FAILED a::b\n"
            "FAILED c::d\n"
        )
        details = _parse_failed_tests(output)
        assert len(details) == 2

    def test_empty_output(self) -> None:
        assert _parse_failed_tests("") == ()
