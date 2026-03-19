"""Unit tests for CommandRegistrar — command file rendering and writing."""

from __future__ import annotations

from pathlib import Path

from specforge.core.command_registrar import CommandFile, CommandRegistrar
from specforge.plugins.agents.claude_plugin import ClaudePlugin
from specforge.plugins.agents.copilot_plugin import CopilotPlugin
from specforge.plugins.agents.gemini_plugin import GeminiPlugin
from specforge.plugins.agents.generic_plugin import GenericPlugin

_CTX = {
    "project_name": "TestApp",
    "stack": "python",
}


class TestCommandFile:
    def test_frozen_dataclass(self) -> None:
        cf = CommandFile(
            stage="decompose",
            filename="specforge.decompose.md",
            relative_path=Path(".claude/commands/specforge.decompose.md"),
            content="test content",
        )
        assert cf.stage == "decompose"
        assert cf.filename == "specforge.decompose.md"
        assert cf.content == "test content"


class TestBuildCommandFiles:
    def test_claude_returns_8_files(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(ClaudePlugin(), _CTX)
        assert len(files) == 8

    def test_claude_filenames(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(ClaudePlugin(), _CTX)
        names = [f.filename for f in files]
        assert "specforge.decompose.md" in names
        assert "specforge.check.md" in names

    def test_claude_relative_paths(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(ClaudePlugin(), _CTX)
        for cf in files:
            assert cf.relative_path.parts[:2] == (".claude", "commands")

    def test_claude_content_nonempty(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(ClaudePlugin(), _CTX)
        for cf in files:
            assert len(cf.content) > 0

    def test_claude_content_has_arguments(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(ClaudePlugin(), _CTX)
        for cf in files:
            assert "$ARGUMENTS" in cf.content

    def test_gemini_returns_toml(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(GeminiPlugin(), _CTX)
        assert len(files) == 8
        for cf in files:
            assert cf.filename.endswith(".toml")
            assert 'prompt = """' in cf.content
            assert 'description = "' in cf.content

    def test_gemini_relative_paths(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(GeminiPlugin(), _CTX)
        for cf in files:
            assert cf.relative_path.parts[:2] == (".gemini", "commands")

    def test_copilot_extension(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(CopilotPlugin(), _CTX)
        assert len(files) == 8
        for cf in files:
            assert cf.filename.endswith(".prompt.md")
            assert cf.relative_path.parts[:2] == (".github", "prompts")

    def test_generic_default_dir(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(GenericPlugin(), _CTX)
        for cf in files:
            assert cf.relative_path.parts[0] == "commands"

    def test_generic_custom_dir(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(
            GenericPlugin(commands_dir="my-cmds"), _CTX,
        )
        for cf in files:
            assert cf.relative_path.parts[0] == "my-cmds"

    def test_content_includes_project_name(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(ClaudePlugin(), _CTX)
        for cf in files:
            assert "TestApp" in cf.content


class TestRegisterCommands:
    def test_writes_8_files(self, tmp_path: Path) -> None:
        reg = CommandRegistrar()
        result = reg.register_commands(ClaudePlugin(), tmp_path, _CTX)
        assert result.ok
        assert len(result.value) == 8
        for p in result.value:
            assert p.exists()

    def test_force_preserves_existing(self, tmp_path: Path) -> None:
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        existing = cmd_dir / "specforge.decompose.md"
        existing.write_text("custom content", encoding="utf-8")

        reg = CommandRegistrar()
        result = reg.register_commands(
            ClaudePlugin(), tmp_path, _CTX, force=True,
        )
        assert result.ok
        assert existing.read_text(encoding="utf-8") == "custom content"
        # Other 7 files should be written
        assert len(result.value) == 7

    def test_creates_directories(self, tmp_path: Path) -> None:
        reg = CommandRegistrar()
        result = reg.register_commands(ClaudePlugin(), tmp_path, _CTX)
        assert result.ok
        assert (tmp_path / ".claude" / "commands").is_dir()

    def test_gemini_toml_files(self, tmp_path: Path) -> None:
        reg = CommandRegistrar()
        result = reg.register_commands(GeminiPlugin(), tmp_path, _CTX)
        assert result.ok
        for p in result.value:
            assert p.suffix == ".toml"
            content = p.read_text(encoding="utf-8")
            assert 'prompt = """' in content

    def test_copilot_prompt_md_files(self, tmp_path: Path) -> None:
        reg = CommandRegistrar()
        result = reg.register_commands(CopilotPlugin(), tmp_path, _CTX)
        assert result.ok
        for p in result.value:
            assert p.name.endswith(".prompt.md")
            assert p.parent.name == "prompts"


class TestTomlRendering:
    def test_toml_has_description(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(GeminiPlugin(), _CTX)
        for cf in files:
            assert cf.content.startswith('description = "')

    def test_toml_no_frontmatter(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(GeminiPlugin(), _CTX)
        for cf in files:
            assert "---" not in cf.content

    def test_toml_ends_with_triple_quotes(self) -> None:
        reg = CommandRegistrar()
        files = reg.build_command_files(GeminiPlugin(), _CTX)
        for cf in files:
            assert cf.content.rstrip().endswith('"""')
