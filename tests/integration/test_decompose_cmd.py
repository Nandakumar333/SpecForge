"""Integration tests for specforge decompose command."""

from click.testing import CliRunner

from specforge.cli.main import cli


class TestDecomposeCommand:
    def test_with_description_exits_0(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decompose", "A task manager app"])
        assert result.exit_code == 0, result.output
        assert "task manager" in result.output.lower()

    def test_without_description_exits_2(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decompose"])
        assert result.exit_code == 2
