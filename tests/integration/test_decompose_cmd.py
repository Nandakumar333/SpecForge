"""Integration tests for specforge decompose command."""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


class TestDecomposeCommand:
    def test_with_description_exits_0(self, tmp_path: Path) -> None:
        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(
                cli,
                [
                    "decompose",
                    "--arch",
                    "monolithic",
                    "Create a personal finance webapp",
                ],
            )
            assert result.exit_code == 0, result.output
        finally:
            os.chdir(old_cwd)

    def test_without_description_exits_2(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decompose"])
        assert result.exit_code == 2
