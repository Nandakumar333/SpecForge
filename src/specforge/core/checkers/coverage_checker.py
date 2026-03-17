"""CoverageChecker — runs pytest with coverage and checks threshold."""

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

_COV_TIMEOUT = 600
_COV_REPORT = "coverage.json"


def _run_coverage_command(
    cmd: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with timeout and capture output."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_COV_TIMEOUT,
        cwd=cwd,
    )


def _parse_coverage_json(path: Path) -> float | None:
    """Read coverage.json and return total coverage percent."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return float(data["totals"]["percent_covered"])
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError):
        return None


class CoverageChecker:
    """Checks test coverage meets a configured threshold."""

    def __init__(self, threshold: float | None = None) -> None:
        self._threshold = threshold

    @property
    def name(self) -> str:
        return "coverage"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.COVERAGE

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
        """Run pytest --cov and compare coverage to threshold."""
        if self._threshold is None:
            return Ok(
                CheckResult(
                    checker_name=self.name,
                    passed=True,
                    category=self.category,
                    skipped=True,
                    skip_reason="No coverage threshold configured",
                ),
            )
        return self._run_coverage()

    def _run_coverage(self) -> Ok[CheckResult] | Err[str]:
        """Execute pytest with coverage collection."""
        cmd = [
            "python", "-m", "pytest",
            "--cov", f"--cov-report=json:{_COV_REPORT}",
        ]
        try:
            proc = _run_coverage_command(cmd)
        except subprocess.TimeoutExpired:
            return Err(f"Coverage timed out after {_COV_TIMEOUT}s")
        except FileNotFoundError:
            return Err("Python interpreter not found")

        return self._evaluate_coverage(proc)

    def _evaluate_coverage(
        self,
        proc: subprocess.CompletedProcess[str],
    ) -> Ok[CheckResult] | Err[str]:
        """Parse coverage JSON and compare against threshold."""
        cov_path = Path(_COV_REPORT)
        percent = _parse_coverage_json(cov_path)
        if percent is None:
            return Err("Failed to parse coverage report")

        assert self._threshold is not None  # guarded by caller
        passed = percent >= self._threshold
        output = f"Coverage: {percent:.1f}% (threshold: {self._threshold:.1f}%)"
        details = self._build_details(passed, percent)
        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=passed,
                category=self.category,
                output=output,
                error_details=details,
            ),
        )

    def _build_details(
        self,
        passed: bool,
        percent: float,
    ) -> tuple[ErrorDetail, ...]:
        """Build error details when coverage is below threshold."""
        if passed:
            return ()
        assert self._threshold is not None
        return (
            ErrorDetail(
                file_path="<coverage>",
                message=(
                    f"Coverage {percent:.1f}% is below "
                    f"threshold {self._threshold:.1f}%"
                ),
            ),
        )
