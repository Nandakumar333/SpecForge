"""QualityReport — JSON persistence for quality gate results."""

from __future__ import annotations

import json
import logging
from pathlib import Path

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
from specforge.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)
REPORT_FILENAME = ".quality-report.json"


def write_report(report: QualityReport, output_dir: Path) -> Result[Path, str]:
    """Serialize QualityReport to JSON file."""
    path = output_dir / REPORT_FILENAME
    try:
        data = _serialize_report(report)
        output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return Ok(path)
    except OSError as exc:
        return Err(f"Failed to write report: {exc}")


def read_report(path: Path) -> Result[QualityReport | None, str]:
    """Deserialize QualityReport from JSON file. Returns None if missing."""
    if not path.exists():
        return Ok(None)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Ok(_deserialize_report(data))
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        return Err(f"Failed to read report: {exc}")


# -- Serialization helpers ---------------------------------------------------


def _serialize_report(report: QualityReport) -> dict:
    """Convert a QualityReport dataclass to a JSON-safe dict."""
    return {
        "schema_version": report.schema_version,
        "service_slug": report.service_slug,
        "architecture": report.architecture,
        "level": report.level,
        "task_id": report.task_id,
        "timestamp": report.timestamp,
        "gate_result": _serialize_gate_result(report.gate_result),
        "fix_attempts": [_serialize_fix_attempt(a) for a in report.fix_attempts],
        "diagnostic": _serialize_diagnostic(report.diagnostic),
    }


def _serialize_gate_result(gr: QualityGateResult) -> dict:
    """Convert QualityGateResult to dict."""
    return {
        "passed": gr.passed,
        "failed_checks": list(gr.failed_checks),
        "skipped_checks": list(gr.skipped_checks),
        "architecture": gr.architecture,
        "level": gr.level.value,
        "check_results": [_serialize_check_result(r) for r in gr.check_results],
    }


def _serialize_check_result(cr: CheckResult) -> dict:
    """Convert CheckResult to dict."""
    return {
        "checker_name": cr.checker_name,
        "passed": cr.passed,
        "category": cr.category.value,
        "output": cr.output,
        "skipped": cr.skipped,
        "skip_reason": cr.skip_reason,
        "attribution": cr.attribution.value if cr.attribution else None,
        "error_details": [_serialize_error_detail(e) for e in cr.error_details],
    }


def _serialize_error_detail(ed: ErrorDetail) -> dict:
    """Convert ErrorDetail to dict."""
    return {
        "file_path": ed.file_path,
        "line_number": ed.line_number,
        "column": ed.column,
        "code": ed.code,
        "message": ed.message,
        "context": ed.context,
    }


def _serialize_fix_attempt(fa: FixAttempt) -> dict:
    """Convert FixAttempt to dict."""
    return {
        "attempt_number": fa.attempt_number,
        "category": fa.category.value,
        "fix_prompt": fa.fix_prompt,
        "files_changed": list(fa.files_changed),
        "result": _serialize_gate_result(fa.result) if fa.result else None,
        "reverted": fa.reverted,
        "revert_reason": fa.revert_reason,
    }


def _serialize_diagnostic(diag: DiagnosticReport | None) -> dict | None:
    """Convert DiagnosticReport to dict, or None."""
    if diag is None:
        return None
    return {
        "task_id": diag.task_id,
        "original_error": _serialize_gate_result(diag.original_error),
        "attempts": [_serialize_fix_attempt(a) for a in diag.attempts],
        "still_failing": list(diag.still_failing),
        "suggested_steps": list(diag.suggested_steps),
        "created_at": diag.created_at,
    }


# -- Deserialization helpers -------------------------------------------------


def _deserialize_report(data: dict) -> QualityReport:
    """Convert a dict back to a QualityReport dataclass."""
    return QualityReport(
        schema_version=data["schema_version"],
        service_slug=data["service_slug"],
        architecture=data["architecture"],
        level=data["level"],
        task_id=data.get("task_id"),
        timestamp=data.get("timestamp", ""),
        gate_result=_deserialize_gate_result(data["gate_result"]),
        fix_attempts=tuple(
            _deserialize_fix_attempt(a) for a in data.get("fix_attempts", [])
        ),
        diagnostic=_deserialize_diagnostic(data.get("diagnostic")),
    )


def _deserialize_gate_result(data: dict) -> QualityGateResult:
    """Convert a dict back to QualityGateResult."""
    return QualityGateResult(
        passed=data["passed"],
        failed_checks=tuple(data.get("failed_checks", ())),
        skipped_checks=tuple(data.get("skipped_checks", ())),
        architecture=data.get("architecture", "monolithic"),
        level=CheckLevel(data["level"]),
        check_results=tuple(
            _deserialize_check_result(r) for r in data.get("check_results", [])
        ),
    )


def _deserialize_check_result(data: dict) -> CheckResult:
    """Convert a dict back to CheckResult."""
    attr = data.get("attribution")
    return CheckResult(
        checker_name=data["checker_name"],
        passed=data["passed"],
        category=ErrorCategory(data["category"]),
        output=data.get("output", ""),
        skipped=data.get("skipped", False),
        skip_reason=data.get("skip_reason", ""),
        attribution=ContractAttribution(attr) if attr else None,
        error_details=tuple(
            _deserialize_error_detail(e) for e in data.get("error_details", [])
        ),
    )


def _deserialize_error_detail(data: dict) -> ErrorDetail:
    """Convert a dict back to ErrorDetail."""
    return ErrorDetail(
        file_path=data["file_path"],
        line_number=data.get("line_number"),
        column=data.get("column"),
        code=data.get("code", ""),
        message=data.get("message", ""),
        context=data.get("context", ""),
    )


def _deserialize_fix_attempt(data: dict) -> FixAttempt:
    """Convert a dict back to FixAttempt."""
    result_data = data.get("result")
    return FixAttempt(
        attempt_number=data["attempt_number"],
        category=ErrorCategory(data["category"]),
        fix_prompt=data.get("fix_prompt", ""),
        files_changed=tuple(data.get("files_changed", ())),
        result=_deserialize_gate_result(result_data) if result_data else None,
        reverted=data.get("reverted", False),
        revert_reason=data.get("revert_reason", ""),
    )


def _deserialize_diagnostic(data: dict | None) -> DiagnosticReport | None:
    """Convert a dict back to DiagnosticReport, or None."""
    if data is None:
        return None
    return DiagnosticReport(
        task_id=data["task_id"],
        original_error=_deserialize_gate_result(data["original_error"]),
        attempts=tuple(
            _deserialize_fix_attempt(a) for a in data.get("attempts", [])
        ),
        still_failing=tuple(data.get("still_failing", ())),
        suggested_steps=tuple(data.get("suggested_steps", ())),
        created_at=data.get("created_at", ""),
    )
