"""DiagnosticReporter — renders structured escalation reports."""

from __future__ import annotations

import logging
from pathlib import Path

from specforge.core.quality_models import DiagnosticReport, ErrorCategory
from specforge.core.result import Err, Ok, Result

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category-specific suggested manual steps
# ---------------------------------------------------------------------------

SUGGESTED_STEPS: dict[ErrorCategory, tuple[str, ...]] = {
    ErrorCategory.SYNTAX: (
        "Check the error output for the exact file and line number",
        "Look for missing imports, unclosed brackets, or typos",
        "Run the build command manually to see the full error",
    ),
    ErrorCategory.LOGIC: (
        "Read the failing test carefully — understand what it expects",
        "Check if the logic matches the specification requirements",
        "Add debug logging to trace the actual vs expected values",
    ),
    ErrorCategory.DOCKER: (
        "Check Dockerfile layer order — install dependencies before copying code",
        "Verify all system packages are listed in apt-get install",
        "Run docker build locally to reproduce the exact error",
        "Check if multi-stage build copies all needed artifacts",
    ),
    ErrorCategory.CONTRACT: (
        "Compare the API response shape against the Pact contract file",
        "Check if field names, types, or required/optional status changed",
        "If provider-side: coordinate with the provider team to fix their API",
    ),
    ErrorCategory.BOUNDARY: (
        "Refactor the import to use the module's public interface",
        "Move shared code to a common/shared module if it's truly shared",
        "Check module boundary definitions in manifest.json",
    ),
    ErrorCategory.SECURITY: (
        "Remove the hardcoded secret from the source file immediately",
        "Add the secret to .env or a secrets manager",
        "Replace with os.environ['KEY_NAME'] or config.get('key')",
        "Check git history — the secret may need to be rotated",
    ),
    ErrorCategory.COVERAGE: (
        "Identify uncovered lines with: pytest --cov --cov-report=term-missing",
        "Write tests for the uncovered branches and edge cases",
        "Focus on error handling paths which are often missed",
    ),
    ErrorCategory.LINT: (
        "Run ruff check --fix to auto-fix what's possible",
        "Manually fix remaining issues by reading the rule documentation",
        "Check if ruff rules need to be configured in pyproject.toml",
    ),
    ErrorCategory.TYPE: (
        "Check the type error message for the expected vs actual type",
        "Add missing type annotations to function signatures",
        "Import the correct types from typing module",
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_suggested_steps(
    categories: tuple[ErrorCategory, ...],
) -> tuple[str, ...]:
    """Get category-specific remediation steps for failed categories."""
    steps: list[str] = []
    seen: set[str] = set()
    for cat in categories:
        for step in SUGGESTED_STEPS.get(cat, ()):
            if step not in seen:
                steps.append(step)
                seen.add(step)
    return tuple(steps)


def render_diagnostic(
    report: DiagnosticReport,
    output_dir: Path,
) -> Result[Path, str]:
    """Write diagnostic report as Markdown to *output_dir*."""
    filename = f"diagnostic-{report.task_id}.md"
    path = output_dir / filename
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        content = _render_markdown(report)
        path.write_text(content, encoding="utf-8")
        return Ok(path)
    except OSError as exc:
        return Err(f"Failed to write diagnostic: {exc}")


# ---------------------------------------------------------------------------
# Internal rendering
# ---------------------------------------------------------------------------


def _render_markdown(report: DiagnosticReport) -> str:
    """Render DiagnosticReport to Markdown string."""
    lines = _render_header(report)
    lines += _render_still_failing(report)
    lines += _render_timeline(report)
    lines += _render_suggestions(report)
    return "\n".join(lines) + "\n"


def _render_header(report: DiagnosticReport) -> list[str]:
    """Render the report header section."""
    return [
        f"# Diagnostic Report: {report.task_id}",
        f"\n**Generated**: {report.created_at}",
        f"**Status**: Auto-fix exhausted after {len(report.attempts)} attempts\n",
    ]


def _render_still_failing(report: DiagnosticReport) -> list[str]:
    """Render the still-failing checkers section."""
    lines = ["## Still Failing\n"]
    for name in report.still_failing:
        lines.append(f"- **{name}**")
    return lines


def _render_timeline(report: DiagnosticReport) -> list[str]:
    """Render the fix-attempt timeline section."""
    lines = ["\n## Fix Attempt Timeline\n"]
    for attempt in report.attempts:
        lines += _render_one_attempt(attempt)
    return lines


def _render_one_attempt(attempt: object) -> list[str]:
    """Render a single FixAttempt block."""
    lines = [
        f"### Attempt {attempt.attempt_number}",
        f"- Category: {attempt.category.value}",
    ]
    files = (
        ", ".join(attempt.files_changed)
        if attempt.files_changed else "none"
    )
    lines.append(f"- Files changed: {files}")
    if attempt.reverted:
        lines.append(f"- ⚠️ REVERTED: {attempt.revert_reason}")
    if attempt.result:
        status = _attempt_status(attempt.result)
        lines.append(f"- Result: {status}")
    lines.append("")
    return lines


def _attempt_status(result: object) -> str:
    """Format pass/fail status for a gate result."""
    if result.passed:
        return "✅ Passed"
    failed = ", ".join(result.failed_checks)
    return f"❌ Failed ({failed})"


def _render_suggestions(report: DiagnosticReport) -> list[str]:
    """Render the suggested manual steps section."""
    lines = ["## Suggested Manual Steps\n"]
    for i, step in enumerate(report.suggested_steps, 1):
        lines.append(f"{i}. {step}")
    return lines
