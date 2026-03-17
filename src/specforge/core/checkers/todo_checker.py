"""Todo checker — flags TODO/FIXME/HACK/XXX comments in changed files."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from specforge.core.config import TODO_PATTERNS
from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
    ErrorDetail,
)
from specforge.core.result import Err, Ok

logger = logging.getLogger(__name__)

_COMBINED_PATTERN: re.Pattern[str] = re.compile(
    "|".join(TODO_PATTERNS), re.IGNORECASE
)


class TodoChecker:
    """Scans changed files for TODO/FIXME/HACK/XXX comments."""

    @property
    def name(self) -> str:
        return "todo"

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
        """Scan changed files for TODO-style comments."""
        errors: list[ErrorDetail] = []

        for fpath in changed_files:
            _scan_file(fpath, errors)

        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=len(errors) == 0,
                category=self.category,
                error_details=tuple(errors),
            )
        )


def _scan_file(fpath: Path, errors: list[ErrorDetail]) -> None:
    """Read a single file and check each line for TODO patterns."""
    try:
        lines = fpath.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return

    for line_no, line in enumerate(lines, start=1):
        if _COMBINED_PATTERN.search(line):
            errors.append(
                ErrorDetail(
                    file_path=str(fpath),
                    line_number=line_no,
                    code="todo",
                    message=line.strip(),
                )
            )
