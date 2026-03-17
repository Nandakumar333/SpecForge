"""Tests for CoverageChecker."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.checkers.coverage_checker import (
    CoverageChecker,
    _parse_coverage_json,
)
from specforge.core.quality_models import CheckLevel, ErrorCategory
from specforge.core.result import Err, Ok


class TestCoverageCheckerProperties:
    """Property tests for CoverageChecker."""

    def test_name(self) -> None:
        checker = CoverageChecker()
        assert checker.name == "coverage"

    def test_category(self) -> None:
        checker = CoverageChecker()
        assert checker.category == ErrorCategory.COVERAGE

    def test_levels(self) -> None:
        checker = CoverageChecker()
        assert checker.levels == (CheckLevel.TASK,)

    def test_is_applicable_all(self) -> None:
        checker = CoverageChecker()
        assert checker.is_applicable("monolith") is True
        assert checker.is_applicable("microservice") is True


class TestCoverageCheckerCheck:
    """Check method tests for CoverageChecker."""

    def test_no_threshold_skips(self) -> None:
        checker = CoverageChecker(threshold=None)
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.skipped is True
        assert result.value.skip_reason == "No coverage threshold configured"

    @patch("specforge.core.checkers.coverage_checker._parse_coverage_json")
    @patch("specforge.core.checkers.coverage_checker._run_coverage_command")
    def test_above_threshold_passes(
        self, mock_run: MagicMock, mock_parse: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        mock_parse.return_value = 95.0
        checker = CoverageChecker(threshold=80.0)
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is True
        assert "95.0%" in result.value.output

    @patch("specforge.core.checkers.coverage_checker._parse_coverage_json")
    @patch("specforge.core.checkers.coverage_checker._run_coverage_command")
    def test_below_threshold_fails(
        self, mock_run: MagicMock, mock_parse: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        mock_parse.return_value = 50.0
        checker = CoverageChecker(threshold=80.0)
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is False
        assert result.value.category == ErrorCategory.COVERAGE
        assert len(result.value.error_details) == 1
        assert "50.0%" in result.value.error_details[0].message

    @patch("specforge.core.checkers.coverage_checker._parse_coverage_json")
    @patch("specforge.core.checkers.coverage_checker._run_coverage_command")
    def test_exact_threshold_passes(
        self, mock_run: MagicMock, mock_parse: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        mock_parse.return_value = 80.0
        checker = CoverageChecker(threshold=80.0)
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Ok)
        assert result.value.passed is True

    @patch("specforge.core.checkers.coverage_checker._run_coverage_command")
    def test_timeout_returns_err(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="", timeout=600)
        checker = CoverageChecker(threshold=80.0)
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Err)
        assert "timed out" in result.error

    @patch("specforge.core.checkers.coverage_checker._run_coverage_command")
    def test_missing_interpreter_returns_err(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        checker = CoverageChecker(threshold=80.0)
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Err)
        assert "not found" in result.error

    @patch("specforge.core.checkers.coverage_checker._parse_coverage_json")
    @patch("specforge.core.checkers.coverage_checker._run_coverage_command")
    def test_unparseable_report_returns_err(
        self, mock_run: MagicMock, mock_parse: MagicMock,
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        mock_parse.return_value = None
        checker = CoverageChecker(threshold=80.0)
        result = checker.check([Path("app.py")], None)
        assert isinstance(result, Err)
        assert "parse" in result.error.lower()


class TestParseCoverageJson:
    """Tests for _parse_coverage_json helper."""

    def test_valid_json(self, tmp_path: Path) -> None:
        data = {"totals": {"percent_covered": 87.5}}
        report = tmp_path / "coverage.json"
        report.write_text(json.dumps(data), encoding="utf-8")
        assert _parse_coverage_json(report) == 87.5

    def test_missing_file(self, tmp_path: Path) -> None:
        assert _parse_coverage_json(tmp_path / "nope.json") is None

    def test_invalid_json(self, tmp_path: Path) -> None:
        report = tmp_path / "coverage.json"
        report.write_text("not json", encoding="utf-8")
        assert _parse_coverage_json(report) is None

    def test_missing_key(self, tmp_path: Path) -> None:
        report = tmp_path / "coverage.json"
        report.write_text(json.dumps({"totals": {}}), encoding="utf-8")
        assert _parse_coverage_json(report) is None
