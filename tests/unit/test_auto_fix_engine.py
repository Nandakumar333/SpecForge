"""Tests for AutoFixEngine — categorisation, strategies, retry, regression."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.auto_fix_engine import (
    AutoFixEngine,
    _build_fix_prompt,
    _find_provider_failure,
    _get_failures,
    _get_strategy,
    _is_regression,
    _make_attempt,
)
from specforge.core.executor_models import ImplementPrompt
from specforge.core.quality_models import (
    CheckResult,
    ContractAttribution,
    ErrorCategory,
    ErrorDetail,
    FixAttempt,
    QualityGateResult,
)
from specforge.core.result import Err, Ok


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _detail(
    file_path: str = "src/app.py",
    line: int | None = 10,
    code: str = "",
    message: str = "",
) -> ErrorDetail:
    return ErrorDetail(
        file_path=file_path,
        line_number=line,
        code=code,
        message=message,
    )


def _check(
    name: str = "build",
    passed: bool = False,
    category: ErrorCategory = ErrorCategory.SYNTAX,
    output: str = "error output",
    details: tuple[ErrorDetail, ...] = (),
    skipped: bool = False,
    attribution: ContractAttribution | None = None,
) -> CheckResult:
    return CheckResult(
        checker_name=name,
        passed=passed,
        category=category,
        output=output,
        error_details=details,
        skipped=skipped,
        attribution=attribution,
    )


def _gate(
    passed: bool = False,
    checks: tuple[CheckResult, ...] = (),
    failed: tuple[str, ...] = (),
) -> QualityGateResult:
    return QualityGateResult(
        passed=passed,
        check_results=checks,
        failed_checks=failed,
    )


def _prompt() -> ImplementPrompt:
    return ImplementPrompt(
        system_context="You are a dev assistant.",
        task_description="Implement user login",
        file_hints=("src/auth.py",),
    )


# ===================================================================
# T037 — Error Categorisation
# ===================================================================


class TestErrorCategorisation:
    """T037: each category produces a targeted prompt."""

    def test_syntax_error_references_file_and_compilation(self) -> None:
        detail = _detail(file_path="src/main.py", message="unexpected EOF")
        failure = _check(
            category=ErrorCategory.SYNTAX,
            details=(detail,),
            output="SyntaxError: unexpected EOF",
        )
        instructions = _get_strategy(failure)
        assert "compilation" in instructions or "syntax" in instructions
        assert "src/main.py" in instructions

    def test_lint_error_includes_file_line_rule(self) -> None:
        detail = _detail(
            file_path="src/utils.py", line=42, code="E501",
        )
        failure = _check(
            category=ErrorCategory.LINT,
            details=(detail,),
        )
        instructions = _get_strategy(failure)
        assert "src/utils.py" in instructions
        assert "42" in instructions
        assert "E501" in instructions

    def test_docker_error_mentions_dockerfile(self) -> None:
        failure = _check(
            category=ErrorCategory.DOCKER,
            output="missing dependency libpq",
            details=(_detail(file_path="Dockerfile"),),
        )
        instructions = _get_strategy(failure)
        assert "Dockerfile" in instructions
        assert "apt-get install" in instructions
        assert "missing dependency libpq" in instructions

    def test_contract_consumer_references_schema(self) -> None:
        failure = _check(
            category=ErrorCategory.CONTRACT,
            attribution=ContractAttribution.CONSUMER,
            output="field 'email' missing from response",
            details=(_detail(file_path="contracts/user.json"),),
        )
        instructions = _get_strategy(failure)
        assert "contract" in instructions.lower()
        assert "response" in instructions.lower()

    def test_contract_provider_immediate_escalation(self) -> None:
        provider = _check(
            name="pact-provider",
            category=ErrorCategory.CONTRACT,
            attribution=ContractAttribution.PROVIDER,
            output="Provider broke field 'name'",
        )
        gate = _gate(
            checks=(provider,),
            failed=("pact-provider",),
        )

        engine = AutoFixEngine(MagicMock(), MagicMock(), max_attempts=3)
        result = engine.fix(_prompt(), gate, [], "prompt-display")

        assert not result.ok
        assert "Provider contract failure" in result.error

    def test_coverage_identifies_uncovered_function(self) -> None:
        detail = _detail(file_path="src/handlers.py", message="uncovered")
        failure = _check(
            category=ErrorCategory.COVERAGE,
            details=(detail,),
        )
        instructions = _get_strategy(failure)
        assert "src/handlers.py" in instructions
        assert "uncovered" in instructions.lower() or "tests" in instructions.lower()

    def test_boundary_specifies_module(self) -> None:
        detail = _detail(file_path="src/internal/db.py")
        failure = _check(
            category=ErrorCategory.BOUNDARY,
            details=(detail,),
        )
        instructions = _get_strategy(failure)
        assert "src/internal/db.py" in instructions
        assert "public interface" in instructions

    def test_logic_analyses_assertion(self) -> None:
        detail = _detail(message="test_login::assert 200 == 401")
        failure = _check(
            category=ErrorCategory.LOGIC,
            details=(detail,),
            output="AssertionError",
        )
        instructions = _get_strategy(failure)
        assert "assertion" in instructions.lower()
        assert "business logic" in instructions.lower()

    def test_security_instructs_secret_removal(self) -> None:
        detail = _detail(
            file_path="src/config.py", line=5, code="API_KEY",
        )
        failure = _check(
            category=ErrorCategory.SECURITY,
            details=(detail,),
        )
        instructions = _get_strategy(failure)
        assert "os.environ" in instructions
        assert "src/config.py" in instructions

    def test_type_error_references_file_and_line(self) -> None:
        detail = _detail(file_path="src/models.py", line=22)
        failure = _check(
            category=ErrorCategory.TYPE,
            details=(detail,),
        )
        instructions = _get_strategy(failure)
        assert "src/models.py" in instructions
        assert "22" in instructions


# ===================================================================
# T039 — Fix Strategies
# ===================================================================


class TestFixStrategies:
    """T039: each strategy returns actionable guidance."""

    def test_syntax_includes_compilation(self) -> None:
        failure = _check(
            category=ErrorCategory.SYNTAX,
            details=(_detail(message="bad token"),),
        )
        s = _get_strategy(failure)
        assert "compilation" in s or "syntax" in s
        assert "src/app.py" in s

    def test_lint_includes_ruff(self) -> None:
        failure = _check(
            category=ErrorCategory.LINT,
            details=(_detail(code="W291", line=7),),
        )
        s = _get_strategy(failure)
        assert "ruff" in s

    def test_docker_includes_dockerfile(self) -> None:
        failure = _check(
            category=ErrorCategory.DOCKER,
            output="no such package: libpq-dev",
            details=(_detail(file_path="Dockerfile"),),
        )
        s = _get_strategy(failure)
        assert "Dockerfile" in s
        assert "no such package" in s or "libpq" in s

    def test_security_includes_os_environ(self) -> None:
        failure = _check(
            category=ErrorCategory.SECURITY,
            details=(_detail(file_path="src/app.py", code="DB_PASS"),),
        )
        s = _get_strategy(failure)
        assert "os.environ" in s


# ===================================================================
# T041 — Retry Loop
# ===================================================================


class TestRetryLoop:
    """T041: retry with progressive context."""

    def test_attempt_1_success(self) -> None:
        runner = MagicMock()
        runner.run.return_value = Ok([Path("src/fixed.py")])

        gate_mock = MagicMock()
        gate_mock.run_selective_checks.return_value = Ok(
            _gate(passed=True, checks=(), failed=()),
        )

        initial_gate = _gate(
            checks=(_check(name="build"),),
            failed=("build",),
        )

        engine = AutoFixEngine(runner, gate_mock, max_attempts=3)
        result = engine.fix(_prompt(), initial_gate, [], "prompt-display")

        assert result.ok
        assert Path("src/fixed.py") in result.value

    def test_attempt_2_success_includes_prior_context(self) -> None:
        runner = MagicMock()
        gate_mock = MagicMock()

        still_failing = _gate(
            checks=(_check(name="build"),),
            failed=("build",),
        )
        now_passing = _gate(passed=True, checks=(), failed=())

        runner.run.side_effect = [
            Ok([Path("a.py")]),
            Ok([Path("b.py")]),
        ]
        gate_mock.run_selective_checks.side_effect = [
            Ok(still_failing),
            Ok(now_passing),
        ]

        engine = AutoFixEngine(runner, gate_mock, max_attempts=3)
        result = engine.fix(_prompt(), still_failing, [], "prompt-display")

        assert result.ok
        # Second call's prompt should contain prior attempt context
        second_prompt = runner.run.call_args_list[1][0][0]
        assert "attempt" in second_prompt.dependency_context.lower() or \
               "attempt" in second_prompt.task_description.lower()

    def test_all_attempts_exhausted(self) -> None:
        runner = MagicMock()
        runner.run.return_value = Ok([Path("x.py")])

        gate_mock = MagicMock()
        still_failing = _gate(
            checks=(_check(name="lint"),),
            failed=("lint",),
        )
        gate_mock.run_selective_checks.return_value = Ok(still_failing)

        engine = AutoFixEngine(runner, gate_mock, max_attempts=3)
        result = engine.fix(_prompt(), still_failing, [], "prompt-display")

        assert not result.ok
        assert "exhausted" in result.error.lower()
        assert "lint" in result.error

    def test_progressive_context_grows(self) -> None:
        runner = MagicMock()
        runner.run.return_value = Ok([Path("f.py")])

        gate_mock = MagicMock()
        failing = _gate(
            checks=(_check(name="test"),),
            failed=("test",),
        )
        gate_mock.run_selective_checks.return_value = Ok(failing)

        engine = AutoFixEngine(runner, gate_mock, max_attempts=3)
        engine.fix(_prompt(), failing, [], "prompt-display")

        prompts = [call[0][0] for call in runner.run.call_args_list]
        assert len(prompts) == 3
        # Later prompts should have more context about prior attempts
        assert len(prompts[2].dependency_context) >= len(
            prompts[0].dependency_context,
        )


# ===================================================================
# T042 — Regression Detection
# ===================================================================


class TestRegressionDetection:
    """T042: detect regressions and revert."""

    def test_new_failure_is_regression(self) -> None:
        before = _gate(failed=("build",))
        after = _gate(failed=("build", "lint"))
        assert _is_regression(before, after)

    def test_same_failures_not_regression(self) -> None:
        before = _gate(failed=("build", "lint"))
        after = _gate(failed=("build",))
        assert not _is_regression(before, after)

    def test_subset_not_regression(self) -> None:
        before = _gate(failed=("build", "lint"))
        after = _gate(failed=("lint",))
        assert not _is_regression(before, after)

    @patch("specforge.core.auto_fix_engine.subprocess.run")
    def test_regression_triggers_git_revert(self, mock_run: MagicMock) -> None:
        runner = MagicMock()
        runner.run.return_value = Ok([Path("src/bad.py")])

        gate_mock = MagicMock()
        initial = _gate(
            checks=(_check(name="build"),),
            failed=("build",),
        )
        regressed = _gate(
            checks=(
                _check(name="build"),
                _check(name="lint", category=ErrorCategory.LINT),
            ),
            failed=("build", "lint"),
        )
        gate_mock.run_selective_checks.return_value = Ok(regressed)

        engine = AutoFixEngine(runner, gate_mock, max_attempts=1)
        engine.fix(_prompt(), initial, [], "prompt-display")

        # git checkout should have been called for reverted file
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert "checkout" in args

    @patch("specforge.core.auto_fix_engine.subprocess.run")
    def test_reverted_attempt_flagged(self, mock_run: MagicMock) -> None:
        runner = MagicMock()
        runner.run.return_value = Ok([Path("src/bad.py")])

        gate_mock = MagicMock()
        initial = _gate(
            checks=(_check(name="build"),),
            failed=("build",),
        )
        regressed = _gate(
            checks=(
                _check(name="build"),
                _check(name="new-checker", category=ErrorCategory.LINT),
            ),
            failed=("build", "new-checker"),
        )
        gate_mock.run_selective_checks.return_value = Ok(regressed)

        engine = AutoFixEngine(runner, gate_mock, max_attempts=3)
        result = engine.fix(_prompt(), initial, [], "prompt-display")

        assert not result.ok  # eventually exhausts
        # Verify git revert was called
        assert mock_run.called

    def test_non_regression_continues(self) -> None:
        runner = MagicMock()
        gate_mock = MagicMock()

        initial = _gate(
            checks=(_check(name="build"), _check(name="lint")),
            failed=("build", "lint"),
        )
        improved = _gate(
            checks=(_check(name="build"),),
            failed=("build",),
        )
        fixed = _gate(passed=True, checks=(), failed=())

        runner.run.side_effect = [Ok([Path("a.py")]), Ok([Path("b.py")])]
        gate_mock.run_selective_checks.side_effect = [Ok(improved), Ok(fixed)]

        engine = AutoFixEngine(runner, gate_mock, max_attempts=3)
        result = engine.fix(_prompt(), initial, [], "prompt-display")

        assert result.ok


# ===================================================================
# Helper function unit tests
# ===================================================================


class TestHelperFunctions:
    """Direct tests for module-level helpers."""

    def test_get_failures_excludes_passed(self) -> None:
        passed = _check(name="lint", passed=True)
        failed = _check(name="build", passed=False)
        gate = _gate(checks=(passed, failed))
        assert _get_failures(gate) == [failed]

    def test_get_failures_excludes_skipped(self) -> None:
        skipped = _check(name="docker", passed=False, skipped=True)
        failed = _check(name="build", passed=False)
        gate = _gate(checks=(skipped, failed))
        assert _get_failures(gate) == [failed]

    def test_find_provider_failure_returns_provider(self) -> None:
        consumer = _check(
            category=ErrorCategory.CONTRACT,
            attribution=ContractAttribution.CONSUMER,
        )
        provider = _check(
            category=ErrorCategory.CONTRACT,
            attribution=ContractAttribution.PROVIDER,
        )
        assert _find_provider_failure([consumer, provider]) is provider

    def test_find_provider_failure_returns_none(self) -> None:
        consumer = _check(
            category=ErrorCategory.CONTRACT,
            attribution=ContractAttribution.CONSUMER,
        )
        assert _find_provider_failure([consumer]) is None

    def test_is_regression_empty_before(self) -> None:
        before = _gate(failed=())
        after = _gate(failed=("build",))
        assert _is_regression(before, after)

    def test_make_attempt(self) -> None:
        attempt = _make_attempt(
            1, ErrorCategory.SYNTAX, "fix prompt",
            (Path("a.py"),), None, False, "",
        )
        assert attempt.attempt_number == 1
        assert attempt.category == ErrorCategory.SYNTAX
        assert not attempt.reverted

    def test_build_fix_prompt_contains_checker_info(self) -> None:
        failure = _check(
            name="ruff",
            category=ErrorCategory.LINT,
            output="E501 line too long",
            details=(_detail(code="E501"),),
        )
        prompt = _build_fix_prompt(
            _prompt(), failure, 1, (), "Fix the lint error",
        )
        assert "ruff" in prompt.task_description
        assert "lint" in prompt.task_description

    def test_build_fix_prompt_has_progressive_context(self) -> None:
        prior = (
            FixAttempt(
                attempt_number=1,
                category=ErrorCategory.SYNTAX,
                fix_prompt="first try",
            ),
        )
        failure = _check(name="build")
        prompt = _build_fix_prompt(
            _prompt(), failure, 2, prior, "Fix the error",
        )
        assert "Attempt 1" in prompt.dependency_context

    def test_generate_diagnostic(self) -> None:
        gate = _gate(
            checks=(_check(name="build"),),
            failed=("build",),
        )
        engine = AutoFixEngine(MagicMock(), MagicMock())
        report = engine.generate_diagnostic("task-1", gate, (), gate)
        assert report.task_id == "task-1"
        assert "build" in report.still_failing
