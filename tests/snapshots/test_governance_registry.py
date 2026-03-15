"""Snapshot/registry tests for governance template discovery."""

from __future__ import annotations

from specforge.core.template_models import TemplateSource, TemplateType
from specforge.core.template_registry import TemplateRegistry


class TestGovernanceRegistryDiscovery:
    def setup_method(self) -> None:
        self._registry = TemplateRegistry()
        result = self._registry.discover()
        assert result.ok, f"Discovery failed: {result}"

    def test_all_7_base_domains_discoverable(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        # Filter to built-in, non-stack-specific (stack=None), non-base entries
        base_domains = {
            t.logical_name
            for t in governance
            if t.stack is None and t.source == TemplateSource.built_in
        }
        expected = {
            "architecture",
            "backend",
            "frontend",
            "database",
            "security",
            "testing",
            "cicd",
        }
        assert expected == base_domains

    def test_dotnet_stack_variants_present(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        dotnet_names = {
            t.logical_name
            for t in governance
            if t.stack == "dotnet" and t.source == TemplateSource.built_in
        }
        assert "backend" in dotnet_names
        assert "testing" in dotnet_names

    def test_nodejs_stack_variants_present(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        nodejs_names = {
            t.logical_name
            for t in governance
            if t.stack == "nodejs" and t.source == TemplateSource.built_in
        }
        assert "backend" in nodejs_names
        assert "testing" in nodejs_names

    def test_python_stack_variants_present(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        python_names = {
            t.logical_name
            for t in governance
            if t.stack == "python" and t.source == TemplateSource.built_in
        }
        assert "backend" in python_names
        assert "testing" in python_names

    def test_go_stack_variants_present(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        go_names = {
            t.logical_name
            for t in governance
            if t.stack == "go" and t.source == TemplateSource.built_in
        }
        assert "backend" in go_names
        assert "testing" in go_names

    def test_java_stack_variants_present(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        java_names = {
            t.logical_name
            for t in governance
            if t.stack == "java" and t.source == TemplateSource.built_in
        }
        assert "backend" in java_names
        assert "testing" in java_names

    def test_all_5_stack_variants_present(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        stacks_present = {
            t.stack
            for t in governance
            if t.stack is not None and t.source == TemplateSource.built_in
        }
        expected_stacks = {"dotnet", "nodejs", "python", "go", "java"}
        assert expected_stacks == stacks_present

    def test_governance_templates_from_base_governance_path(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        for t in governance:
            if t.source == TemplateSource.built_in:
                assert "base/governance" in t.template_path, (
                    f"Template {t.logical_name} has unexpected path: {t.template_path}"
                )

    def test_zero_governance_templates_from_non_governance_path(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        for t in governance:
            if t.source == TemplateSource.built_in:
                assert "base/prompts" not in t.template_path
                assert "base/features" not in t.template_path
                assert "base/partials" not in t.template_path

    def test_governance_type_not_in_other_directories(self) -> None:
        prompts = self._registry.list(TemplateType.prompt)
        for t in prompts:
            assert t.template_type == TemplateType.prompt

    def test_base_template_excluded_from_listing(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        names = [t.logical_name for t in governance]
        # _base_governance.md.j2 should not appear (is_base=True, excluded from list)
        assert "base_governance" not in names

    def test_governance_templates_have_correct_type(self) -> None:
        governance = self._registry.list(TemplateType.governance)
        assert len(governance) > 0
        for t in governance:
            assert t.template_type == TemplateType.governance

    def test_registry_get_architecture_agnostic(self) -> None:
        result = self._registry.get(
            "architecture", TemplateType.governance, stack="agnostic"
        )
        assert result.ok
        assert result.value.logical_name == "architecture"

    def test_registry_get_backend_dotnet(self) -> None:
        result = self._registry.get(
            "backend", TemplateType.governance, stack="dotnet"
        )
        assert result.ok
        assert result.value.logical_name == "backend"
        assert result.value.stack == "dotnet"

    def test_registry_get_backend_falls_back_to_agnostic(self) -> None:
        # frontend has no stack-specific variant — should get agnostic
        result = self._registry.get(
            "frontend", TemplateType.governance, stack="dotnet"
        )
        assert result.ok
        assert result.value.logical_name == "frontend"
        # stack on the TemplateInfo will be None (agnostic)
        assert result.value.stack is None
