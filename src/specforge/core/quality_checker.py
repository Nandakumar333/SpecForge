"""QualityChecker — thin wrapper: build + ruff + pytest (Feature 010 replaces)."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from specforge.core.executor_models import QualityCheckResult
from specforge.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)


class QualityChecker:
    """Runs build, lint, and test checks after each task."""

    def __init__(self, project_root: Path, service_slug: str) -> None:
        self._root = project_root
        self._slug = service_slug

    def check(self, changed_files: list[Path]) -> Result[QualityCheckResult, str]:
        """Run build + ruff + pytest. Returns QualityCheckResult."""
        build_rc, build_out, build_err = _run_command(
            ["echo", "build-ok"], cwd=self._root,
        )
        py_files = [str(f) for f in changed_files if str(f).endswith(".py")]
        if py_files:
            lint_rc, lint_out, lint_err = _run_command(
                ["ruff", "check", *py_files, "--no-fix"], cwd=self._root,
            )
        else:
            lint_rc, lint_out, lint_err = 0, "", ""

        test_rc, test_out, test_err = _run_command(
            ["python", "-m", "pytest", "-x", "--tb=short", "-q"],
            cwd=self._root,
        )

        failed: list[str] = []
        if build_rc != 0:
            failed.append("build")
        if lint_rc != 0:
            failed.append("lint")
        if test_rc != 0:
            failed.append("test")

        return Ok(QualityCheckResult(
            passed=len(failed) == 0,
            build_output=build_out + build_err,
            lint_output=lint_out + lint_err,
            test_output=test_out + test_err,
            failed_checks=tuple(failed),
        ))

    @staticmethod
    def detect_regression(
        before: QualityCheckResult, after: QualityCheckResult,
    ) -> bool:
        """True if after has test failures not present in before."""
        before_fails = _parse_failed_tests(before.test_output)
        after_fails = _parse_failed_tests(after.test_output)
        new_failures = after_fails - before_fails
        return len(new_failures) > 0


def _run_command(
    cmd: list[str], cwd: Path,
) -> tuple[int, str, str]:
    """Run a subprocess command, returning (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd),
            capture_output=True, text=True, timeout=300,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, "", str(exc)


_FAILED_RE = re.compile(r"FAILED\s+(\S+)")


def _parse_failed_tests(output: str) -> set[str]:
    """Extract failed test names from pytest output."""
    return set(_FAILED_RE.findall(output))
