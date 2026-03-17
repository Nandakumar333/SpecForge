"""Hardcoded URL checker for microservice architectures."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
    ErrorDetail,
)
from specforge.core.result import Err, Ok

if TYPE_CHECKING:
    from pathlib import Path

_URL_PATTERN = re.compile(
    r"https?://[a-zA-Z0-9][\w.\-]+(:\d+)?(/[\w.\-/]*)?"
)

_EXCLUDED_HOSTS: frozenset[str] = frozenset({
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "test.org",
    "test.local",
})

_COMMENT_PATTERN = re.compile(r"^\s*(?:#|//|/\*|\*|<!--)")


class UrlChecker:
    """Detects hardcoded service URLs in microservice source files."""

    @property
    def name(self) -> str:
        return "url"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.BOUNDARY

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return (CheckLevel.TASK,)

    def is_applicable(self, architecture: str) -> bool:
        return architecture == "microservice"

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]:
        """Scan changed files for hardcoded service URLs."""
        violations = self._scan_files(changed_files)

        if not violations:
            return Ok(self._passed("No hardcoded URLs detected"))

        return Ok(self._failed(violations))

    def _scan_files(
        self, changed_files: list[Path]
    ) -> tuple[ErrorDetail, ...]:
        """Scan all changed files for URL violations."""
        errors: list[ErrorDetail] = []
        for fpath in changed_files:
            file_errors = _scan_file_for_urls(fpath)
            errors.extend(file_errors)
        return tuple(errors)

    def _passed(self, output: str) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=True,
            category=self.category,
            output=output,
        )

    def _failed(self, errors: tuple[ErrorDetail, ...]) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=False,
            category=self.category,
            output=f"Found {len(errors)} hardcoded URL(s)",
            error_details=errors,
        )


def _scan_file_for_urls(file_path: Path) -> list[ErrorDetail]:
    """Scan a single file for hardcoded URLs."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    errors: list[ErrorDetail] = []
    for i, line in enumerate(content.splitlines(), start=1):
        if _COMMENT_PATTERN.match(line):
            continue
        for match in _URL_PATTERN.finditer(line):
            url = match.group(0)
            if not _is_excluded_url(url):
                errors.append(
                    ErrorDetail(
                        file_path=str(file_path),
                        line_number=i,
                        message=f"Hardcoded URL: {url}",
                    )
                )
    return errors


def _is_excluded_url(url: str) -> bool:
    """Check if URL host is in the exclusion list."""
    stripped = re.sub(r"^https?://", "", url)
    host = stripped.split(":")[0].split("/")[0]
    return host in _EXCLUDED_HOSTS
