"""T053: Unit tests for NodejsPlugin build commands and folder structure."""

from __future__ import annotations

import pytest

from specforge.plugins.stacks.nodejs_plugin import NodejsPlugin

ARCHS = ["microservice", "monolithic", "modular-monolith"]


@pytest.fixture()
def plugin() -> NodejsPlugin:
    return NodejsPlugin()


# ── Build Commands ───────────────────────────────────────────────────


class TestNodejsBuildCommandsMicroservice:
    def test_includes_npm_ci(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert any("npm ci" in c for c in cmds)

    def test_includes_build(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert any("build" in c for c in cmds)

    def test_returns_list_of_strings(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert isinstance(cmds, list)
        assert all(isinstance(c, str) for c in cmds)


class TestNodejsBuildCommandsMonolith:
    def test_includes_npm_ci(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_build_commands("monolithic")
        assert any("npm ci" in c for c in cmds)

    def test_includes_build(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_build_commands("monolithic")
        assert any("build" in c for c in cmds)


class TestNodejsBuildCommandsModularMonolith:
    def test_includes_npm_ci(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_build_commands("modular-monolith")
        assert any("npm" in c for c in cmds)


@pytest.mark.parametrize("arch", ARCHS)
def test_build_commands_non_empty(plugin: NodejsPlugin, arch: str) -> None:
    cmds = plugin.get_build_commands(arch)
    assert len(cmds) > 0


# ── Test Commands ────────────────────────────────────────────────────


class TestNodejsTestCommands:
    def test_returns_list(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_test_commands()
        assert isinstance(cmds, list)
        assert all(isinstance(c, str) for c in cmds)

    def test_includes_npm_test(self, plugin: NodejsPlugin) -> None:
        cmds = plugin.get_test_commands()
        assert any("npm test" in c for c in cmds)

    def test_non_empty(self, plugin: NodejsPlugin) -> None:
        assert len(plugin.get_test_commands()) > 0


# ── Folder Structure ─────────────────────────────────────────────────


class TestNodejsFolderMicroservice:
    def test_has_services_dir(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("service" in k.lower() for k in fs)

    def test_has_deploy_dir(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("deploy" in k.lower() for k in fs)

    def test_has_shared_packages(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("shared" in k.lower() or "package" in k.lower() for k in fs)


class TestNodejsFolderMonolith:
    def test_has_src_dir(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any("src" in k.lower() for k in fs)

    def test_has_routes_or_services(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any(
            "route" in k.lower() or "service" in k.lower()
            for k in fs
        )

    def test_has_tests(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any("test" in k.lower() for k in fs)


class TestNodejsFolderModularMonolith:
    def test_has_modules_dir(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("modular-monolith")
        assert any("module" in k.lower() for k in fs)

    def test_has_shared(self, plugin: NodejsPlugin) -> None:
        fs = plugin.get_folder_structure("modular-monolith")
        assert any("shared" in k.lower() for k in fs)


@pytest.mark.parametrize("arch", ARCHS)
def test_folder_structure_returns_dict(
    plugin: NodejsPlugin, arch: str,
) -> None:
    fs = plugin.get_folder_structure(arch)
    assert isinstance(fs, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in fs.items())


@pytest.mark.parametrize("arch", ARCHS)
def test_folder_structure_non_empty(
    plugin: NodejsPlugin, arch: str,
) -> None:
    assert len(plugin.get_folder_structure(arch)) > 0


@pytest.mark.parametrize(
    ("arch_a", "arch_b"),
    [
        ("microservice", "monolithic"),
        ("microservice", "modular-monolith"),
        ("monolithic", "modular-monolith"),
    ],
)
def test_folder_structures_differ(
    plugin: NodejsPlugin, arch_a: str, arch_b: str,
) -> None:
    assert plugin.get_folder_structure(arch_a) != plugin.get_folder_structure(arch_b)
