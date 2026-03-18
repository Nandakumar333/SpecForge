"""T054: Docker config verification across all stack plugins."""

from __future__ import annotations

import pytest

from specforge.plugins.stack_plugin_base import DockerConfig, StackPlugin
from specforge.plugins.stacks.dotnet_plugin import DotnetPlugin
from specforge.plugins.stacks.nodejs_plugin import NodejsPlugin
from specforge.plugins.stacks.python_plugin import PythonPlugin

ALL_STACK_PLUGINS: list[StackPlugin] = [
    DotnetPlugin(),
    PythonPlugin(),
    NodejsPlugin(),
]

PLUGIN_IDS = [p.plugin_name for p in ALL_STACK_PLUGINS]


@pytest.mark.parametrize(
    "plugin", ALL_STACK_PLUGINS, ids=PLUGIN_IDS,
)
class TestMicroserviceDockerConfig:
    """ALL stack plugins return DockerConfig for 'microservice'."""

    def test_returns_docker_config(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("microservice")
        assert isinstance(dc, DockerConfig)

    def test_base_image_non_empty(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("microservice")
        assert dc is not None
        assert dc.base_image
        assert dc.base_image.strip()

    def test_base_image_has_tag(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("microservice")
        assert dc is not None
        assert ":" in dc.base_image, f"Missing tag in {dc.base_image}"

    def test_build_stages_non_empty(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("microservice")
        assert dc is not None
        assert len(dc.build_stages) >= 2

    def test_build_stages_are_strings(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("microservice")
        assert dc is not None
        assert all(isinstance(s, str) and s.strip() for s in dc.build_stages)

    def test_exposed_ports_non_empty(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("microservice")
        assert dc is not None
        assert len(dc.exposed_ports) >= 1

    def test_exposed_ports_valid_range(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("microservice")
        assert dc is not None
        for port in dc.exposed_ports:
            assert isinstance(port, int)
            assert 1 <= port <= 65535

    def test_health_check_path_starts_with_slash(
        self, plugin: StackPlugin,
    ) -> None:
        dc = plugin.get_docker_config("microservice")
        assert dc is not None
        assert dc.health_check_path.startswith("/")


@pytest.mark.parametrize(
    "plugin", ALL_STACK_PLUGINS, ids=PLUGIN_IDS,
)
class TestMonolithDockerConfig:
    """ALL stack plugins return None for 'monolithic' arch."""

    def test_returns_none(self, plugin: StackPlugin) -> None:
        assert plugin.get_docker_config("monolithic") is None


@pytest.mark.parametrize(
    "plugin", ALL_STACK_PLUGINS, ids=PLUGIN_IDS,
)
class TestModularMonolithDockerConfig:
    """ALL stack plugins return appropriate config for 'modular-monolith'."""

    def test_returns_none_or_docker_config(self, plugin: StackPlugin) -> None:
        dc = plugin.get_docker_config("modular-monolith")
        assert dc is None or isinstance(dc, DockerConfig)


class TestDockerConfigFieldIntegrity:
    """Cross-stack validation of DockerConfig fields."""

    def test_all_stacks_have_unique_base_images(self) -> None:
        images = [
            p.get_docker_config("microservice").base_image
            for p in ALL_STACK_PLUGINS
        ]
        assert len(set(images)) == len(images)

    def test_all_stacks_have_unique_ports(self) -> None:
        ports = [
            p.get_docker_config("microservice").exposed_ports
            for p in ALL_STACK_PLUGINS
        ]
        assert len(set(ports)) == len(ports)

    def test_base_images_are_well_known(self) -> None:
        for plugin in ALL_STACK_PLUGINS:
            dc = plugin.get_docker_config("microservice")
            assert dc is not None
            image = dc.base_image.lower()
            assert any(
                kw in image
                for kw in ("dotnet", "python", "node", "mcr.microsoft")
            ), f"Unexpected base image: {dc.base_image}"
