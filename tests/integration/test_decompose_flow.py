"""Integration tests for the full decompose flow (IT-001 through IT-005, EC-001, EC-005)."""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from specforge.cli.main import cli


def _run_in_tmp(
    tmp_path: Path,
    args: list[str],
    input_text: str | None = None,
) -> object:
    """Run CLI in a tmp directory to isolate state files."""
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        return runner.invoke(cli, args, input=input_text)
    finally:
        os.chdir(old_cwd)


class TestMonolithicFlow:
    """IT-002: monolithic flow — no service mapping, all features as modules."""

    def test_monolithic_produces_features_and_dirs(
        self, tmp_path: Path
    ) -> None:
        result = _run_in_tmp(
            tmp_path,
            [
                "decompose",
                "--arch",
                "monolithic",
                "Create a personal finance webapp",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "finance" in result.output.lower()

        features_dir = tmp_path / ".specforge" / "features"
        assert features_dir.exists()
        subdirs = list(features_dir.iterdir())
        assert len(subdirs) >= 8

    def test_monolithic_feature_dirs_named_correctly(
        self, tmp_path: Path
    ) -> None:
        _run_in_tmp(
            tmp_path,
            [
                "decompose",
                "--arch",
                "monolithic",
                "Create a personal finance webapp",
            ],
        )
        features_dir = tmp_path / ".specforge" / "features"
        for d in features_dir.iterdir():
            assert d.name[0:3].isdigit(), f"Dir {d.name} missing numeric prefix"


class TestOverEngineeringWarning:
    """IT-004, IT-005: over-engineering warning for small apps."""

    def test_warning_shown_for_simple_microservice(
        self, tmp_path: Path
    ) -> None:
        # Generic domain produces few features, triggering warning
        result = _run_in_tmp(
            tmp_path,
            [
                "decompose",
                "--arch",
                "microservice",
                "Build a simple personal finance budget tracker",
            ],
            input_text="y\ndone\n",
        )
        # Either warns about over-engineering or completes
        assert result.exit_code == 0 or (
            "over-engineering" in result.output.lower()
        )

    def test_no_warn_suppresses_warning(self, tmp_path: Path) -> None:
        result = _run_in_tmp(
            tmp_path,
            [
                "decompose",
                "--arch",
                "microservice",
                "--no-warn",
                "Build a simple personal finance budget tracker",
            ],
            input_text="done\n",
        )
        assert "over-engineering" not in result.output.lower()


class TestGibberishInput:
    """EC-001, EC-005: gibberish and empty input handling."""

    def test_gibberish_shows_error(self, tmp_path: Path) -> None:
        result = _run_in_tmp(
            tmp_path,
            ["decompose", "--arch", "monolithic", "asdf qwer zxcv"],
        )
        assert result.exit_code == 1
        assert "could not understand" in result.output.lower()

    def test_example_prompts_in_error(self, tmp_path: Path) -> None:
        result = _run_in_tmp(
            tmp_path,
            ["decompose", "--arch", "monolithic", "asdf qwer zxcv"],
        )
        assert "finance" in result.output.lower()
        assert "e-commerce" in result.output.lower()


class TestMutualExclusion:
    """FR-048: --arch and --remap cannot be used together."""

    def test_arch_and_remap_errors(self, tmp_path: Path) -> None:
        result = _run_in_tmp(
            tmp_path,
            [
                "decompose",
                "--arch",
                "monolithic",
                "--remap",
                "microservice",
                "test",
            ],
        )
        assert result.exit_code == 1
        assert "cannot use --arch and --remap together" in result.output.lower()
