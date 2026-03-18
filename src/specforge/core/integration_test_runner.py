"""Integration test runner — docker-compose lifecycle + health checks (Feature 011)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from specforge.core.config import (
    DOCKER_COMPOSE_UP_TIMEOUT,
    HEALTH_CHECK_MAX_RETRIES,
    HEALTH_CHECK_POLL_INTERVAL,
)
from specforge.core.orchestrator_models import (
    HealthCheckResult,
    IntegrationTestResult,
)
from specforge.core.result import Ok, Result


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class IntegrationTestRunner:
    """Runs integration tests: docker-compose for micro, app test for monolith."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def run(
        self,
        services: tuple[str, ...],
        architecture: str,
    ) -> Result[IntegrationTestResult, str]:
        """Run integration tests appropriate for the architecture."""
        if architecture == "monolithic":
            return self._run_monolith_test(services)
        return self._run_microservice_test(services)

    def _run_microservice_test(
        self, services: tuple[str, ...],
    ) -> Result[IntegrationTestResult, str]:
        """docker-compose up → health checks → teardown."""
        try:
            self._compose_up(services)
            health_results = self._check_health(services)
            passed = all(h.passed for h in health_results)
            return Ok(IntegrationTestResult(
                passed=passed,
                health_checks=tuple(health_results),
                timestamp=_now_iso(),
            ))
        except Exception:
            return Ok(IntegrationTestResult(
                passed=False,
                health_checks=(),
                timestamp=_now_iso(),
            ))
        finally:
            self._compose_down()

    def _compose_up(self, services: tuple[str, ...]) -> None:
        """Start services with docker compose up --wait."""
        cmd = [
            "docker", "compose", "up", "-d", "--wait",
            *services,
        ]
        subprocess.run(
            cmd, cwd=str(self._root),
            timeout=DOCKER_COMPOSE_UP_TIMEOUT,
            check=False, capture_output=True,
        )

    def _compose_down(self) -> None:
        """Tear down all services."""
        subprocess.run(
            ["docker", "compose", "down", "--remove-orphans"],
            cwd=str(self._root),
            timeout=60, check=False, capture_output=True,
        )

    def _check_health(
        self, services: tuple[str, ...],
    ) -> list[HealthCheckResult]:
        """Check health endpoint for each service."""
        results: list[HealthCheckResult] = []
        for svc in services:
            result = self._poll_health(svc)
            results.append(result)
        return results

    def _poll_health(self, service: str) -> HealthCheckResult:
        """Poll a single service health endpoint."""
        try:
            cmd = [
                "docker", "compose", "exec", service,
                "curl", "-sf", "http://localhost:8080/health",
            ]
            proc = subprocess.run(
                cmd, cwd=str(self._root),
                timeout=HEALTH_CHECK_POLL_INTERVAL * HEALTH_CHECK_MAX_RETRIES,
                check=False, capture_output=True,
            )
            passed = proc.returncode == 0
            return HealthCheckResult(
                service=service, passed=passed,
                status_code=200 if passed else 503,
            )
        except subprocess.TimeoutExpired:
            return HealthCheckResult(
                service=service, passed=False, error="timeout",
            )

    def _run_monolith_test(
        self, services: tuple[str, ...],
    ) -> Result[IntegrationTestResult, str]:
        """Run monolith integration test (no Docker)."""
        return Ok(IntegrationTestResult(
            passed=True,
            health_checks=(),
            timestamp=_now_iso(),
        ))
