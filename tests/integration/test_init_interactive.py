"""Integration tests for interactive agent selection in specforge init."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from specforge.cli.main import cli


class TestInteractiveInit:
    """Tests for interactive agent selection prompt."""

    def test_explicit_agent_claude_creates_commands(
        self, tmp_path: Path,
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            cmd_dir = Path("myapp") / ".claude" / "commands"
            assert cmd_dir.is_dir()
            md_files = list(cmd_dir.glob("specforge.*.md"))
            assert len(md_files) == 8

    def test_explicit_agent_config_json(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            config = json.loads(
                (Path("myapp") / ".specforge" / "config.json").read_text()
            )
            assert config["agent"] == "claude"
            assert config["commands_dir"] == ".claude/commands"

    def test_explicit_agent_copilot_prompt_md(
        self, tmp_path: Path,
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "copilot", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            prompts_dir = Path("myapp") / ".github" / "prompts"
            assert prompts_dir.is_dir()
            prompt_files = list(prompts_dir.glob("specforge.*.prompt.md"))
            assert len(prompt_files) == 8

    def test_explicit_agent_gemini_toml(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "gemini", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            cmd_dir = Path("myapp") / ".gemini" / "commands"
            assert cmd_dir.is_dir()
            toml_files = list(cmd_dir.glob("specforge.*.toml"))
            assert len(toml_files) == 8
            content = toml_files[0].read_text(encoding="utf-8")
            assert 'prompt = """' in content

    def test_explicit_agent_no_prompt_shown(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            assert "Which AI agent" not in result.output

    def test_noninteractive_auto_detect(self, tmp_path: Path) -> None:
        """CliRunner uses non-TTY stdin → auto-detect path used."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "specforge.core.agent_detector.shutil.which",
                return_value=None,
            ):
                result = runner.invoke(
                    cli, ["init", "myapp", "--no-git"],
                )
            assert result.exit_code == 0, result.output
            assert "generic" in result.output.lower()

    def test_force_preserves_existing_commands(
        self, tmp_path: Path,
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # First init
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output

            # Modify one command file
            custom = Path("myapp/.claude/commands/specforge.decompose.md")
            custom.write_text("custom content", encoding="utf-8")

            # Force re-init
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "claude", "--no-git", "--force"],
            )
            assert result.exit_code == 0, result.output
            assert custom.read_text(encoding="utf-8") == "custom content"

    def test_here_with_agent_creates_commands(
        self, tmp_path: Path,
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "--here", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            assert (Path(".claude") / "commands").is_dir()
            md_files = list(Path(".claude/commands").glob("specforge.*.md"))
            assert len(md_files) == 8

    def test_dry_run_no_commands_written(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["init", "myapp", "--agent", "claude", "--dry-run"],
            )
            assert result.exit_code == 0, result.output
            assert not Path("myapp").exists()
            assert "DRY RUN" in result.output or "Would create" in result.output

    def test_command_files_contain_project_name(
        self, tmp_path: Path,
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "TestApp", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            content = (
                Path("TestApp/.claude/commands/specforge.decompose.md")
                .read_text(encoding="utf-8")
            )
            assert "TestApp" in content

    def test_summary_shows_agent_info(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli, ["init", "myapp", "--agent", "claude", "--no-git"],
            )
            assert result.exit_code == 0, result.output
            assert "claude" in result.output.lower()
            assert "commands" in result.output.lower()


class TestCommandsDirectoryValidation:
    """Tests for _validate_commands_dir path validation."""

    def test_valid_relative_path(self) -> None:
        from specforge.cli.init_cmd import _validate_commands_dir

        result = _validate_commands_dir("my-commands")
        assert result.ok
        assert result.value == "my-commands"

    def test_rejects_absolute_path(self) -> None:
        from specforge.cli.init_cmd import _validate_commands_dir

        result = _validate_commands_dir("/absolute/path")
        assert not result.ok
        assert "relative" in result.error.lower()

    def test_rejects_traversal(self) -> None:
        from specforge.cli.init_cmd import _validate_commands_dir

        result = _validate_commands_dir("../escape")
        assert not result.ok
        assert "traverse" in result.error.lower()

    def test_rejects_empty(self) -> None:
        from specforge.cli.init_cmd import _validate_commands_dir

        result = _validate_commands_dir("")
        assert not result.ok
        assert "empty" in result.error.lower()

    def test_normalizes_backslashes(self) -> None:
        from specforge.cli.init_cmd import _validate_commands_dir

        result = _validate_commands_dir("my\\commands")
        assert result.ok
        assert result.value == "my/commands"
