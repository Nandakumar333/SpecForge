"""AutoFixLoop — error → analyze → fix → retry (thin wrapper, Feature 010 replaces)."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import replace as dc_replace
from pathlib import Path

from specforge.core.executor_models import (
    ExecutionMode,
    ImplementPrompt,
    QualityCheckResult,
)
from specforge.core.quality_checker import QualityChecker
from specforge.core.result import Err, Ok, Result
from specforge.core.task_runner import TaskRunner

logger = logging.getLogger(__name__)


class AutoFixLoop:
    """Retry loop: error → fix prompt → execute → quality check."""

    def __init__(
        self,
        task_runner: TaskRunner,
        quality_checker: QualityChecker,
        max_attempts: int = 3,
    ) -> None:
        self._runner = task_runner
        self._checker = quality_checker
        self._max_attempts = max_attempts

    def fix(
        self,
        original_prompt: ImplementPrompt,
        error: QualityCheckResult,
        changed_files: list[Path],
        mode: ExecutionMode,
    ) -> Result[list[Path], str]:
        """Attempt to fix quality failures up to max_attempts times.

        Returns Ok(all_changed_files) on success, Err(diagnostic) on exhaustion.
        """
        all_files = list(changed_files)
        current_error = error
        diagnostics: list[str] = []

        for attempt in range(1, self._max_attempts + 1):
            fix_prompt = self._build_fix_prompt(
                original_prompt, current_error, attempt,
            )

            run_result = self._runner.run(fix_prompt, mode)
            if not run_result.ok:
                return Err(f"Fix attempt {attempt} rejected: {run_result.error}")

            fix_files = run_result.value
            all_files.extend(f for f in fix_files if f not in all_files)

            check_result = self._checker.check(all_files)
            if not check_result.ok:
                diagnostics.append(f"Attempt {attempt}: checker error")
                continue

            qc = check_result.value
            if qc.passed:
                logger.info("Auto-fix succeeded on attempt %d", attempt)
                return Ok(all_files)

            if QualityChecker.detect_regression(current_error, qc):
                logger.warning(
                    "Regression detected on attempt %d, reverting fix files",
                    attempt,
                )
                _git_checkout_files(fix_files)
                all_files = [f for f in all_files if f not in fix_files]
                diagnostics.append(
                    f"Attempt {attempt}: regression detected, reverted",
                )
            else:
                diagnostics.append(
                    f"Attempt {attempt}: {', '.join(qc.failed_checks)}",
                )

            current_error = qc

        summary = (
            f"Auto-fix exhausted after {self._max_attempts} attempts. "
            f"Diagnostics: {'; '.join(diagnostics)}"
        )
        return Err(summary)

    def _build_fix_prompt(
        self,
        original: ImplementPrompt,
        error: QualityCheckResult,
        attempt: int,
    ) -> ImplementPrompt:
        """Build a targeted fix prompt from error output."""
        error_summary = []
        if "build" in error.failed_checks:
            error_summary.append(f"Build error:\n{error.build_output}")
        if "lint" in error.failed_checks:
            error_summary.append(f"Lint error:\n{error.lint_output}")
        if "test" in error.failed_checks:
            error_summary.append(f"Test error:\n{error.test_output}")

        fix_desc = (
            f"AUTO-FIX (attempt {attempt}/{self._max_attempts})\n\n"
            f"Original task: {original.task_description}\n\n"
            f"Errors to fix:\n" + "\n".join(error_summary)
        )

        return dc_replace(original, task_description=fix_desc)


def _git_checkout_files(files: list[Path]) -> None:
    """Revert specific files via git checkout."""
    for f in files:
        try:
            subprocess.run(
                ["git", "checkout", "--", str(f)],
                capture_output=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("git checkout failed for %s: %s", f, exc)
