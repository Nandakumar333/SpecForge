"""Line-limit checker — flags functions/classes exceeding size thresholds."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from specforge.core.analyzers.python_analyzer import PythonAnalyzer
from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
    ErrorDetail,
)
from specforge.core.result import Err, Ok

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LineLimitChecker:
    """Checks that functions and classes stay within line-count limits."""

    def __init__(
        self,
        analyzers: tuple = (),
        max_function_lines: int = 30,
        max_class_lines: int = 200,
    ) -> None:
        self._analyzers = analyzers or (PythonAnalyzer(),)
        self._max_fn = max_function_lines
        self._max_cls = max_class_lines

    @property
    def name(self) -> str:
        return "line-limit"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.LINT

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return (CheckLevel.TASK,)

    def is_applicable(self, architecture: str) -> bool:
        return True

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]:
        """Scan changed files for oversized functions/classes."""
        errors: list[ErrorDetail] = []
        warnings: list[str] = []

        for fpath in changed_files:
            ext = fpath.suffix
            analyzer = self._find_analyzer(ext)
            if analyzer is None:
                warnings.append(f"Skipped {fpath}: no analyzer for '{ext}'")
                continue
            self._check_file(fpath, analyzer, errors)

        output = "\n".join(warnings) if warnings else ""
        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=len(errors) == 0,
                category=self.category,
                output=output,
                error_details=tuple(errors),
            )
        )

    # ── Private helpers ───────────────────────────────────────────────

    def _find_analyzer(self, ext: str) -> object | None:
        """Return the first analyzer that supports the given extension."""
        for a in self._analyzers:
            if a.supports_extension(ext):
                return a
        return None

    def _check_file(
        self,
        fpath: Path,
        analyzer: object,
        errors: list[ErrorDetail],
    ) -> None:
        """Run function and class analysis on a single file."""
        self._check_functions(fpath, analyzer, errors)
        self._check_classes(fpath, analyzer, errors)

    def _check_functions(
        self,
        fpath: Path,
        analyzer: object,
        errors: list[ErrorDetail],
    ) -> None:
        """Flag functions exceeding the line limit."""
        result = analyzer.analyze_functions(fpath)  # type: ignore[union-attr]
        if not result.ok:
            return
        for fn in result.value:
            if fn.line_count > self._max_fn:
                errors.append(
                    ErrorDetail(
                        file_path=str(fpath),
                        line_number=fn.start_line,
                        code="line-limit:function",
                        message=(
                            f"Function '{fn.name}' is {fn.line_count}"
                            f" lines (max {self._max_fn})"
                        ),
                    )
                )

    def _check_classes(
        self,
        fpath: Path,
        analyzer: object,
        errors: list[ErrorDetail],
    ) -> None:
        """Flag classes exceeding the line limit."""
        result = analyzer.analyze_classes(fpath)  # type: ignore[union-attr]
        if not result.ok:
            return
        for cls in result.value:
            if cls.line_count > self._max_cls:
                errors.append(
                    ErrorDetail(
                        file_path=str(fpath),
                        line_number=cls.start_line,
                        code="line-limit:class",
                        message=(
                            f"Class '{cls.name}' is {cls.line_count}"
                            f" lines (max {self._max_cls})"
                        ),
                    )
                )
