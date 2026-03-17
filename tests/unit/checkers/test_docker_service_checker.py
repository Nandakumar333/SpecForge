"""Unit tests for DockerServiceChecker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specforge.core.checkers.docker_service_checker import DockerServiceChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


class TestDockerServiceCheckerApplicability:
    """Verify architecture filtering."""

    def test_applicable_for_microservice(self) -> None:
        checker = DockerServiceChecker()
        assert checker.is_applicable("microservice") is True

    def test_not_applicable_for_monolithic(self) -> None:
        checker = DockerServiceChecker()
        assert checker.is_applicable("monolithic") is False

    def test_not_applicable_for_modular_monolith(self) -> None:
        checker = DockerServiceChecker()
        assert checker.is_applicable("modular-monolith") is False

    def test_name_is_docker_service(self) -> None:
        checker = DockerServiceChecker()
        assert checker.name == "docker-service"

    def test_category_is_docker(self) -> None:
        checker = DockerServiceChecker()
        assert checker.category == ErrorCategory.DOCKER

    def test_levels_is_service(self) -> None:
        checker = DockerServiceChecker()
        assert checker.levels == (CheckLevel.SERVICE,)


class TestDockerServiceCheckerSkip:
    """Verify skip conditions."""

    @patch("specforge.core.checkers.docker_service_checker.shutil.which", return_value=None)
    def test_skip_if_docker_compose_not_available(self, mock_which: object) -> None:
        checker = DockerServiceChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is True
        assert "docker-compose CLI not available" in cr.skip_reason


class TestDockerServiceCheckerExecution:
    """Verify compose up and health check."""

    @patch("specforge.core.checkers.docker_service_checker.subprocess.run")
    @patch("specforge.core.checkers.docker_service_checker.shutil.which", return_value="/usr/bin/docker-compose")
    def test_compose_success_and_health_pass(self, mock_which: object, mock_run: object) -> None:
        # First call = compose up, second = curl health
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="Started", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="OK", stderr=""),
        ]
        checker = DockerServiceChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is False

    @patch("specforge.core.checkers.docker_service_checker.subprocess.run")
    @patch("specforge.core.checkers.docker_service_checker.shutil.which", return_value="/usr/bin/docker-compose")
    def test_compose_failure(self, mock_which: object, mock_run: object) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error: service 'web' failed to build"
        )
        checker = DockerServiceChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert len(cr.error_details) > 0

    @patch("specforge.core.checkers.docker_service_checker.subprocess.run")
    @patch("specforge.core.checkers.docker_service_checker.shutil.which", return_value="/usr/bin/docker-compose")
    def test_health_check_failure(self, mock_which: object, mock_run: object) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="Started", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Connection refused"),
        ]
        checker = DockerServiceChecker()
        result = checker.check([], object())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert any("Health check failed" in e.message for e in cr.error_details)

    @patch("specforge.core.checkers.docker_service_checker.subprocess.run")
    @patch("specforge.core.checkers.docker_service_checker.shutil.which", return_value="/usr/bin/docker-compose")
    def test_compose_timeout(self, mock_which: object, mock_run: object) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker-compose", timeout=120)
        checker = DockerServiceChecker()
        result = checker.check([], object())
        assert not result.ok
        assert "timed out" in result.error
