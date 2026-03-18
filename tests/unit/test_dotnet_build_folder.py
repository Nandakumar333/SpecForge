"""T051: Unit tests for DotnetPlugin build commands and folder structure."""

from __future__ import annotations

import pytest

from specforge.plugins.stacks.dotnet_plugin import DotnetPlugin

ARCHS = ["microservice", "monolithic", "modular-monolith"]


@pytest.fixture()
def plugin() -> DotnetPlugin:
    return DotnetPlugin()


# ── Build Commands ───────────────────────────────────────────────────


class TestDotnetBuildCommandsMicroservice:
    def test_includes_restore(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert any("restore" in c for c in cmds)

    def test_includes_publish(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert any("publish" in c for c in cmds)

    def test_includes_release_config(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert any("Release" in c for c in cmds)

    def test_returns_list_of_strings(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert isinstance(cmds, list)
        assert all(isinstance(c, str) for c in cmds)


class TestDotnetBuildCommandsMonolith:
    def test_includes_restore(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("monolithic")
        assert any("restore" in c for c in cmds)

    def test_includes_build(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("monolithic")
        assert any("build" in c for c in cmds)

    def test_no_publish(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("monolithic")
        assert not any("publish" in c for c in cmds)


class TestDotnetBuildCommandsModularMonolith:
    def test_includes_restore(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("modular-monolith")
        assert any("restore" in c for c in cmds)

    def test_includes_build(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_build_commands("modular-monolith")
        assert any("build" in c for c in cmds)


@pytest.mark.parametrize("arch", ARCHS)
def test_build_commands_non_empty(plugin: DotnetPlugin, arch: str) -> None:
    cmds = plugin.get_build_commands(arch)
    assert len(cmds) > 0


@pytest.mark.parametrize(
    ("arch_a", "arch_b"),
    [("microservice", "monolithic"), ("microservice", "modular-monolith")],
)
def test_build_commands_differ_across_archs(
    plugin: DotnetPlugin, arch_a: str, arch_b: str,
) -> None:
    assert plugin.get_build_commands(arch_a) != plugin.get_build_commands(arch_b)


# ── Test Commands ────────────────────────────────────────────────────


class TestDotnetTestCommands:
    def test_returns_list(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_test_commands()
        assert isinstance(cmds, list)
        assert all(isinstance(c, str) for c in cmds)

    def test_includes_dotnet_test(self, plugin: DotnetPlugin) -> None:
        cmds = plugin.get_test_commands()
        assert any("dotnet test" in c for c in cmds)

    def test_non_empty(self, plugin: DotnetPlugin) -> None:
        assert len(plugin.get_test_commands()) > 0


# ── Folder Structure ─────────────────────────────────────────────────


class TestDotnetFolderMicroservice:
    def test_has_services_dir(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("Services" in k or "service" in k.lower() for k in fs)

    def test_has_deploy_dir(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("deploy" in k.lower() for k in fs)

    def test_has_contracts_or_shared(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any(
            "contract" in k.lower() or "shared" in k.lower()
            or "building" in k.lower()
            for k in fs
        )


class TestDotnetFolderMonolith:
    def test_has_api_dir(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any("api" in k.lower() for k in fs)

    def test_has_domain_or_application(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any(
            "domain" in k.lower() or "application" in k.lower()
            for k in fs
        )

    def test_has_tests(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any("test" in k.lower() for k in fs)


class TestDotnetFolderModularMonolith:
    def test_has_modules_dir(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("modular-monolith")
        assert any("module" in k.lower() for k in fs)

    def test_has_host_or_startup(self, plugin: DotnetPlugin) -> None:
        fs = plugin.get_folder_structure("modular-monolith")
        assert any("host" in k.lower() or "startup" in k.lower() for k in fs)


@pytest.mark.parametrize("arch", ARCHS)
def test_folder_structure_returns_dict(
    plugin: DotnetPlugin, arch: str,
) -> None:
    fs = plugin.get_folder_structure(arch)
    assert isinstance(fs, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in fs.items())


@pytest.mark.parametrize("arch", ARCHS)
def test_folder_structure_non_empty(
    plugin: DotnetPlugin, arch: str,
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
    plugin: DotnetPlugin, arch_a: str, arch_b: str,
) -> None:
    assert plugin.get_folder_structure(arch_a) != plugin.get_folder_structure(arch_b)
