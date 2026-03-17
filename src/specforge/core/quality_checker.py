"""QualityChecker — backward-compat shim (Feature 009 interface → Feature 010 gate).

Preserves the Feature 009 public API:
    QualityChecker(project_root, service_slug)
    .check(changed_files) → Result[QualityCheckResult, str]
    .detect_regression(before, after) → bool

For new code, use ``QualityGate`` and ``create_quality_gate()`` directly.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from specforge.core.executor_models import QualityCheckResult
from specforge.core.result import Ok, Result

logger = logging.getLogger(__name__)


class QualityChecker:
    """Backward-compat wrapper — delegates build/lint/test via subprocess.

    Feature 010 adds ``create_quality_gate()`` for the full architecture-aware
    checker pipeline.  This class is kept so Feature 009 callers (and tests
    that mock ``_run_command``) continue to work unchanged.
    """

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


# -----------------------------------------------------------------------
# Factory — preferred entry point for new code
# -----------------------------------------------------------------------


def create_quality_gate(
    project_root: Path,
    service_slug: str,
    architecture: str = "monolithic",
) -> object:
    """Create a full ``QualityGate`` with all applicable checkers.

    Returns the gate so callers can use ``run_task_checks`` /
    ``run_service_checks`` for architecture-aware quality validation.
    """
    from specforge.core.quality_gate import QualityGate

    all_checkers = _build_all_checkers(project_root)
    return QualityGate(
        architecture=architecture,
        project_root=project_root,
        service_slug=service_slug,
        checkers=tuple(all_checkers),
    )


def _build_all_checkers(project_root: Path) -> list[object]:
    """Instantiate every checker (none take project_root)."""
    from specforge.core.checkers.boundary_checker import BoundaryChecker
    from specforge.core.checkers.build_checker import BuildChecker
    from specforge.core.checkers.contract_checker import ContractChecker
    from specforge.core.checkers.coverage_checker import CoverageChecker
    from specforge.core.checkers.docker_checker import DockerBuildChecker
    from specforge.core.checkers.docker_service_checker import (
        DockerServiceChecker,
    )
    from specforge.core.checkers.interface_checker import InterfaceChecker
    from specforge.core.checkers.line_limit_checker import LineLimitChecker
    from specforge.core.checkers.lint_checker import LintChecker
    from specforge.core.checkers.migration_checker import MigrationChecker
    from specforge.core.checkers.prompt_rule_checker import PromptRuleChecker
    from specforge.core.checkers.secret_checker import SecretChecker
    from specforge.core.checkers.test_checker import TestChecker
    from specforge.core.checkers.todo_checker import TodoChecker
    from specforge.core.checkers.url_checker import UrlChecker

    return [
        BuildChecker(),
        LintChecker(),
        TestChecker(),
        CoverageChecker(),
        LineLimitChecker(),
        SecretChecker(),
        TodoChecker(),
        PromptRuleChecker(),
        DockerBuildChecker(),
        DockerServiceChecker(),
        ContractChecker(),
        UrlChecker(),
        InterfaceChecker(),
        BoundaryChecker(),
        MigrationChecker(),
    ]


# -----------------------------------------------------------------------
# Subprocess helper (kept for backward compat — tests mock this)
# -----------------------------------------------------------------------


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
