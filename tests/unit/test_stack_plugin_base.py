"""Unit tests for StackPlugin ABC."""

from __future__ import annotations

import pytest

from specforge.plugins.stack_plugin_base import (
    DockerConfig,
    PluginRule,
    StackPlugin,
)


class TestStackPluginABC:
    """StackPlugin cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            StackPlugin()  # type: ignore[abstract]

    def test_partial_implementation_raises(self) -> None:
        class Partial(StackPlugin):
            @property
            def plugin_name(self) -> str:
                return "partial"

        with pytest.raises(TypeError):
            Partial()  # type: ignore[abstract]

    def test_missing_single_method_raises(self) -> None:
        """Omitting just get_test_commands should still fail."""

        class AlmostComplete(StackPlugin):
            @property
            def plugin_name(self) -> str:
                return "almost"

            @property
            def description(self) -> str:
                return "Almost there"

            @property
            def supported_architectures(self) -> list[str]:
                return ["monolithic"]

            def get_prompt_rules(self, arch: str) -> dict[str, list[PluginRule]]:
                return {}

            def get_build_commands(self, arch: str) -> list[str]:
                return []

            def get_docker_config(self, arch: str) -> DockerConfig | None:
                return None

            # get_test_commands intentionally omitted

            def get_folder_structure(self, arch: str) -> dict[str, str]:
                return {}

        with pytest.raises(TypeError):
            AlmostComplete()  # type: ignore[abstract]


class TestStackPluginConcreteSubclass:
    """A fully concrete subclass can be instantiated and used."""

    def _make_plugin(self) -> StackPlugin:
        class StubPlugin(StackPlugin):
            @property
            def plugin_name(self) -> str:
                return "stub"

            @property
            def description(self) -> str:
                return "A stub plugin for testing"

            @property
            def supported_architectures(self) -> list[str]:
                return ["monolithic", "microservice"]

            def get_prompt_rules(self, arch: str) -> dict[str, list[PluginRule]]:
                return {"backend": []}

            def get_build_commands(self, arch: str) -> list[str]:
                return ["make build"]

            def get_docker_config(self, arch: str) -> DockerConfig | None:
                return DockerConfig(
                    base_image="alpine:3.19",
                    build_stages=("build",),
                    exposed_ports=(8080,),
                )

            def get_test_commands(self) -> list[str]:
                return ["make test"]

            def get_folder_structure(self, arch: str) -> dict[str, str]:
                return {"src/": "Application source"}

        return StubPlugin()

    def test_instantiation(self) -> None:
        plugin = self._make_plugin()
        assert isinstance(plugin, StackPlugin)

    def test_plugin_name(self) -> None:
        assert self._make_plugin().plugin_name == "stub"

    def test_description(self) -> None:
        assert self._make_plugin().description == "A stub plugin for testing"

    def test_supported_architectures(self) -> None:
        assert self._make_plugin().supported_architectures == [
            "monolithic",
            "microservice",
        ]

    def test_get_prompt_rules(self) -> None:
        rules = self._make_plugin().get_prompt_rules("monolithic")
        assert "backend" in rules

    def test_get_build_commands(self) -> None:
        cmds = self._make_plugin().get_build_commands("monolithic")
        assert cmds == ["make build"]

    def test_get_docker_config(self) -> None:
        cfg = self._make_plugin().get_docker_config("monolithic")
        assert cfg is not None
        assert cfg.base_image == "alpine:3.19"

    def test_get_test_commands(self) -> None:
        assert self._make_plugin().get_test_commands() == ["make test"]

    def test_get_folder_structure(self) -> None:
        folders = self._make_plugin().get_folder_structure("monolithic")
        assert "src/" in folders
