"""T058: Verify public API exports from specforge.plugins."""

from __future__ import annotations


class TestPluginPublicAPI:
    """All documented public classes are importable from specforge.plugins."""

    def test_import_plugin_manager(self) -> None:
        from specforge.plugins import PluginManager
        assert PluginManager is not None

    def test_import_stack_plugin(self) -> None:
        from specforge.plugins import StackPlugin
        assert StackPlugin is not None

    def test_import_agent_plugin(self) -> None:
        from specforge.plugins import AgentPlugin
        assert AgentPlugin is not None

    def test_import_plugin_rule(self) -> None:
        from specforge.plugins import PluginRule
        assert PluginRule is not None

    def test_import_docker_config(self) -> None:
        from specforge.plugins import DockerConfig
        assert DockerConfig is not None

    def test_all_exports_in_dunder_all(self) -> None:
        import specforge.plugins as pkg
        expected = {
            "AgentPlugin",
            "DockerConfig",
            "PluginManager",
            "PluginRule",
            "StackPlugin",
        }
        assert set(pkg.__all__) == expected

    def test_plugin_manager_instantiable(self) -> None:
        from specforge.plugins import PluginManager
        mgr = PluginManager()
        assert hasattr(mgr, "discover")
        assert hasattr(mgr, "get_stack_plugin")
        assert hasattr(mgr, "get_agent_plugin")
        assert hasattr(mgr, "list_stack_plugins")
        assert hasattr(mgr, "list_agent_plugins")

    def test_stack_plugin_is_abstract(self) -> None:
        import pytest

        from specforge.plugins import StackPlugin
        with pytest.raises(TypeError):
            StackPlugin()

    def test_agent_plugin_is_abstract(self) -> None:
        import pytest

        from specforge.plugins import AgentPlugin
        with pytest.raises(TypeError):
            AgentPlugin()

    def test_plugin_rule_is_frozen_dataclass(self) -> None:
        import pytest

        from specforge.plugins import PluginRule
        rule = PluginRule(
            rule_id="TEST-001",
            title="Test",
            severity="ERROR",
            scope="all",
            description="A test rule",
            thresholds={},
            example_correct="good",
            example_incorrect="bad",
        )
        with pytest.raises(AttributeError):
            rule.title = "changed"

    def test_docker_config_is_frozen_dataclass(self) -> None:
        import pytest

        from specforge.plugins import DockerConfig
        dc = DockerConfig(
            base_image="test:latest",
            build_stages=("a", "b"),
            exposed_ports=(80,),
        )
        with pytest.raises(AttributeError):
            dc.base_image = "other"
