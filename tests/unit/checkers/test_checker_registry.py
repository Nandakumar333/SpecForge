"""Unit tests for CheckerProtocol and get_applicable_checkers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from specforge.core.result import Ok, Err


class TestCheckerProtocol:
    """Verify CheckerProtocol is runtime-checkable and structurally typed."""

    def test_protocol_is_runtime_checkable(self) -> None:
        from specforge.core.checkers import CheckerProtocol

        assert hasattr(CheckerProtocol, "__protocol_attrs__") or hasattr(
            CheckerProtocol, "__abstractmethods__"
        )
        # runtime_checkable protocols support isinstance()
        assert isinstance(CheckerProtocol, type)

    def test_conforming_class_is_instance(self) -> None:
        from specforge.core.checkers import CheckerProtocol
        from specforge.core.quality_models import CheckLevel, CheckResult, ErrorCategory
        from specforge.core.result import Ok

        class FakeChecker:
            @property
            def name(self) -> str:
                return "fake"

            @property
            def category(self) -> ErrorCategory:
                return ErrorCategory.LINT

            @property
            def levels(self) -> tuple[CheckLevel, ...]:
                return (CheckLevel.TASK,)

            def check(
                self,
                changed_files: list[Path],
                service_context: object,
            ) -> Ok[CheckResult] | Err[str]:
                return Ok(
                    CheckResult(
                        checker_name="fake",
                        passed=True,
                        category=ErrorCategory.LINT,
                    )
                )

            def is_applicable(self, architecture: str) -> bool:
                return True

        assert isinstance(FakeChecker(), CheckerProtocol)

    def test_non_conforming_class_is_not_instance(self) -> None:
        from specforge.core.checkers import CheckerProtocol

        class Incomplete:
            """Missing required protocol methods."""

            @property
            def name(self) -> str:
                return "incomplete"

        assert not isinstance(Incomplete(), CheckerProtocol)


class TestGetApplicableCheckers:
    """Verify filtering by architecture and execution level."""

    def _make_checker(
        self,
        *,
        name: str = "test",
        architectures: tuple[str, ...] = ("monolithic",),
        levels: tuple[object, ...] | None = None,
    ) -> object:
        from specforge.core.quality_models import CheckLevel, CheckResult, ErrorCategory
        from specforge.core.result import Ok

        _levels = levels or (CheckLevel.TASK,)

        class _Checker:
            @property
            def name(self) -> str:
                return name

            @property
            def category(self) -> ErrorCategory:
                return ErrorCategory.LINT

            @property
            def levels(self) -> tuple[CheckLevel, ...]:
                return _levels  # type: ignore[return-value]

            def check(
                self,
                changed_files: list[Path],
                service_context: object,
            ) -> Ok[CheckResult] | Err[str]:
                return Ok(
                    CheckResult(
                        checker_name=name,
                        passed=True,
                        category=ErrorCategory.LINT,
                    )
                )

            def is_applicable(self, architecture: str) -> bool:
                return architecture in architectures

        return _Checker()

    def test_filters_by_architecture_includes(self) -> None:
        from specforge.core.checkers import get_applicable_checkers
        from specforge.core.quality_models import CheckLevel

        micro = self._make_checker(name="micro", architectures=("microservice",))
        result = get_applicable_checkers(
            (micro,), "microservice", CheckLevel.TASK  # type: ignore[arg-type]
        )
        assert len(result) == 1
        assert result[0].name == "micro"

    def test_filters_by_architecture_excludes(self) -> None:
        from specforge.core.checkers import get_applicable_checkers
        from specforge.core.quality_models import CheckLevel

        micro = self._make_checker(name="micro", architectures=("microservice",))
        result = get_applicable_checkers(
            (micro,), "monolithic", CheckLevel.TASK  # type: ignore[arg-type]
        )
        assert len(result) == 0

    def test_universal_checker_always_included(self) -> None:
        from specforge.core.checkers import get_applicable_checkers
        from specforge.core.quality_models import CheckLevel

        universal = self._make_checker(
            name="universal",
            architectures=("monolithic", "microservice", "modular"),
        )
        for arch in ("monolithic", "microservice", "modular"):
            result = get_applicable_checkers(
                (universal,), arch, CheckLevel.TASK  # type: ignore[arg-type]
            )
            assert len(result) == 1

    def test_filters_by_level_includes(self) -> None:
        from specforge.core.checkers import get_applicable_checkers
        from specforge.core.quality_models import CheckLevel

        task_checker = self._make_checker(
            name="task-only", levels=(CheckLevel.TASK,)
        )
        result = get_applicable_checkers(
            (task_checker,), "monolithic", CheckLevel.TASK  # type: ignore[arg-type]
        )
        assert len(result) == 1

    def test_filters_by_level_excludes(self) -> None:
        from specforge.core.checkers import get_applicable_checkers
        from specforge.core.quality_models import CheckLevel

        task_checker = self._make_checker(
            name="task-only", levels=(CheckLevel.TASK,)
        )
        result = get_applicable_checkers(
            (task_checker,), "monolithic", CheckLevel.SERVICE  # type: ignore[arg-type]
        )
        assert len(result) == 0

    def test_multi_level_checker_included_for_both(self) -> None:
        from specforge.core.checkers import get_applicable_checkers
        from specforge.core.quality_models import CheckLevel

        both = self._make_checker(
            name="both", levels=(CheckLevel.TASK, CheckLevel.SERVICE)
        )
        for level in (CheckLevel.TASK, CheckLevel.SERVICE):
            result = get_applicable_checkers(
                (both,), "monolithic", level  # type: ignore[arg-type]
            )
            assert len(result) == 1

    def test_empty_checkers_returns_empty(self) -> None:
        from specforge.core.checkers import get_applicable_checkers
        from specforge.core.quality_models import CheckLevel

        result = get_applicable_checkers((), "monolithic", CheckLevel.TASK)
        assert result == ()
