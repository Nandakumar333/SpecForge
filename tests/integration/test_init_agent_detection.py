"""Integration tests for agent auto-detection in specforge init."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specforge.cli.main import cli


class TestInitAgentDetection:
    def test_claude_only_detects_claude(self, tmp_path: Path) -> None:
        runner = CliRunner()

        def fake_which(name: str) -> str | None:
            return "/usr/bin/claude" if name == "claude" else None

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("specforge.core.agent_detector.shutil.which", fake_which):
                result = runner.invoke(cli, ["init", "myapp", "--no-git"])
            assert result.exit_code == 0, result.output
            assert "claude" in result.output.lower()
            assert "auto-detected" in result.output.lower()

    def test_no_agents_detects_generic(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "specforge.core.agent_detector.shutil.which",
                return_value=None,
            ):
                result = runner.invoke(cli, ["init", "myapp", "--no-git"])
            assert result.exit_code == 0, result.output
            assert "generic" in result.output.lower()

    def test_multiple_agents_first_in_priority(self, tmp_path: Path) -> None:
        runner = CliRunner()
        available = {"copilot", "cursor"}

        def fake_which(name: str) -> str | None:
            return f"/usr/bin/{name}" if name in available else None

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("specforge.core.agent_detector.shutil.which", fake_which):
                result = runner.invoke(cli, ["init", "myapp", "--no-git"])
            assert result.exit_code == 0, result.output
            assert "copilot" in result.output.lower()

    def test_explicit_agent_overrides_detection(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "specforge.core.agent_detector.shutil.which",
                return_value="/usr/bin/claude",
            ):
                result = runner.invoke(cli, ["init", "myapp", "--agent", "gemini"])
            assert result.exit_code == 0, result.output
            assert "gemini" in result.output.lower()
            assert "explicit" in result.output.lower()
