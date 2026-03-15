"""Unit tests for TemplateRegistry — discovery, resolution, overrides, variants."""

from __future__ import annotations

from pathlib import Path

from specforge.core.template_models import TemplateSource, TemplateType
from specforge.core.template_registry import TemplateRegistry


class TestBuiltInDiscovery:
    def test_discover_returns_ok_with_count(self) -> None:
        registry = TemplateRegistry()
        result = registry.discover()
        assert result.ok
        assert result.value > 0

    def test_all_prompt_templates_found(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        prompts = registry.list(TemplateType.prompt)
        names = {t.logical_name for t in prompts if t.stack is None}
        expected = {
            "backend",
            "frontend",
            "database",
            "security",
            "testing",
            "cicd",
            "api-design",
        }
        assert expected == names

    def test_all_feature_templates_found(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        features = registry.list(TemplateType.feature)
        names = {t.logical_name for t in features}
        expected = {
            "spec",
            "research",
            "datamodel",
            "plan",
            "checklist",
            "edge-cases",
            "tasks",
        }
        assert expected == names

    def test_constitution_found(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        result = registry.get("constitution", TemplateType.constitution)
        assert result.ok

    def test_base_templates_excluded_from_list(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        all_templates = registry.list()
        for t in all_templates:
            assert not t.is_base

    def test_stack_variants_discovered(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        prompts = registry.list(TemplateType.prompt)
        variants = [t for t in prompts if t.stack is not None]
        assert len(variants) >= 3  # dotnet, nodejs, python


# ── User Override Tests (US2 — T020) ────────────────────────────────


class TestUserOverrides:
    def test_user_override_wins_over_built_in(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".specforge" / "templates"
        user_dir.mkdir(parents=True)
        custom = user_dir / "constitution.md.j2"
        custom.write_text("# Custom Constitution\n", encoding="utf-8")

        registry = TemplateRegistry(tmp_path)
        registry.discover()
        result = registry.get("constitution", TemplateType.constitution)
        assert result.ok
        assert result.value.source == TemplateSource.user_override

    def test_missing_override_falls_back(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".specforge" / "templates"
        user_dir.mkdir(parents=True)
        # No custom constitution
        registry = TemplateRegistry(tmp_path)
        registry.discover()
        result = registry.get("constitution", TemplateType.constitution)
        assert result.ok
        assert result.value.source == TemplateSource.built_in

    def test_user_prompt_override(self, tmp_path: Path) -> None:
        prompts_dir = tmp_path / ".specforge" / "templates" / "prompts"
        prompts_dir.mkdir(parents=True)
        custom = prompts_dir / "backend.md.j2"
        custom.write_text("# Custom Backend\n", encoding="utf-8")

        registry = TemplateRegistry(tmp_path)
        registry.discover()
        result = registry.get("backend", TemplateType.prompt)
        assert result.ok
        assert result.value.source == TemplateSource.user_override

    def test_no_user_dir_is_fine(self) -> None:
        registry = TemplateRegistry(Path("/nonexistent"))
        result = registry.discover()
        assert result.ok


# ── Stack Variant Resolution Tests (US3 — T025) ─────────────────────


class TestStackVariantResolution:
    def test_dotnet_variant_returned(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        result = registry.get("backend", TemplateType.prompt, stack="dotnet")
        assert result.ok
        assert result.value.stack == "dotnet"

    def test_unknown_stack_falls_back_to_generic(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        result = registry.get("backend", TemplateType.prompt, stack="ruby")
        assert result.ok
        assert result.value.stack is None

    def test_user_override_variant_wins(self, tmp_path: Path) -> None:
        prompts_dir = tmp_path / ".specforge" / "templates" / "prompts"
        prompts_dir.mkdir(parents=True)
        custom = prompts_dir / "backend.dotnet.md.j2"
        custom.write_text("# Custom .NET Backend\n", encoding="utf-8")

        registry = TemplateRegistry(tmp_path)
        registry.discover()
        result = registry.get("backend", TemplateType.prompt, stack="dotnet")
        assert result.ok
        assert result.value.source == TemplateSource.user_override
        assert result.value.stack == "dotnet"

    def test_dot_notation_parsing(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        prompts = registry.list(TemplateType.prompt)
        dotnet = [t for t in prompts if t.stack == "dotnet"]
        assert len(dotnet) >= 1
        assert dotnet[0].logical_name == "backend"


# ── List and Has Tests (US4 — T030) ─────────────────────────────────


class TestListAndHas:
    def test_list_all(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        all_templates = registry.list()
        assert len(all_templates) >= 18  # 1 const + 7 prompts + 3 variants + 7 features

    def test_list_by_type(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        prompts = registry.list(TemplateType.prompt)
        for t in prompts:
            assert t.template_type == TemplateType.prompt

    def test_has_existing(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        assert registry.has("backend", TemplateType.prompt)

    def test_has_nonexistent(self) -> None:
        registry = TemplateRegistry()
        registry.discover()
        assert not registry.has("nonexistent", TemplateType.feature)

    def test_discovery_completeness(self) -> None:
        """All 7 prompts + 7 features + 1 constitution + 3 variants."""
        registry = TemplateRegistry()
        registry.discover()
        prompts = registry.list(TemplateType.prompt)
        features = registry.list(TemplateType.feature)
        consts = registry.list(TemplateType.constitution)
        assert len(consts) == 1
        assert len(features) == 7
        # 7 generic + 3 stack variants
        assert len(prompts) == 10
