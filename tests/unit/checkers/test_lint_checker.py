"""Tests for LintChecker."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.checkers.lint_checker import (
    LintChecker,
    _parse_ruff_json,
    _ruff_item_to_detail,
)
from specforge.core.quality_models import CheckLevel, ErrorCategory
from specforge.core.result import Err, Ok


def _ruff_output(items: list[dict]) -> str:
    """Helper to produce ruff-style JSON output."""
    return json.dumps(items)


class TestLintCheckerProperties:
    """Property tests for LintChecker."""

    def test_name(self) -> None:
        checker = LintChecker()
        assert checker.name == "lint"

    def test_category(self) -> None:
        checker = LintChecker()
        assert checker.category == ErrorCategory.LINT

    def test_levels(self) -> None:
        checker = LintChecker()
        assert checker.levels == (CheckLevel.TASK,)

    def test_is_applicable_all(self) -> None:
        checker = LintChecker()
        assert checker.is_applicable("monolith") is True
        assert checker.is_applicable("microservice") is True


class TestLintCheckerCheck:
    """Check method tests for LintChecker."""

    def test_no_python_files_skips(self) -> None:
        checker = LintChecker()
        result = checker.check([Path("readme.md"), Path("data.csv")], None)
        assert isinstance(result, Ok)
        assert result.value.skipped is True
        assert result.value.skip_reason == "No Python files"

    @patch("specforge.core.checkers.lint_checker._run_lint_command")
    def test_clean_returns_passed(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr="",
        )
        checker = LintChecker()
        result = checker.check([Path("clean.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is True
        assert result.value.error_details == ()

    @patch("specforge.core.checkers.lint_checker._run_lint_command")
    def test_violations_return_lint_category(self, mock_run: MagicMock) -> None:
        items = [
            {
                "filename": "bad.py",
                "location": {"row": 10, "column": 5},
                "code": "E501",
                "message": "Line too long",
            },
        ]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=_ruff_output(items), stderr="",
        )
        checker = LintChecker()
        result = checker.check([Path("bad.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is False
        assert result.value.category == ErrorCategory.LINT
        detail = result.value.error_details[0]
        assert detail.file_path == "bad.py"
        assert detail.line_number == 10
        assert detail.column == 5
        assert detail.code == "E501"
        assert detail.message == "Line too long"

    @patch("specforge.core.checkers.lint_checker._run_lint_command")
    def test_multiple_violations(self, mock_run: MagicMock) -> None:
        items = [
            {
                "filename": "a.py",
                "location": {"row": 1, "column": 1},
                "code": "E501",
                "message": "Line too long",
            },
            {
                "filename": "b.py",
                "location": {"row": 5, "column": 3},
                "code": "F401",
                "message": "Unused import",
            },
        ]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=_ruff_output(items), stderr="",
        )
        checker = LintChecker()
        result = checker.check([Path("a.py"), Path("b.py")], None)
        assert isinstance(result, Ok)
        assert len(result.value.error_details) == 2

    @patch("specforge.core.checkers.lint_checker._run_lint_command")
    def test_ruff_not_found_skips(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        checker = LintChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.skipped is True
        assert result.value.skip_reason == "ruff not found"

    @patch("specforge.core.checkers.lint_checker._run_lint_command")
    def test_timeout_returns_err(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="", timeout=300)
        checker = LintChecker()
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Err)
        assert "timed out" in result.error

    def test_empty_file_list_skips(self) -> None:
        checker = LintChecker()
        result = checker.check([], None)
        assert isinstance(result, Ok)
        assert result.value.skipped is True


class TestParseRuffJson:
    """Tests for _parse_ruff_json helper."""

    def test_valid_json(self) -> None:
        raw = json.dumps([
            {
                "filename": "x.py",
                "location": {"row": 1, "column": 2},
                "code": "E001",
                "message": "msg",
            },
        ])
        details = _parse_ruff_json(raw)
        assert len(details) == 1
        assert details[0].file_path == "x.py"

    def test_empty_list(self) -> None:
        assert _parse_ruff_json("[]") == ()

    def test_invalid_json(self) -> None:
        assert _parse_ruff_json("not json") == ()

    def test_non_list_json(self) -> None:
        assert _parse_ruff_json('{"key": "val"}') == ()


class TestRuffItemToDetail:
    """Tests for _ruff_item_to_detail helper."""

    def test_complete_item(self) -> None:
        item = {
            "filename": "f.py",
            "location": {"row": 42, "column": 8},
            "code": "W001",
            "message": "warning",
        }
        detail = _ruff_item_to_detail(item)
        assert detail.file_path == "f.py"
        assert detail.line_number == 42
        assert detail.column == 8
        assert detail.code == "W001"
        assert detail.message == "warning"

    def test_missing_fields(self) -> None:
        detail = _ruff_item_to_detail({})
        assert detail.file_path == "<unknown>"
        assert detail.line_number is None
        assert detail.code == ""
