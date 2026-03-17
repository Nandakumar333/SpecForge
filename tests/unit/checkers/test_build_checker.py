"""Tests for BuildChecker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.checkers.build_checker import BuildChecker, _parse_compile_errors
from specforge.core.quality_models import CheckLevel, ErrorCategory
from specforge.core.result import Err, Ok


class TestBuildCheckerProperties:
    """Property tests for BuildChecker."""

    def test_name(self) -> None:
        checker = BuildChecker()
        assert checker.name == "build"

    def test_category(self) -> None:
        checker = BuildChecker()
        assert checker.category == ErrorCategory.SYNTAX

    def test_levels(self) -> None:
        checker = BuildChecker()
        assert checker.levels == (CheckLevel.TASK,)

    def test_is_applicable_all(self) -> None:
        checker = BuildChecker()
        assert checker.is_applicable("monolith") is True
        assert checker.is_applicable("microservice") is True
        assert checker.is_applicable("anything") is True


class TestBuildCheckerCheck:
    """Check method tests for BuildChecker."""

    def test_no_python_files_skips(self) -> None:
        checker = BuildChecker()
        result = checker.check([Path("readme.md")], None)
        assert isinstance(result, Ok)
        assert result.value.skipped is True
        assert result.value.passed is True

    @patch("specforge.core.checkers.build_checker._run_build_command")
    def test_success_returns_passed(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        checker = BuildChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is True

    @patch("specforge.core.checkers.build_checker._run_build_command")
    def test_failure_returns_syntax_category(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="SyntaxError: invalid syntax\n",
        )
        checker = BuildChecker()
        result = checker.check([Path("bad.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is False
        assert result.value.category == ErrorCategory.SYNTAX
        assert len(result.value.error_details) > 0

    @patch("specforge.core.checkers.build_checker._run_build_command")
    def test_timeout_returns_err(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="", timeout=300)
        checker = BuildChecker()
        result = checker.check([Path("slow.py")], None)
        assert isinstance(result, Err)
        assert "timed out" in result.error

    @patch("specforge.core.checkers.build_checker._run_build_command")
    def test_missing_interpreter_returns_err(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        checker = BuildChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Err)
        assert "not found" in result.error

    @patch("specforge.core.checkers.build_checker._run_build_command")
    def test_multiple_files(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        checker = BuildChecker()
        files = [Path("a.py"), Path("b.py"), Path("c.txt")]
        result = checker.check(files, None)
        assert isinstance(result, Ok)
        assert result.value.passed is True
        # c.txt is filtered out; only 2 .py files compiled
        assert mock_run.call_count == 2

    def test_empty_file_list(self) -> None:
        checker = BuildChecker()
        result = checker.check([], None)
        assert isinstance(result, Ok)
        assert result.value.skipped is True


class TestParseCompileErrors:
    """Tests for _parse_compile_errors helper."""

    def test_parses_stderr_lines(self) -> None:
        stderr = "line 1 error\nline 2 error\n"
        details = _parse_compile_errors(stderr)
        assert len(details) == 2
        assert details[0].message == "line 1 error"

    def test_empty_stderr(self) -> None:
        assert _parse_compile_errors("") == ()

    def test_blank_lines_skipped(self) -> None:
        stderr = "error one\n\n\nerror two\n"
        details = _parse_compile_errors(stderr)
        assert len(details) == 2
