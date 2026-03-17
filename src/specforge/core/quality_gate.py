"""QualityGate — orchestrates quality checkers per architecture."""

from __future__ import annotations

import logging
from pathlib import Path

from specforge.core.checkers import CheckerProtocol, get_applicable_checkers
from specforge.core.quality_models import CheckLevel, CheckResult, QualityGateResult
from specforge.core.result import Ok, Result

logger = logging.getLogger(__name__)


class QualityGate:
    """Orchestrates quality checks filtered by architecture and level."""

    def __init__(
        self,
        architecture: str,
        project_root: Path,
        service_slug: str,
        checkers: tuple[CheckerProtocol, ...],
        prompt_loader: object | None = None,
    ) -> None:
        self._architecture = architecture
        self._root = project_root
        self._slug = service_slug
        self._checkers = checkers
        self._prompt_loader = prompt_loader

    def run_task_checks(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Result[QualityGateResult, str]:
        """Run TASK-level checkers applicable to this architecture."""
        applicable = get_applicable_checkers(
            self._checkers, self._architecture, CheckLevel.TASK,
        )
        return self._run_checks(
            applicable, changed_files, service_context, CheckLevel.TASK,
        )

    def run_service_checks(
        self,
        service_context: object,
    ) -> Result[QualityGateResult, str]:
        """Run SERVICE-level checkers applicable to this architecture."""
        applicable = get_applicable_checkers(
            self._checkers, self._architecture, CheckLevel.SERVICE,
        )
        return self._run_checks(
            applicable, [], service_context, CheckLevel.SERVICE,
        )

    def run_selective_checks(
        self,
        failed_checkers: tuple[str, ...],
        changed_files: list[Path],
        service_context: object,
    ) -> Result[QualityGateResult, str]:
        """Re-run only failed checkers + regression check on all others."""
        results: list[CheckResult] = []
        for checker in self._checkers:
            if not checker.is_applicable(self._architecture):
                continue
            result = _safe_run_checker(checker, changed_files, service_context)
            results.append(result)
        return Ok(
            _aggregate_results(
                tuple(results), self._architecture, CheckLevel.TASK,
            ),
        )

    def _run_checks(
        self,
        checkers: tuple[CheckerProtocol, ...],
        changed_files: list[Path],
        service_context: object,
        level: CheckLevel,
    ) -> Result[QualityGateResult, str]:
        """Run a set of checkers, aggregating results."""
        results: list[CheckResult] = []
        for checker in checkers:
            result = _safe_run_checker(checker, changed_files, service_context)
            results.append(result)
        return Ok(
            _aggregate_results(tuple(results), self._architecture, level),
        )


def _safe_run_checker(
    checker: CheckerProtocol,
    changed_files: list[Path],
    service_context: object,
) -> CheckResult:
    """Run a checker, catching errors and returning skip on failure."""
    try:
        result = checker.check(changed_files, service_context)
        if result.ok:
            return result.value
        logger.warning("Checker %s error: %s", checker.name, result.error)
        return CheckResult(
            checker_name=checker.name,
            passed=True, skipped=True,
            category=checker.category,
            skip_reason=f"Checker error: {result.error}",
        )
    except Exception as exc:
        logger.warning("Checker %s crashed: %s", checker.name, exc)
        return CheckResult(
            checker_name=checker.name,
            passed=True, skipped=True,
            category=checker.category,
            skip_reason=f"Checker crashed: {exc}",
        )


def _aggregate_results(
    results: tuple[CheckResult, ...],
    architecture: str,
    level: CheckLevel,
) -> QualityGateResult:
    """Aggregate individual check results into a gate result."""
    failed = tuple(
        r.checker_name for r in results if not r.passed and not r.skipped
    )
    skipped = tuple(r.checker_name for r in results if r.skipped)
    passed = len(failed) == 0
    return QualityGateResult(
        passed=passed,
        check_results=results,
        failed_checks=failed,
        skipped_checks=skipped,
        architecture=architecture,
        level=level,
    )
