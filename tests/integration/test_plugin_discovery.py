"""Integration tests for full plugin discovery."""

from __future__ import annotations

from specforge.plugins.plugin_manager import PluginManager


class TestFullDiscovery:
    """Verify built-in plugin discovery across stack and agent packages."""

    def test_discovers_three_stack_plugins(self) -> None:
        pm = PluginManager()
        pm.discover()
        stacks = pm.list_stack_plugins()
        names = {p.plugin_name for p in stacks}
        assert names == {"dotnet", "nodejs", "python"}

    def test_discovers_25_plus_agent_plugins(self) -> None:
        pm = PluginManager()
        pm.discover()
        agents = pm.list_agent_plugins()
        assert len(agents) >= 25

    def test_all_stack_plugins_have_metadata(self) -> None:
        pm = PluginManager()
        pm.discover()
        for p in pm.list_stack_plugins():
            assert p.plugin_name
            assert p.description
            assert len(p.supported_architectures) >= 1

    def test_all_agent_plugins_have_metadata(self) -> None:
        pm = PluginManager()
        pm.discover()
        for a in pm.list_agent_plugins():
            assert a.agent_name()
            assert a.config_files()
