"""Unit tests for DockerManager — all subprocess calls are mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from specforge.core.docker_manager import DockerManager


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create minimal project layout with Dockerfile."""
    dockerfile = tmp_path / "src" / "billing" / "Dockerfile"
    dockerfile.parent.mkdir(parents=True)
    dockerfile.write_text("FROM python:3.11-slim\n")
    return tmp_path


@pytest.fixture()
def mgr(project: Path) -> DockerManager:
    return DockerManager(project_root=project, service_slug="billing")


# ── build_image ──────────────────────────────────────────────────────

class TestBuildImage:
    def test_build_image_runs_docker_build(self, mgr: DockerManager, project: Path) -> None:
        proc = MagicMock(returncode=0, stdout="Successfully built abc123\n", stderr="")
        with patch("specforge.core.docker_manager.subprocess.run", return_value=proc) as mock_run:
            result = mgr.build_image()

        assert result.ok is True
        assert result.value == "billing:latest"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "docker"
        assert args[1] == "build"
        assert "-t" in args
        assert "billing:latest" in args
        assert "-f" in args
        dockerfile = str(project / "src" / "billing" / "Dockerfile")
        assert dockerfile in args

    def test_build_image_returns_err_on_failure(self, mgr: DockerManager) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="error: no space left on device")
        with patch("specforge.core.docker_manager.subprocess.run", return_value=proc):
            result = mgr.build_image()

        assert result.ok is False
        assert "no space left on device" in result.error

    def test_build_image_returns_err_when_dockerfile_missing(self, tmp_path: Path) -> None:
        mgr = DockerManager(project_root=tmp_path, service_slug="billing")
        result = mgr.build_image()
        assert result.ok is False
        assert "Dockerfile not found" in result.error


# ── health_check ─────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_check_polls_health_endpoint(self, mgr: DockerManager) -> None:
        # docker run returns container id
        run_proc = MagicMock(returncode=0, stdout="abc123\n", stderr="")
        # curl succeeds on first poll
        curl_proc = MagicMock(returncode=0, stdout="OK", stderr="")
        # stop + rm succeed
        stop_proc = MagicMock(returncode=0, stdout="", stderr="")
        rm_proc = MagicMock(returncode=0, stdout="", stderr="")

        call_sequence = [run_proc, curl_proc, stop_proc, rm_proc]

        with patch(
            "specforge.core.docker_manager.subprocess.run",
            side_effect=call_sequence,
        ) as mock_run:
            with patch("specforge.core.docker_manager.time.sleep"):
                result = mgr.health_check(timeout=5)

        assert result.ok is True
        calls = mock_run.call_args_list
        # First call: docker run
        assert calls[0][0][0][0] == "docker"
        assert "run" in calls[0][0][0]
        # Second call: curl health endpoint
        assert calls[1][0][0][0] == "curl"
        # Stop call
        assert "stop" in calls[2][0][0]
        # Remove call
        assert "rm" in calls[3][0][0]

    def test_health_check_returns_err_on_timeout(self, mgr: DockerManager) -> None:
        run_proc = MagicMock(returncode=0, stdout="abc123\n", stderr="")
        curl_fail = MagicMock(returncode=7, stdout="", stderr="Connection refused")
        stop_proc = MagicMock(returncode=0, stdout="", stderr="")
        rm_proc = MagicMock(returncode=0, stdout="", stderr="")

        # curl fails every time → timeout
        def side_effect_fn(cmd: list[str], **kwargs: object) -> MagicMock:
            if cmd[0] == "docker" and "run" in cmd:
                return run_proc
            if cmd[0] == "curl":
                return curl_fail
            if cmd[0] == "docker" and "stop" in cmd:
                return stop_proc
            if cmd[0] == "docker" and "rm" in cmd:
                return rm_proc
            return MagicMock(returncode=1)

        with patch(
            "specforge.core.docker_manager.subprocess.run",
            side_effect=side_effect_fn,
        ):
            with patch("specforge.core.docker_manager.time.sleep"):
                result = mgr.health_check(timeout=3)

        assert result.ok is False
        assert "timeout" in result.error.lower() or "health" in result.error.lower()


# ── run_contract_tests ───────────────────────────────────────────────

class TestRunContractTests:
    def test_run_contract_tests_runs_pytest(self, mgr: DockerManager, project: Path) -> None:
        proc = MagicMock(returncode=0, stdout="2 passed\n", stderr="")
        with patch("specforge.core.docker_manager.subprocess.run", return_value=proc) as mock_run:
            result = mgr.run_contract_tests()

        assert result.ok is True
        args = mock_run.call_args[0][0]
        assert args[0] == "pytest"
        expected_dir = str(project / "tests" / "billing" / "contract")
        assert expected_dir in args
        assert "-v" in args

    def test_run_contract_tests_returns_err_on_failure(self, mgr: DockerManager) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="1 failed")
        with patch("specforge.core.docker_manager.subprocess.run", return_value=proc):
            result = mgr.run_contract_tests()

        assert result.ok is False


# ── register_in_compose ──────────────────────────────────────────────

class TestRegisterInCompose:
    def test_register_in_compose_writes_service(self, mgr: DockerManager, project: Path) -> None:
        compose_file = project / "docker-compose.yml"
        compose_file.write_text(
            "version: '3.8'\nservices:\n  existing-svc:\n    image: nginx\n"
        )

        result = mgr.register_in_compose(compose_path=compose_file)

        assert result.ok is True
        import yaml

        data = yaml.safe_load(compose_file.read_text())
        assert "billing" in data["services"]
        assert data["services"]["billing"]["image"] == "billing:latest"
        # Existing service preserved
        assert "existing-svc" in data["services"]

    def test_register_in_compose_creates_new_file(self, mgr: DockerManager, project: Path) -> None:
        compose_file = project / "docker-compose.yml"
        result = mgr.register_in_compose(compose_path=compose_file)

        assert result.ok is True
        import yaml

        data = yaml.safe_load(compose_file.read_text())
        assert "billing" in data["services"]


# ── compose_up / compose_down ────────────────────────────────────────

class TestComposeProfiles:
    def test_compose_up_test_profile(self, mgr: DockerManager) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch("specforge.core.docker_manager.subprocess.run", return_value=proc) as mock_run:
            result = mgr.compose_up_test_profile()

        assert result.ok is True
        args = mock_run.call_args[0][0]
        assert "docker-compose" in args[0] or "docker" in args[0]
        joined = " ".join(args)
        assert "--profile" in joined
        assert "test" in joined
        assert "up" in joined
        assert "-d" in joined

    def test_compose_down_test_profile(self, mgr: DockerManager) -> None:
        proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch("specforge.core.docker_manager.subprocess.run", return_value=proc) as mock_run:
            result = mgr.compose_down_test_profile()

        assert result.ok is True
        args = mock_run.call_args[0][0]
        joined = " ".join(args)
        assert "--profile" in joined
        assert "test" in joined
        assert "down" in joined
