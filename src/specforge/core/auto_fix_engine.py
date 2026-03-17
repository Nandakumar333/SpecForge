"""AutoFixEngine — targeted fix prompts + retry loop + regression detection."""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from specforge.core.executor_models import ExecutionMode, ImplementPrompt
from specforge.core.quality_models import (
    CheckResult,
    ContractAttribution,
    DiagnosticReport,
    ErrorCategory,
    FixAttempt,
    QualityGateResult,
)
from specforge.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category → targeted fix instructions
# ---------------------------------------------------------------------------

_STRATEGY_MAP: dict[ErrorCategory, str] = {
    ErrorCategory.SYNTAX: (
        "Fix the compilation/syntax error in {file}. "
        "The specific error is: {message}. "
        "Check for missing imports, typos, or unclosed brackets."
    ),
    ErrorCategory.LOGIC: (
        "The test '{test_name}' is failing. "
        "Analyze the assertion: expected vs actual. "
        "Fix the business logic, not the test."
    ),
    ErrorCategory.TYPE: (
        "Fix the type error in {file}:{line}. "
        "Add or correct the type annotation."
    ),
    ErrorCategory.LINT: (
        "Fix lint violation {code} in {file}:{line}. "
        "Run `ruff check --fix` first for auto-fixable rules, "
        "then manually fix remaining."
    ),
    ErrorCategory.COVERAGE: (
        "Coverage is below threshold. "
        "Add tests for uncovered code in {file}. "
        "Focus on the untested functions/branches."
    ),
    ErrorCategory.DOCKER: (
        "Docker build failed: {error}. Fix the Dockerfile — "
        "check layer order, missing dependencies "
        "(`apt-get install`), and build context."
    ),
    ErrorCategory.CONTRACT: (
        "Contract test failed. The API response doesn't match "
        "the consumer contract. Fix the response shape to match: {details}"
    ),
    ErrorCategory.BOUNDARY: (
        "Cross-module boundary violation in {file}. "
        "Import from the module's public interface "
        "instead of internal modules."
    ),
    ErrorCategory.SECURITY: (
        "Security issue: hardcoded secret detected in {file}:{line}. "
        "Remove the secret and replace with "
        "`os.environ['{key}']` or load from .env config."
    ),
}


# ---------------------------------------------------------------------------
# Engine class
# ---------------------------------------------------------------------------


class AutoFixEngine:
    """Targeted auto-fix with categorized prompts and retry budget."""

    def __init__(
        self,
        task_runner: object,  # TaskRunner
        quality_gate: object,  # QualityGate
        max_attempts: int = 3,
    ) -> None:
        self._runner = task_runner
        self._gate = quality_gate
        self._max = max_attempts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fix(
        self,
        original_prompt: ImplementPrompt,
        gate_result: QualityGateResult,
        changed_files: list[Path],
        mode: ExecutionMode,
    ) -> Result[list[Path], str]:
        """Attempt targeted fixes up to *max_attempts* times.

        Returns ``Ok(all_changed_files)`` on success,
        ``Err(diagnostic_summary)`` on exhaustion.
        """
        all_files = list(changed_files)
        current_result = gate_result
        attempts: list[FixAttempt] = []

        for attempt_num in range(1, self._max + 1):
            result = self._try_one(
                original_prompt, current_result,
                all_files, attempts, attempt_num, mode,
            )
            if result is None:
                return Ok(all_files)

            new_result, attempt = result
            attempts.append(attempt)

            if isinstance(new_result, str):
                return Err(new_result)

            current_result = new_result

        return self._exhaust(gate_result, tuple(attempts), current_result)

    def generate_diagnostic(
        self,
        task_id: str,
        original_error: QualityGateResult,
        attempts: tuple[FixAttempt, ...],
        final_result: QualityGateResult,
    ) -> DiagnosticReport:
        """Build a DiagnosticReport for escalation."""
        return _build_diagnostic(task_id, original_error, attempts, final_result)

    # ------------------------------------------------------------------
    # Internal helpers (kept short for 30-line rule)
    # ------------------------------------------------------------------

    def _try_one(
        self,
        original_prompt: ImplementPrompt,
        current_result: QualityGateResult,
        all_files: list[Path],
        attempts: list[FixAttempt],
        attempt_num: int,
        mode: ExecutionMode,
    ) -> tuple[QualityGateResult | str, FixAttempt] | None:
        """Run one fix attempt. Returns None if already passing."""
        failures = _get_failures(current_result)
        if not failures:
            return None

        provider_fail = _find_provider_failure(failures)
        if provider_fail:
            msg = (
                f"Provider contract failure (not auto-fixable): "
                f"{provider_fail.output}"
            )
            return msg, _make_attempt(
                attempt_num, ErrorCategory.CONTRACT, "", (), None, False, "",
            )

        primary = failures[0]
        instructions = _get_strategy(primary)
        fix_prompt = _build_fix_prompt(
            original_prompt, primary, attempt_num,
            tuple(attempts), instructions,
        )

        return self._apply_fix(
            fix_prompt, primary, current_result,
            all_files, attempt_num, mode,
        )

    def _apply_fix(
        self,
        fix_prompt: ImplementPrompt,
        primary: CheckResult,
        current_result: QualityGateResult,
        all_files: list[Path],
        attempt_num: int,
        mode: ExecutionMode,
    ) -> tuple[QualityGateResult | str, FixAttempt] | None:
        """Execute fix prompt and evaluate the outcome."""
        run_result = self._runner.run(fix_prompt, mode)
        if not run_result.ok:
            msg = f"Fix attempt {attempt_num} rejected: {run_result.error}"
            return msg, _make_attempt(
                attempt_num, primary.category, fix_prompt.task_description,
                (), None, False, "",
            )

        fix_files = run_result.value
        _merge_files(all_files, fix_files)

        return self._evaluate_fix(
            fix_prompt, primary, current_result,
            all_files, fix_files, attempt_num,
        )

    def _evaluate_fix(
        self,
        fix_prompt: ImplementPrompt,
        primary: CheckResult,
        current_result: QualityGateResult,
        all_files: list[Path],
        fix_files: list[Path],
        attempt_num: int,
    ) -> tuple[QualityGateResult, FixAttempt] | None:
        """Recheck quality and handle regression."""
        recheck = self._gate.run_selective_checks(
            current_result.failed_checks, all_files, None,
        )
        if not recheck.ok:
            attempt = _make_attempt(
                attempt_num, primary.category, fix_prompt.task_description,
                _paths_to_strings(fix_files), None, False, "",
            )
            return current_result, attempt

        new_result = recheck.value
        if new_result.passed:
            logger.info("Auto-fix succeeded on attempt %d", attempt_num)
            return None

        return _handle_regression(
            current_result, new_result, fix_prompt,
            primary, all_files, fix_files, attempt_num,
        )

    def _exhaust(
        self,
        gate_result: QualityGateResult,
        attempts: tuple[FixAttempt, ...],
        current_result: QualityGateResult,
    ) -> Err[str]:
        """Build diagnostic and return exhaustion error."""
        report = _build_diagnostic(
            "unknown", gate_result, attempts, current_result,
        )
        return Err(
            f"Auto-fix exhausted after {self._max} attempts. "
            f"Still failing: {', '.join(report.still_failing)}"
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _get_failures(gate_result: QualityGateResult) -> list[CheckResult]:
    """Extract non-skipped, failed CheckResults."""
    return [
        cr for cr in gate_result.check_results
        if not cr.passed and not cr.skipped
    ]


def _find_provider_failure(
    failures: list[CheckResult],
) -> CheckResult | None:
    """Find CONTRACT failure with attribution == PROVIDER."""
    for f in failures:
        if (
            f.category == ErrorCategory.CONTRACT
            and f.attribution == ContractAttribution.PROVIDER
        ):
            return f
    return None


def _get_strategy(failure: CheckResult) -> str:
    """Return category-specific fix instructions with placeholders filled."""
    template = _STRATEGY_MAP.get(failure.category, "Fix the failing check.")
    detail = _first_detail(failure)
    return template.format(
        file=detail.file_path,
        line=detail.line_number or "?",
        message=detail.message,
        code=detail.code,
        error=failure.output,
        details=failure.output,
        test_name=_extract_test_name(failure),
        key=_extract_secret_key(detail),
    )


def _first_detail(failure: CheckResult) -> object:
    """Return the first ErrorDetail or a placeholder."""
    if failure.error_details:
        return failure.error_details[0]
    from specforge.core.quality_models import ErrorDetail
    return ErrorDetail(file_path="unknown")


def _extract_test_name(failure: CheckResult) -> str:
    """Pull test name from output or error details."""
    if failure.error_details:
        msg = failure.error_details[0].message
        if msg:
            return msg.split("::")[0] if "::" in msg else msg
    return failure.output[:80] if failure.output else "unknown"


def _extract_secret_key(detail: object) -> str:
    """Guess an env var name from the error detail context."""
    code = getattr(detail, "code", "")
    return code.upper() if code else "SECRET_KEY"


def _build_fix_prompt(
    original: ImplementPrompt,
    failure: CheckResult,
    attempt_num: int,
    prior_attempts: tuple[FixAttempt, ...],
    instructions: str,
) -> ImplementPrompt:
    """Create an ImplementPrompt targeted at the specific failure."""
    prior_ctx = _format_prior_attempts(prior_attempts)
    affected = _affected_files(failure)

    description = (
        f"[Auto-fix attempt {attempt_num}] "
        f"Checker '{failure.checker_name}' failed "
        f"(category: {failure.category.value}).\n\n"
        f"Error output:\n{failure.output}\n\n"
        f"Instructions:\n{instructions}"
    )

    return ImplementPrompt(
        system_context=original.system_context,
        task_description=description,
        file_hints=tuple(affected) + original.file_hints,
        dependency_context=prior_ctx,
        prior_task_commits=original.prior_task_commits,
    )


def _format_prior_attempts(
    attempts: tuple[FixAttempt, ...],
) -> str:
    """Render prior attempts as context for progressive prompts."""
    if not attempts:
        return ""
    lines = ["Previous fix attempts:"]
    for a in attempts:
        status = "reverted" if a.reverted else "applied"
        lines.append(
            f"  Attempt {a.attempt_number} ({a.category.value}): {status}"
        )
    return "\n".join(lines)


def _affected_files(failure: CheckResult) -> list[str]:
    """Extract file paths from error details."""
    return [d.file_path for d in failure.error_details if d.file_path]


def _make_attempt(
    attempt_num: int,
    category: ErrorCategory,
    fix_prompt: str,
    files: tuple[str, ...] | list[Path],
    result: QualityGateResult | None,
    reverted: bool,
    revert_reason: str,
) -> FixAttempt:
    """Create a FixAttempt record."""
    changed = tuple(str(f) for f in files)
    return FixAttempt(
        attempt_number=attempt_num,
        category=category,
        fix_prompt=fix_prompt if isinstance(fix_prompt, str) else "",
        files_changed=changed,
        result=result,
        reverted=reverted,
        revert_reason=revert_reason,
    )


def _is_regression(
    before: QualityGateResult,
    after: QualityGateResult,
) -> bool:
    """True if *after* has new failures that were not in *before*."""
    old_failures = set(before.failed_checks)
    new_failures = set(after.failed_checks)
    return bool(new_failures - old_failures)


def _git_revert_files(files: list[Path]) -> None:
    """Revert files via ``git checkout --``."""
    for path in files:
        try:
            subprocess.run(
                ["git", "checkout", "--", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Failed to revert %s: %s", path, exc)


def _handle_regression(
    current_result: QualityGateResult,
    new_result: QualityGateResult,
    fix_prompt: ImplementPrompt,
    primary: CheckResult,
    all_files: list[Path],
    fix_files: list[Path],
    attempt_num: int,
) -> tuple[QualityGateResult, FixAttempt]:
    """Revert on regression, otherwise record and continue."""
    file_strs = _paths_to_strings(fix_files)

    if _is_regression(current_result, new_result):
        _git_revert_files(fix_files)
        for f in fix_files:
            if f in all_files:
                all_files.remove(f)
        attempt = _make_attempt(
            attempt_num, primary.category, fix_prompt.task_description,
            file_strs, new_result, True,
            "Regression: new failures introduced",
        )
        return current_result, attempt

    attempt = _make_attempt(
        attempt_num, primary.category, fix_prompt.task_description,
        file_strs, new_result, False, "",
    )
    return new_result, attempt


def _paths_to_strings(files: list[Path]) -> tuple[str, ...]:
    """Convert Path list to string tuple."""
    return tuple(str(f) for f in files)


def _merge_files(all_files: list[Path], new_files: list[Path]) -> None:
    """Add new files to all_files without duplicates."""
    for f in new_files:
        if f not in all_files:
            all_files.append(f)


def _build_diagnostic(
    task_id: str,
    original_error: QualityGateResult,
    attempts: tuple[FixAttempt, ...],
    final_result: QualityGateResult,
) -> DiagnosticReport:
    """Create a DiagnosticReport with category-specific suggestions."""
    categories = _failing_categories(final_result)
    from specforge.core.diagnostic_reporter import get_suggested_steps

    return DiagnosticReport(
        task_id=task_id,
        original_error=original_error,
        attempts=attempts,
        still_failing=final_result.failed_checks,
        suggested_steps=get_suggested_steps(categories),
        created_at=datetime.now(tz=UTC).isoformat(),
    )


def _failing_categories(
    result: QualityGateResult,
) -> tuple[ErrorCategory, ...]:
    """Extract unique categories from non-skipped failures."""
    seen: list[ErrorCategory] = []
    for cr in result.check_results:
        if not cr.passed and not cr.skipped and cr.category not in seen:
            seen.append(cr.category)
    return tuple(seen)
