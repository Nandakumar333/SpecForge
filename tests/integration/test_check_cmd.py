"""Integration tests for specforge check command."""

from unittest.mock import patch

from click.testing import CliRunner

from specforge.cli.main import cli


class TestCheckCommand:
    def test_exit_0_when_all_present(self) -> None:
        runner = CliRunner()
        with (
            patch("specforge.core.checker.shutil.which", return_value="/usr/bin/x"),
            patch("specforge.core.checker._get_version", return_value="1.0.0"),
        ):
            result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0, result.output

    def test_exit_1_when_missing(self) -> None:
        runner = CliRunner()
        with (
            patch("specforge.core.checker.shutil.which", return_value=None),
            patch("specforge.core.checker._get_version", return_value=None),
        ):
            result = runner.invoke(cli, ["check"])
        assert result.exit_code == 1

    def test_agent_flag_adds_agent_check(self) -> None:
        runner = CliRunner()
        with (
            patch("specforge.core.checker.shutil.which", return_value="/usr/bin/x"),
            patch("specforge.core.checker._get_version", return_value="1.0.0"),
        ):
            result = runner.invoke(cli, ["check", "--agent", "claude"])
        assert result.exit_code == 0, result.output
        assert "claude" in result.output.lower()
