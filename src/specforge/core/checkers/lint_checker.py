"""LintChecker — runs ruff check on changed Python files."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
    ErrorDetail,
)
from specforge.core.result import Err, Ok

logger = logging.getLogger(__name__)

_LINT_TIMEOUT = 300


def _run_lint_command(
    cmd: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with timeout and capture output."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_LINT_TIMEOUT,
        cwd=cwd,
    )


def _parse_ruff_json(raw: str) -> tuple[ErrorDetail, ...]:
    """Parse ruff JSON output into ErrorDetail tuples."""
    try:
        items = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ()
    if not isinstance(items, list):
        return ()
    return tuple(_ruff_item_to_detail(item) for item in items)


def _ruff_item_to_detail(item: dict) -> ErrorDetail:
    """Convert a single ruff JSON entry to ErrorDetail."""
    location = item.get("location", {})
    return ErrorDetail(
        file_path=item.get("filename", "<unknown>"),
        line_number=location.get("row"),
        column=location.get("column"),
        code=item.get("code", ""),
        message=item.get("message", ""),
    )


class LintChecker:
    """Runs ruff linter on changed Python files."""

    @property
    def name(self) -> str:
        return "lint"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.LINT

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return (CheckLevel.TASK,)

    def is_applicable(self, architecture: str) -> bool:
        return True

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]:
        """Run ruff check on changed .py files."""
        py_files = [f for f in changed_files if f.suffix == ".py"]
        if not py_files:
            return Ok(
                CheckResult(
                    checker_name=self.name,
                    passed=True,
                    category=self.category,
                    skipped=True,
                    skip_reason="No Python files",
                ),
            )
        return self._run_ruff(py_files)

    def _run_ruff(
        self,
        py_files: list[Path],
    ) -> Ok[CheckResult] | Err[str]:
        """Execute ruff and parse results."""
        cmd = [
            "ruff",
            "check",
            "--output-format=json",
            *[str(f) for f in py_files],
        ]
        try:
            proc = _run_lint_command(cmd)
        except FileNotFoundError:
            logger.warning("ruff binary not found; skipping lint check")
            return Ok(
                CheckResult(
                    checker_name=self.name,
                    passed=True,
                    category=self.category,
                    skipped=True,
                    skip_reason="ruff not found",
                ),
            )
        except subprocess.TimeoutExpired:
            return Err(f"Lint timed out after {_LINT_TIMEOUT}s")

        return self._build_result(proc)

    def _build_result(
        self,
        proc: subprocess.CompletedProcess[str],
    ) -> Ok[CheckResult] | Err[str]:
        """Build CheckResult from ruff process output."""
        details = _parse_ruff_json(proc.stdout)
        passed = proc.returncode == 0 and len(details) == 0
        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=passed,
                category=self.category,
                output=proc.stdout,
                error_details=details,
            ),
        )
