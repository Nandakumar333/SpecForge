"""Unit tests for PluginManager — discovery, lookup, listing."""

from __future__ import annotations

from pathlib import Path

from specforge.core.result import Err, Ok
from specforge.plugins.agents.base import AgentPlugin
from specforge.plugins.stack_plugin_base import (
    DockerConfig,
    PluginRule,
    StackPlugin,
)


# ── Stub implementations for testing ────────────────────────────────


class _StubStack(StackPlugin):
    """Minimal concrete StackPlugin for test registration."""

    def __init__(self, name: str = "stub") -> None:
        self._name = name

    @property
    def plugin_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"{self._name} plugin"

    @property
    def supported_architectures(self) -> list[str]:
        return ["monolithic"]

    def get_prompt_rules(self, arch: str) -> dict[str, list[PluginRule]]:
        return {}

    def get_build_commands(self, arch: str) -> list[str]:
        return []

    def get_docker_config(self, arch: str) -> DockerConfig | None:
        return None

    def get_test_commands(self) -> list[str]:
        return []

    def get_folder_structure(self, arch: str) -> dict[str, str]:
        return {}


class _StubAgent(AgentPlugin):
    """Minimal concrete AgentPlugin for test registration."""

    def __init__(self, name: str = "stub-agent") -> None:
        self._name = name

    def agent_name(self) -> str:
        return self._name

    def generate_config(
        self, target_dir: Path, context: dict
    ) -> list[Path]:
        return []

    def config_files(self) -> list[str]:
        return []


# ── Tests ────────────────────────────────────────────────────────────


class TestPluginManagerDiscover:
    """discover() scans built-in plugin packages."""

    def test_discover_returns_ok(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        result = mgr.discover()
        assert result.ok

    def test_discover_count_with_empty_packages(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        result = mgr.discover()
        # No concrete plugins yet, so count should be the existing agents
        assert isinstance(result, Ok)
        assert isinstance(result.value, int)


class TestPluginManagerGetStack:
    """get_stack_plugin() lookup."""

    def test_unknown_returns_err(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        result = mgr.get_stack_plugin("nonexistent")
        assert isinstance(result, Err)
        assert "nonexistent" in result.error

    def test_err_lists_available(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        mgr._stack_plugins["alpha"] = _StubStack("alpha")
        result = mgr.get_stack_plugin("unknown")
        assert isinstance(result, Err)
        assert "alpha" in result.error

    def test_known_returns_ok(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        stub = _StubStack("mystack")
        mgr._stack_plugins["mystack"] = stub
        result = mgr.get_stack_plugin("mystack")
        assert isinstance(result, Ok)
        assert result.value is stub


class TestPluginManagerGetAgent:
    """get_agent_plugin() lookup."""

    def test_unknown_returns_err(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        result = mgr.get_agent_plugin("nonexistent")
        assert isinstance(result, Err)
        assert "nonexistent" in result.error

    def test_err_lists_available(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        mgr._agent_plugins["beta"] = _StubAgent("beta")
        result = mgr.get_agent_plugin("unknown")
        assert isinstance(result, Err)
        assert "beta" in result.error

    def test_known_returns_ok(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        stub = _StubAgent("myagent")
        mgr._agent_plugins["myagent"] = stub
        result = mgr.get_agent_plugin("myagent")
        assert isinstance(result, Ok)
        assert result.value is stub


class TestPluginManagerListPlugins:
    """list_stack_plugins() / list_agent_plugins() sorted output."""

    def test_list_stack_empty(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        assert mgr.list_stack_plugins() == []

    def test_list_stack_sorted(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        mgr._stack_plugins["zeta"] = _StubStack("zeta")
        mgr._stack_plugins["alpha"] = _StubStack("alpha")
        mgr._stack_plugins["mid"] = _StubStack("mid")

        names = [p.plugin_name for p in mgr.list_stack_plugins()]
        assert names == ["alpha", "mid", "zeta"]

    def test_list_agent_empty(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        assert mgr.list_agent_plugins() == []

    def test_list_agent_sorted(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        mgr._agent_plugins["copilot"] = _StubAgent("copilot")
        mgr._agent_plugins["claude"] = _StubAgent("claude")

        names = [p.agent_name() for p in mgr.list_agent_plugins()]
        assert names == ["claude", "copilot"]


class TestPluginManagerProjectRoot:
    """project_root parameter."""

    def test_stores_project_root(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        root = Path("/my/project")
        mgr = PluginManager(project_root=root)
        assert mgr._project_root == root

    def test_none_project_root(self) -> None:
        from specforge.plugins.plugin_manager import PluginManager

        mgr = PluginManager()
        assert mgr._project_root is None
