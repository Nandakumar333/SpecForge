"""Tests for SingleFileAgentPlugin and DirectoryAgentPlugin base classes."""

from __future__ import annotations

from pathlib import Path

from specforge.plugins.agents.directory_base import DirectoryAgentPlugin
from specforge.plugins.agents.single_file_base import SingleFileAgentPlugin


class _MockSingleFile(SingleFileAgentPlugin):
    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "mock-single"
        self._file_path = "MOCK.md"
        self._template_name = "generic.md.j2"


class _MockDirectory(DirectoryAgentPlugin):
    def __init__(self) -> None:
        super().__init__()
        self._agent_id = "mock-dir"
        self._dir_path = ".mock"
        self._file_specs = [("rules.md", "generic.md.j2")]


_CTX = {
    "project_name": "test",
    "stack": "python",
    "architecture": "monolithic",
    "governance_summary": "rules here",
    "agent_name": "mock",
}


class TestSingleFileAgentPlugin:
    def test_agent_name(self) -> None:
        assert _MockSingleFile().agent_name() == "mock-single"

    def test_config_files(self) -> None:
        assert _MockSingleFile().config_files() == ["MOCK.md"]

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        paths = _MockSingleFile().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        assert paths[0].exists()
        content = paths[0].read_text(encoding="utf-8")
        assert "test" in content
        assert "rules here" in content

    def test_generate_creates_parent_dirs(self, tmp_path: Path) -> None:
        plugin = _MockSingleFile()
        plugin._file_path = "nested/dir/MOCK.md"
        paths = plugin.generate_config(tmp_path, _CTX)
        assert paths[0].exists()

    def test_is_agent_plugin_subclass(self) -> None:
        from specforge.plugins.agents.base import AgentPlugin

        assert isinstance(_MockSingleFile(), AgentPlugin)


class TestDirectoryAgentPlugin:
    def test_agent_name(self) -> None:
        assert _MockDirectory().agent_name() == "mock-dir"

    def test_config_files(self) -> None:
        assert _MockDirectory().config_files() == [".mock/rules.md"]

    def test_generate_creates_directory_and_files(self, tmp_path: Path) -> None:
        paths = _MockDirectory().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        assert paths[0].exists()
        content = paths[0].read_text(encoding="utf-8")
        assert "test" in content
        assert "rules here" in content

    def test_generate_multiple_files(self, tmp_path: Path) -> None:
        plugin = _MockDirectory()
        plugin._file_specs = [
            ("rules.md", "generic.md.j2"),
            ("extra.md", "generic.md.j2"),
        ]
        paths = plugin.generate_config(tmp_path, _CTX)
        assert len(paths) == 2
        for p in paths:
            assert p.exists()

    def test_is_agent_plugin_subclass(self) -> None:
        from specforge.plugins.agents.base import AgentPlugin

        assert isinstance(_MockDirectory(), AgentPlugin)
