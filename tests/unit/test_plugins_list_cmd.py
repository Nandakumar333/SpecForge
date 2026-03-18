"""Unit tests for specforge plugins list CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from specforge.cli.main import cli


class TestPluginsListCommand:
    """specforge plugins list — table output."""

    def test_list_shows_stack_plugins(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "list"])
        assert result.exit_code == 0, result.output
        assert "Stack Plugins" in result.output
        assert "dotnet" in result.output
        assert "nodejs" in result.output
        assert "python" in result.output

    def test_list_shows_agent_plugins(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "list"])
        assert result.exit_code == 0, result.output
        assert "Agent Plugins" in result.output
        assert "claude" in result.output
        assert "cursor" in result.output

    def test_plugins_group_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["plugins", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
