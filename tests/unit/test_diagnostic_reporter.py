"""Tests for DiagnosticReporter — suggested steps + markdown rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.diagnostic_reporter import (
    SUGGESTED_STEPS,
    get_suggested_steps,
    render_diagnostic,
)
from specforge.core.quality_models import (
    DiagnosticReport,
    ErrorCategory,
    FixAttempt,
    QualityGateResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gate(
    passed: bool = False,
    failed: tuple[str, ...] = (),
) -> QualityGateResult:
    return QualityGateResult(passed=passed, failed_checks=failed)


def _report(
    task_id: str = "task-1",
    still_failing: tuple[str, ...] = ("build",),
    attempts: tuple[FixAttempt, ...] = (),
    categories: tuple[ErrorCategory, ...] = (ErrorCategory.SYNTAX,),
) -> DiagnosticReport:
    steps = get_suggested_steps(categories)
    return DiagnosticReport(
        task_id=task_id,
        original_error=_gate(failed=still_failing),
        attempts=attempts,
        still_failing=still_failing,
        suggested_steps=steps,
        created_at="2025-01-15T12:00:00+00:00",
    )


# ===================================================================
# T045 — Suggested Steps
# ===================================================================


class TestGetSuggestedSteps:
    """T045: category-specific suggested steps."""

    @pytest.mark.parametrize("category", list(ErrorCategory))
    def test_every_category_has_steps(
        self, category: ErrorCategory,
    ) -> None:
        steps = get_suggested_steps((category,))
        assert len(steps) > 0

    def test_syntax_steps(self) -> None:
        steps = get_suggested_steps((ErrorCategory.SYNTAX,))
        combined = " ".join(steps)
        assert "file and line" in combined
        assert "missing imports" in combined

    def test_docker_steps_mention_dockerfile(self) -> None:
        steps = get_suggested_steps((ErrorCategory.DOCKER,))
        combined = " ".join(steps)
        assert "Dockerfile" in combined
        assert "layer order" in combined

    def test_boundary_steps_mention_interface(self) -> None:
        steps = get_suggested_steps((ErrorCategory.BOUNDARY,))
        combined = " ".join(steps)
        assert "public interface" in combined

    def test_security_steps_mention_secret(self) -> None:
        steps = get_suggested_steps((ErrorCategory.SECURITY,))
        combined = " ".join(steps)
        assert "secret" in combined.lower()
        assert "os.environ" in combined

    def test_coverage_steps_mention_pytest(self) -> None:
        steps = get_suggested_steps((ErrorCategory.COVERAGE,))
        combined = " ".join(steps)
        assert "pytest" in combined

    def test_lint_steps_mention_ruff(self) -> None:
        steps = get_suggested_steps((ErrorCategory.LINT,))
        combined = " ".join(steps)
        assert "ruff" in combined

    def test_type_steps_mention_annotation(self) -> None:
        steps = get_suggested_steps((ErrorCategory.TYPE,))
        combined = " ".join(steps)
        assert "type" in combined.lower()
        assert "annotation" in combined.lower()

    def test_logic_steps_mention_test(self) -> None:
        steps = get_suggested_steps((ErrorCategory.LOGIC,))
        combined = " ".join(steps)
        assert "test" in combined.lower()

    def test_contract_steps_mention_pact(self) -> None:
        steps = get_suggested_steps((ErrorCategory.CONTRACT,))
        combined = " ".join(steps)
        assert "Pact" in combined or "contract" in combined.lower()

    def test_multiple_categories_dedup(self) -> None:
        cats = (ErrorCategory.SYNTAX, ErrorCategory.LINT)
        steps = get_suggested_steps(cats)
        assert len(steps) == len(set(steps))

    def test_multiple_categories_combined(self) -> None:
        syntax_steps = get_suggested_steps((ErrorCategory.SYNTAX,))
        lint_steps = get_suggested_steps((ErrorCategory.LINT,))
        combined = get_suggested_steps((ErrorCategory.SYNTAX, ErrorCategory.LINT))
        assert len(combined) == len(syntax_steps) + len(lint_steps)


# ===================================================================
# T046 — Diagnostic Report Rendering
# ===================================================================


class TestRenderDiagnostic:
    """T046: render markdown diagnostic reports."""

    def test_creates_file(self, tmp_path: Path) -> None:
        report = _report()
        result = render_diagnostic(report, tmp_path)
        assert result.ok
        assert result.value.exists()

    def test_filename_contains_task_id(self, tmp_path: Path) -> None:
        report = _report(task_id="auth-login")
        result = render_diagnostic(report, tmp_path)
        assert result.ok
        assert "auth-login" in result.value.name

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "dir"
        report = _report()
        result = render_diagnostic(report, out)
        assert result.ok
        assert out.exists()

    def test_markdown_contains_header(self, tmp_path: Path) -> None:
        report = _report(task_id="my-task")
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-my-task.md").read_text()
        assert "# Diagnostic Report: my-task" in content

    def test_markdown_contains_still_failing(self, tmp_path: Path) -> None:
        report = _report(still_failing=("build", "lint"))
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-task-1.md").read_text()
        assert "## Still Failing" in content
        assert "**build**" in content
        assert "**lint**" in content

    def test_markdown_contains_timeline(self, tmp_path: Path) -> None:
        attempt = FixAttempt(
            attempt_number=1,
            category=ErrorCategory.SYNTAX,
            files_changed=("src/a.py",),
            result=_gate(failed=("build",)),
        )
        report = _report(attempts=(attempt,))
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-task-1.md").read_text(encoding="utf-8")
        assert "## Fix Attempt Timeline" in content
        assert "### Attempt 1" in content
        assert "syntax" in content

    def test_markdown_contains_suggested_steps(self, tmp_path: Path) -> None:
        report = _report(categories=(ErrorCategory.DOCKER,))
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-task-1.md").read_text()
        assert "## Suggested Manual Steps" in content
        assert "Dockerfile" in content

    def test_reverted_attempt_shown(self, tmp_path: Path) -> None:
        attempt = FixAttempt(
            attempt_number=2,
            category=ErrorCategory.LINT,
            reverted=True,
            revert_reason="Regression: new failures introduced",
        )
        report = _report(attempts=(attempt,))
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-task-1.md").read_text(encoding="utf-8")
        assert "REVERTED" in content
        assert "Regression" in content

    def test_passed_result_shown(self, tmp_path: Path) -> None:
        attempt = FixAttempt(
            attempt_number=1,
            category=ErrorCategory.SYNTAX,
            result=_gate(passed=True),
        )
        report = _report(attempts=(attempt,))
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-task-1.md").read_text()
        assert "Passed" in content

    def test_failed_result_shows_checkers(self, tmp_path: Path) -> None:
        attempt = FixAttempt(
            attempt_number=1,
            category=ErrorCategory.LINT,
            result=_gate(failed=("ruff", "mypy")),
        )
        report = _report(attempts=(attempt,))
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-task-1.md").read_text(encoding="utf-8")
        assert "ruff" in content
        assert "mypy" in content

    def test_boundary_category_actionable(self, tmp_path: Path) -> None:
        report = _report(categories=(ErrorCategory.BOUNDARY,))
        render_diagnostic(report, tmp_path)
        content = (tmp_path / "diagnostic-task-1.md").read_text()
        assert "public interface" in content
