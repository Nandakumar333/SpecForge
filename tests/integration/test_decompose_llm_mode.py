"""Integration tests for LLM decompose mode (--dry-run-prompt and --template-mode)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specforge.cli.main import cli
from specforge.core.result import Ok


def _setup_specforge(tmp_path: Path, agent: str = "claude") -> None:
    """Create minimal .specforge directory with config and constitution."""
    specforge_dir = tmp_path / ".specforge"
    specforge_dir.mkdir(parents=True, exist_ok=True)
    config = {"agent": agent, "stack": "python"}
    (specforge_dir / "config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    (specforge_dir / "constitution.md").write_text(
        "# Constitution\n\nMinimal constitution for testing.\n",
        encoding="utf-8",
    )


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


class TestDryRunPrompt:
    """Tests for --dry-run-prompt flag (writes assembled prompt without calling LLM)."""

    def test_decompose_dry_run_writes_prompt_file(self, tmp_path: Path) -> None:
        _setup_specforge(tmp_path, agent="claude")
        with patch(
            "specforge.core.llm_provider.SubprocessProvider.is_available",
            return_value=Ok(None),
        ):
            result = _run_in_tmp(
                tmp_path,
                ["decompose", "--dry-run-prompt", "Personal Finance App"],
            )
        assert result.exit_code == 0, result.output
        prompt_file = tmp_path / ".specforge" / "decompose.prompt.md"
        assert prompt_file.exists(), (
            f"Expected decompose.prompt.md to be created. Output: {result.output}"
        )

    def test_decompose_prompt_contains_description(self, tmp_path: Path) -> None:
        _setup_specforge(tmp_path, agent="claude")
        with patch(
            "specforge.core.llm_provider.SubprocessProvider.is_available",
            return_value=Ok(None),
        ):
            _run_in_tmp(
                tmp_path,
                ["decompose", "--dry-run-prompt", "Personal Finance App"],
            )
        prompt_file = tmp_path / ".specforge" / "decompose.prompt.md"
        content = prompt_file.read_text(encoding="utf-8")
        assert "Personal Finance App" in content

    def test_decompose_prompt_contains_json_format(self, tmp_path: Path) -> None:
        _setup_specforge(tmp_path, agent="claude")
        with patch(
            "specforge.core.llm_provider.SubprocessProvider.is_available",
            return_value=Ok(None),
        ):
            _run_in_tmp(
                tmp_path,
                ["decompose", "--dry-run-prompt", "Personal Finance App"],
            )
        prompt_file = tmp_path / ".specforge" / "decompose.prompt.md"
        content = prompt_file.read_text(encoding="utf-8").lower()
        assert "json" in content, (
            "Prompt file should reference JSON output format"
        )


class TestTemplateMode:
    """Tests for --template-mode flag (rule-based decomposition, no LLM)."""

    def test_decompose_template_mode_produces_manifest(
        self, tmp_path: Path
    ) -> None:
        _setup_specforge(tmp_path, agent="generic")
        # Provide answers for up to 5 clarification questions, then "done" for mapping
        input_lines = "finance\ngeneral users\nweb app\nbudgeting\nyes\ndone\n"
        result = _run_in_tmp(
            tmp_path,
            [
                "decompose",
                "--template-mode",
                "--arch",
                "microservice",
                "--no-warn",
                "Personal Finance: auth, payments, notifications",
            ],
            input_text=input_lines,
        )
        assert result.exit_code == 0, result.output
        manifest_path = tmp_path / ".specforge" / "manifest.json"
        assert manifest_path.exists(), (
            f"Expected manifest.json to be created. Output: {result.output}"
        )
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "services" in data
        assert "features" in data

    def test_decompose_template_mode_creates_feature_dirs(
        self, tmp_path: Path
    ) -> None:
        _setup_specforge(tmp_path, agent="generic")
        input_lines = "finance\ngeneral users\nweb app\nbudgeting\nyes\ndone\n"
        result = _run_in_tmp(
            tmp_path,
            [
                "decompose",
                "--template-mode",
                "--arch",
                "microservice",
                "--no-warn",
                "Personal Finance: auth, payments, notifications",
            ],
            input_text=input_lines,
        )
        assert result.exit_code == 0, result.output
        features_dir = tmp_path / ".specforge" / "features"
        assert features_dir.exists(), (
            f"Expected features/ directory. Output: {result.output}"
        )
        subdirs = [d for d in features_dir.iterdir() if d.is_dir()]
        assert len(subdirs) >= 1, (
            f"Expected at least one feature subdirectory, got {len(subdirs)}"
        )
