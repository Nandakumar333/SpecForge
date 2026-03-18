"""Unit tests for PythonPlugin — Python stack plugin."""

from __future__ import annotations

import re

from specforge.plugins.stack_plugin_base import DockerConfig, PluginRule
from specforge.plugins.stacks.python_plugin import PythonPlugin


def _all_rules_flat(rules: dict[str, list[PluginRule]]) -> list[PluginRule]:
    """Flatten domain-keyed rules into a single list."""
    return [r for domain_rules in rules.values() for r in domain_rules]


def _assert_all_rules_valid(rules: dict[str, list[PluginRule]]) -> None:
    """Assert every rule has valid severity, non-empty fields, valid ID."""
    pattern = re.compile(r"^[A-Z]+-[A-Z0-9-]+$")
    for domain, domain_rules in rules.items():
        for rule in domain_rules:
            assert isinstance(rule, PluginRule)
            assert pattern.match(rule.rule_id), f"Bad rule_id: {rule.rule_id}"
            assert rule.severity in {"ERROR", "WARNING"}
            assert rule.title.strip()
            assert rule.scope.strip()
            assert rule.description.strip()
            assert rule.example_correct.strip()
            assert rule.example_incorrect.strip()


class TestPythonPluginMetadata:
    def test_plugin_name(self) -> None:
        plugin = PythonPlugin()
        assert plugin.plugin_name == "python"

    def test_description_non_empty(self) -> None:
        plugin = PythonPlugin()
        assert plugin.description
        assert plugin.description.strip()

    def test_supported_architectures_all_three(self) -> None:
        plugin = PythonPlugin()
        archs = plugin.supported_architectures
        assert "microservice" in archs
        assert "monolithic" in archs
        assert "modular-monolith" in archs


class TestPythonMicroserviceRules:
    def setup_method(self) -> None:
        self.rules = PythonPlugin().get_prompt_rules("microservice")
        self.flat = _all_rules_flat(self.rules)

    def test_returns_backend_domain(self) -> None:
        assert "backend" in self.rules

    def test_backend_rules_non_empty(self) -> None:
        assert len(self.rules["backend"]) > 0

    def test_contains_fastapi_per_service(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("fastapi" in t for t in texts)

    def test_contains_container_build(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "docker" in t or "container" in t or "multi-stage" in t
            for t in texts
        )

    def test_contains_sqlalchemy_per_service(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("sqlalchemy" in t for t in texts)

    def test_contains_celery_or_dramatiq(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "celery" in t or "dramatiq" in t or "task queue" in t
            for t in texts
        )

    def test_returns_database_domain(self) -> None:
        assert "database" in self.rules

    def test_returns_cicd_domain(self) -> None:
        assert "cicd" in self.rules

    def test_all_rules_valid(self) -> None:
        _assert_all_rules_valid(self.rules)


class TestPythonMonolithRules:
    def setup_method(self) -> None:
        self.rules = PythonPlugin().get_prompt_rules("monolithic")
        self.flat = _all_rules_flat(self.rules)

    def test_returns_backend_domain(self) -> None:
        assert "backend" in self.rules

    def test_contains_single_app(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("single" in t or "monolith" in t for t in texts)

    def test_contains_shared_models(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "shared" in t or "model" in t or "sqlalchemy" in t
            for t in texts
        )

    def test_no_container_rules(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert not any(
            "docker" in t or "container" in t or "multi-stage" in t
            for t in texts
        )

    def test_no_event_bus_rules(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert not any(
            "celery" in t or "dramatiq" in t or "task queue" in t
            for t in texts
        )

    def test_all_rules_valid(self) -> None:
        _assert_all_rules_valid(self.rules)


class TestPythonModularMonolithRules:
    def setup_method(self) -> None:
        self.rules = PythonPlugin().get_prompt_rules("modular-monolith")
        self.flat = _all_rules_flat(self.rules)

    def test_returns_backend_domain(self) -> None:
        assert "backend" in self.rules

    def test_contains_boundary_enforcement(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "module boundary" in t or "interface contract" in t
            for t in texts
        )

    def test_no_container_rules(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert not any(
            "docker" in t or "container" in t or "multi-stage" in t
            for t in texts
        )

    def test_all_rules_valid(self) -> None:
        _assert_all_rules_valid(self.rules)


class TestPythonDockerConfig:
    def test_microservice_returns_docker_config(self) -> None:
        dc = PythonPlugin().get_docker_config("microservice")
        assert isinstance(dc, DockerConfig)
        assert "python" in dc.base_image.lower()

    def test_monolith_returns_none(self) -> None:
        assert PythonPlugin().get_docker_config("monolithic") is None

    def test_modular_monolith_returns_none(self) -> None:
        assert PythonPlugin().get_docker_config("modular-monolith") is None


class TestPythonBuildCommands:
    def test_microservice_includes_install(self) -> None:
        cmds = PythonPlugin().get_build_commands("microservice")
        assert any("install" in c for c in cmds)

    def test_monolith_includes_install(self) -> None:
        cmds = PythonPlugin().get_build_commands("monolithic")
        assert any("install" in c for c in cmds)


class TestPythonTestCommands:
    def test_includes_pytest(self) -> None:
        assert "pytest" in PythonPlugin().get_test_commands()


class TestPythonFolderStructure:
    def test_microservice_has_services_dir(self) -> None:
        fs = PythonPlugin().get_folder_structure("microservice")
        assert any("service" in k.lower() for k in fs)

    def test_monolith_has_src_dir(self) -> None:
        fs = PythonPlugin().get_folder_structure("monolithic")
        assert len(fs) > 0
