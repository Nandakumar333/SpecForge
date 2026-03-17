"""TestChecker — runs pytest on the project and reports failures."""

from __future__ import annotations

import logging
import re
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

_TEST_TIMEOUT = 300
_FAILED_RE = re.compile(r"FAILED\s+(\S+)")


def _run_test_command(
    cmd: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with timeout and capture output."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_TEST_TIMEOUT,
        cwd=cwd,
    )


def _parse_failed_tests(output: str) -> tuple[ErrorDetail, ...]:
    """Extract FAILED test names from pytest output."""
    matches = _FAILED_RE.findall(output)
    return tuple(
        ErrorDetail(file_path=name, message=f"Test failed: {name}")
        for name in matches
    )


class TestChecker:
    """Runs project test suite via pytest."""

    @property
    def name(self) -> str:
        return "test"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.LOGIC

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
        """Run pytest and report failures."""
        cmd = ["python", "-m", "pytest", "-x", "--tb=short", "-q"]
        try:
            proc = _run_test_command(cmd)
        except subprocess.TimeoutExpired:
            return Err(f"Tests timed out after {_TEST_TIMEOUT}s")
        except FileNotFoundError:
            return Err("Python interpreter not found")

        return self._build_result(proc)

    def _build_result(
        self,
        proc: subprocess.CompletedProcess[str],
    ) -> Ok[CheckResult] | Err[str]:
        """Build CheckResult from pytest process output."""
        combined = proc.stdout + proc.stderr
        details = _parse_failed_tests(combined)
        passed = proc.returncode == 0
        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=passed,
                category=self.category,
                output=combined,
                error_details=details,
            ),
        )
