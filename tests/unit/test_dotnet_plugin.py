"""Unit tests for DotnetPlugin — .NET stack plugin."""

from __future__ import annotations

import re

from specforge.plugins.stack_plugin_base import DockerConfig, PluginRule
from specforge.plugins.stacks.dotnet_plugin import DotnetPlugin


def _all_rules_flat(rules: dict[str, list[PluginRule]]) -> list[PluginRule]:
    """Flatten domain-keyed rules into a single list."""
    return [r for domain_rules in rules.values() for r in domain_rules]


def _assert_all_rules_valid(rules: dict[str, list[PluginRule]]) -> None:
    """Assert every rule has valid severity, non-empty fields, valid ID."""
    pattern = re.compile(r"^[A-Z]+-[A-Z0-9-]+$")
    for _domain, domain_rules in rules.items():
        for rule in domain_rules:
            assert isinstance(rule, PluginRule)
            assert pattern.match(rule.rule_id), f"Bad rule_id: {rule.rule_id}"
            assert rule.severity in {"ERROR", "WARNING"}
            assert rule.title.strip()
            assert rule.scope.strip()
            assert rule.description.strip()
            assert rule.example_correct.strip()
            assert rule.example_incorrect.strip()


class TestDotnetPluginMetadata:
    def test_plugin_name(self) -> None:
        plugin = DotnetPlugin()
        assert plugin.plugin_name == "dotnet"

    def test_description_non_empty(self) -> None:
        plugin = DotnetPlugin()
        assert plugin.description
        assert plugin.description.strip()

    def test_supported_architectures_all_three(self) -> None:
        plugin = DotnetPlugin()
        archs = plugin.supported_architectures
        assert "microservice" in archs
        assert "monolithic" in archs
        assert "modular-monolith" in archs


class TestDotnetMicroserviceRules:
    def setup_method(self) -> None:
        self.rules = DotnetPlugin().get_prompt_rules("microservice")
        self.flat = _all_rules_flat(self.rules)

    def test_returns_backend_domain(self) -> None:
        assert "backend" in self.rules

    def test_backend_rules_non_empty(self) -> None:
        assert len(self.rules["backend"]) > 0

    def test_contains_per_service_dbcontext(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("dbcontext" in t for t in texts)

    def test_contains_container_build(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "docker" in t or "container" in t or "multi-stage" in t
            for t in texts
        )

    def test_contains_grpc_proto(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("grpc" in t or "proto" in t for t in texts)

    def test_contains_masstransit_events(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any(
            "masstransit" in t or "event handler" in t or "event bus" in t
            for t in texts
        )

    def test_returns_database_domain(self) -> None:
        assert "database" in self.rules

    def test_returns_cicd_domain(self) -> None:
        assert "cicd" in self.rules

    def test_all_rules_valid(self) -> None:
        _assert_all_rules_valid(self.rules)


class TestDotnetMonolithRules:
    def setup_method(self) -> None:
        self.rules = DotnetPlugin().get_prompt_rules("monolithic")
        self.flat = _all_rules_flat(self.rules)

    def test_returns_backend_domain(self) -> None:
        assert "backend" in self.rules

    def test_contains_single_dbcontext(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("dbcontext" in t for t in texts)

    def test_contains_mediatr(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert any("mediatr" in t or "mediator" in t for t in texts)

    def test_no_container_rules(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert not any(
            "docker" in t or "container" in t or "multi-stage" in t
            for t in texts
        )

    def test_no_grpc_rules(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert not any("grpc" in t or "proto" in t for t in texts)

    def test_no_event_bus_rules(self) -> None:
        texts = [r.description.lower() + r.title.lower() for r in self.flat]
        assert not any(
            "masstransit" in t or "event bus" in t for t in texts
        )

    def test_all_rules_valid(self) -> None:
        _assert_all_rules_valid(self.rules)


class TestDotnetModularMonolithRules:
    def setup_method(self) -> None:
        self.rules = DotnetPlugin().get_prompt_rules("modular-monolith")
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


class TestDotnetDockerConfig:
    def test_microservice_returns_docker_config(self) -> None:
        dc = DotnetPlugin().get_docker_config("microservice")
        assert isinstance(dc, DockerConfig)
        assert (
            "dotnet" in dc.base_image.lower()
            or "mcr.microsoft.com" in dc.base_image
        )

    def test_monolith_returns_none(self) -> None:
        assert DotnetPlugin().get_docker_config("monolithic") is None

    def test_modular_monolith_returns_none(self) -> None:
        assert DotnetPlugin().get_docker_config("modular-monolith") is None


class TestDotnetBuildCommands:
    def test_microservice_includes_publish(self) -> None:
        cmds = DotnetPlugin().get_build_commands("microservice")
        assert any("publish" in c for c in cmds)

    def test_monolith_includes_build(self) -> None:
        cmds = DotnetPlugin().get_build_commands("monolithic")
        assert any("build" in c for c in cmds)


class TestDotnetTestCommands:
    def test_includes_dotnet_test(self) -> None:
        assert "dotnet test" in DotnetPlugin().get_test_commands()


class TestDotnetFolderStructure:
    def test_microservice_has_services_dir(self) -> None:
        fs = DotnetPlugin().get_folder_structure("microservice")
        assert any("service" in k.lower() for k in fs)

    def test_monolith_has_single_project(self) -> None:
        fs = DotnetPlugin().get_folder_structure("monolithic")
        assert len(fs) > 0
