"""Unit tests for specforge plugins CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from specforge.cli.main import cli


class TestPluginsCommand:
    """specforge plugins — table output."""

    def test_shows_stack_plugins(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["plugins"])
        assert result.exit_code == 0, result.output
        assert "Stack Plugins" in result.output
        assert "dotnet" in result.output
        assert "nodejs" in result.output
        assert "python" in result.output

    def test_shows_agent_plugins(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["plugins"])
        assert result.exit_code == 0, result.output
        assert "Agent Plugins" in result.output
        assert "claude" in result.output
        assert "cursor" in result.output

    def test_plugins_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "--help"])
        assert result.exit_code == 0
        assert "plugins" in result.output.lower()
