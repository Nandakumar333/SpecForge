"""Unit tests for quality_gate.py — QualityGate orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
)
from specforge.core.result import Err, Ok


# ---------------------------------------------------------------------------
# Stub checker for deterministic testing
# ---------------------------------------------------------------------------


class _StubChecker:
    """Minimal checker satisfying CheckerProtocol for tests."""

    def __init__(
        self,
        name: str,
        category: ErrorCategory,
        levels: tuple[CheckLevel, ...],
        applicable_archs: tuple[str, ...],
        result: Ok[CheckResult] | Err[str],
    ) -> None:
        self._name = name
        self._category = category
        self._levels = levels
        self._applicable = applicable_archs
        self._result = result

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> ErrorCategory:
        return self._category

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return self._levels

    def is_applicable(self, arch: str) -> bool:
        return arch in self._applicable

    def check(self, changed_files: list[Path], ctx: object) -> Ok[CheckResult] | Err[str]:
        return self._result


class _CrashingChecker(_StubChecker):
    """Checker that raises on check()."""

    def check(self, changed_files: list[Path], ctx: object) -> Ok[CheckResult] | Err[str]:
        msg = "boom"
        raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_ARCHS = ("monolithic", "microservice", "modular-monolith")

_PASS = lambda name, cat=ErrorCategory.SYNTAX, levels=(CheckLevel.TASK,), archs=_ALL_ARCHS: _StubChecker(  # noqa: E731
    name, cat, levels, archs,
    Ok(CheckResult(checker_name=name, passed=True, category=cat)),
)

_FAIL = lambda name, cat=ErrorCategory.SYNTAX, levels=(CheckLevel.TASK,), archs=_ALL_ARCHS: _StubChecker(  # noqa: E731
    name, cat, levels, archs,
    Ok(CheckResult(checker_name=name, passed=False, category=cat)),
)


def _gate(arch: str, checkers: tuple) -> "QualityGate":
    from specforge.core.quality_gate import QualityGate

    return QualityGate(
        architecture=arch,
        project_root=Path("/tmp/proj"),
        service_slug="svc",
        checkers=checkers,
    )


# ---------------------------------------------------------------------------
# Architecture filtering
# ---------------------------------------------------------------------------


class TestArchitectureFiltering:
    """Checkers are filtered by architecture before execution."""

    def test_monolithic_runs_standard_only(self) -> None:
        standard = _PASS("std", archs=("monolithic", "microservice", "modular-monolith"))
        micro_only = _PASS("micro", archs=("microservice",))
        gate = _gate("monolithic", (standard, micro_only))

        res = gate.run_task_checks([], {})
        assert res.ok
        names = [r.checker_name for r in res.value.check_results]
        assert "std" in names
        assert "micro" not in names

    def test_microservice_runs_standard_and_micro(self) -> None:
        standard = _PASS("std", archs=_ALL_ARCHS)
        micro_only = _PASS("micro", archs=("microservice",))
        gate = _gate("microservice", (standard, micro_only))

        res = gate.run_task_checks([], {})
        assert res.ok
        names = [r.checker_name for r in res.value.check_results]
        assert "std" in names
        assert "micro" in names

    def test_modular_monolith_runs_standard_and_modular(self) -> None:
        standard = _PASS("std", archs=_ALL_ARCHS)
        modular = _PASS("mod", archs=("modular-monolith",))
        gate = _gate("modular-monolith", (standard, modular))

        res = gate.run_task_checks([], {})
        assert res.ok
        names = [r.checker_name for r in res.value.check_results]
        assert "std" in names
        assert "mod" in names


# ---------------------------------------------------------------------------
# Level filtering
# ---------------------------------------------------------------------------


class TestLevelFiltering:
    """run_task_checks / run_service_checks filter by level."""

    def test_run_task_checks_filters_task_level(self) -> None:
        task_checker = _PASS("task-chk", levels=(CheckLevel.TASK,))
        svc_checker = _PASS("svc-chk", levels=(CheckLevel.SERVICE,))
        gate = _gate("monolithic", (task_checker, svc_checker))

        res = gate.run_task_checks([], {})
        assert res.ok
        names = [r.checker_name for r in res.value.check_results]
        assert "task-chk" in names
        assert "svc-chk" not in names

    def test_run_service_checks_filters_service_level(self) -> None:
        task_checker = _PASS("task-chk", levels=(CheckLevel.TASK,))
        svc_checker = _PASS("svc-chk", levels=(CheckLevel.SERVICE,))
        gate = _gate("monolithic", (task_checker, svc_checker))

        res = gate.run_service_checks({})
        assert res.ok
        names = [r.checker_name for r in res.value.check_results]
        assert "svc-chk" in names
        assert "task-chk" not in names


# ---------------------------------------------------------------------------
# Pass / fail / skip aggregation
# ---------------------------------------------------------------------------


class TestAggregation:
    """Gate aggregation — pass, fail, skip semantics."""

    def test_gate_passes_when_all_pass(self) -> None:
        gate = _gate("monolithic", (_PASS("a"), _PASS("b")))
        res = gate.run_task_checks([], {})
        assert res.ok
        assert res.value.passed is True
        assert res.value.failed_checks == ()

    def test_gate_fails_when_any_non_skipped_checker_fails(self) -> None:
        gate = _gate("monolithic", (_PASS("a"), _FAIL("b")))
        res = gate.run_task_checks([], {})
        assert res.ok
        assert res.value.passed is False
        assert "b" in res.value.failed_checks

    def test_skipped_checkers_appear_in_skipped_checks(self) -> None:
        err_checker = _StubChecker(
            "err-chk", ErrorCategory.LINT,
            (CheckLevel.TASK,), _ALL_ARCHS,
            Err("something broke"),
        )
        gate = _gate("monolithic", (err_checker,))
        res = gate.run_task_checks([], {})
        assert res.ok
        assert "err-chk" in res.value.skipped_checks
        assert res.value.passed is True

    def test_crashed_checker_treated_as_skipped(self) -> None:
        crasher = _CrashingChecker(
            "crash", ErrorCategory.SYNTAX,
            (CheckLevel.TASK,), _ALL_ARCHS,
            Ok(CheckResult(checker_name="crash", passed=True, category=ErrorCategory.SYNTAX)),
        )
        gate = _gate("monolithic", (crasher,))
        res = gate.run_task_checks([], {})
        assert res.ok
        assert "crash" in res.value.skipped_checks
        assert res.value.passed is True

    def test_checker_returning_err_treated_as_skipped(self) -> None:
        err_checker = _StubChecker(
            "err-chk", ErrorCategory.COVERAGE,
            (CheckLevel.TASK,), _ALL_ARCHS,
            Err("check failed"),
        )
        gate = _gate("monolithic", (err_checker,))
        res = gate.run_task_checks([], {})
        assert res.ok
        cr = res.value.check_results[0]
        assert cr.skipped is True
        assert "Checker error" in cr.skip_reason


# ---------------------------------------------------------------------------
# Selective re-run
# ---------------------------------------------------------------------------


class TestSelectiveChecks:
    """run_selective_checks runs all applicable checkers regardless of level."""

    def test_runs_all_applicable_checkers(self) -> None:
        task_chk = _PASS("task-chk", levels=(CheckLevel.TASK,))
        svc_chk = _PASS("svc-chk", levels=(CheckLevel.SERVICE,))
        inapplicable = _PASS("other", archs=("microservice",))
        gate = _gate("monolithic", (task_chk, svc_chk, inapplicable))

        res = gate.run_selective_checks(("task-chk",), [], {})
        assert res.ok
        names = [r.checker_name for r in res.value.check_results]
        assert "task-chk" in names
        assert "svc-chk" in names
        assert "other" not in names
