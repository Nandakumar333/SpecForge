"""Checker protocol and registry for the quality validation system."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from specforge.core.quality_models import CheckLevel, ErrorCategory

if TYPE_CHECKING:
    from pathlib import Path

    from specforge.core.quality_models import CheckResult
    from specforge.core.result import Err, Ok


@runtime_checkable
class CheckerProtocol(Protocol):
    """Structural interface for all quality checkers."""

    @property
    def name(self) -> str: ...

    @property
    def category(self) -> ErrorCategory: ...

    @property
    def levels(self) -> tuple[CheckLevel, ...]: ...

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]: ...

    def is_applicable(self, architecture: str) -> bool: ...


def get_applicable_checkers(
    checkers: tuple[CheckerProtocol, ...],
    architecture: str,
    level: CheckLevel,
) -> tuple[CheckerProtocol, ...]:
    """Filter checker instances by architecture and execution level.

    Returns only checkers that:
    1. Are applicable to the given architecture
    2. Include the requested level in their levels tuple
    """
    return tuple(
        c for c in checkers
        if c.is_applicable(architecture) and level in c.levels
    )
