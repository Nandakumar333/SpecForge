"""Protobuf interface checker for microservice architectures."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
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


class InterfaceChecker:
    """Validates .proto files compile successfully with protoc."""

    @property
    def name(self) -> str:
        return "interface"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.CONTRACT

    @property
    def levels(self) -> tuple[CheckLevel, ...]:
        return (CheckLevel.SERVICE,)

    def is_applicable(self, architecture: str) -> bool:
        return architecture == "microservice"

    def check(
        self,
        changed_files: list[Path],
        service_context: object,
    ) -> Ok[CheckResult] | Err[str]:
        """Find and validate .proto files."""
        project_root = self._get_project_root(service_context)
        proto_files = self._find_proto_files(project_root)

        if not proto_files:
            return Ok(self._skipped("No .proto files found"))

        if not shutil.which("protoc"):
            return Ok(self._skipped("protoc not available"))

        return self._run_protoc(proto_files, project_root)

    def _get_project_root(self, ctx: object) -> Path:
        """Extract project root from context."""
        root = getattr(ctx, "project_root", None)
        return Path(root) if root else Path(".")

    def _find_proto_files(self, root: Path) -> list[Path]:
        """Discover .proto files under project root."""
        return list(root.rglob("*.proto"))

    def _run_protoc(
        self, proto_files: list[Path], root: Path
    ) -> Ok[CheckResult] | Err[str]:
        """Run protoc compilation check."""
        file_args = [str(f) for f in proto_files]
        try:
            result = subprocess.run(
                ["protoc", f"--proto_path={root}", *file_args],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return Err("protoc timed out")

        if result.returncode == 0:
            return Ok(self._passed(f"Compiled {len(proto_files)} .proto file(s)"))

        errors = _parse_protoc_errors(result.stderr)
        return Ok(self._failed(result.stderr, errors))

    def _skipped(self, reason: str) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=True,
            category=self.category,
            skipped=True,
            skip_reason=reason,
        )

    def _passed(self, output: str) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=True,
            category=self.category,
            output=output,
        )

    def _failed(
        self, output: str, errors: tuple[ErrorDetail, ...]
    ) -> CheckResult:
        return CheckResult(
            checker_name=self.name,
            passed=False,
            category=self.category,
            output=output,
            error_details=errors,
        )


def _parse_protoc_errors(stderr: str) -> tuple[ErrorDetail, ...]:
    """Extract error details from protoc stderr."""
    errors: list[ErrorDetail] = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # protoc errors: "file.proto:10:5: error message"
        parts = stripped.split(":", 3)
        if len(parts) >= 4:
            errors.append(
                ErrorDetail(
                    file_path=parts[0],
                    line_number=int(parts[1]) if parts[1].isdigit() else None,
                    column=int(parts[2]) if parts[2].isdigit() else None,
                    message=parts[3].strip(),
                )
            )
        else:
            errors.append(
                ErrorDetail(file_path="proto", message=stripped)
            )
    return tuple(errors) if errors else (
        ErrorDetail(file_path="proto", message=stderr.strip()),
    )
