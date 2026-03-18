"""Integration tests for custom plugin loading from project directories."""

from __future__ import annotations

from pathlib import Path

from specforge.plugins.plugin_manager import PluginManager

_CUSTOM_STACK_TEMPLATE = '''\
from specforge.plugins.stack_plugin_base import StackPlugin, PluginRule, DockerConfig


class {class_name}(StackPlugin):
    @property
    def plugin_name(self):
        return "{name}"

    @property
    def description(self):
        return "{desc}"

    @property
    def supported_architectures(self):
        return ["monolithic"]

    def get_prompt_rules(self, arch):
        return {{}}

    def get_build_commands(self, arch):
        return []

    def get_docker_config(self, arch):
        return None

    def get_test_commands(self):
        return []

    def get_folder_structure(self, arch):
        return {{}}
'''


class TestCustomPluginDiscovery:
    """Custom plugin loading from .specforge/plugins/."""

    def test_no_custom_dir_still_works(self, tmp_path: Path) -> None:
        pm = PluginManager(project_root=tmp_path)
        result = pm.discover()
        assert result.ok

    def test_loads_custom_stack_plugin(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / ".specforge" / "plugins" / "stacks"
        custom_dir.mkdir(parents=True)
        code = _CUSTOM_STACK_TEMPLATE.format(
            class_name="CustomPlugin",
            name="custom",
            desc="Custom test plugin",
        )
        (custom_dir / "custom_plugin.py").write_text(code)

        pm = PluginManager(project_root=tmp_path)
        pm.discover()
        result = pm.get_stack_plugin("custom")
        assert result.ok
        assert result.value.plugin_name == "custom"

    def test_custom_overrides_builtin(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / ".specforge" / "plugins" / "stacks"
        custom_dir.mkdir(parents=True)
        code = _CUSTOM_STACK_TEMPLATE.format(
            class_name="CustomDotnetPlugin",
            name="dotnet",
            desc="Custom dotnet override",
        )
        (custom_dir / "custom_dotnet_plugin.py").write_text(code)

        pm = PluginManager(project_root=tmp_path)
        pm.discover()
        result = pm.get_stack_plugin("dotnet")
        assert result.ok
        assert result.value.description == "Custom dotnet override"

    def test_invalid_plugin_is_skipped(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / ".specforge" / "plugins" / "stacks"
        custom_dir.mkdir(parents=True)
        (custom_dir / "bad_plugin.py").write_text(
            "raise ImportError('broken')"
        )

        pm = PluginManager(project_root=tmp_path)
        result = pm.discover()
        assert result.ok
