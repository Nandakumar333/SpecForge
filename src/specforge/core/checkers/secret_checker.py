"""Secret checker — detects hard-coded credentials and high-entropy strings."""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path

from specforge.core.config import (
    ENTROPY_THRESHOLD,
    SECRET_PATTERNS,
)
from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
    ErrorDetail,
)
from specforge.core.result import Err, Ok

logger = logging.getLogger(__name__)

_COMPILED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern)) for name, pattern in SECRET_PATTERNS
)

_MIN_TOKEN_LEN = 20


class SecretChecker:
    """Scans changed files for hard-coded secrets and high-entropy tokens."""

    @property
    def name(self) -> str:
        return "secret"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.SECURITY

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
        """Scan changed files for secret patterns and entropy anomalies."""
        errors: list[ErrorDetail] = []

        for fpath in changed_files:
            if _is_test_fixture(fpath):
                continue
            _scan_file(fpath, errors)

        return Ok(
            CheckResult(
                checker_name=self.name,
                passed=len(errors) == 0,
                category=self.category,
                error_details=tuple(errors),
            )
        )


def _is_test_fixture(fpath: Path) -> bool:
    """Return True if the file path matches any test-fixture pattern."""
    path_str = fpath.as_posix()
    filename = fpath.name

    # Directory-level patterns: check path contains the directory segment
    for dir_pat in ("tests/", "fixtures/", "testdata/"):
        if dir_pat in path_str:
            return True

    # Filename-level patterns
    return filename.startswith("test_") or filename == "conftest.py"


def _scan_file(fpath: Path, errors: list[ErrorDetail]) -> None:
    """Read file and scan each line for patterns and entropy."""
    try:
        lines = fpath.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return

    for line_no, line in enumerate(lines, start=1):
        _check_patterns(fpath, line_no, line, errors)
        _check_entropy(fpath, line_no, line, errors)


def _check_patterns(
    fpath: Path,
    line_no: int,
    line: str,
    errors: list[ErrorDetail],
) -> None:
    """Match line against all compiled secret patterns."""
    for pat_name, regex in _COMPILED_PATTERNS:
        if regex.search(line):
            errors.append(
                ErrorDetail(
                    file_path=str(fpath),
                    line_number=line_no,
                    code=pat_name,
                    message=f"Potential secret ({pat_name}): {line.strip()}",
                )
            )


def _check_entropy(
    fpath: Path,
    line_no: int,
    line: str,
    errors: list[ErrorDetail],
) -> None:
    """Flag high-entropy tokens that may be secrets."""
    stripped = line.strip()
    if stripped.startswith("#") or stripped.startswith("//"):
        return

    for token in stripped.split():
        token_clean = token.strip("\"'`,;:()[]{}=")
        if len(token_clean) > _MIN_TOKEN_LEN:
            entropy = _shannon_entropy(token_clean)
            if entropy > ENTROPY_THRESHOLD:
                errors.append(
                    ErrorDetail(
                        file_path=str(fpath),
                        line_number=line_no,
                        code="high-entropy",
                        message=(
                            f"High-entropy string (entropy={entropy:.2f}):"
                            f" {token_clean[:40]}..."
                        ),
                    )
                )


def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string in bits per character."""
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )
