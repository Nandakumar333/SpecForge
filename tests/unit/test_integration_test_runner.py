"""Unit tests for integration_test_runner.py — docker-compose + health checks."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge.core.integration_test_runner import IntegrationTestRunner
from specforge.core.orchestrator_models import (
    IntegrationTestResult,
)


@pytest.fixture()
def runner(tmp_path: Path) -> IntegrationTestRunner:
    return IntegrationTestRunner(project_root=tmp_path)


class TestIntegrationTestRunner:
    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_run_microservice_starts_compose(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.run(
            services=("identity-service", "ledger-service"),
            architecture="microservice",
        )

        assert result.ok
        # docker compose up should have been called
        compose_calls = [
            c for c in mock_run.call_args_list
            if "compose" in str(c) and "up" in str(c)
        ]
        assert len(compose_calls) > 0

    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_run_health_checks_all_pass(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.run(
            services=("svc-a", "svc-b", "svc-c"),
            architecture="microservice",
        )

        assert result.ok
        itr = result.value
        assert itr.passed is True

    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_run_health_check_failure(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            cmd_str = " ".join(str(c) for c in cmd)
            if "up" in cmd_str:
                return MagicMock(returncode=0)
            if "down" in cmd_str:
                return MagicMock(returncode=0)
            # health check fails
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)

        mock_run.side_effect = side_effect

        result = runner.run(
            services=("failing-service",),
            architecture="microservice",
        )

        assert result.ok
        assert result.value.passed is False

    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_run_teardown_always_called(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        # First call (compose up) succeeds, health check fails
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            cmd = args[0] if args else kwargs.get("args", [])
            cmd_str = " ".join(str(c) for c in cmd)
            if "down" in cmd_str:
                return MagicMock(returncode=0)
            if call_count > 1:
                raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        runner.run(services=("svc",), architecture="microservice")

        # docker compose down should have been called
        down_calls = [
            c for c in mock_run.call_args_list
            if "down" in str(c)
        ]
        assert len(down_calls) > 0

    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_run_monolith_mode(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.run(
            services=("module-a",),
            architecture="monolithic",
        )

        assert result.ok
        # No docker compose calls in monolith mode
        compose_calls = [
            c for c in mock_run.call_args_list
            if "compose" in str(c)
        ]
        assert len(compose_calls) == 0

    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_run_returns_integration_test_result(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.run(
            services=("svc-a", "svc-b"),
            architecture="microservice",
        )

        assert result.ok
        itr = result.value
        assert isinstance(itr, IntegrationTestResult)
        assert itr.timestamp is not None

    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_compose_up_waits_for_dependencies(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)

        runner.run(
            services=("svc-a",),
            architecture="microservice",
        )

        # Verify --wait flag is used
        up_calls = [
            c for c in mock_run.call_args_list
            if "up" in str(c)
        ]
        assert any("--wait" in str(c) for c in up_calls)

    @patch("specforge.core.integration_test_runner.subprocess.run")
    def test_compose_up_subset_for_verification(
        self, mock_run: MagicMock, runner: IntegrationTestRunner,
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.run(
            services=("identity-service", "admin-service"),
            architecture="microservice",
        )

        assert result.ok
        # Services should be passed to compose up
        up_calls = [
            c for c in mock_run.call_args_list
            if "up" in str(c)
        ]
        assert len(up_calls) > 0
