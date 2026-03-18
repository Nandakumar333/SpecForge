"""Tests for all agent plugins — individual and parametrized."""

from __future__ import annotations

from pathlib import Path

import pytest

from specforge.plugins.agents.claude_plugin import ClaudePlugin
from specforge.plugins.agents.codex_plugin import CodexPlugin
from specforge.plugins.agents.copilot_plugin import CopilotPlugin
from specforge.plugins.agents.cursor_plugin import CursorPlugin
from specforge.plugins.agents.gemini_plugin import GeminiPlugin
from specforge.plugins.agents.kiro_plugin import KiroPlugin
from specforge.plugins.agents.windsurf_plugin import WindsurfPlugin
from specforge.plugins.plugin_manager import PluginManager

_CTX = {
    "project_name": "test-project",
    "stack": "python",
    "architecture": "monolithic",
    "governance_summary": "Test governance rules.",
    "agent_name": "test",
}


# ── Individual reference agent tests ─────────────────────────────────


class TestClaudePlugin:
    def test_agent_name(self) -> None:
        assert ClaudePlugin().agent_name() == "claude"

    def test_config_files(self) -> None:
        assert ClaudePlugin().config_files() == ["CLAUDE.md"]

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        paths = ClaudePlugin().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        assert paths[0].name == "CLAUDE.md"
        content = paths[0].read_text(encoding="utf-8")
        assert "test-project" in content
        assert "Slash Commands" in content


class TestCursorPlugin:
    def test_agent_name(self) -> None:
        assert CursorPlugin().agent_name() == "cursor"

    def test_config_files(self) -> None:
        assert CursorPlugin().config_files() == [".cursorrules"]

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        paths = CursorPlugin().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        assert paths[0].name == ".cursorrules"
        assert paths[0].read_text(encoding="utf-8").strip()


class TestCopilotPlugin:
    def test_agent_name(self) -> None:
        assert CopilotPlugin().agent_name() == "copilot"

    def test_config_files(self) -> None:
        assert CopilotPlugin().config_files() == [
            ".github/copilot-instructions.md"
        ]

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        paths = CopilotPlugin().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        assert paths[0].name == "copilot-instructions.md"
        assert (tmp_path / ".github").is_dir()


class TestWindsurfPlugin:
    def test_agent_name(self) -> None:
        assert WindsurfPlugin().agent_name() == "windsurf"

    def test_config_files(self) -> None:
        assert WindsurfPlugin().config_files() == [".windsurfrules"]


class TestCodexPlugin:
    def test_agent_name(self) -> None:
        assert CodexPlugin().agent_name() == "codex"

    def test_config_files(self) -> None:
        assert CodexPlugin().config_files() == ["AGENTS.md"]


class TestGeminiPlugin:
    def test_agent_name(self) -> None:
        assert GeminiPlugin().agent_name() == "gemini"

    def test_config_files(self) -> None:
        assert GeminiPlugin().config_files() == [".gemini/style-guide.md"]

    def test_generate_creates_directory(self, tmp_path: Path) -> None:
        paths = GeminiPlugin().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        assert (tmp_path / ".gemini").is_dir()


class TestKiroPlugin:
    def test_agent_name(self) -> None:
        assert KiroPlugin().agent_name() == "kiro"

    def test_config_files(self) -> None:
        assert KiroPlugin().config_files() == [".kiro/rules.md"]

    def test_generate_creates_directory(self, tmp_path: Path) -> None:
        paths = KiroPlugin().generate_config(tmp_path, _CTX)
        assert len(paths) == 1
        assert (tmp_path / ".kiro").is_dir()


# ── Parametrized test for ALL discovered agent plugins ───────────────


def _all_agent_plugins() -> list:
    pm = PluginManager()
    pm.discover()
    return pm.list_agent_plugins()


@pytest.mark.parametrize(
    "plugin", _all_agent_plugins(), ids=lambda p: p.agent_name()
)
class TestAllAgentPlugins:
    def test_agent_name_non_empty(self, plugin) -> None:
        assert plugin.agent_name()

    def test_config_files_non_empty(self, plugin) -> None:
        files = plugin.config_files()
        assert files
        for f in files:
            assert isinstance(f, str)
            assert len(f) > 0

    def test_generate_creates_files(self, plugin, tmp_path: Path) -> None:
        context = {
            "project_name": "test-project",
            "stack": "python",
            "architecture": "monolithic",
            "governance_summary": "Test governance rules.",
            "agent_name": plugin.agent_name(),
        }
        paths = plugin.generate_config(tmp_path, context)
        assert len(paths) >= 1
        for p in paths:
            assert p.exists(), f"{p} should exist"
            assert p.stat().st_size > 0, f"{p} should be non-empty"
