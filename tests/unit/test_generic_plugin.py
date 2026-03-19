"""Tests for GenericPlugin — fallback agent plugin."""

from __future__ import annotations

from pathlib import Path

from specforge.plugins.agents.generic_plugin import GenericPlugin

_CTX = {
    "project_name": "test-project",
    "stack": "python",
    "architecture": "monolithic",
    "governance_summary": "Test governance rules.",
}


class TestGenericPlugin:
    def test_agent_name(self) -> None:
        assert GenericPlugin().agent_name() == "generic"

    def test_config_files_default(self) -> None:
        assert GenericPlugin().config_files() == [
            "commands/rules.md"
        ]

    def test_config_files_custom_dir(self) -> None:
        plugin = GenericPlugin(commands_dir="custom-dir")
        assert plugin.config_files() == ["custom-dir/rules.md"]

    def test_generate_writes_to_default_path(self, tmp_path: Path) -> None:
        paths = GenericPlugin().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        expected = tmp_path / "commands" / "rules.md"
        assert paths[0] == expected
        assert expected.exists()
        content = expected.read_text(encoding="utf-8")
        assert "test-project" in content
        assert "Test governance rules." in content

    def test_generate_uses_generic_agent_name(self, tmp_path: Path) -> None:
        paths = GenericPlugin().generate_config(tmp_path, _CTX)
        content = paths[0].read_text(encoding="utf-8")
        assert "generic" in content.lower()

    def test_generate_custom_dir(self, tmp_path: Path) -> None:
        plugin = GenericPlugin(commands_dir="my-agent")
        paths = plugin.generate_config(tmp_path, _CTX)
        assert paths[0] == tmp_path / "my-agent" / "rules.md"
        assert paths[0].exists()

    def test_commands_dir_default(self) -> None:
        assert GenericPlugin().commands_dir == "commands"

    def test_commands_dir_custom(self) -> None:
        assert GenericPlugin(commands_dir="custom").commands_dir == "custom"
