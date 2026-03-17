"""Docker Compose service checker for microservice architectures."""

from __future__ import annotations

import shutil
import subprocess
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


class DockerServiceChecker:
    """Validates that services start via docker-compose and pass health checks."""

    @property
    def name(self) -> str:
        return "docker-service"

    @property
    def category(self) -> ErrorCategory:
        return ErrorCategory.DOCKER

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
        """Start services with compose and verify health."""
        if not shutil.which("docker-compose"):
            return Ok(self._skipped("docker-compose CLI not available"))

        compose_result = self._run_compose_up()
        if not compose_result.ok:
            return compose_result

        check_result: CheckResult = compose_result.value  # type: ignore[union-attr]
        if not check_result.passed:
            return compose_result

        endpoint = self._get_health_endpoint(service_context)
        return self._run_health_check(endpoint)

    def _run_compose_up(self) -> Ok[CheckResult] | Err[str]:
        """Execute docker-compose up -d."""
        try:
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return Err("docker-compose up timed out")

        if result.returncode != 0:
            errors = _parse_compose_errors(result.stderr)
            return Ok(self._failed(result.stderr, errors))

        return Ok(self._passed(result.stdout))

    def _get_health_endpoint(self, ctx: object) -> str:
        """Extract health check URL from context."""
        return getattr(ctx, "health_endpoint", "http://localhost:8080/health")

    def _run_health_check(
        self, endpoint: str
    ) -> Ok[CheckResult] | Err[str]:
        """HTTP GET to health check endpoint via curl."""
        try:
            result = subprocess.run(
                ["curl", "-sf", endpoint],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return Ok(self._failed("Health check timed out or curl unavailable", ()))

        if result.returncode != 0:
            err = ErrorDetail(
                file_path="docker-compose.yml",
                message=f"Health check failed: {endpoint}",
            )
            return Ok(self._failed(result.stderr, (err,)))

        return Ok(self._passed(f"Health check passed: {endpoint}"))

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


def _parse_compose_errors(stderr: str) -> tuple[ErrorDetail, ...]:
    """Extract error details from docker-compose stderr."""
    errors: list[ErrorDetail] = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped and ("error" in stripped.lower() or "ERROR" in stripped):
            errors.append(
                ErrorDetail(
                    file_path="docker-compose.yml", message=stripped
                )
            )
    return tuple(errors) if errors else (
        ErrorDetail(
            file_path="docker-compose.yml", message=stderr.strip()
        ),
    )
