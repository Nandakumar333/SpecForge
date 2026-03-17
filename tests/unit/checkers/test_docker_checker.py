"""Unit tests for DockerBuildChecker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specforge.core.checkers.docker_checker import DockerBuildChecker
from specforge.core.quality_models import CheckLevel, ErrorCategory


class TestDockerBuildCheckerApplicability:
    """Verify architecture filtering."""

    def test_applicable_for_microservice(self) -> None:
        checker = DockerBuildChecker()
        assert checker.is_applicable("microservice") is True

    def test_not_applicable_for_monolithic(self) -> None:
        checker = DockerBuildChecker()
        assert checker.is_applicable("monolithic") is False

    def test_not_applicable_for_modular_monolith(self) -> None:
        checker = DockerBuildChecker()
        assert checker.is_applicable("modular-monolith") is False

    def test_name_is_docker_build(self) -> None:
        checker = DockerBuildChecker()
        assert checker.name == "docker-build"

    def test_category_is_docker(self) -> None:
        checker = DockerBuildChecker()
        assert checker.category == ErrorCategory.DOCKER

    def test_levels_is_task(self) -> None:
        checker = DockerBuildChecker()
        assert checker.levels == (CheckLevel.TASK,)


class TestDockerBuildCheckerSkip:
    """Verify skip conditions."""

    def test_skip_if_no_container_files_changed(self) -> None:
        checker = DockerBuildChecker()
        files = [Path("src/main.py"), Path("README.md")]
        result = checker.check(files, object())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is True
        assert "No container-relevant files changed" in cr.skip_reason

    @patch("specforge.core.checkers.docker_checker.shutil.which", return_value=None)
    def test_skip_if_docker_not_available(self, mock_which: object) -> None:
        checker = DockerBuildChecker()
        files = [Path("Dockerfile")]
        result = checker.check(files, object())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is True
        assert "Docker CLI not available" in cr.skip_reason


class TestDockerBuildCheckerExecution:
    """Verify build execution."""

    @patch("specforge.core.checkers.docker_checker.subprocess.run")
    @patch("specforge.core.checkers.docker_checker.shutil.which", return_value="/usr/bin/docker")
    def test_successful_build(self, mock_which: object, mock_run: object) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Successfully built abc123", stderr=""
        )
        checker = DockerBuildChecker()
        files = [Path("Dockerfile")]
        result = checker.check(files, object())
        assert result.ok
        cr = result.value
        assert cr.passed is True
        assert cr.skipped is False

    @patch("specforge.core.checkers.docker_checker.subprocess.run")
    @patch("specforge.core.checkers.docker_checker.shutil.which", return_value="/usr/bin/docker")
    def test_failed_build(self, mock_which: object, mock_run: object) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error: COPY failed: file not found"
        )
        checker = DockerBuildChecker()
        files = [Path("Dockerfile")]
        result = checker.check(files, object())
        assert result.ok
        cr = result.value
        assert cr.passed is False
        assert len(cr.error_details) > 0
        assert cr.category == ErrorCategory.DOCKER

    @patch("specforge.core.checkers.docker_checker.subprocess.run")
    @patch("specforge.core.checkers.docker_checker.shutil.which", return_value="/usr/bin/docker")
    def test_build_timeout(self, mock_which: object, mock_run: object) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=300)
        checker = DockerBuildChecker()
        files = [Path("Dockerfile")]
        result = checker.check(files, object())
        assert not result.ok
        assert "timed out" in result.error

    def test_container_relevant_file_matching(self) -> None:
        """Verify fnmatch matching for container patterns."""
        checker = DockerBuildChecker()
        assert checker._has_container_files([Path("Dockerfile")]) is True
        assert checker._has_container_files([Path("docker-compose.yml")]) is True
        assert checker._has_container_files([Path("requirements.txt")]) is True
        assert checker._has_container_files([Path("package.json")]) is True
        assert checker._has_container_files([Path("main.py")]) is False
