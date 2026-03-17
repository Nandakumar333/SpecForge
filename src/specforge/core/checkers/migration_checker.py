"""Migration boundary checker for modular-monolith architectures."""

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

_SQL_TABLE_PATTERN = re.compile(
    r"(?:CREATE\s+TABLE|ALTER\s+TABLE|INSERT\s+INTO|UPDATE|DELETE\s+FROM"
    r"|DROP\s+TABLE|TRUNCATE|FROM|JOIN)\s+(?:`|\")?(\w+)(?:`|\")?",
    re.IGNORECASE,
)

_MIGRATION_FILE_PATTERNS: tuple[str, ...] = (
    "migration",
    "migrate",
    "alembic",
    "flyway",
    "changeset",
)


class MigrationChecker:
    """Detects cross-module table access in migration files."""

    @property
    def name(self) -> str:
        return "migration"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.BOUNDARY

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return (CheckLevel.TASK,)

    def is_applicable(self, architecture: str) -> bool:
        return architecture == "modular-monolith"

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]:
        """Scan migration files for cross-module table references."""
        migration_files = _filter_migration_files(changed_files)
        if not migration_files:
            return Ok(self._passed("No migration files in changeset"))

        boundaries = self._get_table_boundaries(service_context)
        violations = self._find_violations(migration_files, boundaries)

        if not violations:
            return Ok(self._passed("No cross-module table access"))

        return Ok(self._failed(violations))

    def _get_table_boundaries(
        self, ctx: object
    ) -> dict[str, str]:
        """Get table→module ownership map from context."""
        boundaries = getattr(ctx, "table_boundaries", None)
        if boundaries and isinstance(boundaries, dict):
            return boundaries
        return {}

    def _find_violations(
        self,
        migration_files: list[Path],
        boundaries: dict[str, str],
    ) -> tuple[ErrorDetail, ...]:
        """Check migration files for cross-module table access."""
        errors: list[ErrorDetail] = []
        for fpath in migration_files:
            file_module = _extract_module(fpath)
            errs = _check_migration(fpath, file_module, boundaries)
            errors.extend(errs)
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
            output=f"Found {len(errors)} cross-module table access(es)",
            error_details=errors,
        )


def _filter_migration_files(files: list[Path]) -> list[Path]:
    """Keep only files that look like migration files."""
    result: list[Path] = []
    for f in files:
        lower = str(f).lower()
        if any(pat in lower for pat in _MIGRATION_FILE_PATTERNS):
            result.append(f)
    return result


def _extract_module(file_path: Path) -> str | None:
    """Extract module name from migration file path."""
    parts = file_path.parts
    if "src" in parts:
        idx = parts.index("src")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return parts[0] if parts else None


def _check_migration(
    file_path: Path,
    file_module: str | None,
    boundaries: dict[str, str],
) -> list[ErrorDetail]:
    """Check a migration file for cross-module table references."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    errors: list[ErrorDetail] = []
    for i, line in enumerate(content.splitlines(), start=1):
        for match in _SQL_TABLE_PATTERN.finditer(line):
            table = match.group(1)
            owner = boundaries.get(table)
            if owner and file_module and owner != file_module:
                errors.append(
                    ErrorDetail(
                        file_path=str(file_path),
                        line_number=i,
                        message=(
                            f"Cross-module table access: "
                            f"{table} (owned by {owner}) "
                            f"from module {file_module}"
                        ),
                    )
                )
    return errors
