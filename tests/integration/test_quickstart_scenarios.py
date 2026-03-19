"""T057: Integration tests validating quickstart.md scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from specforge.cli.main import cli


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


class TestQuickstartInitScenarios:
    """Verify the init commands from quickstart.md work correctly."""

    def test_python_microservice_with_claude(
        self, runner: CliRunner, tmp_path: Path,
    ) -> None:
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                [
                    "init", "my-api",
                    "--stack", "python",
                    "--arch", "microservice",
                    "--agent", "claude",
                    "--no-git",
                ],
            )
            assert result.exit_code == 0, result.output
            base = Path("my-api")
            assert (base / "CLAUDE.md").exists()
            assert (base / ".specforge").is_dir()
            prompts = base / ".specforge" / "prompts"
            assert prompts.is_dir()
            backend = prompts / "backend.python.prompts.md"
            assert backend.exists()
            assert "BACK-PYTHON" in backend.read_text()

    def test_dotnet_monolith_with_copilot(
        self, runner: CliRunner, tmp_path: Path,
    ) -> None:
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                [
                    "init", "my-app",
                    "--stack", "dotnet",
                    "--arch", "monolithic",
                    "--agent", "copilot",
                    "--no-git",
                ],
            )
            assert result.exit_code == 0, result.output
            base = Path("my-app")
            assert (base / ".specforge").is_dir()
            backend = (
                base / ".specforge" / "prompts"
                / "backend.dotnet.prompts.md"
            )
            assert backend.exists()
            content = backend.read_text()
            assert "BACK-DOTNET-MO" in content

    def test_nodejs_microservice_no_agent(
        self, runner: CliRunner, tmp_path: Path,
    ) -> None:
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                [
                    "init", "my-service",
                    "--stack", "nodejs",
                    "--arch", "microservice",
                    "--no-git",
                ],
            )
            assert result.exit_code == 0, result.output
            base = Path("my-service")
            assert (base / ".specforge").is_dir()
            backend = (
                base / ".specforge" / "prompts"
                / "backend.nodejs.prompts.md"
            )
            assert backend.exists()
            assert "BACK-NODEJS" in backend.read_text()


class TestQuickstartPlugins:
    """Verify 'specforge plugins' shows all plugins."""

    def test_plugins_shows_stack_plugins(
        self, runner: CliRunner,
    ) -> None:
        result = runner.invoke(cli, ["plugins"])
        assert result.exit_code == 0, result.output
        assert "dotnet" in result.output
        assert "python" in result.output
        assert "nodejs" in result.output

    def test_plugins_shows_agent_plugins(
        self, runner: CliRunner,
    ) -> None:
        result = runner.invoke(cli, ["plugins"])
        assert result.exit_code == 0, result.output
        assert "claude" in result.output
        assert "copilot" in result.output
        assert "cursor" in result.output
