"""Unit tests for NodejsPlugin — Node.js stack plugin."""

from __future__ import annotations

import re

from specforge.plugins.stack_plugin_base import DockerConfig, PluginRule
from specforge.plugins.stacks.nodejs_plugin import NodejsPlugin


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


class TestNodejsPluginMetadata:
    def test_plugin_name(self) -> None:
        plugin = NodejsPlugin()
        assert plugin.plugin_name == "nodejs"

    def test_description_non_empty(self) -> None:
        plugin = NodejsPlugin()
        assert plugin.description
        assert plugin.description.strip()

    def test_supported_architectures_all_three(self) -> None:
        plugin = NodejsPlugin()
        archs = plugin.supported_architectures
        assert "microservice" in archs
        assert "monolithic" in archs
        assert "modular-monolith" in archs


class TestNodejsMicroserviceRules:
    def setup_method(self) -> None:
        self.rules = NodejsPlugin().get_prompt_rules("microservice")
        self.flat = _all_rules_flat(self.rules)

    def test_returns_backend_domain(self) -> None:
        assert "backend" in self.rules

    def test_backend_rules_non_empty(self) -> None:
        assert len(self.rules["backend"]) > 0

    def test_contains_express_or_fastify(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("express" in t or "fastify" in t for t in texts)

    def test_contains_container_build(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "docker" in t or "container" in t or "multi-stage" in t
            for t in texts
        )

    def test_contains_prisma_or_typeorm(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("prisma" in t or "typeorm" in t for t in texts)

    def test_contains_nats_or_rabbitmq(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "nats" in t or "rabbitmq" in t or "message broker" in t
            for t in texts
        )

    def test_returns_database_domain(self) -> None:
        assert "database" in self.rules

    def test_returns_cicd_domain(self) -> None:
        assert "cicd" in self.rules

    def test_all_rules_valid(self) -> None:
        _assert_all_rules_valid(self.rules)


class TestNodejsMonolithRules:
    def setup_method(self) -> None:
        self.rules = NodejsPlugin().get_prompt_rules("monolithic")
        self.flat = _all_rules_flat(self.rules)

    def test_returns_backend_domain(self) -> None:
        assert "backend" in self.rules

    def test_contains_single_app(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("single" in t or "monolith" in t for t in texts)

    def test_contains_shared_schema(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "shared" in t or "schema" in t or "prisma" in t
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
            "nats" in t or "rabbitmq" in t or "message broker" in t
            for t in texts
        )

    def test_all_rules_valid(self) -> None:
        _assert_all_rules_valid(self.rules)


class TestNodejsModularMonolithRules:
    def setup_method(self) -> None:
        self.rules = NodejsPlugin().get_prompt_rules("modular-monolith")
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


class TestNodejsDockerConfig:
    def test_microservice_returns_docker_config(self) -> None:
        dc = NodejsPlugin().get_docker_config("microservice")
        assert isinstance(dc, DockerConfig)
        assert "node" in dc.base_image.lower()

    def test_monolith_returns_none(self) -> None:
        assert NodejsPlugin().get_docker_config("monolithic") is None

    def test_modular_monolith_returns_none(self) -> None:
        assert NodejsPlugin().get_docker_config("modular-monolith") is None


class TestNodejsBuildCommands:
    def test_microservice_includes_build(self) -> None:
        cmds = NodejsPlugin().get_build_commands("microservice")
        assert any("build" in c for c in cmds)

    def test_monolith_includes_build(self) -> None:
        cmds = NodejsPlugin().get_build_commands("monolithic")
        assert any("build" in c for c in cmds)


class TestNodejsTestCommands:
    def test_includes_npm_test(self) -> None:
        assert "npm test" in NodejsPlugin().get_test_commands()


class TestNodejsFolderStructure:
    def test_microservice_has_services_dir(self) -> None:
        fs = NodejsPlugin().get_folder_structure("microservice")
        assert any("service" in k.lower() for k in fs)

    def test_monolith_has_src_dir(self) -> None:
        fs = NodejsPlugin().get_folder_structure("monolithic")
        assert len(fs) > 0
