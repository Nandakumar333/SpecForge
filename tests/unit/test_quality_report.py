"""Unit tests for quality_report.py — JSON persistence round-trip."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ContractAttribution,
    DiagnosticReport,
    ErrorCategory,
    ErrorDetail,
    FixAttempt,
    QualityGateResult,
    QualityReport,
)
from specforge.core.quality_report import REPORT_FILENAME, read_report, write_report


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_check_result(
    name: str = "lint",
    passed: bool = True,
    **kwargs,
) -> CheckResult:
    return CheckResult(
        checker_name=name,
        passed=passed,
        category=kwargs.get("category", ErrorCategory.LINT),
        output=kwargs.get("output", "ok"),
        error_details=kwargs.get("error_details", ()),
        skipped=kwargs.get("skipped", False),
        skip_reason=kwargs.get("skip_reason", ""),
        attribution=kwargs.get("attribution"),
    )


def _make_gate_result(**kwargs) -> QualityGateResult:
    cr = _make_check_result()
    return QualityGateResult(
        passed=kwargs.get("passed", True),
        check_results=kwargs.get("check_results", (cr,)),
        failed_checks=kwargs.get("failed_checks", ()),
        skipped_checks=kwargs.get("skipped_checks", ()),
        architecture=kwargs.get("architecture", "monolithic"),
        level=kwargs.get("level", CheckLevel.TASK),
    )


def _make_report(**kwargs) -> QualityReport:
    return QualityReport(
        schema_version=kwargs.get("schema_version", "1.0.0"),
        service_slug=kwargs.get("service_slug", "auth-svc"),
        architecture=kwargs.get("architecture", "monolithic"),
        level=kwargs.get("level", "task"),
        gate_result=kwargs.get("gate_result", _make_gate_result()),
        task_id=kwargs.get("task_id", "T001"),
        fix_attempts=kwargs.get("fix_attempts", ()),
        diagnostic=kwargs.get("diagnostic"),
        timestamp=kwargs.get("timestamp", "2025-01-01T00:00:00Z"),
    )


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------


class TestWriteReport:
    """write_report creates a valid JSON file."""

    def test_creates_json_file(self, tmp_path: Path) -> None:
        report = _make_report()
        result = write_report(report, tmp_path)
        assert result.ok
        path = result.value
        assert path.name == REPORT_FILENAME
        assert path.exists()

    def test_json_is_valid(self, tmp_path: Path) -> None:
        report = _make_report()
        write_report(report, tmp_path)
        data = json.loads((tmp_path / REPORT_FILENAME).read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_json_contains_schema_version(self, tmp_path: Path) -> None:
        report = _make_report(schema_version="2.0.0")
        write_report(report, tmp_path)
        data = json.loads((tmp_path / REPORT_FILENAME).read_text(encoding="utf-8"))
        assert data["schema_version"] == "2.0.0"

    def test_overwrites_on_subsequent_writes(self, tmp_path: Path) -> None:
        write_report(_make_report(task_id="T001"), tmp_path)
        write_report(_make_report(task_id="T002"), tmp_path)
        data = json.loads((tmp_path / REPORT_FILENAME).read_text(encoding="utf-8"))
        assert data["task_id"] == "T002"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        result = write_report(_make_report(), nested)
        assert result.ok
        assert result.value.exists()


# ---------------------------------------------------------------------------
# read_report
# ---------------------------------------------------------------------------


class TestReadReport:
    """read_report parses JSON back to QualityReport."""

    def test_missing_file_returns_ok_none(self, tmp_path: Path) -> None:
        result = read_report(tmp_path / "nonexistent.json")
        assert result.ok
        assert result.value is None

    def test_invalid_json_returns_err(self, tmp_path: Path) -> None:
        bad = tmp_path / REPORT_FILENAME
        bad.write_text("{not valid json", encoding="utf-8")
        result = read_report(bad)
        assert not result.ok
        assert "Failed to read report" in result.error

    def test_parses_valid_json(self, tmp_path: Path) -> None:
        report = _make_report()
        write_report(report, tmp_path)
        result = read_report(tmp_path / REPORT_FILENAME)
        assert result.ok
        assert isinstance(result.value, QualityReport)
        assert result.value.service_slug == "auth-svc"


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """write → read returns equivalent data."""

    def test_simple_round_trip(self, tmp_path: Path) -> None:
        original = _make_report()
        write_report(original, tmp_path)
        result = read_report(tmp_path / REPORT_FILENAME)
        assert result.ok
        restored = result.value
        assert restored.schema_version == original.schema_version
        assert restored.service_slug == original.service_slug
        assert restored.architecture == original.architecture
        assert restored.gate_result.passed == original.gate_result.passed
        assert len(restored.gate_result.check_results) == len(
            original.gate_result.check_results,
        )

    def test_round_trip_with_error_details(self, tmp_path: Path) -> None:
        ed = ErrorDetail(
            file_path="src/main.py",
            line_number=42,
            column=5,
            code="E001",
            message="unused import",
            context="import os",
        )
        cr = _make_check_result(
            passed=False,
            error_details=(ed,),
        )
        gr = _make_gate_result(
            passed=False,
            check_results=(cr,),
            failed_checks=("lint",),
        )
        report = _make_report(gate_result=gr)
        write_report(report, tmp_path)
        result = read_report(tmp_path / REPORT_FILENAME)
        assert result.ok
        restored_ed = result.value.gate_result.check_results[0].error_details[0]
        assert restored_ed.file_path == "src/main.py"
        assert restored_ed.line_number == 42
        assert restored_ed.code == "E001"

    def test_round_trip_with_fix_attempts(self, tmp_path: Path) -> None:
        fa = FixAttempt(
            attempt_number=1,
            category=ErrorCategory.LINT,
            fix_prompt="fix the lint",
            files_changed=("src/a.py",),
            reverted=False,
        )
        report = _make_report(fix_attempts=(fa,))
        write_report(report, tmp_path)
        result = read_report(tmp_path / REPORT_FILENAME)
        assert result.ok
        restored_fa = result.value.fix_attempts[0]
        assert restored_fa.attempt_number == 1
        assert restored_fa.category == ErrorCategory.LINT

    def test_round_trip_with_diagnostic(self, tmp_path: Path) -> None:
        diag = DiagnosticReport(
            task_id="T005",
            original_error=_make_gate_result(passed=False),
            still_failing=("lint",),
            suggested_steps=("Run ruff --fix",),
            created_at="2025-01-01T00:00:00Z",
        )
        report = _make_report(diagnostic=diag)
        write_report(report, tmp_path)
        result = read_report(tmp_path / REPORT_FILENAME)
        assert result.ok
        restored_diag = result.value.diagnostic
        assert restored_diag is not None
        assert restored_diag.task_id == "T005"
        assert restored_diag.still_failing == ("lint",)

    def test_round_trip_with_attribution(self, tmp_path: Path) -> None:
        cr = _make_check_result(
            name="contract",
            category=ErrorCategory.CONTRACT,
            attribution=ContractAttribution.CONSUMER,
        )
        gr = _make_gate_result(check_results=(cr,))
        report = _make_report(gate_result=gr)
        write_report(report, tmp_path)
        result = read_report(tmp_path / REPORT_FILENAME)
        assert result.ok
        restored_cr = result.value.gate_result.check_results[0]
        assert restored_cr.attribution == ContractAttribution.CONSUMER
