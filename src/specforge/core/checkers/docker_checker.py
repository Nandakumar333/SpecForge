"""Docker build checker for microservice architectures."""

from __future__ import annotations

import fnmatch
import shutil
import subprocess
from typing import TYPE_CHECKING

from specforge.core.config import CONTAINER_RELEVANT_PATTERNS
from specforge.core.quality_models import (
    CheckLevel,
    CheckResult,
    ErrorCategory,
    ErrorDetail,
)
from specforge.core.result import Err, Ok

if TYPE_CHECKING:
    from pathlib import Path


class DockerBuildChecker:
    """Validates that the Docker image builds successfully."""

    @property
    def name(self) -> str:
        return "docker-build"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.DOCKER

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
        """Run docker build and report errors."""
        if not self._has_container_files(changed_files):
            return Ok(self._skipped("No container-relevant files changed"))

        if not shutil.which("docker"):
            return Ok(self._skipped("Docker CLI not available"))

        slug = self._get_slug(service_context)
        return self._run_build(slug)

    def _has_container_files(self, changed_files: list[Path]) -> bool:
        """Check if any changed file matches container patterns."""
        return any(
            fnmatch.fnmatch(f.name, pat)
            for f in changed_files
            for pat in CONTAINER_RELEVANT_PATTERNS
        )

    def _get_slug(self, service_context: object) -> str:
        """Extract service slug from context."""
        return getattr(service_context, "slug", "service")

    def _run_build(self, slug: str) -> Ok[CheckResult] | Err[str]:
        """Execute docker build and parse output."""
        try:
            result = subprocess.run(
                ["docker", "build", "-t", f"{slug}-test", "."],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return Err("Docker build timed out")

        if result.returncode == 0:
            return Ok(self._passed(result.stdout))

        errors = _parse_docker_errors(result.stderr)
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


def _parse_docker_errors(stderr: str) -> tuple[ErrorDetail, ...]:
    """Extract error details from docker build stderr."""
    errors: list[ErrorDetail] = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped and ("error" in stripped.lower() or "ERROR" in stripped):
            errors.append(
                ErrorDetail(file_path="Dockerfile", message=stripped)
            )
    return tuple(errors) if errors else (
        ErrorDetail(file_path="Dockerfile", message=stderr.strip()),
    )
