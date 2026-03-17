"""BuildChecker — runs project build via py_compile on changed Python files."""

from __future__ import annotations

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

_BUILD_TIMEOUT = 300


def _run_build_command(
    cmd: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with timeout and capture output."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_BUILD_TIMEOUT,
        cwd=cwd,
    )


def _parse_compile_errors(stderr: str) -> tuple[ErrorDetail, ...]:
    """Extract file/line/message from py_compile stderr output."""
    details: list[ErrorDetail] = []
    for line in stderr.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        details.append(
            ErrorDetail(file_path="<build>", message=line),
        )
    return tuple(details)


class BuildChecker:
    """Runs Python compilation check on changed files."""

    @property
    def name(self) -> str:
        return "build"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.SYNTAX

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
        """Compile each changed .py file and report errors."""
        py_files = [f for f in changed_files if f.suffix == ".py"]
        if not py_files:
            return Ok(
                CheckResult(
                    checker_name=self.name,
                    passed=True,
                    category=self.category,
                    skipped=True,
                    skip_reason="No Python files to compile",
                ),
            )
        return self._compile_files(py_files)

    def _compile_files(
        self,
        py_files: list[Path],
    ) -> Ok[CheckResult] | Err[str]:
        """Run py_compile on each file and aggregate results."""
        all_details: list[ErrorDetail] = []
        failed = False
        output_lines: list[str] = []

        for py_file in py_files:
            result = self._compile_single(py_file)
            if result is None:
                continue
            if isinstance(result, Err):
                return result
            val = result.value
            if not val.passed:
                failed = True
            all_details.extend(val.error_details)
            if val.output:
                output_lines.append(val.output)

        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=not failed,
                category=self.category,
                output="\n".join(output_lines),
                error_details=tuple(all_details),
            ),
        )

    def _compile_single(
        self,
        py_file: Path,
    ) -> Ok[CheckResult] | Err[str] | None:
        """Compile a single Python file; return None on success."""
        cmd = ["python", "-m", "py_compile", str(py_file)]
        try:
            proc = _run_build_command(cmd)
        except subprocess.TimeoutExpired:
            return Err(f"Build timed out after {_BUILD_TIMEOUT}s")
        except FileNotFoundError:
            return Err("Python interpreter not found")

        if proc.returncode == 0:
            return None

        details = _parse_compile_errors(proc.stderr)
        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=False,
                category=self.category,
                output=proc.stderr,
                error_details=details,
            ),
        )
