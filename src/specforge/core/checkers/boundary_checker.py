"""Cross-module boundary checker for modular-monolith architectures."""

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

_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
)


class BoundaryChecker:
    """Detects cross-module import violations in modular-monolith projects."""

    @property
    def name(self) -> str:
        return "boundary"

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
        """Analyze changed files for cross-module import violations."""
        modules = self._get_modules(service_context)
        violations = self._find_violations(changed_files, modules)

        if not violations:
            return Ok(self._passed("No cross-module boundary violations"))

        return Ok(self._failed(violations))

    def _get_modules(self, ctx: object) -> dict[str, set[str]]:
        """Get module boundary map from context.

        Returns mapping of module name → set of public export paths.
        Empty dict means use directory convention.
        """
        boundaries = getattr(ctx, "module_boundaries", None)
        if boundaries and isinstance(boundaries, dict):
            return {k: set(v) for k, v in boundaries.items()}
        return {}

    def _find_violations(
        self,
        changed_files: list[Path],
        modules: dict[str, set[str]],
    ) -> tuple[ErrorDetail, ...]:
        """Scan files for cross-module import violations."""
        errors: list[ErrorDetail] = []
        for fpath in changed_files:
            file_module = _extract_module(fpath)
            if not file_module:
                continue
            file_errors = _check_file_imports(fpath, file_module, modules)
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
            output=f"Found {len(errors)} boundary violation(s)",
            error_details=errors,
        )


def _extract_module(file_path: Path) -> str | None:
    """Extract top-level module name from file path."""
    parts = file_path.parts
    if "src" in parts:
        idx = parts.index("src")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return parts[0] if parts else None


def _check_file_imports(
    file_path: Path,
    file_module: str,
    modules: dict[str, set[str]],
) -> list[ErrorDetail]:
    """Check a single file for cross-module import violations."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    errors: list[ErrorDetail] = []
    for i, line in enumerate(content.splitlines(), start=1):
        match = _IMPORT_PATTERN.match(line)
        if not match:
            continue
        import_path = match.group(1) or match.group(2)
        target_module = import_path.split(".")[0]

        if target_module == file_module:
            continue
        if _is_public_import(target_module, import_path, modules):
            continue

        errors.append(
            ErrorDetail(
                file_path=str(file_path),
                line_number=i,
                message=(
                    f"Cross-module import: {file_module} → "
                    f"{target_module} ({import_path})"
                ),
            )
        )
    return errors


def _is_public_import(
    target_module: str,
    import_path: str,
    modules: dict[str, set[str]],
) -> bool:
    """Check if an import uses a module's public API."""
    if target_module not in modules:
        return False
    return import_path in modules[target_module]
