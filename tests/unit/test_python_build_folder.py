"""T052: Unit tests for PythonPlugin build commands and folder structure."""

from __future__ import annotations

import pytest

from specforge.plugins.stacks.python_plugin import PythonPlugin

ARCHS = ["microservice", "monolithic", "modular-monolith"]


@pytest.fixture()
def plugin() -> PythonPlugin:
    return PythonPlugin()


# ── Build Commands ───────────────────────────────────────────────────


class TestPythonBuildCommandsMicroservice:
    def test_includes_pip_install(self, plugin: PythonPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert any("install" in c for c in cmds)

    def test_returns_list_of_strings(self, plugin: PythonPlugin) -> None:
        cmds = plugin.get_build_commands("microservice")
        assert isinstance(cmds, list)
        assert all(isinstance(c, str) for c in cmds)


class TestPythonBuildCommandsMonolith:
    def test_includes_pip_install(self, plugin: PythonPlugin) -> None:
        cmds = plugin.get_build_commands("monolithic")
        assert any("install" in c for c in cmds)

    def test_returns_list(self, plugin: PythonPlugin) -> None:
        cmds = plugin.get_build_commands("monolithic")
        assert isinstance(cmds, list)


class TestPythonBuildCommandsModularMonolith:
    def test_includes_install(self, plugin: PythonPlugin) -> None:
        cmds = plugin.get_build_commands("modular-monolith")
        assert any("install" in c for c in cmds)


@pytest.mark.parametrize("arch", ARCHS)
def test_build_commands_non_empty(plugin: PythonPlugin, arch: str) -> None:
    cmds = plugin.get_build_commands(arch)
    assert len(cmds) > 0


# ── Test Commands ────────────────────────────────────────────────────


class TestPythonTestCommands:
    def test_returns_list(self, plugin: PythonPlugin) -> None:
        cmds = plugin.get_test_commands()
        assert isinstance(cmds, list)
        assert all(isinstance(c, str) for c in cmds)

    def test_includes_pytest(self, plugin: PythonPlugin) -> None:
        cmds = plugin.get_test_commands()
        assert any("pytest" in c for c in cmds)

    def test_non_empty(self, plugin: PythonPlugin) -> None:
        assert len(plugin.get_test_commands()) > 0


# ── Folder Structure ─────────────────────────────────────────────────


class TestPythonFolderMicroservice:
    def test_has_services_dir(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("service" in k.lower() for k in fs)

    def test_has_deploy_dir(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("deploy" in k.lower() for k in fs)

    def test_has_shared_libs(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("microservice")
        assert any("shared" in k.lower() for k in fs)


class TestPythonFolderMonolith:
    def test_has_app_dir(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any("app" in k.lower() for k in fs)

    def test_has_models_or_services(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any(
            "model" in k.lower() or "service" in k.lower()
            for k in fs
        )

    def test_has_tests(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("monolithic")
        assert any("test" in k.lower() for k in fs)


class TestPythonFolderModularMonolith:
    def test_has_modules_dir(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("modular-monolith")
        assert any("module" in k.lower() for k in fs)

    def test_has_shared_kernel(self, plugin: PythonPlugin) -> None:
        fs = plugin.get_folder_structure("modular-monolith")
        assert any("shared" in k.lower() for k in fs)


@pytest.mark.parametrize("arch", ARCHS)
def test_folder_structure_returns_dict(
    plugin: PythonPlugin, arch: str,
) -> None:
    fs = plugin.get_folder_structure(arch)
    assert isinstance(fs, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in fs.items())


@pytest.mark.parametrize("arch", ARCHS)
def test_folder_structure_non_empty(
    plugin: PythonPlugin, arch: str,
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
    plugin: PythonPlugin, arch_a: str, arch_b: str,
) -> None:
    assert plugin.get_folder_structure(arch_a) != plugin.get_folder_structure(arch_b)
