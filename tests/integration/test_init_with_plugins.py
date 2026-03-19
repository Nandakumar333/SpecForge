"""Integration tests for init with plugin system."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


class TestInitWithStackPlugin:
    """Test init command with stack plugins generating governance rules."""

    def test_init_with_stack_and_arch_generates_governance(
        self, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                [
                    "init", "myapp",
                    "--stack", "python",
                    "--arch", "microservice",
                    "--no-git",
                ],
            )
            assert result.exit_code == 0, result.output
            backend = (
                Path("myapp") / ".specforge" / "prompts"
                / "backend.python.prompts.md"
            )
            assert backend.exists()
            content = backend.read_text()
            assert "BACK-PYTHON" in content

    def test_init_default_arch_is_monolithic(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["init", "myapp", "--stack", "dotnet", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            backend = (
                Path("myapp") / ".specforge" / "prompts"
                / "backend.dotnet.prompts.md"
            )
            assert backend.exists()
            content = backend.read_text()
            assert "BACK-DOTNET-MO" in content
            assert "BACK-DOTNET-MS" not in content


class TestInitWithAgentPlugin:
    """Test init command generates agent-specific config files."""

    def test_init_with_claude_creates_config(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["init", "myapp", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            claude_file = Path("myapp") / "CLAUDE.md"
            assert claude_file.exists()
            assert claude_file.read_text().strip()

    def test_init_with_cursor_creates_cursorrules(
        self, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["init", "myapp", "--agent", "cursor", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            assert (Path("myapp") / ".cursorrules").exists()


class TestInitCombined:
    """Test init with both stack and agent plugins together."""

    def test_stack_and_agent_together(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                [
                    "init", "myapp",
                    "--stack", "dotnet",
                    "--agent", "claude",
                    "--arch", "microservice",
                    "--no-git",
                ],
            )
            assert result.exit_code == 0, result.output
            assert (Path("myapp") / "CLAUDE.md").exists()
            backend = (
                Path("myapp") / ".specforge" / "prompts"
                / "backend.dotnet.prompts.md"
            )
            assert backend.exists()
            assert "BACK-DOTNET-MS" in backend.read_text()

    def test_init_without_flags_still_works(self, tmp_path: Path) -> None:
        """Existing behavior preserved — no flags = generic."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "myapp", "--no-git"],
            )
            assert result.exit_code == 0, result.output
